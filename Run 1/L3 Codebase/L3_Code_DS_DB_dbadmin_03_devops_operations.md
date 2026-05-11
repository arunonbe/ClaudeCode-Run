# DevOps / Operations View — DS_DB_dbadmin

## Build and Packaging
- **SSDT Project**: `DBAdmin.sqlproj` (SQL Server Schema Provider: `Sql130` = SQL Server 2016+), Visual Studio solution `DBAdmin.sln` (VS 2017, format 12.00).
- **Target framework**: .NET 4.5 (TargetFrameworkVersion in sqlproj).
- Build produces a `.dacpac` artifact in `bin\Debug\DBAdmin.sql` or `bin\Release\DBAdmin.sql`.
- `SqlServerVerification=False` — SSDT build does not perform cross-database object verification, which is expected for a monitoring database that cross-references system objects.
- `IncludeCompositeObjects=True` — referenced external objects are included in the model.

## Deployment
- SSDT-based: deploy via `SqlPackage.exe /Action:Publish` or Visual Studio Publish with a publish profile.
- No publish profile (`.publish.xml`) is present in the repository — deployment target, connection string, and options must be supplied at deploy time.
- `DeployToDatabase=True` set in project.

**Recommended deployment steps** (inferred from project structure):
1. Build dacpac: `msbuild DBAdmin.sqlproj /p:Configuration=Release`
2. Deploy: `SqlPackage.exe /Action:Publish /SourceFile:DBAdmin.dacpac /TargetServerName:<host> /TargetDatabaseName:DBAdmin`

Security principal scripts under `Security\` must be deployed separately; they are `ALTER ROLE` / `CREATE USER` statements that depend on SQL logins existing at the instance level prior to deployment.

## Configuration Management
- No environment-specific configuration files (`.sqlcmdvars`, publish profiles) in the repository.
- `@MailRecipients = 'prepaid.support@imcnam.ssmb.com'` hardcoded in `sp_job_monitor` (line 107) — this is a legacy Citigroup/Smith Barney email address that is almost certainly no longer valid.
- `'dba-notify@ecount.com'` and `'dba-notify-emailonly@ecount.com'` hardcoded in `utl_dba_drive_space_alert` — legacy ecount.com email domain.
- `@MailProfile = 'SQLMail'` hardcoded in `sp_job_monitor` — assumes a Database Mail profile named exactly `SQLMail` exists on every target instance.
- No SQLCMD variable substitution for environment-specific values.

## Observability
| Signal | Mechanism | Notes |
|---|---|---|
| Long-running jobs | `sp_job_monitor` + Database Mail | Sends email when job exceeds threshold |
| Drive space pressure | `utl_dba_drive_space_alert` + `sp_send_cdosysmail` | 75% and 85% thresholds; uses legacy CDO mail |
| Blocking sessions | `BlockingMonitor` | Returns live blocking data; no alerting built-in |
| SQL Agent job status | `usp_GetJobStatus` / `usp_GetJobStatus_SiteScope` | SiteScope integration for external monitoring |
| Index fragmentation | `Gather_Index_Stats` + `indexstats` table | DBA-pull; no push alerting |
| Deadlocks | `audit_collection_deadlocks` | Capture table; no automated alert |
| Error log | `QS_ErrorlogCheck` / `QS_ErrorlogEntries` | DBA query; no automated scan |

**Gap**: `utl_dba_drive_space_alert` uses `master.dbo.sp_send_cdosysmail` — CDO (Collaboration Data Objects) mail is a deprecated Windows mechanism, superseded by `msdb.dbo.sp_send_dbmail`. `sp_job_monitor` correctly uses `sp_send_dbmail`.

## Infrastructure Dependencies
| Dependency | Notes |
|---|---|
| SQL Server 2016+ | Sql130DatabaseSchemaProvider |
| SQL Server Agent | Job monitoring requires access to msdb |
| Database Mail (SQLMail profile) | `sp_job_monitor` alerting |
| CDO Mail (`sp_send_cdosysmail`) | `utl_dba_drive_space_alert` — deprecated |
| `xp_fixeddrives` | Extended stored procedure in master |
| `xp_sqlagent_enum_jobs` | Extended procedure for job enumeration |
| Network access to `prepaid.support@imcnam.ssmb.com` | Legacy email target |
| FortiDB | `FortiDBRptRole` security principal implies FortiDB database activity monitor is deployed |
| InfoSec tools | `ifs_infosec`, `ifs_gidadb` security principals |
| Vulnerability scanner | `vascan` principal |

## Operational Risks
1. **Hardcoded legacy email addresses**: Alerts go to `@ecount.com` and `@imcnam.ssmb.com` domains — likely dead. DBA team may not receive any drive space or job alerts.
2. **CDO mail dependency**: `utl_dba_drive_space_alert` uses deprecated `sp_send_cdosysmail`. On newer SQL Server / Windows Server configurations this may fail silently.
3. **Overprovisioned service accounts on DBAdmin**: Multiple application service accounts (ORDERSVC, APISVC, etc.) are `db_owner` on the DBA monitoring database. A compromised service account could tamper with monitoring data or disable alerts.
4. **Encrypted procedures**: `QS_DA_Check_SA_Password` and `QS_CheckCmdShell` cannot be inspected at runtime — failures are opaque.
5. **No SSDT publish profile**: Deployments are ad hoc; no documented deployment runbook.

## CI/CD
- No CI/CD pipeline is present in this repository (no `.gitlab-ci.yml`, Jenkinsfile, or similar).
- SSDT project structure enables pipeline integration (dacpac build + SqlPackage deploy) but it has not been implemented.
- No automated test framework for stored procedures.
- Recommendation: Add a GitLab CI pipeline that builds the dacpac on every commit and runs a smoke-test deploy to a non-production instance.
