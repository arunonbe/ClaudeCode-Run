# DS_DB_ecountcore_process_archive — Data Architect View

## Database Overview

- **Database Name**: `Ecountcore_Process_Archive`
- **Repository Type**: Migration script repository (not SSDT project)
- **Change Set Format**: Dated folder (`YYYYMMDD-StoryID-description`) containing numbered SQL files
- **Active Branch**: `main`
- **Initial Deployment**: 2021-08-23
- **Change Sets**: 2 (initial base + one fix)

---

## Migration Change Sets

### 20210823-Initial-Base

The initial base schema containing all objects.

**Execution Order (numbered files):**

| File | Type | Object |
|---|---|---|
| `001-Storage/001-partf-ecountcore_process_archive_monthly_partition.sql` | Partition Function | `ecountcore_process_archive_monthly_partition` |
| `001-Storage/002-parts-ecountcore_process_archive_scheme.sql` | Partition Scheme | `ecountcore_process_archive_scheme` |
| `002-Tables/001-tbl-ecountcore_process_archive_partition_control.sql` | Table | `ecountcore_process_archive_partition_control` |
| `002-Tables/002-tbl-citi_process_nacha_file.sql` | Table | `citi_process_nacha_file` |
| `002-Tables/002-tbl-citi_process_nacha_file_switch.sql` | Table | `citi_process_nacha_file_switch` |
| `002-Tables/003-tbl-fdr_process_atmach_star_file.sql` | Table | `fdr_process_atmach_star_file` |
| `002-Tables/003-tbl-fdr_process_atmach_star_file_switch.sql` | Table | `fdr_process_atmach_star_file_switch` |
| `002-Tables/004-tbl-fdr_process_dcaf_auth_data.sql` | Table | `fdr_process_dcaf_auth_data` |
| `002-Tables/004-tbl-fdr_process_dcaf_auth_data_switch.sql` | Table | `fdr_process_dcaf_auth_data_switch` |
| `002-Tables/005-tbl-fdr_process_dcaf_chd_data.sql` | Table | `fdr_process_dcaf_chd_data` |
| `002-Tables/005-tbl-fdr_process_dcaf_chd_data_switch.sql` | Table | `fdr_process_dcaf_chd_data_switch` |
| `002-Tables/006-tbl-fdr_process_dcaf_ticket_data.sql` | Table | `fdr_process_dcaf_ticket_data` |
| `002-Tables/006-tbl-fdr_process_dcaf_ticket_data_switch.sql` | Table | `fdr_process_dcaf_ticket_data_switch` |
| `002-Tables/007-tbl-fdr_process_debitach_file.sql` | Table | `fdr_process_debitach_file` |
| `002-Tables/007-tbl-fdr_process_debitach_file_switch.sql` | Table | `fdr_process_debitach_file_switch` |
| `002-Tables/008-tbl-fdr_process_nacha_file.sql` | Table | `fdr_process_nacha_file` |
| `002-Tables/008-tbl-fdr_process_nacha_file_switch.sql` | Table | `fdr_process_nacha_file_switch` |
| `002-Tables/009-tbl-fdr_process_report_cd_011.sql` | Table | `fdr_process_report_cd_011` |
| `002-Tables/009-tbl-fdr_process_report_cd_011_switch.sql` | Table | `fdr_process_report_cd_011_switch` |
| `002-Tables/010-tbl-fdr_process_report_cd_052.sql` | Table | `fdr_process_report_cd_052` |
| `002-Tables/010-tbl-fdr_process_report_cd_052_switch.sql` | Table | `fdr_process_report_cd_052_switch` |
| `002-Tables/011-tbl-fdr_process_report_cd_061.sql` | Table | `fdr_process_report_cd_061` |
| `002-Tables/011-tbl-fdr_process_report_cd_061_switch.sql` | Table | `fdr_process_report_cd_061_switch` |
| `002-Tables/012-tbl-fdr_process_report_us_address_validation.sql` | Table | `fdr_process_report_us_address_validation` |
| `002-Tables/012-tbl-fdr_process_report_us_address_validation_switch.sql` | Table | `fdr_process_report_us_address_validation_switch` |
| `002-Tables/013-tbl-fdvs_process_ivr_capture_file_data.sql` | Table | `fdvs_process_ivr_capture_file_data` |
| `002-Tables/013-tbl-fdvs_process_ivr_capture_file_data_switch.sql` | Table | `fdvs_process_ivr_capture_file_data_switch` |
| `003-Stored Procedures/001-sproc-ecountcore_process_archive_partition_maintain.sql` | Stored Procedure | `ecountcore_process_archive_partition_maintain` |
| `004-Inserts/001-insert-ecountcore_process_archive_partition_control.sql` | Data | Partition control configuration (retention settings) |
| `099-Security/001-role-ecountcore_process_archive_Delete.sql` | Role | `ecountcore_process_archive_Delete` |
| `099-Security/002-role-ecountcore_process_archive_Execute.sql` | Role | `ecountcore_process_archive_Execute` |
| `099-Security/003-role-ecountcore_process_archive_Select.sql` | Role | `ecountcore_process_archive_Select` |
| `099-Security/004-role-ecountcore_process_archive_Update.sql` | Role | `ecountcore_process_archive_Update` |
| `099-Security/005-role-FortiDBRptRole.sql` | Role | `FortiDBRptRole` |
| `099-Security/006-role-gers_role.sql` | Role | `gers_role` |

### 20210824-US565-Fix-monthly-database-archive

Bug fix applied one day after initial deployment:

| File | Purpose |
|---|---|
| `001_create_nci_fdr_process_dcaf_auth.sql` | Creates non-clustered index on `fdr_process_dcaf_auth_data` |
| `002_dml_manual_delete_dcaf_auth_data.sql` | Manual deletion of excess data in `fdr_process_dcaf_auth_data` |
| `003_drop_nci_fdr_process_dcaf_auth.sql` | Drops the temporary non-clustered index |
| `004_drop_pk_alter_batch_spa_create_pk.sql` | Alters the primary key of `fdr_process_dcaf_auth_data` (changes batch_spa/batch_date/batch_record_id PK structure) |
| `005_dml_archive_retention_online_months.sql` | Sets retention period in `ecountcore_process_archive_partition_control` |

---

## Sensitive Data Fields — Complete Flag

The archive tables are structurally identical to their source tables in `Ecountcore_Process`. All sensitivity flags carry over:

| Field | Table | Classification | PCI/Regulatory Flag |
|---|---|---|---|
| `cvv_in` CHAR(2) | `fdr_process_dcaf_auth_data` | **CVV / SAD** | **CRITICAL: PCI DSS Req 3.3.1 — if populated in source DB, this violation is archived here** |
| All cardholder data columns | `fdr_process_dcaf_chd_data` | **PCI CDE data** | Full column assessment required |
| NACHA records | `fdr_process_nacha_file`, `citi_process_nacha_file` | ACH routing/account | NACHA/Reg E |
| DDA numbers | Multiple tables | Account identifier | PCI scope |
| Address data | `fdr_process_report_us_address_validation` | **PII** | CCPA/GDPR |

---

## Partition Architecture

Identical pattern to `Ecountcore_Process`:

- **Partition Function**: `ecountcore_process_archive_monthly_partition` (monthly RIGHT ranges)
- **Partition Scheme**: `ecountcore_process_archive_scheme` (maps to `[PRIMARY]` filegroup — no dedicated filegroup for archive, unlike the process DB which has `ECP_FG1`)
- **Switch Tables**: `*_switch` variants of each main table for partition switch operations
- **Control Table**: `ecountcore_process_archive_partition_control` — stores per-table retention settings (`online_months`)
- **Maintenance Procedure**: `ecountcore_process_archive_partition_maintain` — identical logic to process DB procedure

---

## Key Architectural Observation

The archive uses `[PRIMARY]` filegroup rather than a dedicated filegroup. For a database holding years of historical financial data, storing everything on the PRIMARY filegroup limits storage management flexibility (e.g., cannot move cold partitions to cheaper storage). Recommend adding dedicated filegroups for archive storage in cloud migration (Azure SQL Hyperscale supports this natively).

---

## Data Retention Architecture

```
[Ecountcore_Process DB]
  Data beyond online_months
        ↓
  Partition switch to *_switch table
        ↓
  INSERT INTO [Ecountcore_Process_Archive].dbo.{table} (via archive_partition_maintain SP)
        ↓
  Truncate *_switch table
        ↓
[Ecountcore_Process_Archive DB]
  Data retained for archive_online_months
        ↓
  [Final deletion] when beyond archive retention period
```

The retention period values in `005_dml_archive_retention_online_months.sql` should be confirmed against:
- NACHA: 2-year minimum
- Reg E: 24 months minimum
- PCI DSS: minimum necessary, maximum as defined by legal/policy
- State laws: vary by state, some require 5-7 years for financial records
