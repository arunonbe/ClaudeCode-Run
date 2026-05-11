# contact-center-agent-api — Data Architect View

## Data Stores

| Store | Type | Driver / Protocol | Purpose |
|---|---|---|---|
| **cbaseapp** | Microsoft SQL Server | `mssql-jdbc 12.10.2`, JDBC, TLSv1.2 | Cardholder service records (comments), affiliate/program metadata, API audit log |
| **ecountCore** | Microsoft SQL Server | `mssql-jdbc 12.10.2`, JDBC, TLSv1.2 | Card emboss history, ship status, profile labels, card master data |
| **ECount Core REST API** | HTTP/REST | Spring `RestClient` | Real-time account, balance, transaction, member, device operations |
| **OTP Shared Service** | HTTP/REST (Dapr sidecar) | Spring `RestClient` | OTP generation and validation |
| **Azure App Configuration** | Azure PaaS | `spring-cloud-azure-appconfiguration-config` | Externalised runtime properties per environment (qa/staging/prod) |
| **Azure Key Vault** | Azure PaaS | `spring-cloud-azure-starter-keyvault-secrets` | Secrets: DB credentials, AES key/IV, JWT secret |
| **JVM In-Process Cache** | `ConcurrentMapCacheManager` | Spring Cache | `appProfileLabelTypes` — currency label type lookup from ECount DB |

---

## Schema & Tables

### cbaseapp Database

#### `api_request_audit_log` (DDL: `db/mssql/request_audit_log_ddl.sql`)
| Column | Type | Notes |
|---|---|---|
| `id` | UNIQUEIDENTIFIER PK | Auto-generated via `NEWID()` |
| `request_url` | NVARCHAR(255) | URI path |
| `request_headers` | NVARCHAR(MAX) | Filtered — only `encryptedDDA` and `channel` headers |
| `request_parameters` | NVARCHAR(MAX) | Query string parameters |
| `request_body` | NVARCHAR(MAX) | Full request body — **PII risk** (see Compliance Gaps) |
| `client_ip` | NVARCHAR(45) | Client IP (honours X-Forwarded-For) |
| `response_status` | INT | HTTP response status code |
| `created_date` | DATETIME2 | Auto-set to `GETDATE()` |

JPA entity: `ApiRequestAuditLog.java`; repository: `RequestAuditLogRepository.java`.

#### `service_records` (mapped as `ServiceRecord.java`)
| Column | Key Fields |
|---|---|
| `inquiry_id_number` (PK) | Integer |
| `application_specific_key` | Stores memberId formatted as `{GUID}` |
| `problemDescription` | Comment text — free-form |
| `dda_number` | Account DDA |
| `inquiry_type` | FK → `inquiry_types` |
| `response_type` | FK → `resolution_types` |
| `closed` | FK → `service_record_status` |
| `application_id` | Hardcoded `12` for this application |
| `origdatereceived` | Insert timestamp |

Related tables accessed via JPA joins: `InquiryType`, `InquiryTypeCategory`, `ResolutionType`, `ServiceRecordStatus`, `ServiceRecordEscalation`.

Comment insertion uses a native SQL `INSERT` query in `CommentHistoryRepository.java` (lines 181-223), writing directly to `service_records`. No stored procedure wrapper; this is a partial replacement of the `csa_bc_get_comment_history` stored procedure (noted in `CommentHistoryService.java` Javadoc line 31).

#### `b2c_csa_detailscreen_general` (mapped as `AffiliateDetailScreenGeneral.java`)
| Column | Notes |
|---|---|
| `affiliate_id` (PK) | 4-digit affiliate identifier (last-4 of 8-digit program ID) |
| `program_desc` | Human-readable program description |
| `cust_qualify_payment` | Program qualification text |
| `additional_info` | Concatenated into programInformation |
| `access_check_info` | Concatenated into programInformation |

#### `partnerdetail` (accessed via `AffiliateRepository.findReissuanceInstructionByProgramId`)
Stores per-program reissuance instructions. Accessed with a 9-digit affiliate ID prefixed with `"1"` (e.g., `04016113` → `104016113`).

### ecountCore Database

#### `core_card_account_emboss_history` (mapped as `CoreCardAccountEmbossHistory.java`)
Queried via native SQL in `EmbossHistoryRepository.getEmbossHistoryByCardIdNative`.
Key fields: `delivery_date`, `ship_date`, `tracking_number`, `emboss_vendor`, `ship_status`, `emboss_code`.

#### `core_card_account_ship_status` (mapped as `CoreCardAccountShipStatus.java`)
Ship status reference.

#### `core_profile_emboss_vendor` (mapped as `CoreProfileEmbossVendor.java`)
Vendor name resolution for emboss history.

#### `card` table (mapped as `Card.java`)
Minimal: `id` (INT PK), `card_number`. Used for emboss history joins.

#### `app_profile_promotion_label` / `app_profile_global_label`
Queried via `AppProfileRepository` to resolve program currency labels. Label type lookup is cached in `CACHE_APP_PROFILE_LABEL_TYPES` (`CacheConfig.java`).

---

## Sensitive Data Handling

| Data Element | Handling |
|---|---|
| Full PAN (card number) | Masked via `DataConversionUtils.maskCardNumber` before API response: first-4 + `XXXXXXXX` + last-4 |
| DDA (account number) | Logged masked (last-4 only) in `AuthenticationService.maskDda`; stored in `service_records.dda_number` in plain text |
| Email address | Returned masked from user-lookup (`j***e@domain.com`); stored in plain text in ECount Core |
| Phone number | Returned masked from user-lookup (last-4 only) |
| `memberId` (GUID) | Stored in `service_records.application_specific_key` as `{GUID}` |
| Encrypted DDA (`encryptedDDA` header) | Logged in `api_request_audit_log.request_headers` if audit is enabled — **encrypted value is stored but represents a risk if key is compromised** |
| Request body | Stored in `api_request_audit_log.request_body` when audit enabled — could contain `comment` text or registration PII |
| JWT token | Contains `memberId` + `ddaNumber` as unencrypted claims (only signed). DDA number is stored inside the token |
| AES secret key / IV | Sourced from Azure Key Vault (`mypaymentvaultapi-aes-secret`, `mypaymentvaultapi-aes-iv`). Config class: `EncryptionConfigProperties.java` |
| JWT secret | Sourced from Azure Key Vault (`contact-center-agent-api-jwt-secret`) |
| DB credentials | Sourced from Azure Key Vault (`managepaymentapi-cbaseappdb-*`, `managepaymentapi-ecountcoredb-*`) |

---

## Encryption & Protection

### AES/GCM DDA Decryption (`AesDecryptionService.java`)
- Algorithm: `AES/GCM/NoPadding`, 128-bit authentication tag.
- Key: bytes of secret key string from Key Vault (not padded/derived — raw bytes).
- IV: fixed bytes from Key Vault key `mypaymentvaultapi-aes-iv` — **static IV is a known AES-GCM weakness** (see Compliance Gaps).
- Used only for `CHAT` channel (`encryptedDDA` header).

### JWT (`JwtService.java`)
- Library: `io.jsonwebtoken:jjwt-api:0.12.6`.
- Algorithm: HMAC-SHA (key length determines variant — HS256/384/512 based on key byte length).
- Claims: `memberId`, `ddaNumber`, `iss=contact-center-agent-api`.
- Default expiry: 20 minutes (configurable via `jwt.expiration-minutes`).
- Secret sourced from Azure Key Vault.

### Transport Security
- All MSSQL connections use `sslProtocol=TLSv1.2` (confirmed in `app-config/prod/appsettings.json`).
- `trustServerCertificate=true` is set — this disables server certificate verification and is a security risk for production (see Compliance Gaps).
- ECount Core REST calls target `https://prod.nam.wirecard.sys:8084/service` (TLS).
- CA certificate for `nam.wirecard.sys` is injected into the JVM truststore via `Dockerfile` (`keytool` import of `nam.wirecard.sys.crt`).

---

## Data Flow

```
Decagon (External) 
  → APIM (external, contact-center-agent-east)
    → contact-center-agent-api
        ├── AuthenticationFilter: decodes token/encryptedDDA/accountNumber
        ├── RequestAuditLoggingFilter: writes to cbaseapp.api_request_audit_log
        │
        ├── AccountInquiryService
        │    ├── ECount Core REST: /device/dda/{dda}         (device/account lookup)
        │    ├── ECount Core REST: /device/inquiry/{deviceId} (balance, journal, card)
        │    ├── ECount DB (ecountcore): emboss history       (ship date)
        │    ├── cbaseapp DB: b2c_csa_detailscreen_general    (program description)
        │    ├── cbaseapp DB: partnerdetail                   (reissuance text)
        │    ├── ECount DB: app_profile_promotion_label       (currency label, cached)
        │    └── ECount Core REST: /member/basic/{memberId}   (cardholder name/email)
        │
        ├── AuthenticationService
        │    ├── ECount Core REST: /member/inquiry            (user lookup)
        │    ├── ECount Core REST: /member/extended/{id}      (contact details for OTP)
        │    ├── OTP Service (Dapr): POST /api/v1/Otp/generate
        │    ├── OTP Service (Dapr): POST /api/v1/Otp/validate
        │    ├── ECount Core REST: /member/{id}/device/dda    (get default DDA for JWT)
        │    └── JwtService: generate signed token
        │
        ├── CommentService
        │    ├── ECount Core REST: /device/dda/{dda}
        │    └── cbaseapp DB: service_records INSERT / SELECT
        │
        ├── ReissueCardService
        │    ├── ECount Core REST: /device/dda/{dda}
        │    ├── ECount Core REST: /device/catalog (eCard)
        │    └── ECount Core REST: /device/control (transfer)
        │
        ├── WithdrawFundsService
        │    ├── cbaseapp DB: partnerdetail (paper_check_flag)
        │    ├── ECount Core REST: /device/dda/{dda}
        │    └── ECount Core REST: beginTransfer + commitTransfer
        │
        └── PinResetService
             ├── ECount Core REST: /device/dda/{dda}
             ├── ECount Core REST: /device/control (pin-tries-inquiry)
             ├── ECount Core REST: /device/control (pin-tries-reset)
             └── cbaseapp DB: service_records INSERT (comment)
```

---

## Data Quality & Retention

- **Audit log retention**: No TTL, purge policy, or archival mechanism exists in this service or its DDL. The `api_request_audit_log` table will grow unbounded.
- **Comment history**: Fetched for a configurable window (`daysToFetchComments = 14` days). No retention/purge within this service.
- **Caching**: `appProfileLabelTypes` (currency label) uses default Spring `ConcurrentMapCacheManager` — in-process, no TTL, no eviction, no distributed sync across pods. Cache will be empty on each pod restart.
- **Transaction date filtering**: Supported via `transactionStartDate` / `transactionEndDate` query params, passed through to ECount Core.
- **Duplicate member deduplication**: `ECountCoreService.memberInquiry` uses a `LinkedHashMap` keyed on `memberId` to deduplicate results, keeping the last occurrence.

---

## Compliance Gaps

1. **`trustServerCertificate=true`** in JDBC connection strings for both cbaseapp and ecountCore databases (prod and qa `appsettings.json`). This disables TLS certificate validation, making the service vulnerable to MITM attacks on database connections. This is a PCI DSS requirement failure (Requirement 4.2.1 — protect PAN in transit).

2. **Static AES/GCM IV** (`AesDecryptionService.java` line 31): `new GCMParameterSpec(128, encryptionConfigProperties.ivKey().getBytes())` — the IV is derived from a fixed Key Vault value. GCM requires a unique IV per encryption to prevent key-stream reuse. If the same IV and key are used across multiple encryptions, confidentiality is broken. This is a PCI DSS cryptographic weakness.

3. **Audit log stores raw request body** (`api_request_audit_log.request_body`): When `auditing.enabled = true` (as in prod), the full request body (including comments, registration data with names/addresses) is written to the database. This is PII in a logging table with no access controls visible in this service.

4. **No audit log data retention/purge policy**: Unbounded growth of `api_request_audit_log`. PCI DSS Requirement 10.7 and GDPR Article 5(1)(e) require defined retention limits.

5. **JWT claims contain unencrypted DDA number** (`JwtService.java` lines 43-44): The `ddaNumber` claim is in the JWT payload (base64-encoded, not encrypted). Any party who can decode the token can read the DDA. The token is transmitted in the `token` header of each request. PCI DSS recommends minimising transmission of account numbers.

6. **`service_records.dda_number` stores plaintext DDA**: Written by `CommentHistoryRepository.insertComment`. This table also holds cardholder comments, making the combination a PCI DSS CDE table requiring additional controls.
