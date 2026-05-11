# DevOps / Operations Report — DS_DB_ATL_atlys_fccr

## 1. Build System

| Property | Value |
|---|---|
| Project type | SSDT SQL Server Database Project (`atlys_fccr.sqlproj`) |
| Build tool | MSBuild with SSDT targets (`Microsoft.Data.Tools.Schema.SqlTasks.targets`) |
| Output | DACPAC (`atlys_fccr.dacpac`) |
| Target DSP | `Microsoft.Data.Tools.Schema.Sql.Sql100DatabaseSchemaProvider` (SQL Server 2008 compatible) |
| CompatibilityMode | 90 (SQL Server 2005 mode) |
| DefaultCollation | `SQL_Latin1_General_CP1_CI_AS` |
| Active branch | `development` |
| Solution file | `atlys_fccr.sln` — Visual Studio solution wrapper present |

**Build configurations**: Two standard SSDT configurations — `Debug` (with symbols, no optimization) and `Release` (optimized, no symbols). Outputs to `bin\Debug\` or `bin\Release\`.

**Known build issue**: The project uses `Sql100DatabaseSchemaProvider` (SQL 2008) but sets `CompatibilityMode=90` (SQL 2005). This mismatch between the provider version and the compatibility level can cause SSDT validation warnings for SQL 2008+ features used in procedures. 78 stored procedures in the project — any feature gaps between SQL 2005 and SQL 2008 syntax are unverified without a full build.

---

## 2. Deployment

There is **no CI/CD pipeline configuration** visible in this repository. No `Jenkinsfile`, no Azure DevOps YAML, no `ci-scripts` references, no `Dockerfile`, and no deployment scripts are present. Deployment is expected to follow the Onbe standard SSDT DACPAC deployment pattern used across the Atlys database family.

**Expected deployment pattern** (inferred from sister repos):
1. SSDT project builds DACPAC via MSBuild
2. DACPAC is published to SQL Server using `SqlPackage.exe /Action:Publish`
3. Deployment targets: Production Atlys SQL Server instance (hostname not visible in this repo)
4. Environment-specific variables (server name, database name) are provided at publish time via publish profiles or command-line parameters — not hardcoded in project

**Security scripts deployment**: The `Security\` folder contains 24 SQL scripts defining roles, logins, and permissions. These scripts are included in the DACPAC build (`<Build Include="Security\..."/>`) and would be applied during DACPAC publish. If the target environment has login/role differences, DACPAC publish may attempt to drop and recreate security principals — a risk requiring `--BlockOnPossibleDataLoss=false` or targeted deployment profiles.

---

## 3. Configuration Management

**No application configuration files** are present in this repository (no `.config`, no `appsettings.json`, no environment variable files). Configuration is entirely internal to SQL Server:

- Database compatibility settings are defined in the `.sqlproj` PropertyGroup
- The `tblForecastReports` and `tblForecastViews` tables serve as application configuration stores (report and view layout configurations)
- Salesforce integration parameters (import timing, field mappings) are embedded in the `sys_sf_import` and `sys_sf_upload` stored procedures — any changes require a deployment

**`sys_sf_upload` hardcoded date range** (`sys_sf_upload.sql` lines 30-34): The procedure calculates a 5-year date window using `DATEADD(yy, 4, @start_date1)` and `DATEADD(yy, -1, @start_date1)`. This date range logic is hardcoded and cannot be changed without a stored procedure deployment.

---

## 4. Observability

| Capability | Status |
|---|---|
| Query Store | Configured: `QueryStoreCaptureMode=Auto`, `QueryStoreDesiredState=ReadWrite`, flush interval 900s, stats interval 60s, max 200 plans/query, stale query threshold 30 days, max storage 100MB |
| Application logging | No logging tables in this database |
| Audit trail | No audit tables defined; `Salesforce_to_Atlys.Import Date` provides import timestamps |
| FortiDB DAM | `FortiDBRptRole` security role is present — FortiDB Database Activity Monitoring agent is configured on this database |
| Error handling | Not visible in stored procedure bodies without reading individual files; Atlys family procedures generally lack TRY/CATCH blocks |

Query Store is the primary operational observability tool for this database. FortiDB DAM provides security monitoring.

---

## 5. Infrastructure Dependencies

| Dependency | Type | Notes |
|---|---|---|
| SQL Server instance (Atlys production) | Runtime | Hostname not declared in repo; must be resolved from SSISDB/deployment records |
| Salesforce CRM | Integration | Bidirectional data flow via `sys_sf_import` / `sys_sf_upload`; no direct database link visible in repo — import/export likely ETL-mediated |
| Atlys web application | Consumer | `ATLYS_APP_GRP` / `NAM\PPA_PRD_ATLYS` service account is the primary application consumer |
| `cursforecast` (implied master table) | Data dependency | Core program master data is likely in a shared Atlys database, not defined here |
| Great Plains ERP (ecnt, ecan) | Indirect dependency | Cross-tab reports include GP program data via Atlys infrastructure |

---

## 6. Operational Risks

| Risk | Severity | Description |
|---|---|---|
| No CI/CD pipeline | HIGH | Manual DACPAC deployments are error-prone; no deployment history, no automated regression testing |
| SQL 2005 compat mode (90) | MEDIUM | Running in compat level 90 disables query optimizer improvements and modern T-SQL features; performance and correctness risks accumulate over time |
| BULK_LOGGED recovery | HIGH | Point-in-time recovery is not available during bulk operations; data loss window exists for bulk imports from Salesforce staging |
| Prod_Support DML grants | HIGH | `Prod_Support_Update` and `Prod_Support_execute` roles allow direct data modification in production — bypasses application audit trail |
| No TDE | MEDIUM | Deal economics and BIN sponsor data at rest are unencrypted on disk |
| Staging table no purge | LOW | `Salesforce_to_Atlys` accumulates import records indefinitely; no cleanup procedure |
| FortiDB dependency | MEDIUM | FortiDB DAM role is defined; if FortiDB agent is not running, the security monitoring gap is invisible at the database level |

---

## 7. CI/CD Assessment

**Current state**: No CI/CD. Deployment process is assumed to be manual (developer builds DACPAC in Visual Studio and publishes using SqlPackage.exe or SSMS Publish).

**Recommended Gen-3 pipeline**:
1. GitLab CI pipeline triggers on merge to `development` → builds DACPAC via `MSBuild`
2. Pipeline runs SSDT schema comparison against a reference database
3. DACPAC published to Dev/QA/UAT SQL Server using `SqlPackage.exe /Action:Publish`
4. Automated smoke test runs key stored procedures (e.g., `sys_program`, `sys_dash`) against known test data
5. Production deployment gated by change management approval

The absence of a `.gitignore` entry for build outputs and the presence of the `.sln` file suggests the project is opened directly in Visual Studio for development, with manual deployment steps.
