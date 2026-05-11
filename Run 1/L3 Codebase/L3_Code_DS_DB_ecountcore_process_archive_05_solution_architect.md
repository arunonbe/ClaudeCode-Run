# DS_DB_ecountcore_process_archive — Solution Architect View

## Technical Debt Summary

`Ecountcore_Process_Archive` inherits all PCI DSS violations from its source database (`Ecountcore_Process`) and permanently archives them. The critical `cvv_in` column in `fdr_process_dcaf_auth_data` — a PCI DSS Requirement 3.3.1 violation — is present in the archive schema, meaning any CVV data written to the process DB has been preserved indefinitely in the archive. Additionally, the partition maintenance stored procedure uses dynamic SQL without `QUOTENAME()` guards, and the database uses `[PRIMARY]` filegroup for all data — a storage management limitation for a long-term archive holding years of financial records.

---

## All Objects — Names and Purpose

### Partition Infrastructure

| Object | Type | File | Purpose |
|---|---|---|---|
| `ecountcore_process_archive_monthly_partition` | Partition Function | `001-Storage/001-partf-ecountcore_process_archive_monthly_partition.sql` | Monthly RIGHT-range date partitioning |
| `ecountcore_process_archive_scheme` | Partition Scheme | `001-Storage/002-parts-ecountcore_process_archive_scheme.sql` | Maps partition function to `[PRIMARY]` filegroup |

### Tables (13 main + 12 switch)

| Table | Type | Sensitivity |
|---|---|---|
| `ecountcore_process_archive_partition_control` | Control | Low |
| `citi_process_nacha_file` | Main | NACHA / Reg E |
| `citi_process_nacha_file_switch` | Switch | NACHA / Reg E |
| `fdr_process_atmach_star_file` | Main | Payment data |
| `fdr_process_atmach_star_file_switch` | Switch | Payment data |
| `fdr_process_dcaf_auth_data` | Main | **CRITICAL: `cvv_in` CHAR(2) — PCI SAD** |
| `fdr_process_dcaf_auth_data_switch` | Switch | **CRITICAL: `cvv_in` CHAR(2) — PCI SAD** |
| `fdr_process_dcaf_chd_data` | Main | **PCI CDE — cardholder data** |
| `fdr_process_dcaf_chd_data_switch` | Switch | **PCI CDE — cardholder data** |
| `fdr_process_dcaf_ticket_data` | Main | Transaction data |
| `fdr_process_dcaf_ticket_data_switch` | Switch | Transaction data |
| `fdr_process_debitach_file` | Main | ACH / Reg E |
| `fdr_process_debitach_file_switch` | Switch | ACH / Reg E |
| `fdr_process_nacha_file` | Main | NACHA / Reg E |
| `fdr_process_nacha_file_switch` | Switch | NACHA / Reg E |
| `fdr_process_report_cd_011` | Main | Card status |
| `fdr_process_report_cd_011_switch` | Switch | Card status |
| `fdr_process_report_cd_052` | Main | Balance reports |
| `fdr_process_report_cd_052_switch` | Switch | Balance reports |
| `fdr_process_report_cd_061` | Main | Activity reports |
| `fdr_process_report_cd_061_switch` | Switch | Activity reports |
| `fdr_process_report_us_address_validation` | Main | **PII — address data (CCPA/GDPR)** |
| `fdr_process_report_us_address_validation_switch` | Switch | **PII — address data** |
| `fdvs_process_ivr_capture_file_data` | Main | IVR capture |
| `fdvs_process_ivr_capture_file_data_switch` | Switch | IVR capture |

### Stored Procedures (1)

| Object | File | Purpose |
|---|---|---|
| `ecountcore_process_archive_partition_maintain` | `003-Stored Procedures/001-sproc-ecountcore_process_archive_partition_maintain.sql` | Monthly partition split, archive expiry, and merge for the archive DB |

### Security Roles (6)

| Role | File | Purpose |
|---|---|---|
| `ecountcore_process_archive_Delete` | `099-Security/001-role-ecountcore_process_archive_Delete.sql` | DELETE permission on archive tables |
| `ecountcore_process_archive_Execute` | `099-Security/002-role-ecountcore_process_archive_Execute.sql` | EXECUTE on stored procedures |
| `ecountcore_process_archive_Select` | `099-Security/003-role-ecountcore_process_archive_Select.sql` | SELECT on archive tables |
| `ecountcore_process_archive_Update` | `099-Security/004-role-ecountcore_process_archive_Update.sql` | UPDATE on archive tables |
| `FortiDBRptRole` | `099-Security/005-role-FortiDBRptRole.sql` | FortiDB DAM reporting |
| `gers_role` | `099-Security/006-role-gers_role.sql` | GRC monitoring |

---

## Security Vulnerabilities — Detailed

### CRITICAL: `cvv_in` CHAR(2) in `fdr_process_dcaf_auth_data` (Archived)

**File**: `20210823-Initial-Base/002-Tables/004-tbl-fdr_process_dcaf_auth_data.sql`

The `cvv_in` column stores the CVV value from FDR DCAF (Daily Card Activity File) authorisation records. Under PCI DSS v4.0.1 Requirement 3.3.1, Sensitive Authentication Data including CVV **must not be stored after authorisation completion**, and this prohibition applies regardless of encryption. The `cvv_in` column exists in the archive database and receives data from the process database through the partition switch and INSERT process.

The severity of this finding in the archive database is higher than in the process database: because the archive database is designed for long-term retention (potentially 5-7 years), any CVV data that reached this table has been stored for far longer than PCI DSS permits.

**Remediation**:
1. Immediately execute a targeted `UPDATE fdr_process_dcaf_auth_data SET cvv_in = NULL WHERE cvv_in IS NOT NULL` to purge any archived CVV values
2. Verify purge with `SELECT COUNT(*) FROM fdr_process_dcaf_auth_data WHERE cvv_in IS NOT NULL`
3. Modify the `Ecountcore_Process.ecountcore_process_partition_maintain` stored procedure to null `cvv_in` before the INSERT into this archive table
4. Document remediation steps and notify QSA with evidence of purge
5. Consider `ALTER TABLE fdr_process_dcaf_auth_data DROP COLUMN cvv_in` after purge to prevent future storage

---

### HIGH: Dynamic SQL Without QUOTENAME in `ecountcore_process_archive_partition_maintain`

**File**: `20210823-Initial-Base/003-Stored Procedures/001-sproc-ecountcore_process_archive_partition_maintain.sql`

The partition maintenance procedure constructs SQL using string concatenation from values in `ecountcore_process_archive_partition_control`:
- `@table_name`, `@switch_table`, `@archive_table` come from cursor over the control table
- These values are concatenated directly into dynamic SQL executed via `EXEC(@sql_to_run)`
- `QUOTENAME()` is not applied to any table name variables before concatenation

If a principal with INSERT or UPDATE access to `ecountcore_process_archive_partition_control` modifies a table name value to include SQL injection payload (e.g., `]; DROP TABLE fdr_process_dcaf_chd_data; --`), the maintenance procedure would execute the payload with the permissions of the SQL Server Agent service account.

**Remediation**:
```sql
-- Before: SET @sql = '...FROM ' + @table_name + '...'
-- After:
IF NOT EXISTS (SELECT 1 FROM sys.objects WHERE name = @table_name AND type = 'U')
    RAISERROR('Invalid table name in partition control: %s', 16, 1, @table_name);
SET @sql = '...FROM ' + QUOTENAME(@table_name) + '...'
```

---

### MEDIUM: `[PRIMARY]` Filegroup for All Archive Data

**File**: `20210823-Initial-Base/001-Storage/002-parts-ecountcore_process_archive_scheme.sql`

The partition scheme maps all partitions to `[PRIMARY]`. For a database designed to hold years of regulatory-required financial data, this limits:
- Filegroup-level backup and restore (cannot independently back up or restore cold partitions)
- Storage tiering (cannot move old partitions to cheaper storage)
- Filegroup-level encryption configuration

**Remediation**: Add dedicated filegroups (`ARCHIVE_FG1`, `ARCHIVE_FG2`, etc.) in a future migration and remap the partition scheme using `$PARTITION` boundary alterations.

---

### MEDIUM: No Rollback Capability for Data Deletion Scripts

**File**: `20210824-US565-Fix-monthly-database-archive/002_dml_manual_delete_dcaf_auth_data.sql`

The US565 bug fix included a manual data deletion DML script against `fdr_process_dcaf_auth_data`. There is no corresponding rollback script in the change set. If executed incorrectly or against the wrong environment, the deleted rows cannot be recovered without a pre-execution database backup.

**Remediation**: Require that all DML change set scripts include a corresponding rollback script or explicitly document that a pre-execution backup was taken and retained.

---

### LOW: PII in `fdr_process_report_us_address_validation`

**File**: `20210823-Initial-Base/002-Tables/012-tbl-fdr_process_report_us_address_validation.sql`

The US address validation report table contains cardholder address data — PII under CCPA (California Consumer Privacy Act) and GDPR for any EU cardholders. This data is archived alongside payment processing records. Access to this table should be restricted to roles that have a documented business need and the `ecountcore_process_archive_Select` role membership should be reviewed for compliance with minimum necessary access principles.

---

## Remediation Priority Matrix

| Priority | Finding | Action |
|---|---|---|
| P0 — Immediate | `cvv_in` in archived `fdr_process_dcaf_auth_data` | Purge all non-null `cvv_in` values; modify process DB maintenance SP to null field before archiving; notify QSA |
| P1 — Within 30 days | Dynamic SQL injection in `ecountcore_process_archive_partition_maintain` | Add `QUOTENAME()` and `sys.objects` validation for all table name variables |
| P1 — Within 30 days | Retention period values (`online_months`) | Confirm values against NACHA (2yr), Reg E (24mo), and state law requirements; document with Legal/Compliance sign-off |
| P2 — Within 90 days | `[PRIMARY]` filegroup for all data | Introduce dedicated filegroups in any migration plan; document storage architecture |
| P2 — Within 90 days | No CI/CD for archive DB migration scripts | Add GitLab CI with DBA approval gate for migration script deployment |
| P3 — Within 180 days | PII in address validation table | Review `ecountcore_process_archive_Select` role membership; consider tokenisation of address fields beyond what is needed for dispute resolution |
