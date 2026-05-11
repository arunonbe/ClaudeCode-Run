# Solution Architect Report — DS_DB_ATL_atlys_fccr

## 1. Technical Architecture

`atlys_fccr` is an **SSDT SQL Server Database Project** targeting SQL Server 2008 (`Sql100DatabaseSchemaProvider`) with compatibility level 90 (SQL Server 2005). The project produces a DACPAC for deployment.

**Project identity:**
- Project GUID: `{8ddae437-ee85-49ae-8ed6-27e94f3a391e}` (`atlys_fccr.sqlproj` line 10)
- Active branch: `development`
- Collation: `SQL_Latin1_General_CP1_CI_AS`
- Recovery: `BULK_LOGGED`
- Page verify: `CHECKSUM`
- TDE: disabled (`IsEncryptionOn=False`, line 52)
- Broker: disabled (`ServiceBrokerOption=DisableBroker`)
- Query Store: enabled (`QueryStoreCaptureMode=Auto`)

**Schema composition:**
- `dbo` schema only
- 3 tables (including Salesforce staging)
- 2 views (`vCompanies`, `vPrograms`)
- 1 scalar function (`sys_prg_info`)
- 78 stored procedures — all named `sys_*`
- 24 Security scripts

The architecture is a **single-schema stored procedure API database**. All business logic is encapsulated in stored procedures. The application layer (`atlys_WAPP`) calls procedures exclusively — there is no ORM-based direct table access by the application.

---

## 2. API Surface

The stored procedure API surface is entirely composed of `sys_*` procedures, all in the `dbo` schema. Key API categories:

**Program API** (CRUD):
- `sys_program` — read program
- `sys_program_update` — update program fields
- `sys_program_delete` — delete program
- `sys_program_search` — search programs
- `sys_program_lock` / `sys_program_chk` — concurrency control

**Reporting API** (cross-tab generators, all return tabular datasets):
- `sys_revenue_cross_tab` — revenue cross-tab (primary revenue reporting SP)
- `sys_comm_cross_tab` — commission cross-tab
- `sys_forecast_cross_tab` — forecast cross-tab
- `sys_dash` / `sys_dash_cross_tab` — dashboard data
- `sys_spend_cross_tab` / `sys_costs_cross_tab` / `sys_issuance_cross_tab` — operational metrics

**Salesforce API**:
- `sys_sf_import` — import Salesforce opportunity data into `cursforecast`
- `sys_sf_upload(@report, @s_id, @region_id)` — generate Salesforce upload data set by calling `sys_revenue_cross_tab` with Salesforce-specific parameters (`sys_sf_upload.sql` lines 29–34)

**Key `sys_sf_upload` signature** (`sys_sf_upload.sql`):
```sql
CREATE PROCEDURE [dbo].[sys_sf_upload] 
    @report varchar(50) = '',
    @s_id uniqueidentifier = null,
    @region_id smallint = 1
```
When `@report = 's'`, returns schema definition only (no data). Otherwise executes `sys_revenue_cross_tab` with a 5-year window starting from `@start_date1` derived from `sys_controls`.

**Key `sys_prg_info` output** (`dbo/Functions/sys_prg_info.sql` lines 19–24):
Returns a 400-character dynamic column-list string: `prg_name, prg_type_desc, channel_desc, First_Issue, First_Issue_Override, recurr, Sales_Rep, Rel_Manager, Acct_Manager, Industry_Name, GFCID, LegalName, Status, Probability, High_Pr, Card_Type, First Forecast, Win_Date`. This string is concatenated into dynamic SQL in calling procedures to build Excel-format report column headers.

---

## 3. Security Posture

| Control | Status | Finding |
|---|---|---|
| TDE | Disabled | Data at rest unencrypted — gap for commercially sensitive deal economics |
| BULK_LOGGED recovery | Active | Point-in-time recovery unavailable during bulk loads; RPO gap |
| SQL 2005 compat mode | Active | Compat mode 90 disables certain security and query features available in modern SQL Server |
| Role-based access | Implemented | `ATLYS_APP_GRP` (application), `FortiDBRptRole` (DAM), `gers_read` (security scan), production support roles |
| Prod_Support_Update | Active | Direct production data update grant — bypasses application audit trail. Violates principle of least privilege |
| Prod_Support_execute | Active | Execute any procedure in production — broad grant for support staff |
| `NAM_PROD_CPP_APAC` login | Present | APAC-specific production access — scope of this access should be periodically reviewed |
| FortiDB DAM | Configured | `FortiDBRptRole` role registered — security event monitoring active |
| SSDT `SqlServerVerification=False` | Set | Suppresses SQL Server verification warnings — may mask SQL compatibility issues during build |
| `AnsiNulls=False` | Set | Non-standard NULL comparison behaviour — can cause subtle logic errors in procedures that assume ANSI NULL semantics |
| `QuotedIdentifier=False` | Set | Non-standard identifier quoting — identifier handling may differ from default SQL Server behaviour |

---

## 4. Technical Debt

| Item | Location | Impact |
|---|---|---|
| SQL 2005 compat mode | `atlys_fccr.sqlproj:63` (`CompatibilityMode=90`) | Modern query optimizer features (cardinality estimation, batch mode, etc.) unavailable; performance ceiling |
| `Sql100DatabaseSchemaProvider` targeting SQL 2008 with compat 90 | `.sqlproj:11` | Toolchain/target mismatch; may produce SSDT validation warnings for any SQL 2008+ syntax used in procedures |
| `AnsiNulls=False` / `QuotedIdentifier=False` / `ArithAbort=False` | `.sqlproj:65-69` | All three are non-standard settings that diverge from SQL Server best practices; risk of subtle T-SQL behaviour differences |
| BULK_LOGGED recovery | `.sqlproj` recovery setting | Not FULL recovery; SOC 1 requires transaction log-based point-in-time restore capability |
| No TDE | `.sqlproj:52` | Deal economics data at rest unencrypted |
| `sys_sf_upload` hardcoded 5-year window | `sys_sf_upload.sql:30-34` | Year range (`DATEADD(yy, 4, ...)` and `DATEADD(yy, -1, ...)`) is calculated from fiscal year start; will cover years 2009-2013 as hardcoded columns in the return schema. Historical years with no data return NULLs |
| `sys_prg_info` returns column list as string | `dbo/Functions/sys_prg_info.sql:19-24` | Column list is a 400-char string concatenated into dynamic SQL. Any column rename or addition requires a function deployment and all callers must be re-validated |
| No CI/CD pipeline | Repository | Manual deployment; no regression testing |
| `Prod_Support_Update` and `Prod_Support_execute` | `Security\Prod_Support_*.sql` | Over-privileged production support access — should be time-limited and audited |

---

## 5. Gen-3 Migration Requirements

| Requirement | Description |
|---|---|
| Identify `cursforecast` host database | Core program master table is not in this repo; the host database must be scoped into migration |
| Upgrade SQL Server compat level | Must upgrade from compat 90 → at minimum compat 130 (SQL Server 2016) before Gen-3 modernisation; test all 78 stored procedures under new compat level |
| Replace Salesforce database integration | `sys_sf_import` / `sys_sf_upload` stored procedure integration must be replaced with a Salesforce-connected ETL/API service (Informatica, Azure Data Factory, MuleSoft, or custom) |
| Enable TDE | Add transparent data encryption before or during migration |
| Switch to FULL recovery model | Required for SOC 1 point-in-time recovery guarantees |
| Migrate 78 stored procedures | Cross-tab reporting logic in all `sys_*` procedures must be replicated in the Gen-3 reporting platform (Power BI Paginated Reports, SSRS, or custom microservice) |
| Remove `AnsiNulls=False` / `QuotedIdentifier=False` | Standardise to ANSI settings before migration; test all procedures under ANSI mode |
| Revoke Prod_Support_Update | Replace with time-limited, audited emergency access process |

---

## 6. Code-Level Risks

| Risk | File:Line | Notes |
|---|---|---|
| `AnsiNulls=False` | `atlys_fccr.sqlproj:65` | Procedures written under `AnsiNulls=False` may contain NULL comparisons using `=` instead of `IS NULL`; migrating to ANSI mode could silently change query results |
| `QuotedIdentifier=False` | `atlys_fccr.sqlproj:66` | Object names with spaces or reserved words may behave differently under standard quoting |
| `ArithAbort=False` | `atlys_fccr.sqlproj:69` | Arithmetic overflow errors are silently ignored rather than raising an error — could mask fee calculation errors |
| Dynamic SQL column construction | `sys_prg_info.sql:16-24` | `sys_prg_info()` returns a raw SQL fragment concatenated into caller dynamic SQL; SQL injection risk if any external input reaches the calling context (low risk given internal-only use) |
| `sys_sf_upload` returns historical year columns as YR_2010 through YR_2014 | `sys_sf_upload.sql:18-22` | Schema definition (`@report = 's'` path) hardcodes `YR_2010` through `YR_2014` — these column names are over a decade stale and suggest the Salesforce upload schema has not been updated since ~2014 |
| BULK_LOGGED recovery during Salesforce import | Architecture | `sys_sf_import` bulk-loads the `Salesforce_to_Atlys` staging table; under BULK_LOGGED recovery, these writes are minimally logged — a failure during import cannot be rolled back via transaction log replay |
