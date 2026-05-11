# Data Architect View — cross-border-transfer-service_SVC

## 1. Data Stores

| Store | Technology | Module | Purpose |
|---|---|---|---|
| Primary RDBMS | Microsoft SQL Server (QA: `Q-LIS-DB03.nam.wirecard.sys:2231`, DB `CBTS`) | `cross-border-transfer-service-db-scripts` / persistence | All transactional data for remitters, beneficiaries, rates, transfers, recon/reject files |
| H2 (test only) | H2 in-memory | QA / batch test | Integration test database; schema defined in `schema-h2.sql` |
| Spring Batch Meta-store | SQL Server (same instance, separate Spring Batch tables) | `db.changelog-spring-batch.xml` | Batch job execution metadata, step context, job parameters |
| EhCache 3 (in-process) | EhCache 3 (heap 200 MB) | `cross-border-transfer-service-config` | Cache for beneficiary rules; TTL 14 days; alias `getBeneficiaryRules.country-currency` (`ehcache3.xml`) |
| SFTP — Cambridge | External (Cambridge/Corpay) | `cross-border-transfer-service-batch` | Source for inbound recon/reject CSV files; target for PGP-encrypted outbound recon/reject files |
| SFTP — eCount | External (eCount) | `cross-border-transfer-service-batch` | Outbound reject file delivery to eCount systems |

## 2. Relational Schema (Liquibase-managed)

All tables reside in the `CBTS` database, owner schema `${dataSchema}`, with a separate application schema `${appSchema}` accessed via Oracle-style synonyms (for Oracle-compatible deployments; SQL Server is the active target).

### Core Tables

#### RATE
```
ID              varchar2(36)  PK
RATE_ID         varchar2(36)  UNIQUE (UDX_RATE_TX_REF_ID)
AMOUNT          number(19,5)  NOT NULL
PAYERS_CURRENCY varchar2(3)   NOT NULL
BENEFICIARIES_CURRENCY varchar2(3) NOT NULL
REQUEST_TYPE    varchar2(16)  NOT NULL
VALUE           number(19,5)  NOT NULL
PAYMENT_AMOUNT  number(19,2)
STATUS          varchar2(32)  NOT NULL  (IDX_RATE_STATUS)
GATEWAY         varchar2(32)  NOT NULL
GATEWAY_RATE_ID varchar2(128)
GATEWAY_BOOKING_ID varchar2(128)
BRAND           varchar2(256) NOT NULL
REMITTER_ID     varchar2(36)  FK→REMITTER(ID) (IDX_RATE_REMITTER)
INSERTED_AT/BY, UPDATED_AT/BY audit columns
```
Source: `db.changelog-1.0.xml`, changeSets `create-rate-table`, `create-remitter-brand`, `add-payment-amount-to-rate`.

#### REMITTER
```
ID              varchar2(36)  PK
REMITTER_ID     varchar2(36)  UNIQUE (UDX_REMITTER_ID)
FIRST_NAME      varchar2(100) NOT NULL
LAST_NAME       varchar2(100) NOT NULL
ADDRESS_ID      varchar2(36)  FK→ADDRESS(ID)
ACCOUNT_IDENTIFIER varchar2(50)
GATEWAY         varchar2(32)  NOT NULL
GATEWAY_REMITTER_ID varchar2(128)
ENABLED         boolean       NOT NULL DEFAULT 1
BRAND           varchar2(256) NOT NULL
```

#### BENEFICIARY
```
ID              varchar2(36)  PK
BENEFICIARY_ID  varchar2(36)  UNIQUE (UDX_BENEFICIARY_ID)
REMITTER_ID     varchar2(36)  FK→REMITTER(ID) (IDX_BENE_REMITTER)
FIRST_NAME      varchar2(100) NOT NULL
LAST_NAME       varchar2(100)
BANK_CURRENCY   varchar2(3)   NOT NULL
PAYMENT_METHOD  varchar2(4)   NOT NULL
ADDRESS_ID      varchar2(36)  FK→ADDRESS(ID)
PHONE_NUMBER    varchar2(100)
EMAIL           varchar2(250)
SWIFT_BIC_CODE  varchar2(12)
BANK_NAME       varchar2(50)  NOT NULL
BANK_ADDRESS_ID varchar2(36)  FK→ADDRESS(ID)
ACCOUNT_NUMBER  varchar2(50)
ROUTING_CODE    varchar2(50)
GATEWAY         varchar2(32)  NOT NULL
GATEWAY_BENEFICIARY_ID varchar2(128)
ENABLED         boolean       NOT NULL DEFAULT 1
```
Source: `db.changelog-1.0.xml`, changeSets `create-beneficiary-table`, `rename-preferred-method-beneficiary`.

#### BENEFICIARY_REGULATORY_RULE
```
BENEFICIARY_ID  varchar2(36)  PK (composite with RULE_KEY)
RULE_KEY        varchar2(93)  PK
VALUE           varchar2(93)
```
Keyed regulatory metadata per beneficiary; populated from Cambridge's template-guide API response.

#### TRANSFER
```
ID              varchar2(36)  PK
TRANSFER_ID     varchar2(36)  UNIQUE (UDX_TRANSFER_TX_REF_ID)
RATE_ID         varchar2(36)  FK→RATE(ID)
BENEFICIARY_ID  varchar2(36)  FK→BENEFICIARY(ID)
FEE_AMOUNT      number(19,5)
STATUS          varchar2(32)  NOT NULL  (IDX_TRANSFER_STATUS)
GATEWAY         varchar2(32)  NOT NULL
GATEWAY_TRANSFER_ID varchar2(128)
```

#### TRANSFER_HISTORY
```
ID              varchar2(36)  PK
TRANSFER_ID     varchar2(36)  FK→TRANSFER(ID)
STATUS          varchar2(32)  NOT NULL
```
Append-only status audit trail.

#### TRANSFER_RETURN
```
ID              varchar2(36)  PK
TRANSFER_ID     varchar2(36)  FK→TRANSFER(ID) UNIQUE
GATEWAY_BOOKING_ID varchar2(200) NOT NULL (IDX_TRANSFER_RETURN_DEAL)
WIRE_NUMBER     varchar2(22)  NOT NULL
PAYMENT_REFERENCE varchar2(250)
PAYEE           varchar2(255)
REASON          varchar2(255)
CURRENCY        varchar2(100)
AMOUNT          number(16,2)
FX_RATE         number(19,5)  NOT NULL
RETURNED_USD    number(16,2)
CLOSED          boolean       DEFAULT 0
```
Source: `db.changelog-1.0.xml` + `db.changelog-1.1.xml` + `db.changelog-1.3.xml`.

#### ADDRESS
```
ID              varchar2(36)  PK
ADDRESS_LINE1   varchar2(50)  NOT NULL
ADDRESS_LINE2   varchar2(50)
ADDRESS_LINE3   varchar2(50)
CITY            varchar2(50)  NOT NULL
PROVINCE        varchar2(50)
COUNTRY_CODE    varchar2(2)   NOT NULL
POSTAL_CODE     varchar2(30)
```
Shared by REMITTER (account-holder address) and BENEFICIARY (account-holder + bank address).

#### RECON_FILE
```
ID              varchar(255)  PK
ORDER_NUMBER    varchar(20)   UNIQUE (UDX_ORDER_NUMBER)
PAYEE_ID        varchar(250)  NOT NULL
PAYEE_NAME      varchar(250)  NOT NULL
PAYMENT_CURRENCY varchar(3)   NOT NULL
LOCAL_CURRENCY  varchar(3)    NOT NULL
PAYMENT_REF     varchar(250)  UNIQUE (UDX_PAYMENT_REF)
INTERNAL_REF    varchar(250)
RATE            number(19,5)  NOT NULL
BOOKED_PAYMENT_AMOUNT number(19,5) NOT NULL
BOOKED_PAYMENT_CURRENCY varchar(3) NOT NULL
BOOKED_SETTLEMENT_AMOUNT number(19,5) NOT NULL
BOOKED_SETTLEMENT_CURRENCY varchar(3) NOT NULL
PAYEE_AMOUNT    number(19,5)  NOT NULL
PAYEE_CURRENCY  varchar(3)    NOT NULL
SETTLEMENT_DATE timestamp(6)  NOT NULL
RECON_FILE_NAME varchar(250)
```
Source: `db.changelog-1.1.xml` + `db.changelog-1.2-reconfileupdate.xml` + `db.changelog-1.3.xml`.

## 3. Entity Relationship Summary

```
ADDRESS <──── REMITTER ────> RATE
                 │
                 └──> BENEFICIARY <──────────── TRANSFER <──── RATE
                           │                        │
                  BENEFICIARY_REGULATORY_RULE    TRANSFER_HISTORY
                                                 TRANSFER_RETURN
RECON_FILE (standalone, linked by ORDER_NUMBER/PAYMENT_REF to Cambridge deal)
```

## 4. Sensitive Data Inventory

| Field | Table | Classification | Current Protection |
|---|---|---|---|
| `FIRST_NAME`, `LAST_NAME` | REMITTER, BENEFICIARY | PII (GLBA, GDPR) | Plaintext |
| `ACCOUNT_IDENTIFIER` | REMITTER | PII — bank/card account reference | Plaintext |
| `ACCOUNT_NUMBER` | BENEFICIARY | PII — bank account number | Plaintext |
| `ROUTING_CODE` | BENEFICIARY | PII — bank routing/sort code | Plaintext |
| `SWIFT_BIC_CODE` | BENEFICIARY | Financial data | Plaintext |
| `EMAIL`, `PHONE_NUMBER` | BENEFICIARY | PII | Plaintext |
| `ADDRESS_LINE1-3`, `CITY`, `PROVINCE`, `POSTAL_CODE` | ADDRESS | PII | Plaintext |
| `PAYEE_NAME`, `PAYEE_ID` | RECON_FILE | PII | Plaintext |
| `VALUE` (regulatory map) | BENEFICIARY_REGULATORY_RULE | May include tax IDs, passport numbers (country-dependent) | Plaintext |

No column-level encryption, tokenization, or masking is applied to any of these fields in the current schema. Cambridge API credentials (signatures, IDs, settlement account IDs) are stored in application YAML configuration files checked into Git — not in a secrets manager.

## 5. Encryption and Key Management

### File Encryption (PGP)
- Outbound files to Cambridge SFTP are PGP-encrypted using BouncyCastle (`PGPUtils.java`, `PGPEncryptionTasklet.java`).
- Public key: `cross-border-transfer-service-config/src/main/resources/pgp/0x6392B27D-pub.asc` — committed to source control.
- **Secret key**: `cross-border-transfer-service-config/src/main/resources/pgp/0x6392B27D-sec.asc` — **committed to source control** (critical risk).
- eCount public key: `sftp/ecount/id_ecount_rsa.pub` — also committed.
- PGP algorithm: BouncyCastle RSA/AES; integrity-checked (`pbe.verify()`), `PGPUtils.java` line 127.

### Transport Encryption
- Cambridge Feign client connects to `https://crossborder.beta.corpay.com` — TLS in transit.
- SFTP connections use SSH (key or password auth via `CambridgeSftpConfig`).
- Database TLS: optional (`tlsEnabled` flag in `DataSourceConfiguration.java`); disabled (`tlsEnabled: false`) in QA config (`application-qa.yml`, line 49).

### Authentication to Cambridge
- Two-step JWT-based token: partner-level JWT (HMAC-SHA256, 5-minute expiry) → client-level OAuth2 access token.
- `JwtTokenCreatorImpl.java` line 19: `Algorithm.HMAC256(signatureKey)` where `signatureKey` is the client signature from YAML.
- Tokens flow as `CMG-AccessToken` HTTP header (`CambridgeClient.java` lines 38–110).

## 6. Data Flow

```
Caller ──POST /rates──> RateController → CreateRateHandler
                          → SpotServiceImpl → CambridgeClient (HTTPS) → Cambridge
                          → RateRepository.save() → SQL Server RATE table

Caller ──POST /transfers──> TransferController → CreateTransferHandler
                              → SpotServiceImpl.instructDeal() → Cambridge (HTTPS)
                              → TransferRepository.save() → SQL Server TRANSFER table

Cambridge SFTP ──(CSV+PGP)──> Batch ImportCambridgeReconFile
                                → PGPDecryptionTasklet (BouncyCastle)
                                → ImportCambridgeReconFileReader (CSV parse)
                                → ImportCambridgeReconFileWriter
                                → ReconFileRepository.save() → SQL Server RECON_FILE

SQL Server RECON_FILE ──> Batch PublishCambridgeReconFile
                           → CambridgeReconRecordsRowMapper
                           → PGPEncryptionTasklet
                           → SftpUpload → Cambridge SFTP / eCount SFTP
```

## 7. Data Quality

- **Currency codes**: Validated via `@CurrencyCode` constraint (from internal `utilities` library) on `PAYERS_CURRENCY`, `BENEFICIARIES_CURRENCY` (Rate), `BANK_CURRENCY` (Beneficiary), `CURRENCY` (TransferReturn).
- **Amount precision**: `AMOUNT` fields use `number(19,5)` for FX rates and `number(19,2)` for payment amounts — appropriate for financial precision.
- **Fail reason truncation**: `FailReasonTruncater.java` converter prevents oversized failure reason strings from breaking persistence.
- **Duplicate recon records**: Unique constraints on `ORDER_NUMBER` and `PAYMENT_REF` in `RECON_FILE` — duplicate-import safety.
- **Audit trail**: `BaseEntity` (`BaseEntity.java` lines 56–68) auto-populates `INSERTED_AT/BY` and `UPDATED_AT/BY` on every entity via JPA lifecycle hooks. `INSERTED_BY` is populated from `ThreadLocalBatchJobContext.getJobName()` — only meaningful in batch context; REST calls will leave this empty or with a static value.

## 8. Compliance Gaps

| Gap | Regulation | Detail |
|---|---|---|
| No at-rest encryption for PII | GLBA, GDPR, CCPA | Account numbers, names, routing codes in plaintext SQL Server columns |
| Secret PGP key in Git | Internal security policy | `0x6392B27D-sec.asc` committed to repository |
| API credentials in Git | PCI DSS Req 3/8 | Cambridge client signatures, SMTP passwords in `application-qa.yml` |
| No data-retention or purge policy | GDPR Art. 5(1)(e), CCPA | No time-based deletion of PII from REMITTER/BENEFICIARY tables |
| DB TLS disabled in QA | PCI DSS Req 4 | `tlsEnabled: false` in QA configuration; in-transit encryption not enforced |
| `INSERTED_BY` not populated by REST paths | Audit / SOC 1 | `BaseEntity.onPrePersist()` uses `getJobName()`; REST context may log no meaningful actor |
