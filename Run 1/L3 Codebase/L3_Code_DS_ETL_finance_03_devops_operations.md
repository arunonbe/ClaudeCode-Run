# DevOps / Operations View — DS_ETL_finance

## Repository Overview

**Repo path:** `E:\OnbeEast363\repos\DS_ETL_finance`
**Git branch:** `development` (only branch observed)
**Remote:** `origin` (shallow clone)

---

## CI/CD Pipeline

**No CI/CD configuration is present in this repository.** There are no pipeline YAML files, Jenkinsfiles, or deployment scripts. The repository contains only the SSIS Visual Studio solution and package files.

This is a recurring pattern across the DS_ETL_* repository set: all six repositories lack automated build and deployment pipelines. Deployment relies on manual SSDT-based workflows.

---

## SSIS Deployment Approach

**Project Deployment Model** (confirmed: `Finance.dtproj` line 3).

The project is configured with `EncryptSensitiveWithUserKey` protection, meaning:
- Build produces `Finance.ispac`
- Deployment is performed manually via the Integration Services Deployment Wizard
- Environment variables must be configured in the SSIS catalog (SSISDB) to override connection string parameters per environment

**Connection string parameter overrides required at deployment:**
- `CM.Atlys_FcCR.ConnectionString` (Finance.dtproj line 62)
- `CM.Atlys_FcCR.Password` (Finance.dtproj line 81–93, `Sensitive=1`)
- `CM.cf_report.ConnectionString`
- `CM.ATLYS_RvCR.ConnectionString`
- `CM.ATLYS_RvCR_DotNet.ConnectionString`

---

## Environments

**Project configuration:** One configuration defined — `Development` (Finance.dtproj inferred from standard dtproj structure).

**Default server values in Project.params:**
- `DBServer` = `Q-DB03.NAM.WIRECARD.SYS\DB03,2232` (Q-prefix = QA/test environment)
- `DBServer_ECNT` = `Q-DB04.NAM.WIRECARD.SYS\DB03,2232` (QA)
- `SMTPServer` = `nl-smtp-01.nam.wirecard.sys`
- `DestinationFolder` = `\\q-na-bat03.nam.wirecard.sys\c-base\runtime\CAS_CSL\` (Q-prefix = QA batch server)

The Q-prefix servers suggest the checked-in defaults point to **QA/test servers**, not production. Production server names and file paths are presumably overridden via the SSIS catalog environment at deploy time.

Connection managers in `.conmgr` files reference **development servers** (prefix `d-`):
- `d-na-db02.nam.wirecard.sys\db02,2232` (Atlys_FcCR, Atlys_RvCR)
- `q-db03.nam.wirecard.sys\db03,2232` (cf_report)

---

## SQL Agent Job Scheduling

No SQL Agent job scripts are present in the repository. Based on package naming and financial reporting cadence, the expected scheduling is:

| Package | Expected Frequency | Trigger |
|---|---|---|
| `MonthEnd_NegativeBalance.dtsx` | Monthly — last business day | SQL Agent scheduled job |
| `MonthEnd_NonZeroBalance.dtsx` | Monthly | SQL Agent scheduled job |
| `MonthEnd_PositiveBalance.dtsx` | Monthly | SQL Agent scheduled job |
| `NegativeBalance_Snaphot.dtsx` | Monthly | SQL Agent scheduled job |
| `Cambridge_ReconFile.dtsx` | Daily or monthly | SQL Agent scheduled job |
| `Atlys_RfCks.dtsx` | Daily or weekly | SQL Agent scheduled job |
| `Export_GP_CCP_PBR.dtsx` | Monthly (billing cycle) | SQL Agent scheduled job or manual |
| `Atlys_recalc_forecast.dtsx` | On-demand or weekly | SQL Agent scheduled job or manual |
| `Salesforce_Update_Atlys_Forecast.dtsx` | Weekly or monthly | SQL Agent scheduled job |

---

## Failure Handling

**Within packages:**
- `NegativeBalance_Snaphot.dtsx` — Single Execute SQL Task; failure propagates as package failure with no retry
- `MonthEnd_*.dtsx` packages — typically contain precedence constraints; exact failure handling depends on inner package logic (not fully inspected due to file size)
- No retry loops are visible in the smaller inspected packages

**General SSIS failure handling patterns for this repo:**
- No Script Task retry loops (unlike DS_ETL_database-maintenance)
- SSIS package failures would surface as SQL Agent job step failures
- Without in-package Send Mail Tasks, failure notifications depend on SQL Agent operator email configuration

---

## Alerting

**`SMTPServer` project parameter** is defined (`nl-smtp-01.nam.wirecard.sys`) — suggesting at least some packages include email notification tasks. The SMTP server is referenced in `Project.params` line 58 and is available to all packages as `$Project::SMTPServer`. Whether it is actively used in Send Mail Tasks within the larger packages (`MonthEnd_NegativeBalance`, `Cambridge_ReconFile`) requires deeper inspection of those packages' full XML.

---

## Operational Considerations

### File Output Management
- Flat files are written to `\\q-na-bat03.nam.wirecard.sys\c-base\runtime\CAS_CSL\`
- File names include date stamps (e.g., `MonthlyBalance_20210128.csv`)
- No file archival, cleanup, or rotation logic is visible within these packages
- Long-term accumulation of monthly CSV files on the share must be managed externally

### Network Share Availability
- UNC path `\\q-na-bat03.nam.wirecard.sys` must be accessible from the SSIS execution host
- Share permissions must allow the SQL Server Agent service account write access
- No error handling for share unavailability is visible in the inspected packages

### Salesforce Integration Operational Risk
- `Salesforce_Update_Atlys_Forecast.dtsx` integrates with an external SaaS system (Salesforce)
- API rate limits, credential expiry, or Salesforce maintenance windows could cause failures
- No retry or rate-limit handling is visible from the package metadata

---

## Known Operational Risks

| Risk | Severity | Notes |
|---|---|---|
| No CI/CD | High | All deployments manual; environment drift risk |
| Empty stub package (`Monthly_Account_Balance`) committed | Medium | May indicate incomplete development; could confuse operators |
| Output files not encrypted | High | Account numbers and balances in plaintext CSV on a network share |
| SMTP server referenced but usage unclear | Medium | Alerting gaps if Send Mail Tasks absent in large packages |
| Q-prefix default servers | Low | If Q-servers are accidentally used in production, data integrity issue |
| `development` branch only | Medium | No feature/hotfix branch strategy; changes directly on development |
