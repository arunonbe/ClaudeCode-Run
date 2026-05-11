# Data Architect View — fdr-batch-reports-processing_LIB

## Database Architecture Overview

This library interacts with **four distinct SQL Server databases** across two physical database servers (or as configured). All connections use the jTDS JDBC driver via JDBC URL pattern `jdbc:jtds:sqlserver://<server>:<port>/<dbname>`.

## Source Databases

### 1. EcountCore (Source for New Account Report)
**Database**: `EcountCore_test` (test; production value in external config)  
**Server**: `ecsqldev1` (test config, `FDRBatchReportsProcessor.properties` line 16)

| Table/Object | Columns Read | Purpose |
|-------------|--------------|---------|
| `fdr_batch_creation_report` | `card_id`, `update_date`, `successful`, `error_message`, `exported_date` | FDR batch card creation results. Rows with `exported_date IS NULL` are unprocessed. |
| `core_device_ecard` | `[card.card_id]`, `id` (as `device_id`) | Card-to-device lookup — resolves `card_id` to `device_id` for the target report. |

**Write Operation**: UPDATE `exported_date` on `fdr_batch_creation_report` to mark records as processed.

### 2. EcountCore (Source for Add Funds Report)
**Database**: `Ecountcore_test`

| Table/Object | Columns Read | Purpose |
|-------------|--------------|---------|
| `fdr_dda_account_journal` | `amount`, `dda_number`, `id`, `created`, `facility`, `source`, `phase`, `status` | DDA (Demand Deposit Account) journal for batch add-funds transactions |
| `core_transaction_journal` | `transaction_group`, `id` | Core transaction journal joined to DDA journal for group ID |
| `dbo.app_func_get_member_by_dda` | Function — takes DDA number → returns `member_id` | Maps DDA account to Onbe member ID |

**Alternative source**: `fdr_batch_add_funds_queue` table — used via `batch_add_funds.sql` which performs an `UPDATE ... OUTPUT INSERTED.*` to atomically mark records as exported.

### 3. JobSvc (Source for Message Queue Updates)
**Database**: `jobsvc_test`

| Table/Object | Columns Read | Purpose |
|-------------|--------------|---------|
| `job_batch_completed_actions_messages` | `message_id`, `action_successful` | View of completed batch action outcomes |

## Target Databases

### 1. JobSvc (Target for New Account and Add Funds Reports)
**Database**: `jobsvc_test`  
**Server**: `ecsqldev1`

| Table | Columns Written | Purpose |
|-------|----------------|---------|
| `job_fdr_batch_creation_report` | `device_id`, `insertion_date`, `successful`, `error_message` | FDR batch creation results for job processing |
| `job_member_recent_commited_transfers` | `insertion_date`, `member_id`, `amount`, `journal_tx_group` | Recent committed fund transfers for downstream reconciliation |

### 2. CBaseApp (Target for Message Queue Updates)
**Database**: `cbaseapp`

| Table | Columns Written | Purpose |
|-------|----------------|---------|
| `batch_message_status` | `insertion_date`, `message_id`, `successful` | Batch action completion status feedback |

## Sensitive Data Flag — PCI DSS / Financial Data

**FLAG: This library processes financial transaction data that may be in scope for PCI DSS.**

Key observations:
1. **`dda_number`** (DDA = Demand Deposit Account number): The source `fdr_dda_account_journal.dda_number` field is a bank account number equivalent for prepaid cards. This is sensitive financial data. It is processed through the `dbo.app_func_get_member_by_dda` function and is **not** written to the target database — only the resolved `member_id` is written. However, this DDA number is logged in debug statements (connection strings show the query being assembled with DDA field names).

2. **`card_id`**: The `fdr_batch_creation_report.card_id` is an internal card identifier. While this is not a full PAN, it is a card-related identifier. It is read from the source and passed to the `core_device_ecard` lookup but **not** written to the target tables (only `device_id` is written).

3. **`amount`**: Transaction amounts in minor units are processed and written to `job_member_recent_commited_transfers`. Financial amounts are not SAD but are sensitive financial data.

4. **Connection strings logged at DEBUG level**: `FDRBatchAddFundsReportProcessor.java` line 225 logs the full JDBC connection string including username and password: `"[...]: trying to open DB connection to " + connectionString.toString()`. This is a **critical credential exposure** risk. The password appears in plain text in log files.

## Data Flow Diagram

```
[FDR/Fiserv Batch File Delivery]
        |
        | (upstream import job — not in this library)
        v
[EcountCore DB: fdr_batch_creation_report]
[EcountCore DB: fdr_dda_account_journal + core_transaction_journal]
        |
        | FDRDatabaseNewAccountCreationReportReader (SELECT + UPDATE exported_date)
        | FDRDatabaseBatchAddFundsReportReader (SELECT / UPDATE batch_add_funds_queue)
        v
[In-Memory: ImportedReportData / forward-only cursor]
        |
        | FDRBatchNewAccountReportProcessor (INSERT + SP call)
        | FDRBatchAddFundsReportProcessor (INSERT + duplicate removal + SP call)
        v
[JobSvc DB: job_fdr_batch_creation_report]
[JobSvc DB: job_member_recent_commited_transfers]
        |
        | BatchedActionsStatusReader (SELECT from job_batch_completed_actions_messages)
        v
[CBaseApp DB: batch_message_status]
```

## Data Volume and Performance Considerations

- The `AddFunds` reader supports a configurable `sourceDDAJournalHistoryDaysToConsider` (default 5 days, properties line 82) to limit query scope.
- Both readers support two query modes: file-based SQL (external `.sql` file) or dynamically built SQL. The file-based mode allows custom SQL optimization without code changes.
- No batch INSERT or bulk copy is used — each row is inserted individually via `PreparedStatement.executeUpdate()`. For large volumes, this is a performance bottleneck.
- No connection pooling — each processor creates a single JDBC connection and closes it after processing.

## Configuration-Driven Data Mapping

All field names, table names, database names, and stored procedure names are externalized. The `PropertiesFileConfiguration.java` (Singleton pattern) loads from the properties file. This makes the library deployable in multiple environments without recompilation, but also means the field mappings are not type-safe and errors (e.g., a typo in a field name) are only discovered at runtime.
