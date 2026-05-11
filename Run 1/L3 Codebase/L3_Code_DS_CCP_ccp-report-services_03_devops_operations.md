# DevOps / Operations View — DS_CCP_ccp-report-services

## Build / Deployment Tooling
- **Solution:** `ssrs-2017.sln` (Visual Studio / SSDT 2017 with SSRS project type)
- **SSRS version:** SQL Server Reporting Services 2017
- **Project structure:** 13 separate `.rptproj` files (one per report folder/audience)
- **Report format:** RDLC/RDL 2016 schema (`http://schemas.microsoft.com/sqlserver/reporting/2016/01/reportdefinition`)
- **Deployment:** Reports deployed to SSRS Report Server; deployment target configured per `.rptproj` (not visible in source but set at deployment time)

## Report Project Inventory
| Folder | Project File | Contains RDL |
|--------|-------------|-------------|
| Admin | `Admin.rptproj` | No (data sources only) |
| Analytics | `Analytics.rptproj` | No |
| BIN Banks | `BIN Banks.rptproj` | Yes: Network Settlement Report |
| Client Custom | `Client Custom.rptproj` | No |
| Client Services - Exception | `Client Services - Exception.rptproj` | Yes: 2 RDLs |
| Client Services - Operations | `Client Services - Operations.rptproj` | Yes: 3 RDLs |
| Finance | `Finance.rptproj` | Yes: 4 RDLs |
| Fraud | `Fraud.rptproj` | Yes: 1 RDL |
| Home | `Home.rptproj` | Yes: 3 RDLs |
| Job Services | `Job Services.rptproj` | No |
| Order Services | `Order Services.rptproj` | No |
| Technology | `Technology.rptproj` | No |
| Templates | `Templates.rptproj` | Yes: 3 layout templates |
| UAT | `UAT.rptproj` | No |
| Vendor Management | `Vendor Management.rptproj` | No |

## Data Source Files (.rds)
| File | Target | Used In |
|------|--------|---------|
| `ODS.rds` | `t-phl-db01` / `ODS` | Most folders |
| `Wired.rds` | `t-phl-db01` / `WIRED` | Most folders |
| `DWH.rds` | `DWH_AWS_SSH` (Oracle) | Admin, Finance |
| `Munich DWH_Dev.rds` | Dev Oracle alias | Client Services, Finance (dev) |
| `ReportServer.rds` | SSRS server | Home |

## Scheduling / Subscriptions
- SSRS report subscriptions managed via `Subscription Requests.rdl` and `Subscription Status.rdl` in the Home folder.
- Subscriptions deliver reports by email or to a file share on a configured schedule.
- Subscription configuration (recipients, schedules) is managed in the SSRS server database; not version-controlled here.

## CI/CD
- No GitHub Actions or build pipeline configured for this repository.
- No automated deployment script found.
- Deployment is manual: SSDT "Deploy" to the SSRS Report Server URL.

## Observability
- SSRS built-in execution log (`ReportServer` DB tables: `ExecutionLog3`).
- SSRS subscription delivery history.
- No external monitoring or alerting integration.

## Infrastructure Dependencies
- SSRS 2017 server (Windows)
- SQL Server instance `t-phl-db01` (ODS and WIRED databases)
- Oracle `DWH_AWS_SSH` accessible from the SSRS server
- SMTP server for report subscriptions and email delivery
- Network connectivity between SSRS server and `t-phl-db01.wirecard.lan`

## Operational Risks
1. **`t-phl-db01.wirecard.lan`** — legacy Wirecard internal hostname; if this server is decommissioned or renamed, all SSRS data sources break.
2. **Dev data source in production reports** — `Munich DWH_Dev.rds` used in Client Services and Finance folders; if deployed without overriding to production DWH, reports show dev data.
3. **No version-controlled deployment scripts** — SSRS deployment is manual; rollback requires re-deploying a prior version from source control.
4. **Subscription recipient lists not version-controlled** — if a recipient list changes on the server, it cannot be audited from this repo.
5. **Cache freshness** — `cache_pbr` in WIRED must be refreshed by a separate process; stale cache will cause incorrect Program Balance Reports without any error indication.
6. **No CI/CD pipeline** — no automated validation that reports deploy and execute correctly after changes.
