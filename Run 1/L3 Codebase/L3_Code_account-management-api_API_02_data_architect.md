# account-management-api_API — Data Architect View

## Data Stores

Three Microsoft SQL Server databases are configured as direct JDBC connections, all using `com.microsoft.sqlserver.jdbc.SQLServerDriver` (version `12.8.2.jre11`):

| Logical Name | Spring Property Root | Boot DataSource Bean | JNDI Name (legacy WAR) | Purpose |
|---|---|---|---|---|
| EcountCore | `spring.datasource.ecountcore` | `EcountCoreDataSource` | `jdbc/EcountCoreDataSource` (via JNDI fallback) | Core ecount platform data — promotions, accounts, card details, claimable flags |
| CbaseApp | `spring.datasource.cbaseapp` | `CbaseappDataSource` | `jdbc/CbaseappDataSource` | Cardholder data, affiliate/presentation profiles, CreditCard data |
| JobSvc | `spring.datasource.jobsvc` | `JobSvcDataSource` | — | Job management service, UserMapping lookups |

All three datasources are wrapped in `TransactionAwareDataSourceProxy` beans (see `CbaseAppDataSourceAutoConfiguration`, `ECountCoreDataSourceAutoConfiguration`, `JobSvcDataSourceAutoConfiguration`). Default query timeout is 600 seconds (10 minutes) for all three.

Connection credentials are externalized via Azure App Configuration (`from-app-config` placeholder in `application.yml` lines 22–33) and resolved at runtime through Azure Key Vault via Managed Identity.

## Schema & Tables

The following tables/objects are referenced directly in source code:

| Object | Type | Database | Reference Class | Purpose |
|---|---|---|---|---|
| `app_profile_global_label` | Table | EcountCore | `CheckClaimableFlagQuery` | Holds label type definitions (e.g., `claimable_choice`) |
| `app_profile_promotion_label` | Table | EcountCore | `CheckClaimableFlagQuery` | Associates label types to product/brand/affiliate — inner-joined on `id = label_type` |
| `dbo.check_promotion_belong_to_program` | Stored Procedure | EcountCore | `PromotionBelongToProgramSP` | Validates promotion ID belongs to program; returns `countValue` output param |
| `APIProcGetAffiliatePresentation` | Stored Procedure (inferred) | CbaseApp | `APIProcGetAffiliatePresentation` / `APIProcGetAffiliatePresentationValue` | Retrieves affiliate presentation data |
| FDR Card Account Detail | Stored Procedure (inferred) | EcountCore | `FDRCardAccountDetailInquirySP` / `FDRCardAccountDetailInquiryDAO` | Card activation status and detail inquiry |
| GetBankByProgram | Stored Procedure | EcountCore | `GetBankByProgramStoredProc` | Checks program existence via bank configuration |
| ManageCard | Query | EcountCore | `ManageCardDao` | Instant issue card management; used in `AccountHelper` |

SQL query literals visible in source:

- `CheckClaimableFlagQuery.SQL` (line 24): `SELECT CASE WHEN EXISTS (SELECT 1 FROM app_profile_global_label apgl INNER JOIN app_profile_promotion_label appl ON apgl.id = appl.label_type WHERE apgl.name = 'claimable_choice' AND appl.product = :product AND appl.brand = :brand AND appl.affiliate = :affiliate AND appl.label_id = 1) THEN CAST(1 AS BIT) ELSE CAST(0 AS BIT) END AS is_present`
- `PromotionBelongToProgramSP.SQL` (line 25): `dbo.check_promotion_belong_to_program`

The majority of data read/write operations flow through the **Order Service** (`SynchronousOrderProcessor`) and **Job Manager** client via remote HTTP invocation, not directly via JDBC from this service. JDBC is used only for the above lookup/validation operations and card inquiry.

## Sensitive Data Handling

| Data Element | Classification | Handling |
|---|---|---|
| CVV / CVC (`CreditCard.getCvCode()`) | SAD — PCI DSS Req 3.3 | Retrieved from cbase/CreditCard object; encrypted with AES-CBC + SHA-256 key derivation (`CardEncryptionHelper`) before placement in `CvvInquiryOutput.cvv`; transmitted to caller encrypted |
| PAN / Card Number | PCI SAD | Returned only when `Return-Card-Number` security feature is authorized; optionally wrapped in Visa JWE (AES-256-GCM via `JWEHelper`) or AES-CBC encrypted (`CardEncryptionHelper`) |
| PIN (`SetPinInput.newPin`) | SAD | Passed through to Order Service action; no encryption visible at this layer beyond transport |
| SSN (`RegistrationInput.ssn`) | PII / GLBA / CCPA | Placed inside `SecureUserProfile.toXML()` and stored as `ActionSecureMemo.secureValues`; not logged |
| Date of Birth (`RegistrationInput.date_of_birth`) | PII | Parsed and placed in `SecureUserProfile`; multi-format parsing with `SimpleDateFormat` |
| Bank Account / Routing Number | PII / NACHA | Passed through `WithdrawACHInput` to Order Service ACH device creation; no encryption visible at this layer |
| DDA Number | Account identifier | Encrypted via JWE when `jwe.encryptDDA=Y` (configured in `accountmanagementapi.yaml`); `JWEHelper.createJwe()` with key `jwe.secretKey` |
| Partner User ID / Account Number | Non-PCI identifier | Logged at INFO level in `getRequest()` — `AccountManagementApiServiceImpl` line 662 |

## Encryption & Protection

### AES-CBC (CardEncryptionHelper)
- Algorithm: `AES/CBC/PKCS5Padding`
- Key derivation: SHA-256 hash of shared secret (program-specific from `AppProgramSharedSecretProfile`)
- IV: 16 random bytes generated per operation (`SecureRandom`)
- Output: Base64-encoded (IV prefix + ciphertext)
- Used for: CVV encryption, card number encryption (when `Return-Encrypted-Card` feature authorized)

### AES-256-GCM JWE (JWEHelper)
- Algorithm: `A256GCMKW` (key wrapping) + `A256GCM` (data encryption)
- CEK: 32-byte random key
- IV: 12-byte random salt (96-bit)
- Auth tag: 128-bit
- Key source: Visa shared secret (`accountmanagementapi.security.service.visa.sharedsecret` from app config), or program shared secret for DDA encryption
- Used for: Visa JWE card number delivery (`Return-VISA-JWE` feature), DDA number encryption
- Copyright notice in `JWEHelper.java` indicates origin from Visa (2015–2016)

### DDA Encryption
- Configured via `jwe.encryptDDA=Y` in `accountmanagementapi.yaml`
- Default `jwe.secretKey` is hardcoded as `'$C&F)J@NcRfUjWnZr4u7x!A%D*G-KaPd'` in config (overridden from app config in non-local environments)
- Expiration time: `jwe.expirationTime: 180000` ms (3 minutes)

### Transport
- Azure Key Vault provides secrets at runtime (Managed Identity, `AZURE_MANAGED_IDENTITY_CLIENT_ID`)
- A Wirecard/NAM CA certificate (`nam.wirecard.sys.crt`) is imported into the JVM truststore during Docker image build (`Dockerfile` lines 25–27)

## Data Flow

```
Client (SOAP) 
  → AuthenticationCheckFilter (api-security-lib)
  → AxisServlet / Apache Axis
  → AccountManagementApiWebServiceImpl
  → AccountManagementHandlerImpl (validation, input mapping)
  → [Service class, e.g., CreateAccountService]
    → SynchronousOrderProcessor (HTTP Invoker to Order Service)
    → [EcountCore DB: promotion/claimable validation via JDBC]
    → [CbaseApp DB: affiliate presentation, card data]
    → [JobSvc DB: UserMapping resolution]
  → AccountHelper (JobManager, DeviceManager, MemberManager via ecount platform)
  → Optional: EndClientRelationshipService (HTTP POST, OAuth Bearer token)
  → Optional: RecipientScreening service (HTTP, via AccountHelper)
  → Response assembly → SOAP response
```

Redis caching is referenced (`redis.cacheservice.url: from-app-config`, `redisCacheserviceUrl` wired into `AccountManagementHandlerImpl`); however, no direct Redis client code is visible in the reviewed source — it is likely consumed via a shared library or the `redisURL` string bean.

## Data Quality & Retention

- **Date-of-birth parsing**: `RegistrationInput.parseDateOfBirth()` iterates `dobDateFormat` list with `SimpleDateFormat(format, lenient=false)`; silently ignores parse failures and returns null. No exception is surfaced to the caller.
- **Idempotency**: Transaction deduplication handled by Order Service via `transaction_id`. The service sets `processSweepRequest.setReprocess(true)` in `WithdrawService`, indicating intentional reprocessing semantics for withdraw.
- **Notification failure handling**: `EMAIL_NOTIFICATION_FAILED` is a success response code (code=0) for claim code with notification failure — data is created but delivery fails silently from a client perspective.
- **No visible data retention policy** in this codebase; retention is governed upstream in Order Service and cbase systems.

## Compliance Gaps

1. **CVV accessible in memory as plaintext**: `CreditCard.getCvCode()` returns the CVV as a String in JVM memory before encryption. If a heap dump is captured, SAD is exposed. PCI DSS Req 3.3 requires SAD not be stored after authorization.
2. **Shared secret logged**: `CvvInquiryService` line 64 logs `profile.getSharedSecret()` at DEBUG level. If DEBUG is active on `com.citi` logger (enabled per `application.yml` logging config), program shared secrets appear in logs.
3. **PIN in transit without application-layer encryption**: `SetPinInput.newPin` carries the PIN as a plain string through the service layer to Order Service. No application-layer encryption for PIN is visible in this code (transport-level TLS is assumed but not enforced in code).
4. **Hardcoded DDA secret key in source**: `jwe.secretKey` default in `accountmanagementapi.yaml` is committed to the repository. Even if overridden in production, the presence of a working default is a secret management risk.
5. **SSN transiting in XML blob**: `SecureUserProfile.toXML()` serializes SSN and DOB to XML before sending to Order Service. The XML content of this blob is not visible in this codebase; if logged by Order Service, SSN would be exposed.
6. **No explicit PAN masking in logs**: `getRequest()` logs `partner_user_id` and `program_id` but not PAN; however there is no systematic guard preventing callers from placing a PAN value in partner_user_id.
