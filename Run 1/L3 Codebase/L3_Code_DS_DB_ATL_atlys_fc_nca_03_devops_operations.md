# DevOps / Operations Analysis — DS_DB_ATL_atlys_fc_nca (atlys_fc_nca)

## Build Technology

SSDT `.sqlproj` project, MSBuild ToolsVersion 4.0, provider `Sql100DatabaseSchemaProvider`. Configuration is identical to `atlys_e`: two build configurations (Debug / Release) producing `atlys_fc_nca.sql` output scripts. `<DeployToDatabase>True</DeployToDatabase>`.

Active git branch is `development` (confirmed from `.git/refs/heads/development`), whereas `atlys_e` uses `master`. This difference in branching conventions within the same platform indicates inconsistent source control practices across the Atlys database suite.

---

## CI/CD Pipeline

**No CI/CD configuration files are present.** No pipeline YAML, no publish profiles, no deployment scripts. The same finding as `atlys_e` — manual DBA deployment is the implied practice.

---

## Environments

Security directory files indicate the same multi-environment structure as `atlys_e`:

| Login / File | Implied environment |
|---|---|
| NAM_PROD / NAM_PROD_1 | Production |
| NAM_PROD_CPP | Production CPP |
| NAM_PROD_ITOPS / NAM_PROD_ITOPS_1 | Production IT Operations |
| NAM_UAT / NAM_UAT_1 | UAT |
| NAM_PPA_PRD_ATLYS / NAM_PPA_PRD_ATLYS_1 | PPA Production |

No `NAM_PROD_CPP_APAC` or `NAM_ppa_prd_ABAT` files are present in this repo (unlike `atlys_e`), suggesting the NCA fee-calculation database does not serve APAC or ABAT entities. This is consistent with its regional scope.

---

## Deployment and Migration Approach

State-based SSDT deployment. No migration scripts. Same rollback limitations as `atlys_e`:
- Prior dacpac required for schema rollback.
- Database backup required for data rollback.

The `<Recovery>BULK_LOGGED</Recovery>` setting limits point-in-time recovery capability.

The `sys_copy_table_data` procedure (`dbo/Stored Procedures/sys_copy_table_data.sql`) is a notable utility — it dynamically creates table copies using `SELECT … INTO` or `INSERT INTO`. This procedure is used for data migration/copying within the database and requires the calling account to have `CREATE TABLE` permission. Its use in production (vs. as a migration utility) warrants operational control.

---

## Cross-Database Dependency Operations

`atlys_fc_nca` makes heavy use of cross-database calls to `ATLYS_E.dbo.*`:
- Authentication checks: `ATLYS_E.dbo.sys_chkstr`, `ATLYS_E.dbo.sys_chkuser`, `ATLYS_E.dbo.sys_cinfo`
- Aggregate helpers: `ATLYS_E.dbo.sys_aggr_date`, `ATLYS_E.dbo.sys_aggrt`, `ATLYS_E.dbo.sys_aggrt2`
- Path resolution: `ATLYS_E.dbo.sys_vPaths`

All of these are dependency-bound to the name `ATLYS_E`. Any maintenance window or outage for `atlys_e` directly impacts the ability of this database to execute its calculation procedures.

Additionally, `sys_calc_dormancy.sql` (line 43) contains the explicit test:
```sql
AND CAST(@@SERVERNAME AS char(1)) IN ('Q', 'P', 'C')
```
This is a hard-coded server-name prefix check to determine whether to use SSAS cube data. This means:
- Any server whose name does not start with Q (QA), P (Production), or C (likely another production variant) will bypass the cube data path and use fallback logic.
- This logic is **environment-detection code embedded in a stored procedure** — an anti-pattern that makes environment promotion risky.

---

## Operational Risks

### Risk 1 — Server-Name-Based Logic in Production Code
`sys_calc_dormancy.sql` line 43: `CAST(@@SERVERNAME AS char(1)) IN ('Q', 'P', 'C')` — hard-coded server prefix check to determine data source. If the server is renamed or migrated to a new hostname, the SSAS cube path will be bypassed silently, causing the maintenance fee calculation to use fallback logic rather than actual historical data. This could result in materially incorrect amortisation calculations posted to the GL.  
**Risk level: Critical. Silent financial calculation error.**

### Risk 2 — BULK_LOGGED Recovery Model
Same as `atlys_e`. Point-in-time recovery not available during bulk operations.

### Risk 3 — No TDE
Financial forecast data, fee rates, BIN data, and commission amounts stored in unencrypted database files.

### Risk 4 — Branching Inconsistency
`atlys_fc_nca` uses `development` branch as the default; `atlys_e` uses `master`. Inconsistency suggests different teams or different standards are managing these repos, increasing risk of misaligned deployments.

### Risk 5 — Dynamic Table Copy in Production
`sys_copy_table_data` dynamically creates or populates tables using `sp_executesql` with table names as parameters. This procedure requires broad DDL permissions if creating new tables, and the input validation (via `sys_chkstr`) may not cover all DDL-injection vectors in table/column names. Use in production contexts should be tightly controlled with explicit EXECUTE grants limited to DBA roles only.

### Risk 6 — Cursor-Based Amortisation
`sys_calc_dormancy.sql` uses iterative WHILE loops (not explicit cursors, but equivalent set-processing row iteration) over month periods. For programs with long histories (e.g., 10+ years of issuance data), these loops can run for many minutes. There is no time-limit safeguard or error handling wrapping the amortisation calculation. A runaway calculation could block other transactions on `tblForecast_data`.

### Risk 7 — No Error Handling in Calculation Procedures
`sys_calc_issue.sql`, `sys_calc_dormancy.sql`, and related procedures do not contain TRY/CATCH blocks. An arithmetic overflow or null-propagation error will raise a SQL Server error that bubbles to the application layer without rollback or audit logging. In a financial calculation context, partial writes (some rows updated, error before completion) could leave `tblForecast_data` in an inconsistent state.

### Risk 8 — TEXT Data Type
`tblForecast_data.notes` column uses the deprecated `TEXT` data type. `TEXT` columns have restrictions in JOINs and string functions, and are deprecated in modern SQL Server. They should be migrated to `NVARCHAR(MAX)`.

---

## Monitoring Considerations
- FortiDB DAM agent present (FortiDBRptRole).
- GTS read-only DBA access configured (NAM_GTS_MSSQL_DBA_RO).
- No SQL Agent jobs visible in codebase.
- No alerting on calculation failures or data anomalies.
- Recommendation: Implement SQL Agent jobs to detect stale forecast data (e.g., programs with no forecast update in >30 days) and alert the finance team.
