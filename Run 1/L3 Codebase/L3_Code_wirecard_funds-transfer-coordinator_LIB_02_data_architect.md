# Data Architect — wirecard_funds-transfer-coordinator_LIB

## Data Stores
| Store | Type | Notes |
|---|---|---|
| Oracle DB (production) | RDBMS | ojdbc8 12.2.0.1.0; two-schema pattern (dataSchema / appSchema with synonyms) |
| H2 in-memory | RDBMS | Dev/test only; Mode=Oracle emulation |
| ActiveMQ broker | Messaging | EventHub events; tcp://localhost:61616 in dev |
| Quartz JDBC store | RDBMS (Oracle) | Clustered scheduler state; QRTZ_* tables via Spring Quartz |

## Schema — Core Tables (Liquibase changelog)

### db.changelog-1.0.xml
| Table | Key Columns | Notes |
|---|---|---|
| EVENT_HUB_EVENT | EVENT_ID (PK), EVENT_GROUP_ID, EVENT_TYPE, STATUS, STATUS_DETAIL, EVENT (blob), INSERTED_AT | Event deduplication store |
| ACCOUNT | ID (PK), BRAND, CUSTOMER_ID, LOADING_NUMBER, ACCOUNT_REF_ID, STATUS, CURRENCY | Core account entity |
| FTC_TRIGGER | ID, NAME, TYPE, ACCOUNT_ID (FK), INVOICE_ENABLED, TRIGGER_STATUS | Rule definition |
| TRANSFER | ID, TRIGGER_ID (FK), TYPE, METHOD, FIXED_AMOUNT, DRAWDOWN_PREFORMATCODE | Transfer rail config |
| LOGIC | ID, TRIGGER_ID (FK), SOURCE, CALCULATION, THRESHOLD, PERCENTAGE_AMOUNT | Amount calculation rule |
| EVENT_TRIGGER | ID, TRIGGER_ID (FK), EVENT_TYPE, EVENT_SOURCE, START_TIME, END_TIME | Event-based firing condition |
| TIME_TRIGGER | ID, TRIGGER_ID (FK), ACTIVATION_DATE, RECURRING, YEAR/MONTH/DAY_OF_MONTH/etc. | Schedule-based firing condition |
| SALES_ORDER | ID, ACCOUNT_ID (FK), EVENT_ID (FK), AMOUNT, JOB_ID, CLIENT_EMAIL, VIRTUAL_CLIENT_KEY, STATUS | Money-remittance order |
| FACE_VALUE_DISCOUNT | ID, SALES_ORDER_ID (FK), NUMBER_OF_TRANSACTIONS, TOTAL_AMOUNT, RANGE_FROM, RANGE_TO | Discount ranges on order |
| TRANSACTION | ID, EVENT_ID (FK), ACCOUNT_ID (FK), TRANSACTION_ID, AMOUNT, CURRENCY, STATUS, TYPE, BALANCE_BEFORE, BALANCE_AFTER, BOOKING_DATE, SWEPT, CREDIT_TYPE | Ledger entries |
| CARD_AUTHORIZATION | ID, EVENT_ID (FK), ACCOUNT_ID (FK), CARD_REF_ID, UNIQUE_AUTHORIZATION_ID, AUTHORIZATION_EVENT_TYPE, TRANSFER_AMOUNT/CURRENCY, ACCOUNT_AMOUNT/CURRENCY | Card auth tracking |
| OVERDRAFT | ID, ACCOUNT_ID (FK), EVENT_ID (FK), VIRTUAL_CORPORATE_ACCOUNT, AMOUNT | Overdraft tracking |
| CHECK_TRANSFER | ID, TRANSFER_ID (FK), EXPRESS_SHIPPING, SECONDARY_PAYEES_FIRSTNAME/LASTNAME, WAIVE_FEE | Check issuance details |
| TRANSFER_REQUEST_LOG | ID, TRIGGER_ID (FK), ACCOUNT_ID (FK), JOB_ID, EVENT_ID, TYPE, METHOD, REQUEST, RESPONSE, STATUS, TRANSACTION_ID | Full outbound request audit |
| CLIENT_EMAIL | ID, TRIGGER_ID (FK), EMAIL | Notification recipients |
| TARGET_ACCOUNT | ID, TRANSFER_ID (FK), ACCOUNT_ID (FK) | A2A destination accounts |

### db.changelog-1.0.12.xml / db.changelog-history-tables-1.0.xml / db.changelog-quartz.xml
- QRTZ_* tables for clustered Quartz scheduler
- Envers _AUD history tables for audited entities
- Additional columns: INVOICE_DUE_DATE, PAST_DUE_EMAIL_SENT on SALES_ORDER

## Sensitive Data Classification
| Column | Sensitivity | Notes |
|---|---|---|
| ACCOUNT.CUSTOMER_ID | PII (internal ID) | Not a PAN; internal reference |
| ACCOUNT.LOADING_NUMBER | Financial reference | Card loading/account number — may carry BIN data |
| SALES_ORDER.CLIENT_EMAIL | PII | Email address of corporate client contact |
| SALES_ORDER.VIRTUAL_CLIENT_KEY | Internal key | Links to CCP corporate client |
| TRANSFER.FIXED_AMOUNT / LOGIC.THRESHOLD | Financial | Monetary amounts |
| TRANSACTION.AMOUNT, BALANCE_BEFORE/AFTER | Financial | Ledger balances |
| TRANSFER_REQUEST_LOG.REQUEST / RESPONSE | Sensitive | May contain API payloads with account or payment details |
| CHECK_TRANSFER.SECONDARY_PAYEES_FIRSTNAME/LASTNAME | PII | Payee name data |

No PAN, CVV, or track-data columns observed in Liquibase changelogs.

## Encryption
- Database connection: TLS enabled via `spring.datasource.tlsEnabled=true`; truststore loaded from Base64-encoded content at runtime (`DataSourceConfiguration.java`)
- Truststore type: JKS (`global.datasource.truststore.type=JKS`)
- No column-level encryption observed in schema or entity definitions
- Passwords/credentials in application.yml are plaintext (dev defaults); production values must be injected via environment/Puppet/Vault

## Data Flow
```
EventHub (ActiveMQ) --> EventConsumerContext --> TriggerService
                                                    |
                                              Oracle DB (FTC schema)
                                                    |
                                        CCP API / Check-Agent API / Wire-Transfer API
                                                    |
                                         TRANSFER_REQUEST_LOG (Oracle)
                                                    |
                                         EventHub producer (APP/FTC topic)
```

## Data Quality / Retention
- All tables include VERSION (optimistic locking), INSERTED_AT, INSERTED_BY, UPDATED_AT, UPDATED_BY audit columns
- TRANSFER_REQUEST_LOG.TRANSFER_TRIGGER_PLACEHOLDER has unique constraint — prevents duplicate transfer triggers
- TRANSFER_REQUEST_LOG.REQUEST/RESPONSE capped at VARCHAR(2048) — long payloads may be truncated
- No retention/purge policies observed in schema; data grows unbounded without operational purge procedures
- EVENT_HUB_EVENT.EVENT BLOB — no size cap observed; large event payloads possible

## Compliance Gaps
1. No column-level encryption for PII fields (CLIENT_EMAIL, payee names) — PCI DSS requirement 3.4 / GDPR
2. TRANSFER_REQUEST_LOG stores REQUEST/RESPONSE fields raw; if downstream API responses include account numbers these are retained in plaintext
3. No data retention or purge schedule defined in schema
4. H2 console enabled in base application.yml — if environment profile not properly applied in production, exposes DB to unauthenticated access
5. Audit columns (INSERTED_BY/UPDATED_BY) rely on application-level population; no database-level enforcement
