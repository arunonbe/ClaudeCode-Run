# DS_DB_banker_na — DevOps & Operations View

## Build & Packaging
- **Project type**: SSDT `.sqlproj` (MSBuild `ToolsVersion="4.0"`, `TargetFrameworkVersion=v4.5`).
- **Project name**: `banker_na`; no solution file name is visible (no `.sln` in the root).
- **Schema provider**: `Microsoft.Data.Tools.Schema.Sql.Sql100DatabaseSchemaProvider` (SQL Server 2008).
- **Output type**: `Database` — produces a DACPAC.
- **`DeployToDatabase`: True** — configured for direct publish.
- **`SqlServerVerification`: False** — cross-database references to `ecountcore_ss` synonyms will not cause build failures even if the target database is unreachable.
- **`IncludeCompositeObjects`: True** — synonym targets are included in schema validation scope.

## Deployment
- Deployment mechanism: SSDT DACPAC publish or DBA-executed T-SQL scripts.
- No CI/CD pipeline configuration (no YAML, Jenkinsfile, or equivalent) is present in the repository.
- Synonyms reference a hardcoded production server name (`ppamwdcudsql1c1\ppamwdcudsql1c1`); deploying this project to a non-production environment will produce broken synonyms unless the synonym DDL is manually edited per environment.
- No pre/post-deployment scripts for data seeding or synonym remapping are present.
- The `Security` folder contains 30+ role and permission SQL files covering NAM_PROD, NAM_UAT, gers_read, gers_role, FortiDBRptRole, onus, scpardb, Banker roles (SELECT, UPDATE, DELETE, Execute), and individual logins — indicating a manual permission management approach rather than a DevOps-managed RBAC model.

## Configuration Management
- **`SSISConfigurations` table**: Runtime configuration (connection strings, SSIS package paths, value types) is stored in the database itself; there is no externally managed configuration store (e.g., Azure App Configuration, environment variables). This means SSIS packages can only be re-pointed by updating rows in this table.
- **Hardcoded synonym targets**: The four synonym files reference the production server name directly; environment-specific synonym definitions must be manually maintained or scripted outside the SSDT project.
- **`QueryStore` enabled**: Capture mode Auto, 100 MB, 30-day stale threshold.
- **`PageVerify: CHECKSUM`** — I/O integrity verification enabled.
- **`DelayedDurability: DISABLED`** — all commits are fully durable.
- **`AllowSnapshotIsolation: False`**, **`ReadCommittedSnapshot: False`** — shared-lock read semantics; concurrent reporting and writes will contend.

## Observability
- **`ab_process_plastic_status` table**: Records the status of each plastic processing run, enabling retrospective job-status queries. The `ab_process_plastic_update_status_sp` procedure writes error messages to this table on CATCH, providing a basic error log for card expiry processing.
- **`banker_action_log`** (in external `jobsvc` database): Provides a detailed audit trail of every banker action, but it is not directly observable from within `banker_na`.
- **`banker_reserved_source_log`**: Tracks changes to reserved source records with timestamps and user IDs.
- **No SQL Server Extended Events, Server Audit, or monitoring tables** are defined within this project.
- **No alerting mechanisms** (no Database Mail configuration, no SQL Agent job definitions) are present in this SSDT project.
- Error handling in plastic-processing procedures follows a consistent TRY/CATCH pattern with `RAISERROR` propagation; errors are logged to `ab_process_plastic_processing` via the update-status procedure.

## Infrastructure Dependencies
- **`ecountcore_ss` on `ppamwdcudsql1c1\ppamwdcudsql1c1`**: The card-account master and device tables are in this database; all plastic expiry processing breaks if this server/database is unavailable.
- **Dynamics GP / eConnect**: The GP invoice staging tables (`gp_process_econnect_*`) require a downstream eConnect SSIS package to consume and post to GP. If GP or the eConnect service is down, invoices will accumulate in staging without posting.
- **Job Service database (`jobsvc`)**: The `banker_insert_action_log` procedure inserts into `banker_action_log` which resides in the job service database; operational continuity of the audit trail depends on this external database.
- **SQL Server Agent / SSIS scheduler**: The plastic processing and ONUS reconciliation workflows are assumed to be triggered by scheduled SQL Agent jobs or SSIS packages; no job scripts are in this repository.
- **`syn_ItemPricePerContractPlusKit`**: References a GP pricing table; disruptions to GP connectivity affect price lookup during invoice generation.

## Operational Risks
- **Synonym server dependency**: Any rename, failover, or migration of `ppamwdcudsql1c1` will immediately break all card expiry processing, account-view queries, and expiry-queue reads. There is no fallback or abstraction.
- **`SSISConfigurations` as a configuration source**: If an incorrect value is written to this table (e.g., a wrong connection string), all SSIS packages that depend on it will fail silently or with cryptic connectivity errors.
- **`banker_temp_unsettled_sources` accumulation**: Without a purge job, this staging table will grow and may cause false positives in unsettled-source detection logic.
- **Missing `banker_action_log` DDL in this project**: Because the audit log table is in an external database, a disaster recovery or environment rebuild of `banker_na` alone will not restore the audit history.
- **No error alerting**: Plastic processing errors are written to `ab_process_plastic_status`, but there is no proactive alerting mechanism (email, PagerDuty, monitoring integration) to notify operations teams.
- **Security role proliferation**: 30+ security grant files with `NAM_PROD_*`, `gers_*`, `onus`, `scpardb`, and individual emer_* (emergency access) logins indicate manually managed, potentially stale, permission sets that are difficult to audit and maintain.

## CI/CD
- No pipeline definition files present in the repository.
- Deployment is manual (DBA-executed SSDT publish or T-SQL).
- Security files (30+ grant scripts) would need to be applied in the correct order during environment setup; no orchestration script exists to automate this.
- No automated database tests (tSQLt or equivalent) are present.
- **Recommendation**: Environment-specific synonym definitions should be managed as SQLCMD variable-substituted scripts, and a CI pipeline should validate DACPAC build on every merge to ensure synonym and procedure compilation errors are caught early.
