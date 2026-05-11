# DS_DP_db07 — DevOps / Operations View

## Build Process
- No automated build pipeline present. This repo contains only **T-SQL deployment scripts** (`.sql`) and a few `.txt` files with manual instructions.
- Scripts are named by date prefix and JIRA ticket (e.g., `20210611-SQ-3087-...`), establishing a manual changelog pattern.
- No SQL Server Data Tools (SSDT) project file or `.dacpac` build; changes are applied by running individual `.sql` files.

## Deployment Method
- **Manual script execution** against the target SQL Server instance (`P-DB07-HA`, `C-DB07`, etc.).
- Several scripts use `@@SERVERNAME LIKE 'C%'` and `LEFT(@@SERVERNAME,1) IN ('D','T','Q')` guards to differentiate Cloud/Dev/QA/Prod execution — conditional inline DDL.
- Deployment targets:
  - Production: `p-db07.nam.wirecard.sys\db07` / `p-db07-ha.nam.wirecard.sys\db07`
  - QA/Test: `q-db04.nam.wirecard.sys\db04,2232`
  - Dev: `d-na-db02.nam.wirecard.sys\db02,2232`
  - Cloud: `C-%` server prefix
- Scripts reference both `P-DB07` (standalone) and `P-DB07-HA` (HA listener), suggesting an Always-On Availability Group setup for production.
- Some deployment files are labeled `C-` (Cloud/Cert) and `P-` (Production) in filename prefix (e.g., `20201014_NATS-9461 C-DB07...` and `20201013_NATS-9461 P-DB07...`), indicating dual deployment artefacts.

## Configuration Management
- SSIS project/package parameter values are set via `SSISDB.catalog.set_object_parameter_value` T-SQL calls — environment-specific config stored in SSISDB catalog, not in files.
- SMTP server, email addresses, and DB connection strings are stored as SSIS project parameters, not in files in this repo.
- SMTP server: `nl-smtp-01.nam.wirecard.sys` (NorthLane era branding — may be stale).
- Email addresses: `techds@northlane.com`, `reporting@northlane.com`, `NAMSupport@wirecard.com`, `namds@wirecard.com` — all old-domain addresses.

## Observability
- **SQLAgentJobAlerts** job runs every hour; sends email on cancelled jobs or jobs that missed their scheduled window.
- Blocked login events written to `DBAdmin.dbo.Audit_blocked_ip_user` — queryable but no dashboarding/alerting configured in repo.
- SQL Server Agent email alerts configured via `msdb.dbo.sp_add_alert` (implied by operator setup) but no SCOM or external monitoring configured in repo artifacts.
- No logging or tracing infrastructure in this repo beyond SSISDB execution logs and Windows Event Log (`@notify_level_eventlog=0` — event log notification disabled on most jobs).

## Infrastructure Dependencies
| Dependency | Purpose | Risk if Unavailable |
|---|---|---|
| p-db07-ha.nam.wirecard.sys\DB07 | SSIS execution host | All orchestrated ETL stops |
| p-db08-ha.nam.wirecard.sys\DB08 | Finance SSIS source DB | Finance jobs fail |
| p-db02-ha.nam.wirecard.sys\db02 | eCount core processing | ETL jobs fail |
| p-db06-ha.nam.wirecard.sys\db06 | Vendor data | Vendor ETL fails |
| nl-smtp-01.nam.wirecard.sys | SMTP relay | No email alerts |
| p-na-bat03.nam.wirecard.sys | File share (DailyRecon) | PBR export fails |
| SSISDB catalog on DB07 | Package parameter store | All SSIS jobs misconfigured |

## Operational Risks
1. **All email addresses are legacy domain** (`wirecard.com`, `northlane.com`) — alerts are likely being silently dropped post-rebranding.
2. **Manual deployment with no version control enforcement** — no migration runner (Flyway, Liquibase, SSDT) ensures idempotency or ordering.
3. **`sa` ownership of all SQL Agent jobs** — privilege escalation risk; any job step running as `sa` has unrestricted access.
4. **LOGON trigger runs WITH EXECUTE AS 'sa'** — an error in the trigger could cause all logins to fail.
5. **Always-On AG assumed but not confirmed** — scripts reference both HA listener and standalone names inconsistently.
6. DBAdmin database files on local drives `E:` and `F:` — if these are single-instance disks, no HA for the audit database.

## CI/CD Assessment
- **No CI/CD pipeline** (no YAML, Jenkinsfile, or GitHub Actions workflow in this repo).
- Changes are tracked only by filename date prefix; no automated testing, no linting, no deployment gate.
- This is a Gen-1/Gen-2 operational artefact consistent with manual DBA-managed infrastructure.
