# DS_RPT_ecount-report-services — DevOps / Operations View

## Build Process
- **Visual Studio 2010 SSRS solution** (`ssrs-2012.sln`, format version 11.00).
- 50+ SSRS projects (`.rptproj`) organized by business domain folder, matching the SSRS server folder hierarchy.
- Reports authored as `.rdl` (Report Definition Language) XML files — these are text/XML and can be diff'd in version control.
- Schema: SSRS 2008 (`http://schemas.microsoft.com/sqlserver/reporting/2008/01/reportdefinition`) and 2010 (`2010/01/reportdefinition`) namespace versions observed — reports span two SSRS schema generations.
- No automated build pipeline; no `dotnet build`, no CI/CD YAML.

## Deployment Method
- Reports are deployed from Visual Studio to the SSRS Report Server via the `.rptproj` deployment settings (server URL, target folder — defined in each `.rptproj`).
- Data source files (`.rds`) are deployed alongside reports and provide shared data source definitions.
- **Production data source override**: `CF_Report_Prod.rds` in Exception Reports points to `p-db06` — this appears to be the production server reference for that folder; all other `.rds` files point to QA/dev servers, implying production overrides happen at SSRS server level.
- No database migration scripts for `cf_report` DB are present in this repo (stored procedure DDL is absent — managed separately).

## Configuration Management
- `.rds` connection files are the configuration artefacts — all use Integrated Security (Windows auth).
- QA connection strings embedded in `.rds` files; production overrides managed externally (SSRS catalog or manual update on server).
- SSRS Report Server URL is defined in each `.rptproj` — not visible in the top-level sln file but would be in individual project files.
- Logo images stored in `cf_report.t_Images` table — not in repo; managed in the database.
- Report permissions/security managed at the SSRS server level — not in repo.

## Observability
- `IT.Reports Monitoring` folder contains reports for monitoring the SSRS report server itself (using `RS2008` database).
- No application-level logging configuration in the RDL files.
- Report execution logs are stored in the SSRS `ReportServer` database (standard SSRS behavior) — not in this repo.
- No external monitoring (Splunk, Datadog, etc.) configured in repo artifacts.

## Infrastructure Dependencies
| Component | Details | Risk if Unavailable |
|---|---|---|
| SSRS Report Server | Renders and serves all RDL reports | All reports unavailable |
| cf_report DB (p-db06 prod) | Primary report data store | Most reports fail |
| EcountCore DB (db02) | Core transaction data | Risk/CS reports fail |
| Prepaid_Warehouse (db03) | Warehouse data | Warehouse reports fail |
| ECNT / ECAN | Finance data | Finance reports fail |
| RiskDB / Cbaseapp | Risk data | AML/Risk reports fail |
| ecountcore_rollback | Rollback DB | Daily ACH / CS rollback reports fail |

## Operational Risks
1. **QA server addresses in `.rds` files** — if SSRS production server is not configured to override data sources, all reports run against QA data in production.
2. **`CF_Report_Prod.rds` committed** — the production SQL Server address (`p-db06.nam.wirecard.sys\db06,2431`) is disclosed in source control; if this repo is ever publicly accessible, an attacker learns the production DB server name.
3. **50+ separate SSRS projects** — deployment is complex; a developer deploying one project at a time is error-prone.
4. **Retired Reports still in solution** — they may still be deployed to the SSRS server, consuming resources and presenting an attack surface.
5. **No rollback procedure** for report deployments — if a bad report is deployed, rollback requires manual redeployment from source control.
6. **Visual Studio 2010 solution format** — modern SSDT in VS2019/2022 may not fully support all VS2010 project settings.

## CI/CD Assessment
- **No CI/CD pipeline** for report deployment.
- Recommended: Use `rs.exe` (Report Server utility) or SSRS REST API for automated deployment; add a GitHub Actions / Azure DevOps pipeline that deploys RDL changes to a dev SSRS server on push, and to production on release approval.
- `.rdl` files are XML — linting and automated testing (RDL schema validation) are feasible.
