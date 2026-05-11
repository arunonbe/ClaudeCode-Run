# DS_DB_ATL_atlys_rv_nca — DevOps & Operations View

## Build & Packaging
- **Project type**: SQL Server Data Tools (SSDT) `.sqlproj` (MSBuild format, `ToolsVersion="4.0"`, `TargetFrameworkVersion=v4.5`).
- **Project name**: `atlys_rv_nca`; solution file: `ATLYS_Rv_NCA.sln`.
- **Schema provider**: `Microsoft.Data.Tools.Schema.Sql.Sql100DatabaseSchemaProvider` (SQL Server 2008 schema provider).
- **Output type**: `Database` — the build produces a DACPAC artifact deployable via SqlPackage or SSDT Publish.
- **Configuration levels**: Debug (OutputPath `bin\Debug\`) and Release (OutputPath `bin\Release\`, `Optimize=true`).
- **`IncludeCompositeObjects`: True** — cross-database references to `ATLYS_E` objects are included in validation.
- **`DeployToDatabase`: True** — SSDT is configured for direct-deploy publishing.
- **`SqlServerVerification`: False** — schema validation errors are suppressed, which can hide broken cross-database references at build time.

## Deployment
- Deployment is via SSDT DACPAC/Publish; no CI/CD pipeline scripts (YAML, Jenkinsfile, etc.) are present in this repository.
- The project requires `ATLYS_E` to be resolvable at deploy time because of composite object inclusion.
- No pre/post-deployment scripts observed in the project structure.
- **`Recovery` model is `BULK_LOGGED`** — this must be considered when scheduling deployments; switching to SIMPLE during deployment and back to BULK_LOGGED post-deployment is a common but risky practice that must be coordinated with backup schedules.
- No Flyway, Liquibase, or custom migration scripts are present; all changes are schema-snapshot driven.

## Configuration Management
- **`QueryStore`: Enabled** (ReadWrite, auto-capture, 100 MB, 30-day stale threshold) — query performance history is retained in the database; no external configuration needed.
- **`PageVerify`: CHECKSUM** — I/O integrity verification is enabled.
- **`TwoDigitYearCutoff`: 2049** — two-digit year parsing behaves predictably up to 2049.
- **`DefaultCursor`: GLOBAL** — a legacy setting that can cause cursor-scope issues in multi-statement batches.
- **`DelayedDurability`: DISABLED** — all commits are fully durable (important for financial data).
- **`AllowSnapshotIsolation`: False** and **`ReadCommittedSnapshot`: False** — the database relies on shared-lock read semantics; long-running reports will block writers and vice versa.
- **`AnsiNulls`, `AnsiPadding`, `AnsiWarnings`, `QuotedIdentifier`: all False** — legacy ANSI settings; this means NULL comparisons using `= NULL` will behave inconsistently depending on session settings, a subtle but dangerous configuration for financial code.
- No environment-specific configuration tables or environment variables are managed within this project.

## Observability
- **QueryStore** provides execution-plan history and regression detection, but there is no alerting configuration within the project itself.
- **No application logging tables** are present within this database (unlike `DS_DB_dbadmin` which has explicit monitoring tables).
- **Audit trail**: `tblAuditLog` provides coarse-grained reconciliation audit (who ran a reconciliation run, when), but does not record individual row changes.
- Error handling within stored procedures uses `SELECT 'Access Denied.' AS sError` for authorisation failures; these are application-surface errors with no server-side logging.
- No SQL Server Extended Events sessions or Server Audit specifications are defined in the project.

## Infrastructure Dependencies
- **`ATLYS_E` database**: Hard runtime dependency for authorisation, exchange rates, system paths, and linked-server queries. Must be co-located on the same SQL Server instance or available via a linked-server alias.
- **FDR processor feed**: External batch feed loads data into `tblFDR_*` and `tblEC_Txns` tables; the mechanism (SSIS, file import) is not defined in this repository.
- **SSIS/ETL**: Several stored procedures reference SSIS-loaded data patterns; the actual SSIS packages reside in separate repositories (`DS_ETL_*`).
- **SQL Server Agent**: Revenue calculation and GL batch procedures appear to be invoked on schedule; no Agent job scripts are present in this repo (contrast with `DS_DB_database_maintenance`).
- **Dynamics GP (`ATLYS_E`)**: GL entries are ultimately posted to GP via the linked ATLYS_E layer; this creates a financial close dependency.

## Operational Risks
- **BULK_LOGGED recovery model**: Any bulk-loaded revenue or FDR data is not fully point-in-time recoverable; a mid-bulk failure requires re-running the entire load.
- **`SqlServerVerification: False`**: Build-time cross-database reference validation is disabled; broken references to `ATLYS_E` objects will not surface until runtime deployment or execution.
- **No snapshot isolation**: Heavy reporting queries block write operations; during financial period close, contention could halt revenue imports.
- **FLOAT(53) monetary data**: Cumulative precision errors in `tblEC_Txns` will not surface as errors but will silently distort summary figures.
- **Composite index on `tblGLBatch`**: The unique clustered index is 7 columns wide; this increases insert cost and fragmentation risk for a configuration table that is modified during GL batch setup operations.
- **`trg_revenue` trigger complexity**: The `FOR INSERT, UPDATE` trigger issues a multi-table UPDATE with LEFT JOINs on every revenue write; under high-volume SSIS bulk loads this will be a significant performance bottleneck (and may be disabled during bulk-load sessions, bypassing GL coding logic).
- **No archival or purge strategy**: Without data lifecycle management, `revenue` and `tblEC_Txns` will grow unbounded, eventually impacting query performance.

## CI/CD
- No pipeline definition files (`.gitlab-ci.yml`, Jenkinsfile, `.github/workflows`, Azure Pipelines YAML) are present in this repository.
- The `.gitignore` excludes standard build output (`bin/`, `obj/`).
- Deployment is assumed to be manual SSDT publish or DBA-executed DACPAC deployment.
- No automated unit tests or tSQLt test projects are present.
- No database migration framework (Flyway, Liquibase, DbUp) is in use; all changes are applied as full schema snapshots.
- **Recommendation**: introduce a pipeline that builds the DACPAC on commit, runs schema diff against a UAT target, and gates production deployment on a DBA approval step.
