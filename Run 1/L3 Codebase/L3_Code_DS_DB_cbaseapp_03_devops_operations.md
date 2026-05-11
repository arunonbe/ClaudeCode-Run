# DS_DB_cbaseapp — DevOps and Operations View

## 1. Build System

The repository is structured as a **Visual Studio SQL Server Data Tools (SSDT) Database Project** (`Cbaseapp.sqlproj`, `Cbaseapp.sln`). The project targets:
- MSBuild framework: ToolsVersion 4.0
- SQL Server schema provider: `Microsoft.Data.Tools.Schema.Sql.Sql110DatabaseSchemaProvider` (SQL Server 2012 / 110 compatibility level)
- Target framework: .NET 4.6.1
- Build outputs: `bin\Debug\Cbaseapp.sql` and `bin\Release\Cbaseapp.sql` (DACPAC-based deployment script)

The project uses `IncludeCompositeObjects=True` and `DeployToDatabase=True`, meaning the DACPAC publish process will compare the model against a live target database and generate a differential deployment script.

---

## 2. CI/CD Pipeline

### GitHub Actions — CodeQL
- File: `.github/workflow/CodeQL.yaml`
- Triggers: `push`, `pull_request`, `workflow_dispatch`, and weekly scheduled scan (`cron: '36 14 * * 2'`)
- Reuses a shared Onbe organisation workflow: `Onbe/om-ci-setup/.github/workflows/codeql-auto.yml@main`
- **No build, test, or deployment steps exist in this repository's workflow.** CodeQL provides static analysis only.

### Deployment Process
- No pipeline stages, environment gates, or deployment workflow files exist in `.github/workflow/` beyond CodeQL.
- Deployment is inferred to be manual or orchestrated externally (likely via SSDT `sqlpackage.exe` publish operations or DBA-executed scripts from the `DeltaSql/` folder).
- The `DeltaSql/` directory is present (visible in the project root) but no files were found at read time, suggesting it was empty or is populated at deployment time.

**Gap**: There is no automated deployment pipeline for schema changes. This means database changes rely on manual DBA execution, which creates risks around change tracking, environment parity, and rollback.

---

## 3. Database Change Management

### DeltaSql Pattern
The repository root contains a `DeltaSql/` folder. Based on patterns observed in other Onbe database repos (e.g., `DS_DB_cf_report` which has dated `DeltaSql/YYYY-MM-DD/TICKET/` sub-folders with numbered scripts and rollback scripts), cbaseapp likely follows the same delta-script convention:
- Forward scripts numbered `1__description.sql`, `2__description.sql`, etc.
- Rollback counterparts in `rollback/` sub-folders
- Linked to JIRA/Jira-like ticket identifiers

### Data Migration Scripts
The `dbo/data/` folder contains static data scripts:
- `MasterData.sql` — reference data inserts
- `Insert_affiliate_fieldname_enable_mpv_login_bugfix_EQL1508.sql` — hotfix data patch linked to ticket EQL-1508
- `Insert_affiliate_field_lookup_enable_mpv_login_bugfix_EQL1508.sql` — companion data fix
- `Recover_affiliate_fieldname_enable_mpv_login_bugfix_EQL1508.sql` — rollback/recovery script
- `affiliate_locale_copy_sanction_errors.sql` — sanction list error data

These scripts suggest a manual patch-and-recover workflow rather than a migration framework (Flyway, Liquibase, etc.).

---

## 4. Environments

No environment-specific configuration files were found. The CodeQL YAML uses `$(ESCAPE_SQUOTE(SRVR))` server-token patterns in related maintenance repos, suggesting SQL Agent token substitution is used for server-name resolution. The maintenance job definitions disable jobs on servers whose name begins with `'C'` (test/CI servers), using:
```sql
DECLARE @enabled TINYINT = CASE WHEN LEFT(@@SERVERNAME,1) = 'C' THEN 0 ELSE 1 END
```
This convention implies at least:
- `C`-prefix: non-production / CI
- Other prefix (e.g., `V` for VSQL, production): production

Referenced server names in cross-database queries within cbaseapp stored procedures include `VSQL3.ecountcore` and `VSQL1.webcert`, indicating production SQL Server instances.

---

## 5. Backup and Recovery

No backup scripts are included in this repository. Backup is managed by:
1. The `DS_DB_database_maintenance` repository (Ola Hallengren maintenance solution)
2. SQL Server Agent jobs defined in `msdb` (not captured in this repo)

Key recovery considerations for cbaseapp:
- **RTO**: Given cbaseapp is the primary cardholder database, RTO should be in the minutes-to-low-hours range for a PCI-compliant environment.
- **RPO**: Full transaction logging is implied by the OLTP nature; log backup frequency is not defined in this repo.
- **Point-in-time recovery**: Requires SQL Server full backup + differential + log backup chain. No configuration files confirm recovery model (FULL vs SIMPLE).

---

## 6. Monitoring

### Application-Level Monitoring
- `SiteScopeLog` table stores SiteScope health-check log entries, indicating HP SiteScope (or compatible) monitoring integration.
- `b2c_login_statistics` tracks monthly login volume per user.
- `login_history` tracks authentication attempts (used by account-lockout logic in `b2c_login_user`).

### Database-Level Monitoring
Monitoring infrastructure is provided by `DS_DB_dbadmin` (separate repo). The `dbadmin` procedures that reference cbaseapp include:
- `check_refund_extract_TMW` — cross-database query into `ecountcore` from `dbadmin` for refund extraction
- DBA tables in `dbadmin` (`EcountcoreTables`, `ecountcore_filestats`, `EcountCore_TableGrowth`) track growth of cbaseapp/ecountcore tables

---

## 7. Operational Risks

### Risk 1: No Automated Deployment Pipeline (HIGH)
Schema changes are deployed manually via SSDT publish or DBA scripts. This creates risk of:
- Deployment errors not caught by automated checks
- Environment drift between development, UAT, and production
- Rollback difficulty if a deployment fails mid-script

### Risk 2: Legacy SQL Server 2012 Target (HIGH)
The DACPAC targets `Sql110DatabaseSchemaProvider` (SQL Server 2012). SQL Server 2012 reached End of Support on 12 July 2022. If production runs on a newer version without changing the DACPAC target, schema compatibility issues may arise. If production is still on SQL Server 2012, it receives no security patches.

### Risk 3: Dynamic SQL Without Parameterisation in CSA Procedures (CRITICAL)
`csa_forward_search` (line 54–65) builds a query by string-concatenating user-supplied parameters directly into `@strSQL` and calls `Exec (@strSQL)`. This is an unparameterised dynamic SQL injection vector. Although a `Print @strSQL` / commented-out `Exec` suggests the production version may have this disabled, the code is in source control and the exec call is present. See `05_solution_architect.md`.

### Risk 4: Partition Maintenance Stored Procedure (MEDIUM)
`cbaseapp_process_partition_maintain` uses `sp_executesql` for dynamic DDL — acceptable if inputs are controlled, but requires review.

### Risk 5: Cross-Database Linked Server Queries (MEDIUM)
`csa_GetEcountHist` constructs a view at runtime using `EXEC(@strSql)` that references `VSQL3.ecountcore.dbo.core_transaction_journal` and `VSQL1.webcert.dbo.bank1_late_debit` via hardcoded linked-server names. If linked server topology changes, this procedure will silently fail. The procedure also drops and recreates a view dynamically.

### Risk 6: No Automated Testing (HIGH)
No test scripts, tSQLt tests, or integration test artifacts were found in the repository. Changes to 781 stored procedures lack regression coverage.

---

## 8. SQL Agent Jobs Related to cbaseapp

Based on stored procedures and table naming, the following SQL Agent jobs likely target cbaseapp (defined in msdb outside this repo):
- Fraud score batch update (calls `proc_fraud_score_batch_upd`)
- Card balance debit job (calls `card_balance_debit_update_job`)
- Batch messages status process (calls `batch_messages_status_process`)
- eNotify processing (uses `enotify_task_queue`)
- Partition maintenance (calls `cbaseapp_process_partition_maintain`)
- DDL session-login rotation (calls `ddl_create_session_login` monthly)
