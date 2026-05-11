# Data Architect View — recipient-screening-api

## Data Models

### JPA Entities

**RecipientScreeningPending** (`recipient_screening_pending` table):
```
id              UUID (uniqueidentifier, PK)
member_id       UUID (uniqueidentifier, NOT NULL)
status          VARCHAR(32) NOT NULL — e.g., "FAILED"
account_blocked BOOLEAN NOT NULL
csa_comment_generated BOOLEAN NOT NULL
retry_count     INT NOT NULL
created         DATETIME NOT NULL
updated         DATETIME NULL
```
This table tracks screening operations that failed to complete, enabling retry logic. It stores member UUIDs and processing state but does not store raw PII or card numbers.

**BinBankFriendlyConfigMap** (read from `cbaseapp` database):
Stores the mapping between Onbe program IDs (BIN-level identifiers) and the sanctions vendor's "friendly configuration ID." This is a configuration table with no PII.

### Domain Objects (In-Memory Only)

**RecipientScreeningRequest** (inbound API request payload):
- `memberId` — UUID
- `ddaNumber` — Demand Deposit Account number (sensitive financial identifier)
- `ddaAccountId` — device ID for the DDA
- `cardDeviceIds` — list of card device IDs
- `programId` — Onbe program identifier
- `currency` — ISO currency code
- `person` — nested object containing: `firstName`, `lastName`, `dob` (Date), `phone`, `emails`, `address`

**MemberInfo** (resolved from ECountCore by DDA lookup):
- `memberId`, `userStatus`, `deviceId`, `role`

## Sensitive Data

The following sensitive data classes flow through this service:

| Data Element | Classification | Present In |
|---|---|---|
| `ddaNumber` | DDA — financial account number (GLBA, PCI DSS scope adjacent) | Request payload, logs |
| `firstName`, `lastName` | PII (GDPR, CCPA) | Request payload, forwarded to vendor |
| `dob` | PII — date of birth | Request payload, forwarded to vendor |
| `phone` | PII | Request payload, forwarded to vendor |
| `emails` | PII | Request payload, forwarded to vendor |
| `address` | PII | Request payload, forwarded to vendor |
| `memberId` | Internal identifier | `recipient_screening_pending` table |

### Critical Log Exposure

In `RecipientScreeningService.java` line 65:
```java
log.info("Processing recipient screening for member: {}, DDA: {}", 
    recipientScreeningRequest.getMemberId(), recipientScreeningRequest.getDdaNumber());
```
The DDA number (a financial account number) is written to the INFO-level log. Under GLBA and PCI DSS data classification requirements, DDA numbers should not appear in application logs unless the log storage is within a secured, access-controlled system. Depending on where logs are forwarded (Azure Monitor, Splunk, third-party SIEM), this could constitute unauthorized disclosure of financial account information.

Similarly, at line 84:
```java
log.info("Screening response received for member: {}, DDA: {}", ...)
```
The DDA number is logged again in the response path.

## Encryption Status

- **Data at rest**: The `recipient_screening_pending` table in SQL Server (Azure SQL or on-premises) does not have column-level encryption visible in the JPA entity definition. No `@Convert` or encryption annotation is present on the `memberId` column.
- **Data in transit**: OAuth 2.0 client credentials are used to authenticate to the `om-recipientsanctioning-svc`. Database connections use `sslProtocol=TLSv1.2` (confirmed in `app-config/prod/appsettings.json`). Credentials for both the OAuth client and database are stored in Azure Key Vault (referenced via `key_vault_references` in appsettings.json).
- **TLS version**: `TLSv1.2` for SQL Server connections — TLSv1.3 preferred for new services but 1.2 is compliant with current PCI DSS 4.0.1 requirements.

## Database Schemas

Two SQL Server databases are accessed:
- **`cbaseapp`** (`p-lis-db03.nam.wirecard.sys:2231`): Contains `bin_bank_friendly_config_map` and `recipient_screening_pending` tables.
- **`EcountCore`** (`p-lis-db02.nam.wirecard.sys:2231`): Read for DDA-to-member resolution via ECountCore service.

Both databases reside on Gen-2 (Wirecard) infrastructure (`wirecard.sys` DNS domain), creating a cross-generation infrastructure dependency from this Gen-3 service.

## Data Flows

```
Client → POST /api/v1/screening/request
    → RecipientScreeningService
        → ScreeningRequestValidator (validate DDA, programId)
        → BinBankFriendlyConfigService (read cbaseapp: bin_bank_friendly_config_map)
        → om-recipientsanctioning-svc API (POST with PII payload, OAuth 2.0)
        → [if isUpdateAccountInApiCallEnabled] → ECountCoreService (resolve DDA→members)
            → SanctionMemberHandler (block/unblock eCount accounts)
        → Return RecipientScreeningResponse

Vendor → POST /sanction/webhook
    → SanctionWebhookService
        → SanctionWebhookRequestValidator
        → ECountCoreService (resolve DDA→members)
        → SanctionMemberHandler (block/unblock accounts)
        → Return WebhookAck
```

## Retention Concerns

PII submitted in screening requests is not persisted locally — it is passed through to the sanctions vendor and not stored in any local database table. The `recipient_screening_pending` table stores only member UUIDs and processing metadata, not raw PII. However, PII in logs (DDA numbers) may be retained per the log retention policy of the Azure Monitor/SIEM configuration, which must be reviewed for alignment with GDPR data minimization and CCPA retention obligations.
