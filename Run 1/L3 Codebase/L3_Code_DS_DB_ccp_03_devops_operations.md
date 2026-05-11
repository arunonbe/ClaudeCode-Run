# DS_DB_ccp — DevOps and Operations View

## 1. Build System

The CCP database is packaged as a Visual Studio SSDT project (`CCP.sqlproj` / `CCP.sln`) targeting `Microsoft.Data.Tools.Schema.Sql.Sql110DatabaseSchemaProvider` (SQL Server 2012). The project structure includes:
- `dbo/Tables/` — 23 DDL files (production + staging + archive)
- `dbo/Stored Procedures/` — 12 procedure files
- `Storage/CCP_DATA.sql` — filegroup definition

The DACPAC publish model allows differential deployments against a target database. No CI/CD pipeline files (GitHub Actions, Azure DevOps) were found in this repository.

---

## 2. CI/CD Assessment

**No CI/CD pipeline exists in this repository.** No workflow files were found under `.github/` or any other CI directory. This means:

- Schema changes are deployed manually by a DBA using SSDT Visual Studio publish or `sqlpackage.exe`.
- No automated testing, linting, or deployment gates exist for schema changes.
- There is no pull-request–gated deployment process for the CCP database.

**Gap**: For a database that receives daily PII-containing (SSN, DOB) files from the financial institution, the lack of a controlled deployment pipeline means schema changes could inadvertently alter the staging→production load logic, corrupt archive triggers, or drop columns that downstream reports depend on — with no automated detection.

---

## 3. Database Change Management

### DeltaSql
No `DeltaSql/` directory was found in the CCP repository. This contrasts with `DS_DB_cf_report` which has an active delta-SQL change management pattern. Delta scripts may be managed in a separate repository or communicated informally.

### Archive Trigger Pattern
The delete-archive trigger pattern provides an implicit change-management safety net: any `DELETE` statement (including the upsert-by-replace in stored procedures) automatically archives the previous data snapshot. This reduces the risk of accidental data loss but does not address column schema changes.

---

## 4. Data Loading Operations

### Package Execution Model
The `package_execution` table tracks SSIS package (or SQL Agent job step) executions:
```
PackageID | ExecutionStartDateTime | ExecutionEndDateTime | ExecutionStatus | BatchDate | ...
```
The `get_package_last_execution_date` stored procedure returns the last successful `BatchDate` per `PackageID`, enabling idempotent re-runs (the `remove_package_imported_data` procedure can purge a previously loaded batch before re-importing).

### Daily Processing Sequence
Based on stored procedures and staging tables, the inferred daily processing sequence is:
1. FI delivers batch files for each data type (account, transaction, balance, card status).
2. SSIS packages load file data into `*_STG` tables.
3. `set_package_execution` records job start.
4. Stored procedures (`sp_process_NAM_BIN_ACCOUNTS`, etc.) promote data from staging to production.
5. Previous batch data for the same `BatchDate` + `FinancialInstitution` is deleted (auto-archived by trigger) before new data is inserted.
6. `package_execution` is updated with completion status.

---

## 5. Monitoring

- `package_execution` and `package_execution_log` provide operational job-execution history for monitoring.
- `FISERV_INVENTORY` tracks card stock; a `Below Min` flag enables alerting when inventory drops below threshold.
- **Gap**: No SiteScope integration, no alerting stored procedures, and no error-notification mechanism was found in CCP. The DBA must query `package_execution` manually (or via a monitoring tool that queries this table) to detect job failures.

---

## 6. Environments

No environment-specific configuration files were found. The `Storage/CCP_DATA.sql` file contains just the filegroup reference:
```sql
-- CCP_DATA filegroup
```
No server-specific paths, environment variables, or configuration tables exist in the schema.

---

## 7. Backup and Recovery

No backup configuration is present. Backup is handled by `DS_DB_database_maintenance`. The archive trigger pattern means deleted records are retained in `*_ARCHIVE` tables and can be used for point-in-time data recovery of specific batch records without a full database restore.

### Archive Table Risk
The `*_ARCHIVE` tables are production database objects — they are subject to the same backup/recovery as other tables. However, they are never truncated, making them unbounded growth tables over time. For a database receiving daily batch files with SSN and DOB data, archive table size will grow substantially over years.

---

## 8. Operational Risks

### Risk 1: SSN and DOB in Staging Tables (CRITICAL)
`NAM_BIN_ACCOUNTS_STG` is a transient staging table that holds SSN and DOB data during the load window. If a job fails mid-load, this data remains in the staging table indefinitely. Staging tables often have weaker access controls, monitoring, and encryption management than production tables.

**Mitigation**: Enforce same access controls and TDE on staging tables as production tables; add a cleanup step to truncate staging tables after successful promotion.

### Risk 2: SSN Transmitted in File (HIGH)
The SSN column is populated from FI-delivered batch files. The file transport mechanism (SFTP, Azure Data Factory, etc.) for files containing SSN data must be secured with encryption in transit and access logging.

### Risk 3: Archive Tables Grow Unbounded (MEDIUM)
`TR_NAM_BIN_ACCOUNTS_D` fires on every `DELETE` (including the upsert-by-replace operation in `sp_process_NAM_BIN_ACCOUNTS`). This means every daily batch cycle inserts the previous day's ~N account records into `NAM_BIN_ACCOUNTS_ARCHIVE`. For a large program, archive table size could reach hundreds of millions of rows within a few years.

### Risk 4: SQL Server 2012 Target (HIGH)
DACPAC targets `Sql110DatabaseSchemaProvider` (SQL Server 2012). End of Support 12 July 2022. No security patches issued for known SQL Server vulnerabilities since that date.

### Risk 5: No Automated Testing (HIGH)
No test scripts or tSQLt tests exist. The upsert-by-replace logic in stored procedures could silently fail with a `ROLLBACK` (caught by `BEGIN CATCH`), leaving staging data but no production data for a given batch date.
