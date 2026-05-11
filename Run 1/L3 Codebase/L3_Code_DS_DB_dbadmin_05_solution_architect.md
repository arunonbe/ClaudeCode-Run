# Solution Architect View — DS_DB_dbadmin

## Technical Architecture
- **Project type**: SSDT SQL Database Project (`DBAdmin.sqlproj`), SQL Server 2016 schema provider (`Sql130`), Visual Studio 2017 solution.
- **Object count**: ~70 tables, ~120 stored procedures, 2 functions, ~50 security principals.
- **Execution context**: Stored procedures run in the `DBAdmin` database but cross-reference `master`, `msdb`, and application databases via dynamic SQL and three-part names.
- **Monitoring pattern**: Hybrid — some procedures write to staging tables (pull pattern), others return result sets directly (push/query pattern), and a small number send email (push-notification pattern).

## API Surface
No REST or SOAP API. The external interface consists of:
- **SQL stored procedures** callable by monitoring tools (SiteScope calls `usp_GetJobStatus_SiteScope`).
- **SQL tables** readable by FortiDB, InfoSec scanners via granted roles.
- Implicit interface: any application that calls `dbo.app_func_in_same_fdr_cycle` cross-database depends on this database being present.

## Security Posture

### Authentication
- Windows domain accounts (`NAM\*`) for service accounts and named users.
- SQL logins for application service accounts (ordersvc, report, vascan, scpardb, etc.).
- No evidence of certificate-based or token-based authentication.

### Authorisation
**Critical finding — over-privileged role assignments in `Security\RoleMemberships.sql`:**

| Principal | Role | Risk |
|---|---|---|
| `NAM\ppa_prd_mon` | `db_owner` | Monitoring account should not be owner |
| `NAM\PPA_PRD_CSWSVC` | `db_owner` | Application service account as DB owner |
| `NAM\PPA_DB_ACCESS` | `db_owner` | Generic access account as DB owner |
| `NAM\PPA_PRD_APISVC` through `SCHSVC` (10 accounts) | `db_owner` | ALL major service accounts are db_owner |
| `NAM\PROD_CPP_APAC` | `db_owner`, `db_accessadmin`, `db_securityadmin` | Triple-elevated APAC account |
| `NAM\ISA_SQL_SECADMIN` | `db_accessadmin`, `db_securityadmin`, `db_denydatawriter` | Correct pattern for ISA |

10+ production service accounts holding `db_owner` on a DBA monitoring database violates PCI DSS Req 7 (least-privilege access) and creates a significant lateral movement risk.

### Cryptography
- `QS_DA_Check_SA_Password` — `WITH ENCRYPTION`. Procedure body is opaque; cannot be reviewed for correctness.
- `QS_CheckCmdShell` — `WITH ENCRYPTION`. Same concern.
- No column-level encryption or Always Encrypted in use.
- No TDE project settings.

### Secrets
- **`utl_dba_drive_space_alert`**: `@From = 'dba-notify@ecount.com'` — not a credential, but a hardcoded identity from the legacy ecount.com domain.
- **`sp_job_monitor`**: `@MailRecipients = 'prepaid.support@imcnam.ssmb.com'` — hardcoded legacy Citigroup email. Alerts are effectively dead.
- **`sp_send_cdosysmail`**: This procedure may accept SMTP credentials in its implementation (CDO can be configured with hardcoded SMTP auth). The procedure is in `master` and not in this repo — its implementation is unknown.
- No embedded passwords or API keys found in source files reviewed.

### CVEs
- `sp_send_cdosysmail` uses the deprecated Windows CDO library, which has known security weaknesses and is unsupported on modern Windows Server versions.
- Dynamic SQL in `Collect_Index_Information` (`set @cmd = 'use ' + @dbname`) — `@dbname` is a `sysname` parameter, which limits injection risk to sysname-valid strings, but the pattern should still be validated.

## Technical Debt
| Item | File:Line | Severity | Notes |
|---|---|---|---|
| 10+ service accounts as `db_owner` | `Security\RoleMemberships.sql` | CRITICAL | PCI DSS Req 7 violation; lateral movement risk |
| Hardcoded dead email address | `dbo\Stored Procedures\sp_job_monitor.sql:107` | HIGH | Job alerts are not delivered |
| CDO mail in drive-space alert | `dbo\Stored Procedures\utl_dba_drive_space_alert.sql:22` | HIGH | Deprecated; alerts likely fail silently |
| Hardcoded legacy email domain | `dbo\Stored Procedures\utl_dba_drive_space_alert.sql:22,25` | HIGH | ecount.com domain |
| Encrypted procedures | `QS_DA_Check_SA_Password.sql`, `QS_CheckCmdShell.sql` | MEDIUM | Not auditable; violates code review requirements |
| Point-in-time investigation tables | `DBAdmin.sqlproj:157-168` | MEDIUM | `so_fee_add_funds_*`, `trace_*` tables from 2010–2018 in production project |
| No publish profile / deployment runbook | (repo-level) | MEDIUM | Manual deployment with no documented process |
| No CI/CD pipeline | (repo-level) | MEDIUM | No automated build or deployment validation |
| `app_func_in_same_fdr_cycle` in DBA database | `dbo\Functions\app_func_in_same_fdr_cycle.sql` | LOW | Business logic in infrastructure DB creates hidden dependency |

## Gen-3 Migration Requirements
1. Replace `sp_send_cdosysmail` with `msdb.dbo.sp_send_dbmail` throughout.
2. Update all hardcoded email addresses to current Onbe domain targets.
3. Remediate `db_owner` assignments to least-privilege equivalents.
4. Decrypt and version-control encrypted procedures.
5. Move observability to modern tooling (Datadog, Azure Monitor); retain only SQL-native diagnostics in DBAdmin.
6. Remove all historical investigation tables from the project.
7. Add CI pipeline with dacpac build and deploy to non-production smoke test.

## Code-Level Risks
| Risk | File:Line | Description |
|---|---|---|
| Dynamic SQL cross-db | `Collect_Index_Information.sql:30` | `set @cmd = 'use ' + @dbname` — potential injection if @dbname sourced from untrusted input |
| `PRINT @cmd` in production | `Collect_Index_Information.sql:57` | Prints full SQL command to error log — information leakage of schema |
| `set rowcount` (deprecated) | `Collect_Index_Information.sql` | `SET ROWCOUNT` deprecated in SQL Server 2022; use `TOP` instead |
| Cursor in `SE_Get_Acc_Detail_Hist` pattern | Not in this repo but referenced | Row-by-row cursor pattern; shared function performance risk |
| `proc_kill_blocking_root` / `proc_kill_blocking_tx` | (dbo\Stored Procedures) | Kill procedures — if called incorrectly could terminate legitimate sessions |
