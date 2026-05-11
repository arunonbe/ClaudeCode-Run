# DS_DB_ecountcore_process — DevOps and Operations View

## Build System

- **Project Type**: SQL Server Database Project (`.sqlproj`)
- **Solution File**: `Ecountcore_process.sln`
- **Target SQL Server**: SQL Server 2016 (`Sql130DatabaseSchemaProvider`)
- **Target Framework**: .NET 4.6.1 (toolchain target)
- **Output**: DACPAC artifact via MSBuild/SSDT

---

## CI/CD Pipeline

**No CI/CD pipeline is configured.** No `.gitlab-ci.yml` is present. The `development` branch is active. Deployment is manual via SSDT Publish or `sqlpackage.exe`.

---

## Storage Configuration (`Storage/` folder)

This repository is the only one of the six that includes explicit storage configuration:

| File | Contents |
|---|---|
| `Storage/ecountcore_process_monthly_partition.sql` | Partition function `ecountcore_process_monthly_partition` — monthly date-range partitioning |
| `Storage/ecountcore_process_monthly_scheme.sql` | Partition scheme `ecountcore_process_monthly_scheme` — maps partition function to filegroup |
| `Storage/ECP_FG1.sql` | Filegroup definition `ECP_FG1` — dedicated filegroup for partitioned data |

The partition function uses RIGHT range partitions on DATETIME boundaries (first of each month), enabling partition switching for archive operations.

---

## Partition Maintenance Operations

The `ecountcore_process_partition_maintain` stored procedure performs ongoing partition lifecycle management:
1. **Split**: Creates new partitions for the current month and next month if they don't exist
2. **Switch + Archive**: For each table in `ecountcore_process_partition_control`, switches expired partitions (older than `online_months`) to the corresponding switch table, inserts data into the archive database, then truncates the switch table
3. **Merge**: Cleans up empty partitions that are beyond the maximum retention period

This procedure should be scheduled to run monthly (e.g., first day of month) via SQL Server Agent.

---

## Database Change Management

The `development` branch is active. Security scripts are extensive (40+ files). The pattern of `_1` suffix on some security files (e.g., `B2C_1.sql`, `brigantine_1.sql`) suggests incremental permission grants were added over time without refactoring the original file — ad-hoc change management.

---

## Environments

Service account names in Security scripts confirm:

| Environment | Accounts |
|---|---|
| Production | `NAM\PPA_PRD_*SVC`, `NAM\PROD`, `NAM\PROD_CPP`, `NAM\PROD_ITOPS`, `NAM_PPA_PRD_SQL` |
| UAT | `NAM\UAT` |
| Monitoring | `gers_role`, `gers_read`, `FortiDBRptRole` |
| Security/Audit | `ifs_gidadb`, `ifs_infosec`, `NAM\ISA_SQL_SECADMIN` |
| Emergency | 18+ `emer_*` accounts |

Additional roles not in `DS_DB_ecountbatchjobrepository`:
- `NAM_PPA_PRD_SQL` — direct SQL access account
- `NAM_PPA_PRD_ABAT` — automated batch account
- `brigantine` — additional service/application account
- `GENTRAN` — EDI/file transfer (Sterling Gentran) account
- `vascan` — vulnerability scanning account
- `report`, `report_full`, `report_readonly` — reporting roles
- `workbench` — admin workbench tool account
- `application_owner` — database owner-level account

---

## Backup and Recovery

The `Ecountcore_Process` database has different recovery characteristics from `Ecountcore`:
- Historical processing data (processed files) has lower RPO requirements than live cardholder data
- **However**: In-flight processing records (files currently being processed) must survive failures to prevent duplicate processing or missed transactions
- Partition-switched data that hasn't yet been copied to the archive database is at risk if backup is missed
- The partition control table (`ecountcore_process_partition_control`) and file status tables are critical for resuming after a failure

### Recovery Scenario
If the database is lost after a file is imported to `fdr_process_dd031_data_stage` but before `fdr_process_dd031_import` completes: the source FDR file still exists on the filesystem; the file can be re-imported with appropriate file_id re-creation.

---

## Operational Risks

| Risk | Severity | Detail |
|---|---|---|
| `cvv_in` column in `fdr_process_dcaf_auth_data` | Critical | If populated from FDR DCAF files, this is a PCI DSS violation (CVV stored post-authorisation) |
| `cvv` column in `fdr_process_dd031_data` | Critical | Same issue — CVV from FDR settlement file retained |
| `fdr_process_dd031_data_stage` with transient PAN | High | The import procedure (`fdr_process_dd031_import`) purges the card_number after mapping to card_hash. If the procedure fails mid-execution, PANs may remain in the staging table. |
| Dynamic SQL in partition maintenance | Medium | `ecountcore_process_partition_maintain` uses `exec(@sql_to_run)` with string concatenation. Table name and archive table values come from `ecountcore_process_partition_control` — if this table is modified by an attacker, SQL injection via table names is theoretically possible. |
| Partition maintenance failures | High | If `ecountcore_process_partition_maintain` fails, partitions accumulate, potentially filling disk and causing database outages |
| 40+ user accounts including reporting and workbench | Medium | `report_full` and `workbench` with elevated access should be reviewed for least-privilege compliance |
| GENTRAN account access | Medium | EDI/Gentran file transfer account — if Gentran is no longer in use, this account should be removed |
| No CI/CD for CDE-adjacent database | High | Manual deployment risk to database containing CVV-class data |
