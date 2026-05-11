# Data Architect View — inventory-mgmt-batch-client_LIB

## Data Stores
| Store | Type | Database Reference |
|-------|------|--------------------|
| ecountCore SQL Server | Relational RDBMS | `ecountcore` database — card state sync (CoreSyncCard, CardExternalClient) |
| JobSvc SQL Server | Relational RDBMS | `jobsvc` database — instant issue orders, expiry, email queues (CardExpiryClientDao, EmailNotificationDao, CoreSyncInstantIssue) |
| cbaseapp SQL Server | Relational RDBMS | `cbaseapp` database — C-Base application data (CbaseappDataSource) |

All connections are resolved via Director service registry and configured in `applicationContext-inventory-mgmt-batch.xml` using `DirectorConfiguredDBCPdatasourceCreator`.

## Schema / Tables
Tables accessed are primarily those owned by `inventory-mgmt_LIB`. Additional tables accessed by batch client:

| Table (inferred from DAO) | Store | Description |
|--------------------------|-------|-------------|
| instant_issue_card | jobsvc | Card inventory (read for expiry, update for shipping info) |
| instant_issue_notification | jobsvc | Low inventory flags |
| instant_issue_inv_email_log | jobsvc | Email notification audit |
| App program configuration tables | ecountcore | Program-level instant issue profiles (AppProfileInstantIssue) |
| DDA / card tables | ecountcore | CoreSyncCard queries for assigned/blocked/loaded/expired DDA numbers |

## Sensitive Data Classification
| Data | Classification | Risk |
|------|---------------|------|
| DDA numbers (Demand Deposit Account) | Bank account number | GLBA-regulated; PII |
| card_number (via PopulateShippingInfoBatch) | Cardholder Data — PAN | PCI DSS Req 3 |
| email_address (notification tables) | PII | CCPA/GDPR |

## Encryption
- No encryption of data in transit is configured in Spring XML (`applicationContext-inventory-mgmt-batch.xml`) — raw JDBC via Director DBCP.
- No encryption of data at rest in this library.
- Properties files (`inventoryMgmtBatchClient.properties`, `director-client.properties`) read from `D:/c-base/config/` — plaintext.

## Data Flow
1. **Card Expiry Alert**: Read `AppProfileInstantIssue` from ecountCore → read card expiry state from jobsvc → send notification.
2. **Auto-Reorder CoreSync**: Read DDA lists (assigned/blocked/loaded/expired) as XML from ecountCore → pass to `InventoryManagementManager`.
3. **Shipping Info Population**: Read unshipped cards from jobsvc → update `ship_date`, `tracking_number`, `card_number` in `instant_issue_card`.
4. **Email Notification**: Read pending notifications from jobsvc email queue → send emails.

## Data Quality / Retention
- Batch writes `card_number` to `instant_issue_card.card_number` — if this is a full PAN, it must be encrypted or truncated at rest.
- DDA number lists are held in-memory as `List` and XML strings during processing — no explicit clearing of sensitive data from memory.
- No data retention management in this library.

## Compliance Gaps
1. DDA numbers (bank account identifiers) processed in XML strings in memory — no scrubbing or masking before logging.
2. `card_number` written to database table via `batchSqlUpdate` — full PAN at rest without evidence of encryption (PCI DSS Req 3.4).
3. Properties files with database credentials at `D:/c-base/config/` are plaintext on the server filesystem.
4. TIBCO JMS credentials for ELF logging stored in `d:\c-base\config\elf-cert\pconfig.xml` — plaintext credential file.
5. No formal data lineage from DDA source tables to output; no audit trail of batch runs.
