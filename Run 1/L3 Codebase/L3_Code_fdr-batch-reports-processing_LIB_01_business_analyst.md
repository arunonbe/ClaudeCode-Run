# Business Analyst View — fdr-batch-reports-processing_LIB

## Repository Overview

**fdr-batch-reports-processing_LIB** is a Gen-1 Java library that processes daily batch reports from FDR (First Data Resources, now Fiserv), Onbe's debit card processing network. This library is a critical component in the reconciliation and fund management workflow for Onbe's prepaid card business. It reads processed card transaction and account creation data from an intermediate staging database (populated by upstream FDR file import jobs), and pushes that data into Onbe's core job service (`jobsvc`) database tables for downstream processing by stored procedures.

The library processes three distinct report types in a defined sequence:

## Report Types Processed

### 1. FDR Batch New Account Report (`FDR_BATCH_NEW_ACCOUNT`)

**Business Purpose**: Confirms which prepaid card accounts were successfully created through FDR's batch card issuance process.

**Source**: Database table `fdr_batch_creation_report` in the `EcountCore` database (or as configured, e.g., `EcountCore_test`). This table is populated by an upstream pre-processing stored procedure (`fdr_batch_creation_report_import`) that imports raw FDR batch creation data from the Fiserv file delivery.

**Data Extracted**:
- `card_id` — Internal card identifier
- `device_id` — Physical card/device identifier (resolved via `core_device_ecard` lookup table)
- `insertion_date` — Date the account creation was processed by FDR
- `successful` — 0/1 flag indicating whether the account creation succeeded at FDR
- `error_message` — Error description if creation failed

**Target**: Table `job_fdr_batch_creation_report` in `jobsvc` database. After insertion, stored procedure `job_fdr_batch_creation_report_process` is called to complete downstream processing.

**Operational Significance**: This report feeds the card lifecycle management workflow. A failed account creation (successful=0) indicates that a card intended for a recipient was not successfully provisioned at the card processor, which may result in a failed disbursement.

### 2. FDR Batch Add Funds Report (`FDR_BATCH_ADD_FUNDS`)

**Business Purpose**: Reconciles batch fund loads (adds) to prepaid cards processed through FDR's batch interface. This ensures that funds disbursed to cardholders via the batch channel are accurately reflected in Onbe's internal ledger.

**Source**: `fdr_dda_account_journal` table (joined with `core_transaction_journal`) in `EcountCore`. Alternatively, from the staging table `fdr_batch_add_funds_queue` via a direct UPDATE+OUTPUT SQL statement (`batch_add_funds.sql`), which atomically marks records as exported.

**Data Extracted**:
- `amount` — Transaction amount in minor currency units (cents)
- `member_id` — The cardholder's member identifier (resolved from DDA number via the `dbo.app_func_get_member_by_dda` SQL function)
- `tx_id` / `transaction_group` — Transaction group identifier for journal matching

**Target**: Table `job_member_recent_commited_transfers` in `jobsvc` database. Post-insertion, stored procedures `job_member_recent_commited_transfers_process` and `job_fail_lingering_batch_actions` are executed.

**Duplicate Handling**: The processor implements active duplicate removal logic (`removeDuplicates()`) to delete records already processed and remove duplicate unprocessed records, using member_id + journal_tx_group + amount as the deduplication key.

**Operational Significance**: This is a financial reconciliation report. Inaccurate processing could result in missed or double-applied fund loads. The duplicate removal logic is a compensating control for potential double-delivery of FDR batch files.

### 3. Message Queue Updates (`MESSAGE_QUEUE_UPDATES`)

**Business Purpose**: Synchronizes the status of batch actions (e.g., fund loads, account creations) from the job service database back to the core application database (`cbaseapp`). This closes the feedback loop for batch operations: the job service knows which batch messages completed successfully, and this report publishes those outcomes to the `batch_message_status` table.

**Source**: View `job_batch_completed_actions_messages` in `jobsvc` database. Fields: `message_id`, `action_successful`.

**Target**: Table `batch_message_status` in `cbaseapp` database. Post-insertion, stored procedure `batch_messages_status_process` is called.

**Operational Significance**: This feeds Onbe's internal notification and status tracking systems. If a batch action (e.g., a fund load for a cardholder) succeeded at FDR and was confirmed via the Add Funds report, that success status propagates back through this report to the core application that initiated the request.

## Processing Orchestration

The main class `FDRBatchReportsMain` orchestrates processing in this sequence:
1. **Pre-processing stored procedures**: `fdr_batch_creation_report_import` and `fdr_batch_creation_report_process` are executed first (against `ecountcore`). These import raw FDR file data and process it into the staging tables.
2. **Report processing loop**: The three report types are processed in order.
3. **Post-processing stored procedures**: `job_mark_batch_job_complete` is executed to finalize the batch job.

## Business Impact Assessment

This library is a **critical financial integration component**. Failures in this library can result in:
- Unreconciled fund loads (cardholders credited but Onbe's internal ledger not updated).
- Failed card activations not being surfaced for remediation.
- Stale batch action status (downstream systems not notified of completion).

The library has no retry mechanism, no dead-letter handling, and no alerting integration — all failure handling is limited to log output.

## Configuration

All database connection details, table names, field names, and stored procedure names are externalized to `FDRBatchReportsProcessor.properties` loaded from `/c-base/config/FDRBatchReportsProcessor/FDRBatchReportsProcessor.properties` (hardcoded default path in `FDRBatchReportsMain.java` line 20). This is a server-local file path, consistent with Gen-1 on-premises deployment patterns.
