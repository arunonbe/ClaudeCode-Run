# DevOps / Operations View — DS_ETL_generic-etl

## Repository Overview

**Repo path:** `E:\OnbeEast363\repos\DS_ETL_generic-etl`
**Git branch:** `development`
**Remote:** `origin` (shallow clone)

---

## CI/CD Pipeline

**No CI/CD configuration is present.** Consistent with all other DS_ETL_* repos. All deployments are manual.

---

## SSIS Deployment Approach

**Mixed deployment model indicators:**
- The project file (`ETL.dtproj`) uses Project Deployment Model structure
- Some packages (`StarSf.dtsx`) use project-level parameters (`$Project::SMTPServer`)
- The `Ecountcore_Process.conmgr` and `cbaseapp.conmgr` connection managers suggest this may use the older configuration table approach or direct connection manager files

The `Generic-ETL.sln` is a Visual Studio solution referencing the `ETL` project. Deployment target is the SSIS catalog (`SSISDB`) on the production SQL Server.

---

## Environments

**Default connection strings point to development/QA servers:**
- `d-na-db01.nam.wirecard.sys\db01` (dev) — `cbaseapp`, `Ecountcore_Process`, `Vendor`
- `q-db03.nam.wirecard.sys,2232` (QA) — `cf_report`
- `alchemy-srv-dev.database.windows.net` — **"dev" Azure SQL** in the connection name — this is a development Azure SQL endpoint

The Azure SQL connection (`alchemy-srv-dev`) has "dev" in the hostname. If a production Azure SQL Database exists for this data, it would have a different hostname (e.g., `alchemy-srv-prod.database.windows.net`). The committed connection file points to the development instance.

---

## SQL Agent Job Scheduling

No SQL Agent job definitions in repository. Expected schedules:

| Package | Expected Frequency |
|---|---|
| `FDR_Import_DD031` | Daily — after FDR file delivery (typically early morning) |
| `IVR_CallLogs` | Daily — overnight processing |
| `RC_Contact_Log` | Daily or weekly |
| `IVR_card_activation_update` | Continuous or frequent intraday |
| `StarSf` | Monthly — requires manual file update |
| `CSL_Activity` | Weekly or monthly |
| `Export_Network_Settlement_Sunrise` | Daily or per-settlement-cycle |
| `Add_CSA_Archive_Comment` | Daily or on-demand |
| `Folder_File_CleanUp` | Nightly |

---

## Failure Handling

### `StarSf.dtsx` — Most Complete Alerting Pattern
This package has explicit email notification parameters:
- `FailMailSubject` = "FAILED - Monthly STARsf File Creation"
- `EmailCC`, `EmailFrom` parameters
- SMTP connection manager wired to `smtp.nam.wirecard.sys`

This indicates a Send Mail Task exists within the package body, triggered on the failure path. However:
- Email addresses are Northlane-era (`@northlane.com`) — may be stale post-Onbe rebrand
- SMTP connection uses `UseWindowsAuthentication=False; EnableSsl=False` — unauthenticated, unencrypted relay

### Other Packages
Without full inspection of the large packages (`FDR_Import_DD031`, `IVR_CallLogs`, `RC_Contact_Log`), failure handling cannot be fully assessed. Given the pattern in this repo set, likely minimal in-package alerting beyond SQL Agent job failure notifications.

---

## `StarSf.dtsx` — Operational Concern: Manual Monthly File Update Required

**File:** `StarSf.dtsx`, line 29:
```
C:\ETL\In\STARsf\STARSf_10_2020.XLSX
```

The hardcoded filename includes a month/year (`10_2020`). While this is the default parameter value and the actual path is presumably overridden at runtime, it indicates a manual step is required each month: someone must update the `destination_fullname` variable/parameter with the new file path. This is an operational risk — if the update is forgotten, the package will attempt to read a 2020 file in a future month.

**Remediation:** Replace with a dynamic file path expression based on `GETDATE()` (year/month), similar to the date-stamped file patterns used in DS_ETL_finance packages.

---

## Azure SQL Connectivity — Operational Considerations

**Package:** `RC_Contact_Log.dtsx`
**Connection:** `alchemy-srv-dev.database.windows.net` (Azure SQL Database)

Connecting from an on-premise SSIS execution host to Azure SQL requires:
1. **Firewall rule:** The on-premise execution server's IP must be allowed in the Azure SQL firewall
2. **SQLNCLI11 driver compatibility:** SQLNCLI11.1 is not the recommended driver for Azure SQL (use Microsoft ODBC Driver 18 for SQL Server or `System.Data.SqlClient`/`Microsoft.Data.SqlClient`)
3. **Credential management:** SQL auth credentials (`rc_contact_log_user`) must be rotated periodically; no mechanism for automatic rotation is present
4. **Network egress:** SSIS execution host must have outbound TCP 1433 access to Azure SQL

---

## Known Operational Risks

| Risk | Severity | Notes |
|---|---|---|
| Azure SQL password in git | Critical | `alchemy-srv-dev.conmgr` — SQL auth password blob committed |
| Hardcoded monthly filename in StarSf | High | Manual update required monthly; operator error risk |
| Stale email addresses (`@northlane.com`) | Medium | Post-Onbe rebrand, notifications may be undeliverable |
| Unencrypted SMTP in StarSf | Medium | Email notifications sent without TLS |
| FDR_Import timing dependency | High | Late FDR file delivery cascades to downstream reconciliation |
| No file delivery confirmation | Medium | No logic to verify FDR file integrity before import |
| Azure SQL with SQLNCLI11 | Medium | Deprecated driver for Azure SQL connections |
| No CI/CD | High | All 9 packages deployed manually |
