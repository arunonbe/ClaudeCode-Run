# DevOps & Operations Report — DS_CCP_db09

## Build System

There is **no build system** in DS_CCP_db09. The repository contains no solution files, no project files, no Makefile, no PowerShell deployment scripts, and no CI/CD pipeline definitions (no `.gitlab-ci.yml`, no Jenkinsfile, no Azure DevOps YAML). This is a flat collection of SQL scripts named with date-ticket prefixes.

## Deployment Mechanism

**Fully manual, run-order-by-filename convention.** Scripts are named in the format:

```
YYYYMMDD_TICKET-NUMBER_description.sql
```

Example: `20200804_NAMDATASVC-2398_DB09 Disable jobs.sql`

Operators must:
1. Identify the relevant scripts from the Git commit history or ticket reference.
2. Connect to the target instance (`p-db09\db09` for production, `c-db09\db09` for COB/continuity, or a dev/test server) using SQL Server Management Studio (SSMS).
3. Execute the scripts manually in date order.

There is no idempotency check at the repository level — some scripts include `IF NOT EXISTS` guards on job categories but most job-creation blocks will fail if executed twice (duplicate job error).

## Database Change Management

The change management approach is **ticket-driven manual scripting**, not a formal migration framework (no Flyway, Liquibase, or SSDT publish profiles are present). This has the following implications:

- **No version tracking**: The database instance has no schema version table. There is no way to programmatically determine which scripts have been applied.
- **No rollback scripts**: None of the scripts in the repo include a corresponding rollback or undo script. The mass-disable file (`20200804...`) is a permanent state change with no enable-all counterpart.
- **No automated deployment gate**: Scripts could be applied in the wrong order or duplicated without detection.

## Environment Strategy

The scripts implement an environment-aware pattern through `@@SERVERNAME` prefix conventions:

| Server Prefix | Environment | Job Status |
|---|---|---|
| `D-%` | Development | Jobs disabled |
| `T-%` or `Q-%` | Test/QA | Jobs disabled |
| `C-%` | COB/Continuity | Jobs disabled (explicit `IF @@SERVERNAME LIKE 'C-%' SET @enabled = 0`) |
| `P-%` (default) | Production | Jobs enabled |

This is a reasonable environment isolation pattern, but its correctness depends entirely on servers being correctly named.

## CI/CD Pipelines

None. No pipeline configuration files exist in this repository.

## Scheduled Job Inventory (Operational Reference)

| Job | Schedule | Time |
|---|---|---|
| `oas_export_sunrise_fis_settlement` | Daily | 03:55 AM |
| `oas_export_sunrise_fis_dailyfees` | Daily | 03:57 AM |
| `wired_cache_refresh` | Daily | 03:45 AM |
| `wired_cache_GP` | Daily + 2nd/3rd of month | 05:30 PM / 10:00 AM |
| Various sunrise_* jobs | Daily (DISABLED as of Aug 2020) | — |
| Various Export_* jobs | Daily (DISABLED as of Aug 2020) | — |

All production jobs are configured with email notification on failure to operator `DBA` using Database Mail profile `SQLMail` (updated in `20201113_SQ-1114 update sql agent operator and dbmail account.sql` to use `NoReply@northlane.com`).

## Monitoring and Alerting

- SQL Agent failure notifications are enabled via `@notify_level_email=2` (on failure) in all job definitions.
- A dedicated stored procedure `ODS.dbo.usp_SQLAgentFail_Notification` (defined in DS_CCP_ods) polls `msdb.dbo.sysjobactivity` every 5 minutes and sends HTML-formatted failure emails.
- No application performance monitoring (APM), no Azure Monitor integration, no log aggregation beyond SQL Server Agent logs is evident.
- **Gap**: No alerting on long-running job durations, no SLA-breach monitoring, no dashboard.

## Backup and Recovery

No backup or restore scripts appear in this repository. Backup configuration would be managed at the SQL Server instance level (likely via SQL Server Maintenance Plans or Ola Hallengren scripts on p-db09). This repo provides no evidence of backup coverage.

## Operational Risks

1. **Manual-only deployment**: A human error during manual script execution against production cannot be easily detected or reversed. One incorrectly-run script (e.g., running a job-disable script in production) could halt all ETL processing without notice beyond the nightly failure email.

2. **sa-owned jobs**: All SQL Agent jobs use `@owner_login_name=N'sa'`. If the SA account password changes or is locked, all jobs will fail silently or with permission errors.

3. **Hardcoded SSISDB ENVREFERENCE integers**: Commands like `/ENVREFERENCE 3` will silently execute against the wrong environment configuration if SSISDB is rebuilt and reference IDs shift.

4. **Legacy server names**: Multiple scripts hardcode `p-db09.nam.wirecard.sys\db09` and `c-db09\db09`. These DNS names are Wirecard legacy infrastructure names. If DNS resolution changes (post-Northlane/Onbe migration), jobs will fail to locate the SSIS server.

5. **Missing runbook**: Job descriptions link to `https://confluence.wirecard.sys/pages/viewpage.action?pageId=83015220` — a Wirecard Confluence instance that is likely no longer accessible post-acquisition. Operational runbooks are effectively orphaned.

6. **CCP shutdown state**: The mass job-disable in August 2020 was never followed by a cleanup/decommission script. Disabled jobs occupy SQL Agent namespace and can cause confusion. A formal decommission (job deletion + SSISDB project cleanup) is overdue.

7. **No change audit trail in-DB**: There is no database-side audit table tracking which scripts ran, when, and by whom. The Git history serves as the only record.
