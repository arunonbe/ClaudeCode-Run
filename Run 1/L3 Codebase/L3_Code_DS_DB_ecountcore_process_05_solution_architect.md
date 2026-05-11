# DS_DB_ecountcore_process — Solution Architect View

## Technical Debt Summary

`Ecountcore_Process` has well-designed partitioning and staging patterns but carries critical PCI DSS violations in two CVV columns, ad-hoc security permission growth, and cross-database coupling that complicates migration. The dynamic SQL in the partition maintenance procedure also introduces a low-probability but real SQL injection vector.

---

## All Objects — Names and Purpose

### Functions (4)

| Object | File | Purpose |
|---|---|---|
| `app_func_get_date_from_julian` | `dbo/Functions/` | Converts Julian date format to SQL datetime |
| `fn_file_get_date_compare` | `dbo/Functions/fn_file_get_date_compare.sql` | Compares file date to transaction date with threshold — used in DD031 import to determine `tran_date` |
| `smots_func_is_valid_funding_account` | `dbo/Functions/` | Validates SMOTS funding account |
| `Split` | `dbo/Functions/Split.sql` | String splitting table-valued function |

### Stored Procedures (40+)

| Object | File | Purpose |
|---|---|---|
| `alto_arucs_account_journal_insert` | `dbo/Stored Procedures/` | Inserts ARUCS account journal records |
| `alto_arucs_processed_count` | `dbo/Stored Procedures/` | Returns ARUCS processed record count |
| `alto_process_pacs_load_funds_batch` | `dbo/Stored Procedures/` | Processes PACS bulk fund load |
| `alto_process_pacs_load_funds_batch_count` | `dbo/Stored Procedures/` | Count for above |
| `alto_process_pacs_load_funds_processed_count` | `dbo/Stored Procedures/` | Processed count |
| `alto_process_pacs_load_funds_update` | `dbo/Stored Procedures/` | Updates PACS load status |
| `batch_process_secureaddenda_get_count` | `dbo/Stored Procedures/` | Count of pending secure addenda |
| `batch_process_secureaddenda_get_record` | `dbo/Stored Procedures/` | Gets next secure addenda record |
| `ecountcore_process_partition_maintain` | `dbo/Stored Procedures/ecountcore_process_partition_maintain.sql` | Monthly partition split/merge/archive — uses dynamic SQL |
| `ecs_fetch_IVR_EPMemo_Details` | `dbo/Stored Procedures/` | Fetches IVR EP memo details |
| `ecs_ivr_epmemo_batch_count` | `dbo/Stored Procedures/` | Batch count for IVR EP memos |
| `ecs_ivr_update_processed_count` | `dbo/Stored Procedures/` | Updates IVR processed count |
| `ecs_update_IVR_EPMemo_Details_status` | `dbo/Stored Procedures/` | Updates IVR EP memo status |
| `fdr_auth_master_file_process` | `dbo/Stored Procedures/` | Processes FDR auth master file |
| `FDR_Cards_Status_Posting` | `dbo/Stored Procedures/` | Posts FDR card status updates to EcountCore |
| `fdr_process_atmach_star_post_failure_fix` | `dbo/Stored Procedures/` | Fix for ATM/ACH STAR post failures |
| `fdr_process_dd031_get_file_id` | `dbo/Stored Procedures/` | Gets or creates file_id for DD031 file |
| `fdr_process_dd031_import` | `dbo/Stored Procedures/fdr_process_dd031_import.sql` | Imports DD031 staging data to permanent table; purges card_number; links to EcountCore via cross-DB card_hash join |
| `fdr_process_dd031_post` | `dbo/Stored Procedures/` | Posts DD031 transactions to EcountCore |
| `fdr_process_dd031_prepost` | `dbo/Stored Procedures/` | Pre-posting validation |
| `fdr_process_debitach_post_failure_fix` | `dbo/Stored Procedures/` | Fix for DebitACH post failures |
| `FiServ_Cards_Status_Posting` | `dbo/Stored Procedures/FiServ_Cards_Status_Posting.sql` | Posts Fiserv card status updates to EcountCore |
| `FiServ_Cards_Status_Prepare` | `dbo/Stored Procedures/FiServ_Cards_Status_Prepare.sql` | Prepares Fiserv card status for posting |
| `ivr_card_activation_update` | `dbo/Stored Procedures/ivr_card_activation_update.sql` | Updates IVR card activation status |
| `mq_back_out_msg_insert` | `dbo/Stored Procedures/mq_back_out_msg_insert.sql` | Inserts message queue back-out record |
| `NAOT_Cards_Status_Posting` | `dbo/Stored Procedures/NAOT_Cards_Status_Posting.sql` | Posts Citi NAOT card status to EcountCore |
| `NAOT_Cards_Status_Prepare` | `dbo/Stored Procedures/NAOT_Cards_Status_Prepare.sql` | Prepares NAOT card status |
| `paypoint_call_audit_insert` | `dbo/Stored Procedures/` | Inserts Paypoint call audit record |
| `paypoint_encashment_settlement_file_cleanup` | `dbo/Stored Procedures/` | Cleans up processed settlement records |
| `paypoint_encashment_settlement_file_header_trailer_insert` | `dbo/Stored Procedures/` | Inserts file header/trailer |
| `paypoint_encashment_settlement_file_header_trailer_update` | `dbo/Stored Procedures/` | Updates file header/trailer |
| `paypoint_encashment_settlement_file_insert` | `dbo/Stored Procedures/` | Inserts settlement records |
| `refund_process` | `dbo/Stored Procedures/refund_process.sql` | Processes ATM fee refunds |
| `smots_account_status_sync` | `dbo/Stored Procedures/` | Syncs SMOTS account status with EcountCore |
| `smots_account_status_update` | `dbo/Stored Procedures/` | Updates SMOTS account status |
| `smots_fast_payment_insert` | `dbo/Stored Procedures/` | Inserts SMOTS fast payment record |
| `smots_fetch_accounts_status_by_program` | `dbo/Stored Procedures/` | Fetches accounts by programme for SMOTS |
| `smots_fp_orig_msg_insert` | `dbo/Stored Procedures/` | Inserts SMOTS FP original message |
| `smots_set_processed_flag` | `dbo/Stored Procedures/` | Marks SMOTS records as processed |
| `usp_arroweye_return_mail_report_delete_per_filename` | `dbo/Stored Procedures/` | Deletes Arroweye return mail records by filename |

---

## Security Vulnerabilities — Detailed

### CRITICAL: `cvv_in` CHAR(2) in `fdr_process_dcaf_auth_data`

**File**: `dbo/Tables/fdr_process_dcaf_auth_data.sql`, line 47: `[cvv_in] CHAR (2) NULL`

The FDR DCAF (Daily Card Activity File) contains CVV validation data. The `cvv_in` column stores the CVV input from the authorisation transaction. Under PCI DSS v4.0.1 Requirement 3.3.1, **sensitive authentication data (SAD) must not be stored after completion of the authorisation process**. CVV is explicitly listed as SAD. Storing it in this table constitutes a PCI DSS violation regardless of whether the data is encrypted.

**Remediation**: 
1. Determine if this column is populated in production
2. If populated: immediately purge all values and modify the SSIS import procedure to null this field before INSERT
3. Modify the `FDR_Import_DD031.dtsx` SSIS package and any other ingestion pipeline to strip `cvv_in` at the point of ingestion
4. Notify QSA and initiate remediation tracking in compliance system

---

### CRITICAL: `cvv` VARCHAR(3) in `fdr_process_dd031_data`

**File**: `dbo/Tables/fdr_process_dd031_data.sql`, line 25: `[cvv] VARCHAR (3) NULL`
**Procedure**: `fdr_process_dd031_import.sql`, line 135: `,ds.[cvv]` — the import procedure explicitly copies the `cvv` field from the staging table to the permanent table.

This is a confirmed path where CVV data flows from FDR DD031 file → staging table → permanent process table. This is a **PCI DSS Requirement 3.3.1 violation** unless the FDR DD031 file provides a non-CVV value in this field (some processors use this field for a different purpose). **Must be investigated with FDR documentation and QSA.**

---

### HIGH: Dynamic SQL in `ecountcore_process_partition_maintain`

**File**: `dbo/Stored Procedures/ecountcore_process_partition_maintain.sql`

The procedure constructs SQL using string concatenation from values in `ecountcore_process_partition_control`:
- Line 97: `set @sql_to_run = replace(replace(replace(@switch_sql, '{table_name}',@table_name)...`
- `@table_name`, `@switch_table`, `@archive_table` come from cursor over `ecountcore_process_partition_control`

If a malicious actor with write access to `ecountcore_process_partition_control` inserts a crafted table name value, SQL injection could result in arbitrary SQL execution during the partition maintenance job.

**Remediation**: Validate table names against `sys.objects` before incorporating into dynamic SQL. Use `QUOTENAME()` function around table name variables.

---

### MEDIUM: Transient PAN in `fdr_process_dd031_data_stage`

The staging table `fdr_process_dd031_data_stage` temporarily holds plaintext card numbers. The `fdr_process_dd031_import` procedure purges them after mapping. However:
- If the procedure fails between the UPDATE (which sets `card_number = ''`) and the INSERT into the permanent table, the staging table may be in an inconsistent state
- Any query executed against the staging table during this window could expose PANs
- SQL Server query store, extended events, or DBA queries during this window could capture PANs

**Remediation**: Ensure `card_number = ''` purge in the UPDATE step occurs before any SELECT that might be logged. Consider encrypting the staging table column.

---

### MEDIUM: Cross-Database References Without Abstraction

**Evidence**: `fdr_process_dd031_import.sql`, lines 37-43: Direct three-part name references to `[ecountcore].[dbo].[core_card_master]`, `[ecountcore].[dbo].[fdr_card_account]`, `[ecountcore].[dbo].[fdr_card_account_detail]`

This creates a hard-coded dependency on the `ecountcore` database name. Renaming or migrating either database breaks this procedure.

**Remediation**: Use synonyms or linked server abstractions for cross-database references to enable independent database naming.

---

## Remediation Priority Matrix

| Priority | Finding | Action |
|---|---|---|
| P0 — Immediate | `cvv_in` in `fdr_process_dcaf_auth_data` | Audit population; purge if populated; modify ingestion to null field; notify QSA |
| P0 — Immediate | `cvv` in `fdr_process_dd031_data` (confirmed flow via import proc) | Confirm FDR DD031 field definition with FDR; purge if CVV; modify import to exclude; notify QSA |
| P1 — Within 30 days | Transient PAN in `fdr_process_dd031_data_stage` | Add error handling to ensure purge occurs; consider staging column encryption |
| P1 — Within 30 days | Dynamic SQL injection risk in partition maintain | Add `QUOTENAME()` and `sys.objects` validation for table names |
| P2 — Within 90 days | Cross-database hard-coded references | Replace with synonyms |
| P2 — Within 90 days | GENTRAN and legacy accounts | Audit and remove if services no longer active |
| P2 — Within 90 days | `report_full` account with elevated access | Review and restrict to minimum required permissions |
| P3 — Within 180 days | No CI/CD pipeline | Implement GitLab CI with schema validation and DBA approval gate |
