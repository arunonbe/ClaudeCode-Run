# Solution Architect Report — DS_CCP_db09

## Technical Debt Inventory

| Item | Severity | File(s) |
|---|---|---|
| All SQL Agent jobs owned by `sa` | HIGH | All job-creation scripts |
| Hardcoded SSISDB ENVREFERENCE integers | HIGH | `20190919_*` scripts (lines referencing `/ENVREFERENCE 2`, `/ENVREFERENCE 3`, `/ENVREFERENCE 4`) |
| Hardcoded production server name in commands | HIGH | `20191219-namdatasvc-1696_...sql` line 18, `wired_cache_refresh` job |
| Legacy Wirecard DNS hostnames in job commands | HIGH | Multiple files — `p-db09.nam.wirecard.sys\db09` |
| No deployment automation or CI/CD | HIGH | Entire repo |
| No idempotency protection on job creation | MEDIUM | All job-add scripts — will error if re-run |
| No rollback scripts | MEDIUM | All files |
| Dead Confluence runbook URLs | MEDIUM | Job descriptions referencing `confluence.wirecard.sys` |
| 17 disabled jobs never decommissioned | MEDIUM | `20200804_NAMDATASVC-2398_DB09 Disable jobs.sql` |
| SSISDB ENVREFERENCE resolution approach | MEDIUM | `20191107_...JobsForOASExportSunriseFISPackages.sql` (line 32–36) uses `MAX(reference_id)` query — fragile |
| SSH key file path committed to source control | LOW-MEDIUM | `20191107_namdatasvc-1527_ConfigurationForOASExportSunriseFISPackages.sql` lines 34, 43 |
| Manual data-patch scripts with no validation | LOW | `20200602_...sql`, `20200518_...sql`, `20191021_...sql` |

## Security Vulnerabilities Found

### 1. sa Account Job Ownership (HIGH — PCI DSS Req 8.2 / 8.6)
Every SQL Agent job created in this repo specifies `@owner_login_name=N'sa'`. This is the built-in SQL Server SA account. PCI DSS Requirement 8.2 prohibits use of shared/generic accounts for administrative functions without compensating controls. If the SA password changes or the account is disabled, all production ETL jobs will cease to function. Audit trail is also compromised — all job executions appear as `sa`, not a named service account.

**Remediation**: Create a dedicated SQL Server service account (e.g., `svc_etl_agent`) with minimum necessary permissions, and reassign all job ownership to that account.

### 2. Hardcoded SFTP Key File Path (MEDIUM — PCI DSS Req 3.4 / Secret Management)
File `20191107_namdatasvc-1527_ConfigurationForOASExportSunriseFISPackages.sql`, lines 34 and 43, commits the literal filesystem path to production SSH private key files:
- Production: `F:\ETL\Cert\openssh_wd_oas_prod`
- Test: `R:\ETL\Cert\openssh_wd_oas_test`

While the key file itself is not committed, the path is. Any attacker with read access to this repo can determine exactly where to look for the SFTP private key on the ETL server.

**Remediation**: Store key file paths in SSISDB sensitive parameters or Azure Key Vault, not in committed SQL scripts.

### 3. SSISDB Sensitive Variable with Empty Value Committed (LOW)
File `20191107_namdatasvc-1527_ConfigurationForOASExportSunriseFISPackages.sql`, line 22, creates the `OASSFTPPassphrase` sensitive variable with an empty string value: `@value=@var` where `@var` is explicitly set to `N''`. This means if this script is re-run, it overwrites any previously configured passphrase with an empty string, potentially breaking SFTP authentication silently.

### 4. Dynamic SQL in Job Command Construction (LOW — Information Disclosure)
File `20191107_namdatasvc-1527_JobsForOASExportSunriseFISPackages.sql`, lines 38 and 132: The SSIS execution command is assembled via string concatenation (`N'/ISSERVER ... /SERVER "\"' + @server + '\"" /ENVREFERENCE ' + @envref + ' ...'`). While this is T-SQL variable concatenation rather than user input, the pattern warrants review — particularly the `@envref` value derived from a `SELECT MAX(reference_id)` subquery. If SSISDB is manipulated, a wrong environment reference could be injected.

### 5. No SQL Injection Risk Found
All dynamic SQL in this repo is confined to server configuration commands building job step `@command` strings from server-side variables (`@@SERVERNAME`, static lookup queries). No user-facing parameters are incorporated into dynamic SQL here.

## Stored Procedures / Functions Referenced (Not Defined Here)

This repo does not define stored procedures. It calls system stored procedures:

| Procedure Called | System | Purpose |
|---|---|---|
| `msdb.dbo.sp_add_job` | SQL Server | Create SQL Agent job |
| `msdb.dbo.sp_update_job` | SQL Server | Update SQL Agent job settings |
| `msdb.dbo.sp_add_jobstep` | SQL Server | Add step to job |
| `msdb.dbo.sp_add_jobschedule` | SQL Server | Add schedule to job |
| `msdb.dbo.sp_add_jobserver` | SQL Server | Assign job to server |
| `msdb.dbo.sp_add_category` | SQL Server | Create job category |
| `msdb.dbo.sp_update_operator` | SQL Server | Update SQL Agent operator (email) |
| `msdb.dbo.sysmail_update_account_sp` | SQL Server | Update Database Mail account |
| `SSISDB.catalog.create_environment_variable` | SSISDB | Create SSIS environment variable |
| `SSISDB.catalog.set_object_parameter_value` | SSISDB | Set SSIS project/package parameter |
| `ODS.dbo.set_package_execution` | ODS | Record scheduled package execution config |

## Code Quality Issues

1. **Comment quality**: Older scripts (pre-2020) have minimal comments. Scripts from 2020 onward include JIRA ticket references and brief descriptions in job `@description` fields.
2. **Inconsistent environment detection**: Older scripts hardcode production server names (`p-db09\db09`); newer scripts use `@@SERVERNAME` dynamic resolution. The repo represents two generations of engineering practice.
3. **Tickets mix concerns**: Some scripts (e.g., `20191010_namdatasvc-1243_CopySQLAgentJobs2COB.sql`) bundle many unrelated job definitions into a single large file (~400+ lines), making partial application difficult.
4. **GOTO error handling**: All job-creation scripts use the old-style `GOTO QuitWithRollback` / `GOTO EndSave` pattern rather than TRY/CATCH. This is a SQL Server 2000-era pattern.

## Recommended Remediation Priority

| Priority | Action |
|---|---|
| P1 | Replace `sa` ownership on all SQL Agent jobs with a dedicated named service account |
| P1 | Remove hardcoded production SFTP key file paths from scripts; move to SSISDB sensitive params or Key Vault |
| P1 | Document and formally decommission the 17 disabled jobs (delete from msdb + archive SSIS projects) |
| P2 | Replace hardcoded ENVREFERENCE integers with SSISDB catalog lookup logic consistently |
| P2 | Replace hardcoded `p-db09.nam.wirecard.sys\db09` DNS references with parameterised or environment-detected values |
| P2 | Introduce a lightweight deployment log table on p-db09 to track which scripts have been applied |
| P3 | Convert job creation scripts to idempotent form (DROP-AND-RECREATE with IF EXISTS guards) |
| P3 | Update Confluence runbook URLs in job descriptions to current Onbe documentation |
| P3 | Implement TRY/CATCH error handling in place of GOTO pattern |
