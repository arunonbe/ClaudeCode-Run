# DS_RPT_ecount-report-services — Solution Architect View

## Technical Architecture
- **Platform**: SQL Server Reporting Services (SSRS) 2008/2010 schema
- **Solution**: Visual Studio 2010 (`.sln` format 11.00), 50+ `.rptproj` projects
- **Report format**: RDL XML (two namespace versions: 2008/01 and 2010/01)
- **Data source type**: SQL Server (Extension=SQL, Integrated Security), shared data sources via `.rds` files
- **Report database**: `cf_report` on `p-db06.nam.wirecard.sys\db06,2431` (production), QA servers for development
- **Supporting DB**: EcountCore, Prepaid_Warehouse, RiskDB, Cbaseapp, ECNT, ECAN, ecountcore_rollback
- **No application code** beyond RDL XML and SSRS project configuration

## API Surface
- SSRS Report Server URL (defined per project in `.rptproj`) — standard SSRS HTTP/HTTPS endpoints
- No REST API built in this repo; SSRS provides its own web service interface
- Reports can be subscribed/scheduled via SSRS native subscription engine — subscription configurations not in repo

## Security Posture

### Authentication
- All data sources use `IntegratedSecurity=true` (Windows auth / Kerberos) — no embedded SQL credentials in any `.rds` file.
- Report-level security managed at SSRS server via role assignments — not visible in this repo.
- `Secured Reports` folder implies folder-level SSRS role-based access control for sensitive financial reports.

### Secrets / Credentials
- No passwords or API keys found in any `.rds` or `.rdl` file reviewed.
- Production server hostname `p-db06.nam.wirecard.sys\db06,2431` is embedded in `CF_Report_Prod.rds` — this file is committed to source control.
  - File: `External Report.Exception Reports\CF_Report_Prod.rds` line 5
  - Risk: Server identity disclosure; not a credential leak but an infrastructure information disclosure.

### PAN / Sensitive Data in Reports
- `Masked_card_number` field confirmed in `Cardholder Archived Transactions.rdl` — card number is masked before rendering.
  - File: `Customer Service\Cardholder Archived Transactions.rdl` line 12 (BIN prefix check on masked number)
- `dda_number` field present in Repetitive Fees Report (`Compliance\Repetitive Fees Report.rdl` line 76) — DDA is rendered; must confirm masking policy in the `cf_report` stored procedure.
- PIN reports exist (`PIN Change Report.rdl`, `PIN Selection Status.rdl`) — PIN values must not be rendered; must be confirmed in SP output.

### Crypto / Transport
- No SSL/TLS configuration visible in repo; depends on SSRS server and SQL Server TLS settings.
- All `.rds` use `Extension=SQL` (ADO.NET) — TLS support depends on SQL Server driver configuration on SSRS server.

### CVEs
- SSRS 2008/2010 schema reports running on what is likely SSRS 2012 (matching infrastructure era) — SSRS 2012 is end-of-life July 2022.
- If SSRS server has been upgraded to 2016/2017/2019, older RDL schemas are rendered in compatibility mode.

## Technical Debt
| Item | Severity | Evidence |
|---|---|---|
| Production server hostname in source control | High | `External Report.Exception Reports\CF_Report_Prod.rds:5` |
| QA server addresses in all other .rds files | High | All other `.rds` files |
| SSRS 2008/2010 schema (potential EOL) | High | RDL xmlns versions |
| Retired Reports in active solution | Medium | `Retired Reports\` folder and sub-folders |
| `ecountcore_rollback` as a live report data source | Medium | `Customer Service\ecount_rollback.rds` |
| No CI/CD deployment pipeline | Medium | No pipeline files in repo |
| No automated regression testing | Medium | No test harness |
| Wirecard branding in README | Low | README.md line 3 |
| Dev.rds (unnamed dev data source) | Low | `External Report.Client Custom Reports\Dev.rds` |
| Multiple SSRS schema versions (2008 and 2010) | Low | Mixed RDL namespaces |

## Gen-3 Migration Requirements
1. **Capture cf_report DDL** (stored procedures, tables, views) in a separate migration artefact — this repo does not contain the DB objects that power the reports.
2. **Replace SSRS with modern reporting** (Power BI Paginated Reports, SSRS 2019 on Azure, or embedded analytics).
3. **Migrate .rds to use modern SQL Server auth** (Azure AD / service principal) rather than Windows Integrated Security.
4. **Remove `CF_Report_Prod.rds` from source control** or replace with an environment variable reference.
5. **Decommission Retired Reports** — remove from solution and SSRS server.
6. **Validate PIN and DDA masking** in `cf_report` stored procedures before any data platform migration.
7. **Implement automated RDL regression testing** before migration (compare report output before/after platform change).
8. **Client report mapping** — create an inventory of all client-contractual reports and map to replacement platform equivalents.
9. **Add `.gitignore`** to exclude QA `.rds` files from accidental production commits.

## Code-Level Risks (File:Line References)
| Risk | File | Line |
|---|---|---|
| Production DB server hostname committed | `External Report.Exception Reports\CF_Report_Prod.rds` | 5 |
| Masked card number BIN check | `Customer Service\Cardholder Archived Transactions.rdl` | 12 |
| DDA number rendered in compliance report | `Compliance\Repetitive Fees Report.rdl` | ~76 |
| Issuer disclosure: Sunrise Banks N.A. / Wirecard | `Customer Service\Cardholder Archived Transactions.rdl` | 14 |
| ecountcore_rollback as live data source | `Customer Service\ecount_rollback.rds` | 5 |
| QA server hardcoded in all .rds files | All `.rds` files except `CF_Report_Prod.rds` | All line 5 |
