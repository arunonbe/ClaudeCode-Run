# DevOps / Operations View — DS_ETL_database-maintenance

## Repository Overview

**Repo path:** `E:\OnbeEast363\repos\DS_ETL_database-maintenance`
**Git branch observed:** `master`
**Git remote:** `origin` (shallow clone — `shallow` file present)

---

## CI/CD Pipeline

**No CI/CD configuration was found in this repository.** There are no:
- `.gitlab-ci.yml` files
- `Jenkinsfile`
- Azure DevOps pipeline YAML files
- GitHub Actions workflows
- Build or deployment scripts (`.ps1`, `.bat`, `.sh`)

The repository contains only the SSIS solution and project files. Deployment is entirely manual — an engineer opens the `.dtsproj` in SQL Server Data Tools (SSDT) and deploys to the SSIS catalog (SSISDB), or uses the `isdeploymentwizard.exe` command-line tool.

**Gap:** The absence of a CI/CD pipeline means there is no automated testing, no environment promotion gate, and no deployment audit trail beyond git history.

---

## SSIS Deployment Approach

The project uses the **Project Deployment Model** (confirmed by `<DeploymentModel>Project</DeploymentModel>` in `database-maintenance.dtproj` line 3). This is the modern SSIS deployment approach.

**Manual deployment steps (inferred):**
1. Open `Database-Maintenance.sln` in SSDT
2. Build project → produces `bin\Development\database-maintenance.ispac`
3. Deploy `.ispac` to SSISDB via the Integration Services Deployment Wizard or:
   ```
   isdeploymentwizard.exe /Silent /SourceType:Project /SourcePath:bin\Development\database-maintenance.ispac /DestinationType:SSIS /DestinationServer:<server> /DestinationPath:/SSISDB/FolderName/database-maintenance
   ```
4. Configure environment variables in SSISDB to override `CM.Index Server.ServerName` for each environment (dev/QA/prod)

**Protection level concern:** `EncryptSensitiveWithUserKey` means the `.ispac` is user-key-encrypted. If the build/deploy machine user differs from the developer who last saved the project, sensitive parameters may need to be re-entered at deployment time.

---

## SQL Agent Job Scheduling

**No SQL Agent job definitions (`.sql` scripts) are stored in this repository.** The scheduling must be configured directly on the target SQL Server instance via SQL Server Management Studio (SSMS).

**Inferred schedule based on parameters:**
- The `time_limit` of 28,800 seconds (8 hours) and `exec_time_limit` of 3,600 seconds (1 hour) suggest a nightly maintenance window
- Typical schedule: `EXEC msdb.dbo.sp_start_job N'...'` or a SQL Agent job step of type "SQL Server Integration Services Package" targeting the deployed SSISDB package
- The package is designed to be **self-terminating** — it exits the loop when either the job completes or the 8-hour budget is exhausted

---

## Failure Handling

Failure handling is implemented within the C# Script Task (`ScriptMain.cs`):

| Scenario | Behaviour | Code Location |
|---|---|---|
| SQL command timeout | Sleep `exec_delay` seconds, then continue loop | `ScriptMain.cs` lines 537–539 |
| Non-timeout exception | Fire SSIS error event → package fails | `ScriptMain.cs` lines 533–535 |
| Time limit exceeded | Loop exits, package completes successfully | For Loop condition, dtsx line 226 |
| `exec_done = true` | IndexOptimize completed without timeout; loop exits | `ScriptMain.cs` line 523 |

The distinction between timeout failures (recoverable) and other failures (non-recoverable) is business-appropriate: a timeout means the index operation exceeded the SQL command window but the server is still healthy, while other exceptions (e.g., permission errors, server unavailable) warrant alerting.

---

## Alerting

**No email alert tasks (Send Mail Task) or notification components are present in this package.** Alerts depend entirely on:
1. SQL Agent job failure notification (if configured in SSMS) — not managed by this repo
2. SSIS catalog execution status monitoring (manual or via custom monitoring query against `SSISDB.catalog.executions`)
3. Any external monitoring platform (e.g., Datadog, SCOM) polling the SQL Agent job status

**Gap:** There is no built-in alerting for execution failures or completion confirmation. A production-grade maintenance package should include a Send Mail Task on the failure path.

---

## Environments

The project has one defined configuration:
- **Development** (from `database-maintenance.dtproj` line 243: `<Name>Development</Name>`)

No QA, UAT, or Production configurations are defined in the project file. Environment-specific server names must be overridden via SSIS catalog environment variables at runtime.

**Connection string for development/default target:** `d-phl-db01.wirecard.lan` (Philadelphia data centre, legacy Wirecard domain). Production likely points to a different server via SSIS catalog environment variable binding.

---

## Operational Runbook Notes

- **Pre-requisite:** Ola Hallengren's `IndexOptimize` stored procedure must be deployed to `master` on the target server
- **Monitoring:** Query `master.dbo.CommandLog` after execution to verify which indexes were processed
- **Parameter tuning:** For a server under heavy transactional load, reduce `exec_time_limit` or increase `exec_delay` to reduce index reorganisation contention
- **Scale-out:** This single package targets one server. Each additional SQL Server instance requiring maintenance requires a separate SSIS catalog environment pointing to that server, with the same `.ispac` deployed
- **Git branch:** Only `master` branch exists. No feature/hotfix branching convention is visible. The shallow clone suggests CI/CD pull may only retrieve tip commits

---

## Known Operational Risks

| Risk | Severity | Notes |
|---|---|---|
| No CI/CD | Medium | Manual deployments risk environment drift |
| No in-package alerting | Medium | Failures may go undetected without external monitoring |
| DPAPI protection level | Low-Medium | Deployment from different user account drops sensitive parameters |
| Hardcoded development server | Low | `d-phl-db01.wirecard.lan` in default connection; must be overridden via catalog |
| Single package scope | Low | Only one server targeted per deployment; no fan-out |
