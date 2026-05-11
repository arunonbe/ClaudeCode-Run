# Data Architect — wirecard_check-agent_LIB

## Data Stores
| Store | Technology | Purpose |
|---|---|---|
| Primary database | Oracle (production), H2 in-memory (dev/test) | Check transaction records, event tracking |
| EventHub | ActiveMQ (production), in-memory mock (test/dev) | Asynchronous event messaging |
| EhCache 3 (JCache) | In-process heap cache | Application-level caching (config from `ehcache3.xml`) |

## Schema / Tables (from Liquibase changelogs)

### `CHECK_TRANSACTION` (v1.0)
Core check disbursement record.

| Column | Type | Notes |
|---|---|---|
| ID | VARCHAR2(255) PK | UUID |
| REFERENCE_ID | VARCHAR2(36) NOT NULL, UNIQUE | External reference |
| CUSTOMER_ID | VARCHAR2(36) NOT NULL | Cardholder/beneficiary ID |
| AMOUNT | NUMBER(19,5) NOT NULL | Check face value |
| AMOUNT_CURRENCY | VARCHAR2(3) NOT NULL | ISO 4217 currency code |
| FEE_AMOUNT | NUMBER(19,5) NOT NULL | Fee amount |
| PAYEES_FIRST_NAME | VARCHAR2(128) NOT NULL | **PII** |
| PAYEES_LAST_NAME | VARCHAR2(128) NOT NULL | **PII** |
| SECONDARY_PAYEES_FIRST_NAME | VARCHAR2(128) | **PII** |
| SECONDARY_PAYEES_LAST_NAME | VARCHAR2(128) | **PII** |
| ADDRESS_LINE_1 | VARCHAR2(50) NOT NULL | **PII** |
| ADDRESS_LINE_2 | VARCHAR2(50) | **PII** |
| CITY | VARCHAR2(32) NOT NULL | **PII** |
| POSTAL_CODE | VARCHAR2(50) NOT NULL | **PII** |
| PROVINCE | VARCHAR2(50) NOT NULL | **PII** |
| COUNTRY_CODE | VARCHAR2(2) NOT NULL | |
| CHECK_NUMBER | NUMERIC NOT NULL | Sequential (Oracle sequence) |
| STATUS | VARCHAR2(32) NOT NULL | `CheckStatus` enum |
| RESERVATION_ID | VARCHAR2(36) NOT NULL | CCP fund reservation ID |
| PUBLISH_STATE | VARCHAR2(32) NOT NULL DEFAULT 'TO_PUBLISH' | EventHub publish status |
| BRAND | VARCHAR2(256) NOT NULL | (added v1.1) |
| ALIAS | VARCHAR2(256) NOT NULL | (added v1.1) — login alias |
| ALIAS_TYPE | VARCHAR2(128) | (added v1.1) |
| RESERVATION_STATUS | VARCHAR2(36) | (added v1.1) |
| CHANNEL | VARCHAR2(10) | (added v1.1) |
| CHECK_TRANSACTION_NOTE_ID | VARCHAR2(36) FK | (added v1.1) |
| REISSUE | BOOLEAN NOT NULL DEFAULT 0 | (added v1.1) |

### `CHECK_TRANSACTION_HISTORY`
Status-change audit trail (FK to `CHECK_TRANSACTION`).

### `CHECK_TRANSACTION_NOTE`
Agent notes (CHANNEL, CONTEXT, SUBJECT, CONTENT VARCHAR2(4000), AGENT_LOGIN, AGENT_NAME).

### `CHECK_TRANSACTION_NOTE_HISTORY`
History of note changes (FK to `CHECK_TRANSACTION` and `CHECK_TRANSACTION_NOTE`).

### `CHECK_TRANSACTION_REISSUE`
Tracks reissuance metadata when a check is reissued (amount, fees, express shipping, initiator).

### `EVENT_HUB_EVENT`
EventHub message tracking for idempotency and retry (EVENT_ID PK, EVENT_GROUP_ID, EVENT_TYPE, STATUS, STATUS_DETAIL, INSERTED_AT).

### Spring Batch Tables
Standard Spring Batch schema (via `schema-oracle10g.sql` / `schema-h2.sql` included in changelogs).

## Sensitive Data
- **PII**: Payee names (first, last, secondary), full mailing address (line1, line2, city, postal code, province, country) stored in `CHECK_TRANSACTION`. This data is subject to GLBA, CCPA, and GDPR.
- **Financial data**: Check amount, fee amount, reservation ID.
- **No PAN/CVV/PIN**: Check disbursement does not store primary card account numbers.
- **`AGENT_LOGIN`**: Agent username stored in notes — PII under some privacy regimes.
- **`ALIAS`/`ALIAS_TYPE`**: Login alias may be an email address or identifier — potentially PII.

## Encryption
- **Database TLS**: `DataSourceConfiguration.java` supports TLS for JDBC connections. When `tlsEnabled: true`, a truststore is decoded from Base64 (`truststore.content`) and written to `truststore.location`, then passed as JVM SSL properties to HikariCP.
- **At-rest encryption**: No application-layer column encryption is applied to PII columns. Database-level encryption (Oracle TDE) is not configured via this application — if required, it must be configured at the Oracle infrastructure level.
- **EventHub TLS**: ActiveMQ connection (`tcp://localhost:61616` in dev config) should use `ssl://` in production. The application config does not enforce SSL for ActiveMQ in the committed `application.yml`.

## Data Flow
```
REST API / EventHub Consumer
  --> CheckServiceImpl.createCheck()
  --> CheckRepository.save() --> Oracle: CHECK_TRANSACTION + CHECK_TRANSACTION_HISTORY
  --> NewCheckEventNotifier.notifyNewCheck() --> EventHubProducer --> ActiveMQ topic APP/CHECKAGENT

EventHub Consumer (CheckStatusUpdatedEvent)
  --> IdempotentSubscriberAspect (checks EVENT_HUB_EVENT table)
  --> CheckStatusUpdateService
  --> CheckRepository.save() --> Oracle: UPDATE CHECK_TRANSACTION.STATUS
```

## Data Quality / Retention
- All tables have `INSERTED_AT`, `INSERTED_BY`, `UPDATED_AT`, `UPDATED_BY` audit columns.
- `CHECK_TRANSACTION_HISTORY` and `CHECK_TRANSACTION_NOTE_HISTORY` provide immutable audit trails.
- No data retention / purge policy is defined in the codebase.

## Compliance Gaps
1. **PII at rest without column-level encryption**: Payee names and addresses in `CHECK_TRANSACTION` are stored in plaintext. Under GLBA/GDPR, PII at rest should be encrypted or access-restricted. Oracle TDE or application-layer encryption is not configured.
2. **No data retention/purge policy**: Check transaction records appear to be retained indefinitely. Regulatory requirements (CCPA right-to-erasure, GDPR Art. 17) may require a defined retention schedule.
3. **ActiveMQ connection in dev config uses plaintext TCP** (`tcp://localhost:61616`): If any environment uses this default without overriding to `ssl://`, event messages containing PII could traverse the network unencrypted.
4. **`ALIAS` column could be an email address**: If so, it is PII and should be considered in data mapping for GDPR/CCPA.
