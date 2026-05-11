# DS_ETL_great-plains-to-oas-coda — DevOps / Operations View

## Build Process
- Visual Studio 2010 SSIS solution (`great-plains-to-oas-coda.sln`, format version 11.00).
- Single project: `CODA ETL\CODA ETL.dtproj` — SSIS Integration Services project.
- Package format version 6 (SQL Server 2012 SSIS).
- Last modified product version: `11.0.7001.0` (SQL Server 2012 SP4 CU9).
- No CI/CD build pipeline present; no GitHub Actions, Jenkins, or Azure DevOps YAML.
- Build is via Visual Studio SSDT (SQL Server Data Tools) locally on the developer workstation.

## Deployment Method
- Packages are deployed manually to an SSIS catalog (SSISDB) or run directly via `dtexec`.
- The `.dtproj` file has a single `Development` configuration.
- No deployment scripts (`.ispac` publish scripts, SSISDB catalog deployment) are present in the repo.
- Package parameters (`pStartDate`, `pEndDate`, `pFolderPath`, `pFTPFolder`, `pOverwriteDates`) must be set at runtime or in SSISDB catalog — no environment configuration files in repo.

## Configuration Management
- **pFolderPath** — UNC output path (must be set per environment)
- **pFTPFolder** — FTP destination (empty default — not configured)
- **pStartDate / pEndDate** — date range for historical backfill
- **pOverwriteDates** — toggle between daily-rolling and explicit date range modes
- **uiRegionId** — defaults to `-29`; must be overridden for correct region filtering
- Connection strings in `.conmgr` files point to `q-db04.nam.wirecard.sys\db04,2232` (QA/dev server) — production connection strings must be configured in SSISDB catalog separately.
- Creator computer: `PF0VET79` (likely a developer workstation); creator: `WIRECARD\julia.ginzburg`.

## Observability
- No logging configuration visible in the package beyond SSIS default execution logging.
- No error email task observed in the SSIS package control flow (no Send Mail task).
- SQL Server Agent scheduling of these packages is defined in DS_DP_db07 (see that repo for job definitions referencing SSIS\Finance and SSIS\ETL folders).
- No external monitoring, APM, or alerting configured within this package.

## Infrastructure Dependencies
| Component | Details | Risk if Unavailable |
|---|---|---|
| q-db04.nam.wirecard.sys\db04,2232 | Source: ATLYS_RvCR (Great Plains data) | GP feed fails completely |
| q-db03.nam.wirecard.sys\db03,2232 | ODS database | RfCks feed may fail |
| UNC file share (pFolderPath) | Output destination for CODA files | Files cannot be written |
| CODA/OAS system (downstream consumer) | Finance ledger | Financial data gap |
| Developer workstation C:\GIT\rfcks.csv | Input for SSIS_RfCks | RfCks package cannot run |
| SQL Server 2012 SSIS Runtime | Execution engine | Packages cannot run |

## Operational Risks
1. **`C:\GIT\rfcks.csv` input path** — hardcoded to a local developer path; this package cannot run in any automated/server environment without intervention.
2. **No error handling/notification** — if the package fails silently, Finance may miss daily CODA postings with no alert.
3. **Connection managers point to QA DB (q-db04)** — production deployments must override these; if not overridden, production packages write QA data to production files.
4. **FTP parameter empty** — if the intended delivery mechanism to CODA/OAS is FTP, files are never transmitted.
5. **No idempotency** — `Overwrite=true` on flat file destination; rerunning the same date rewrites the file with no audit of previous content.
6. **SQLNCLI11.1** — legacy OLE DB provider; may not be installed on modern server OSes; connection could silently fail.

## CI/CD Assessment
- **No CI/CD pipeline** — no workflow definitions in this repo.
- This is a development-era artefact (Visual Studio 2010 solution) with no automation investment.
- Manual developer-driven deployment is the only known pattern.
- The "temporary project" label suggests this may have been intended to be replaced before entering long-term maintenance; neither replacement nor formal decommission is visible in the repo.
