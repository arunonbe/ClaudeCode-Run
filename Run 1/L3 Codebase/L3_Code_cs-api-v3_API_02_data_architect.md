# Data Architect View — cs-api-v3_API

## Data Stores
| Store | Connection | Purpose | Technology |
|---|---|---|---|
| CbaseappDataSource | Azure App Config → HikariCP | Affiliate metadata, Hibernate ORM for AffiliateService, CommentService DAOs | SQL Server |
| JobSvcDataSource | Azure App Config → HikariCP | PUID lookup, job account map queries | SQL Server |
| EcountCoreDataSource | Azure App Config → HikariCP | Transaction data, card device data via REST | SQL Server (accessed via ecount-core-rest-api) |
| ecount-core-rest-api | `ecountcore.urls.base-url` | MemberService, DeviceService HTTP REST client | HTTP (TLS) to ecount-core service |
| Redis (international programs) | `redis.cacheservice.url` | International program lookup per affiliateID | HTTP GET to Redis cache service |
| CMS (Content Management Service) | `cms.service.url` / `cms.service.inet.url` | Payout app content URLs | HTTPS (northlane.com domain) |
| Azure App Configuration | `AZURE_APP_CONFIG_ENDPOINT` | All runtime configuration, JDBC URLs, credentials | Azure PaaS |
| Azure Key Vault | Managed Identity | Secrets referenced from App Config | Azure PaaS |

## Datasource Credential Handling
All datasource credentials (`url`, `username`, `password`) are set to placeholder values in `application.yml`:
```
url: url-from-app-config
username: username-from-app-config
password: password-from-app-config
```
Actual values are injected at runtime from Azure App Config, which in non-local environments is accessed via Managed Identity (no secret in code). This is the correct pattern for PCI DSS Requirement 8 / credential management.

**Exception — JWE keys in committed properties file**: `applicationContext-CSWS.properties` (committed to the repository) contains `jwe.secretKey` and `jwe.secretToken` in plaintext. These are used to encrypt DDA numbers. This is a critical finding: encryption keys must not be committed to version control. They must be moved to Azure Key Vault and referenced via App Config.

## Schema

### AccountProfile (input to updateAccount)
```
application_id  String (resolved via AffiliateService)
program_id      String (alternative identifier path, KYC gated)
puid            String (required, max 50)
address_1       String (max 26)
address_2       String (max 26, optional)
city            String (max 18)
state           String (max 2 domestic, max 3 international)
postal          String (max 10 domestic, max 12 international)
country         String (max 2)
home_email      String (max 50)
home_phone      String (max 16)
mobile_phone    String (max 16, optional)
business_phone  String (max 16, optional)
first_name      String (max 25)
last_name       String (max 25)
middle_name     String (max 25, optional)
suffix_name     String (max 25, optional)
```

### AccountInquiry (response from searchAccount)
```
Balance:            balance_available, balance_ledger, balance_pending, balance_date
CardDetail:         card_number (masked: first4+XXXXXXXX+last4), puid, program_id,
                    created_date, last_plastic_date, expiration, account_status, ship_date (V3 addition)
TransactionDetail[]: transaction_date, amount, fee, type, details (merchant name or XXXX)
PaymentDetail[]:    PPD promotion data per transaction (V3 addition)
CommentHistory[]:   historical CS comments (V3 addition, last 12 months)
Registration:       address, name, phone, email fields
Response:           code (int), message (String)
```

### Response (all operations)
```
code    int (0 = success; 34001/34002/34003+ = inquiry errors; 35001+ = update errors; 36010 = access denied)
message String
```

### Payout Sub-Service Value Objects
```
AuthenticationRequest:     application_id, card_number, puid, ddaNumber (JWE-encrypted)
RegistrationRequest:       application_id, card_number, puid, username, password, email, phone
UpdatePasswordRequest:     application_id, card_number, puid, currentPassword, newPassword
ForgotUserNameRequest:     application_id, card_number, puid, email
UpdateRegistrationRequest: application_id, card_number, puid, address, name, phone, email
```

## Sensitive Data — Locations (Values NOT Reproduced)
| Data Type | Location | Risk |
|---|---|---|
| JWE secretKey | applicationContext-CSWS.properties (committed) | Encryption key for DDA numbers — committed to repo; critical PCI DSS / key management violation |
| JWE secretToken | applicationContext-CSWS.properties (committed) | JWE token signing key — same as above |
| CMS internal URL | applicationContext-CSWS.properties (committed) | Internal hostname (ppnaut.nam.wirecard.sys) — legacy domain exposure |
| ecount-core base URL | applicationContext-CSWS.properties | UAT endpoint with internal hostname/port — should be environment-specific |
| JDBC credentials | application.yml → Azure App Config | Properly externalised (placeholder pattern) |
| Azure App Config endpoint | AZURE_APP_CONFIG_ENDPOINT env var | Properly externalised |
| api.application.id | applicationContext-CSWS.properties | Internal application ID value |

## Encryption
- **At rest**: JDBC credentials managed by Azure App Config + Key Vault. No application-level encryption of data at rest.
- **In transit DDA**: JWE encryption using HMAC-SHA256 / AES. Secret key material committed to repository — must be rotated immediately.
- **Card masking**: First 4 + XXXXXXXX + last 4 (consistent 16-char representation). Stronger than V1/V2.
- **Transport**: HTTPS assumed at container/load balancer level; ecount-core-rest-api calls use HTTPS (UAT URL confirms TLS).

## Data Flow — searchAccount
```
SOAP Client
    │ HTTPS SOAP (Axis + Spring Boot embedded container)
    ▼
AccountManagementJaxRPC
    │
    ├── AffiliateService (CbaseappDataSource / Hibernate) — affiliate lookup + flags
    │
    ├── MemberService (ecount-core-rest-api HTTP) — member/DDA search
    │
    ├── DeviceService (ecount-core-rest-api HTTP) — card device inquiry
    │     └── deviceService.inquiryEcardResilient() for FiservDR programs
    │
    ├── ICommentService (CbaseappDataSource) — comment history retrieval
    │
    └── PPDPromotionXref (CbaseappDataSource) — PPD promotion data per transaction
    │
    ▼
AccountInquiry response (masked card, PPD, comments, balance)
```

## Data Flow — updateAccount
```
SOAP Client
    │ HTTPS SOAP
    ▼
AccountManagementJaxRPC
    │
    ├── AffiliateService — translate application_id, check flags (cs_api_enabled, cs_api_v3, kyc_required)
    │
    ├── Redis HTTP — GET programSetup/{affiliateID}/intlProgram (international program check)
    │
    ├── MemberService — PUID → memberId lookup
    │
    ├── MemberService — current registration inquiry
    │
    ├── MemberService.update() — write updated registration
    │
    └── ICommentService.addComment() — write audit comment if address changed
    │
    ▼
Response (int code)
```

## Data Quality
- **Start date default**: `new Date(0)` (epoch) used as default when start_date=0 — explicit default prevents undefined behaviour (improvement over V2).
- **DDA-only account path**: When member has ecount_id (DDA account), `memberService.inquiryDdaOnly()` is called — dual path for card + DDA accounts.
- **International postal/state**: 3-char state, 12-char postal for international countries; validated against Redis-backed country/state lists.
- **Restricted email suffix**: Runtime-configurable list of blocked email domain suffixes; OFAC-aligned.

## Compliance Gaps
1. **JWE keys in source control**: `jwe.secretKey` and `jwe.secretToken` committed to repository — PCI DSS Requirement 3.5 (protect cryptographic keys) and Requirement 6.3 (secure development). Keys must be rotated and placed in Azure Key Vault.
2. **Internal hostnames in committed config**: Legacy wirecard.sys and northlane.com URLs in committed properties file — information disclosure risk.
3. **applicationContext-CSWS.properties in repository root**: This file appears to be a QA/staging config artifact committed to the repository; production values must not be committed. Azure App Config should be the sole source.
4. **Comment service failure tolerance**: Address change auditing can silently fail if comment service is degraded — audit gap under partial failure conditions.
