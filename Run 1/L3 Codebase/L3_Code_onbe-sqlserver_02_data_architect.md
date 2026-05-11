# onbe-sqlserver — Data Architect View

## Data Stores

| Store | Technology | Role | Scope |
|---|---|---|---|
| `petstore` database | SQL Server 2022 Developer Edition | Demonstration OLTP database | Dev / CI only |
| `cdc.dbo_pet_CT` | SQL Server CDC change table | Change event capture for `dbo.pet` | Dev / CI only |
| `cdc.*_capture` / `cdc.*_cleanup` jobs | SQL Server Agent jobs | CDC pipeline maintenance | Automatically created |

There are no application-level data stores beyond SQL Server itself. The Spring Boot application stub (`OnbeSqlserverApplication.java`) contains no data access code and connects to no database.

## Schema / Tables

### `dbo.pet`
```sql
create table pet
(
    id   int identity primary key,  -- auto-increment surrogate key
    name varchar(255) not null,     -- pet name (required)
    tag  varchar(255)               -- optional tag/category
);
```
Minimal demonstration schema. No financial, PII, or sensitive data in the schema definition. In production Onbe deployments, the equivalent init script would create business tables (transactions, accounts, card records) with appropriate column-level encryption where required.

### CDC Change Table `cdc.dbo_pet_CT` (auto-created)
| Column | Type | Description |
|---|---|---|
| `__$start_lsn` | binary(10) | Transaction LSN — identifies when change occurred |
| `__$end_lsn` | binary(10) | NULL for normal rows |
| `__$seqval` | binary(10) | Within-transaction sequence |
| `__$operation` | int | 1=delete, 2=insert, 3=before-update, 4=after-update |
| `__$update_mask` | varbinary(128) | Bitmask of updated columns |
| `id` | int | Mirrored from source table |
| `name` | varchar(255) | Mirrored from source table |
| `tag` | varchar(255) | Mirrored from source table |

### CDC Functions (auto-created)
- `cdc.fn_cdc_get_all_changes_dbo_pet(from_lsn, to_lsn, row_filter_option)` — returns all row changes in LSN range.
- `cdc.fn_cdc_get_net_changes_dbo_pet(from_lsn, to_lsn, row_filter_option)` — returns net row state (collapse multiple changes to same row).

## Sensitive Data Assessment

The current `petstore` schema contains no sensitive data (`pet.name` and `pet.tag` are fictional animal names). However, the CDC configuration pattern (`@role_name = NULL`) would be directly dangerous if applied to production Onbe tables:

| Production Table (examples) | Sensitive Fields | PCI DSS Classification |
|---|---|---|
| `ecountcore.card` | PAN, expiry, CVV (at issuance) | CHD / SAD |
| `ordersvc.order_memo` | Potentially PAN or DDA number if stored | CHD (if unencrypted) |
| `nexpay_claimable.transaction` | Amount, account identifiers | Confidential |
| `DS_DB_notificationsvc.*` | Email, phone, SSN fragments | PII |

Production CDC configurations must always specify `@role_name` to restrict CDC table access to the Debezium service account only.

## Encryption

| Layer | Current State | Required State (Production) |
|---|---|---|
| Data at rest | SQL Server default (TDE optional) | TDE should be enabled for production CDE databases |
| Data in transit (JDBC) | Self-signed certificate; `trustServerCertificate=true` in test clients | CA-signed cert; `encrypt=true`, `trustServerCertificate=false` |
| SA password | Environment variable (cleartext in container env) | Azure Key Vault via Kubernetes ExternalSecret |
| CDC data in transit (Debezium → Kafka) | Debezium config `trustServerCertificate: true` | Kafka TLS + mTLS; SQL Server CA-signed cert |

## Data Flow

```
External client (developer / Debezium connector)
    │
    ▼ TCP 1433 (SQL Server protocol)
SQL Server 2022 container
    │
    ├── DML on dbo.pet
    │       ↓
    │   Transaction log (WAL)
    │       ↓
    │   CDC capture agent (SQL Server Agent job)
    │       ↓
    │   cdc.dbo_pet_CT (change table)
    │       ↓
    │   Debezium SqlServerConnector (external) reads change table
    │       ↓
    │   Kafka topic (petstore CDC events)
    │
    └── Spring Boot stub (OnbeSqlserverApplication)
            — does NOT connect to SQL Server
            — does NOT process any data
```

## Data Quality and Retention

### CDC Retention
SQL Server CDC default retention is 3 days (`sys.sp_cdc_cleanup_change_table` cleanup job). The `init-db.sql` does not configure an explicit retention period; the 3-day default applies. For development containers, this is sufficient. For production, retention must be aligned with the Debezium connector's maximum lag — if Debezium falls behind by more than the retention window, changes will be lost.

### Change Tracking Alternative (Commented Out)
The commented `CHANGE_RETENTION = 2 DAYS` block in `init-db.sql` shows an alternative lighter-weight mechanism. Change Tracking retains only which rows changed (not before/after values), suitable for lower-fidelity use cases like Azure Functions SQL Trigger-based integrations.

## Compliance Gaps

| Gap | PCI DSS Requirement | Current State | Recommended Action |
|---|---|---|---|
| CDC `@role_name = NULL` | Req 3.3 (CHD access restriction) | All DB users can read CDC tables | Set `@role_name` to a restricted role in production scripts |
| Self-signed TLS certificate | Req 4.2.1 | Default self-signed cert | Install CA-signed cert; configure `mssql-conf` |
| No SQL Server Audit configured | Req 10.2 | No audit trails on DML | Configure SQL Server Audit to capture login, DML events |
| TDE not configured | Req 3.5 (CHD encryption at rest) | Default SQL Server data files | Enable TDE on production CDE databases |
| SA used for initialization | Req 8.2 (unique IDs) | SA account — shared account | Create dedicated service accounts; disable SA post-init |
