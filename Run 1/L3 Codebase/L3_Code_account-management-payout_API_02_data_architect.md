# account-management-payout_API — Data Architect View

## Data Stores

Three physical SQL Server databases are consumed, all wired via HikariCP connection pools configured in `accountmanagementapi-payout-war/config/server.xml`:

| JNDI Name | Environment Variable | Purpose |
|---|---|---|
| `jdbc/CbaseappDataSource` | `CBASEAPP_JDBC_URL` / `ACCOUNTMANAGEMENTPAYOUT_CBASEAPPDB_USERNAME/PASSWORD` | Primary application database (CBase/eCount platform). Holds affiliate metadata, security domains, user/member data (Hibernate ORM via `appContextFactory`). |
| `jdbc/JobSvcDataSource` | `JOBSVC_JDBC_URL` / `ACCOUNTMANAGEMENTPAYOUT_JOBSVCDB_USERNAME/PASSWORD` | Job service database. Used for order/sweep request processing and user mapping lookups (`JobManager`, `FindUserMappingRequest`). |
| `jdbc/EcountCoreDataSource` | `ECOUNT_JDBC_URL` / `ACCOUNTMANAGEMENTPAYOUT_ECOUNTDB_USERNAME/PASSWORD` | eCount Core database. Used for KYC status persistence (`KYCStatusInsertUpdateSP`), card detail inquiry (`FDRCardAccountDetailInquirySP`), and program/BIN lookups (`GetBankByProgramStoredProc`). |

Pool configuration (per `server.xml`): maxTotal=30, maxIdle=10, maxWaitMillis=30000, validationQuery="SELECT 1". The `EcountCoreDataSource` pool also sets `logAbandoned=true`, `removeAbandonedOnBorrow=true`, `removeAbandonedTimeout=300`.

---

## Schema & Tables

No DDL files are present in this repository. The schema is owned by the shared CBase/eCount platform. Tables used by this service are accessed only through stored procedures and the Hibernate ORM layer. Evidence from Spring configuration and Java class usage:

| Table / Object | Access Mechanism | Source Reference |
|---|---|---|
| `kyc_status` | Stored Proc `KYCStatusInsertUpdateSP` via `EcountCoreDataSource` | `accountmanagementapi-implContext.xml` line 238; `AMPayoutHelper.java` line 167 |
| FDR card detail (card postal / activation code) | Stored Proc `FDRCardAccountDetailInquirySP` via `EcountCoreDataSource` | `accountmanagementapi-implContext.xml` lines 192–203 |
| Program/BIN lookup | Stored Proc `GetBankByProgramStoredProc` via `EcountCoreDataSource` | `accountmanagementapi-implContext.xml` lines 180–191 |
| Affiliate metadata (kyc_required, etc.) | `ProcGetAffiliateByValue`, `ProcGetAffiliatePresentation` via `CbaseappDataSource` | `accountmanagementapi-implContext.xml` lines 222–237 |
| User/Member mapping | `JobManager.findUserMapping()` via `JobSvcDataSource` | `AccountHelper.java` — `getUserMappingForEcountID()` |
| Security API domains, users | Hibernate ORM via `CbaseappDataSource` — annotated classes including `User`, `UserPersonalInfo`, `UserEmail`, `UserAddress`, `Address`, `UserEcount`, `UserDomain`, `SimpleSecurityGroup`, `Promotion`, `LocationHierarchy` | `accountmanagementapi-implContext.xml` lines 264–290 |
| Order / Sweep requests | Processed via JMS `SynchronousOrderProcessor` (Order Service bus) — not direct DB | `AccountManagementApiServiceImpl.java` line 155 |

---

## Sensitive Data Handling

The following sensitive data fields are present in the domain model and are processed by this service:

| Field | Java Location | Handling |
|---|---|---|
| DDA / Account Number | `ServiceInput.accountNumber`, `SetPinInput`, `ActivateCardInput` | JWE-encrypted (AES-256-GCM) in transit when `jwe.encryptDDA = Y`; first 8 chars (program ID) are prepended to the JWE token (`JweDDAHelper.java` line 80). Decrypted DDA is logged in `AccountManagementHandlerImpl.java` lines 98–100. |
| Card Number | `ActivateCardInput.card_number`, WSDL request `card_number` | Transmitted as plain `xsd:string` in SOAP. Not masked in logs. |
| CVV | `ActivateCardInput.cvv` | Transmitted as plain `xsd:string`. Validator `INVALID_CVV` / `MISSING_CVV` defined in `validation.xml`. |
| PIN | `SetPinInput.new_pin`, `SetPinRequest.new_pin` | Transmitted as plain `xsd:string` in SOAP. Passed to `AccountHelper.pinset()`. Not shown to be encrypted within the SOAP body. |
| SSN | `RegistrationInput.ssn` | Wrapped in `SecureUserProfile` and placed in `ActionSecureMemo.secureValues` (serialized XML via `SecureUserProfile.toXML()`). Passed to Order Service. Field presence validated by `INVALID_SSN` bean. |
| Date of Birth | `RegistrationInput.date_of_birth` | Stored alongside SSN in `SecureUserProfile`. Format `MM/dd/yyyy`. |
| Bank Account Number (ACH) | `WithdrawACHInput.account_number` | In disabled code path (JIRA 476). Validated via `BANK_ACCOUNT_NUMBER` parameter validator. |
| Bank Routing Number | `WithdrawACHInput.routing_number` | In disabled code path. Validated via `BANK_ROUTING_NUMBER`. |
| Address / PII | `RegistrationInput` — address1–4, city, state, postal, country, homePhone, email | Passed to Order Service as `Registration` domain object. |

---

## Encryption & Protection

1. **JWE for DDA numbers**: Implemented in `JweDDAHelper.java` using `com.nimbusds:nimbus-jose-jwt:9.40`. Algorithm: `DIR` (direct encryption). Encryption method: `A256GCM`. The symmetric key is sourced from the Spring property `${jwe.secretKey}` (injected as constructor arg to `JweDDAHelper` bean — `accountmanagementapi-wsContext.xml` line 101). Key is provided as raw bytes (`secretToken.getBytes()`), which means the key strength depends entirely on the property value length and encoding.

2. **JWE for general payloads** (`JWEHelper.java`): A separate, more complex JWE implementation is present in `accountmanagementapi-payout-impl/src/main/java/.../helper/JWEHelper.java`. This class implements AES-256-GCM wrap using BouncyCastle (`bcprov-jdk15on`). It uses `SecureRandom.getInstance("SHA1PRNG")` for IV/key generation and SHA-256 hashing of the shared secret as the KEK. This is the Visa-originated implementation (copyright header present). It is used by `CreateAccountHelper` (for Visa JWE) which is in the currently disabled code path.

3. **Token expiry**: JWE DDA tokens contain a millisecond timestamp (`TIME` key). `JweDDAHelper.decryptDDA()` enforces token age against `jwe.expirationTime` (configured in `accountmanagementapi.properties`).

4. **SSL/TLS**: The Tomcat `server.xml` exposes only port 80 (HTTP). The SSL/TLS connector stanzas are commented out. TLS must be handled upstream (load balancer / ingress). Internal communication is HTTP.

5. **QA certificate import**: The Dockerfile line 21 imports a QA certificate (`certfile_qa.crt`) into the JVM truststore using the default keystore password `changeit`. This is appropriate for QA but must not propagate to production images.

6. **BouncyCastle**: `org.bouncycastle:bcprov-jdk15on` is a direct dependency in `accountmanagementapi-payout-impl/pom.xml`. Note the artifact `jdk15on` is the legacy BouncyCastle provider; the current recommended artifact is `bcprov-jdk18on`.

---

## Data Flow

```
Mobile App
    |
    | SOAP/HTTP (port 80 via Tomcat, TLS terminated upstream)
    v
AxisServlet / AccountManagementApiWebServiceImpl
    |
    | Spring AOP proxy (GlobalRequestIDInterceptor, AuditMethodInterceptor)
    v
AccountManagementHandlerImpl
    |
    |-- JweDDAHelper: decrypt DDA (Nimbus JWE, key from config)
    |-- Validator chain (Spring XML-configured IValidator beans)
    |
    |-- ActivationStatusInquiry:
    |     |-- FDRCardAccountDetailInquiryDAO -> EcountCoreDataSource (SP)
    |     |-- AccountHelper.getActivationStatus() -> eCore/eDevice RPC
    |     |-- AffiliateServiceImpl -> CbaseappDataSource (SP)
    |     |-- KYC.invokeKYCPortal() -> External KYC HTTPS endpoint (MS Auth)
    |     |-- AMPayoutHelper.updateKycStatus() -> KYCStatusInsertUpdateSP -> EcountCoreDataSource
    |     |-- JweDDAHelper: encrypt DDA for response
    |
    |-- ActivateCard:
    |     |-- FDRCardAccountDetailInquiryDAO -> EcountCoreDataSource (SP)
    |     |-- AccountHelper.updateCardStatus() -> eCore/eDevice RPC
    |
    |-- SetPin:
          |-- AccountHelper.getUserMappingForEcountID() -> JobSvcDataSource
          |-- AccountHelper.pinset() -> FDR RPC (ECount.System.RPC)
```

---

## Data Quality & Retention

1. **No schema versioning or migration scripts** are present in this repository. Schema lifecycle is managed entirely by the shared CBase platform team.
2. **KYC status records** are inserted into `kyc_status` table on every `activationStatusInquiry` call for KYC-required programs. There is no retention/purge logic in this service. The `INSERT` action is hard-coded (`AccountManagementConstant.KYC.INSERT`, `AMPayoutHelper.java` line 160).
3. **Audit trail**: The `AuditMethodInterceptor` wraps the `accountManagementHandler` bean and collects statistics for the monitor page, but there is no indication of audit event persistence (no audit table writes observed in this codebase).
4. **Log retention**: Log4j2 configuration is externally sourced from `${CBASE_HOME_URL}/config/accountmanagementapi/log4j2-payout.xml` with a 5-minute refresh interval. Log content includes encrypted DDA strings and IP addresses. Retention policy is not defined in this repo.
5. **Input validation completeness**: Validators enforce string lengths and allowed character sets (via `ParameterValidatorType` enum). Date formats are enforced at the handler level. However, no server-side input sanitization against injection is observable in the Spring XML validator chain.

---

## Compliance Gaps

1. **PCI DSS Req 3.4 — PAN not masked in logs**: `AccountManagementHandlerImpl.java` lines 98 and 100 log the encrypted DDA (which contains a 8-digit clear-text prefix) and the fully decrypted DDA number. If logs are shipped or accessible, this exposes account-equivalent data.
2. **PCI DSS Req 3.2 — CVV/PIN in SOAP payload**: CVV and PIN are transported as unencrypted SOAP string elements. While TLS is expected at the network boundary, within the service boundary these values traverse in memory without per-field encryption.
3. **PCI DSS Req 6.2 — Trivy / CVE allowlist**: `.trivyignore` suppresses 7 CVEs including `CVE-2024-50379` (Tomcat partial PUT) and `CVE-2024-52316` (Tomcat HTTP/2). These CVEs should be reviewed against the actual Tomcat version (10.1.28 per Dockerfile).
4. **GLBA / data minimization**: SSN and DOB are collected in `RegistrationInput` and passed downstream. There is no evidence of field-level access controls or data masking for these fields when accessed via logs or diagnostic endpoints.
5. **No data classification labels** in code or schema. Fields carrying PII (name, address, DOB, SSN) and CHD (card number, CVV, PIN, account number) are not annotated or tagged to support automated data discovery.
6. **External KYC service credential management**: KYC Microsoft MSAL credentials (`kyc.ms.client.secret`) are stored in an external properties file (`accountmanagementapi.properties`) sourced from `${CBASE_HOME_URL}`. There is no evidence of secret rotation or vault integration in this repository.
