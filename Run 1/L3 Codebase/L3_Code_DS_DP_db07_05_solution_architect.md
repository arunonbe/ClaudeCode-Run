# DS_DP_db07 — Solution Architect View

## Technical Architecture
- **Platform**: SQL Server 2012 (MSSQL11), compatibility level 110, on Windows Server
- **Primary artefacts**: T-SQL scripts creating/modifying SQL Agent jobs and SSISDB configuration
- **HA topology**: Scripts reference both `p-db07.nam.wirecard.sys\db07` and `p-db07-ha.nam.wirecard.sys\db07`, consistent with SQL Server Always-On AG with a listener named `p-db07-ha`
- **Tempdb**: Modified for Finance SSIS usage (script `20200124_NAMDATASVC-1454`)
- **DBAdmin database**: SQL Server 2012 compat (110), FULL recovery model, data on `E:\MSSQL11.DB07\MSSQL\DATA\`, log on `F:\MSSQL11.DB07\MSSQL\Data\`
- No application code (no ORM, REST API, or messaging); pure SQL Server infrastructure

## API Surface
- None. DB07 is not an API provider. It exposes:
  - SQL Agent jobs (invocable via `msdb.dbo.sp_start_job`)
  - SSISDB catalog (invocable via SSIS catalog stored procedures)
  - `DBAdmin.dbo.Audit_blocked_ip_user` for security audit queries

## Security Posture

### Authentication / Authorization
- All SQL Agent jobs owned by `sa` — violates PCI DSS least-privilege (Req 7.2)
  - Files: every `.sql` file with `@owner_login_name=N'sa'`
- LOGON trigger `TR_check_ip_address_functional_user` executes as `sa` (`WITH EXECUTE AS 'sa'`)
  - File: `20200821_WDNAMCBTS-322_DB07 Alter server trigger TR_check_ip_address_functional_user.sql`
  - Risk: trigger errors can block all logins; executing as `sa` means trigger code runs with full sysadmin
- SSIS connections use Windows Integrated Security (`Integrated Security=SSPI`) — no embedded passwords visible in connection managers

### Secrets / Credentials
- No hardcoded passwords found in any `.sql` file
- Connection strings reference Windows auth exclusively for SQL connections
- SMTP server address `nl-smtp-01.nam.wirecard.sys` is hardcoded; no credentials present (assumes relay allows from server)

### Crypto
- SMTP explicitly set `EnableSsl=False` — plaintext email for all job alerts
  - File: `20201207_SQ-307_p-db07_Warehouse_update_package_configs.sql` line 1
- No TDE configuration scripts present
- No column encryption

### Network Controls
- LOGON trigger enforces IP allowlist for functional accounts via `ValidIPAddress` table
- Audit logging to `DBAdmin.dbo.Audit_blocked_ip_user` with 90-day retention
- Retention gap: PCI DSS Req 10.7 requires 12 months; only 90 days implemented

## Technical Debt
| Item | Severity | Evidence |
|---|---|---|
| SQL Server 2012 EOL (July 2022) | Critical | MSSQL11.DB07, compat level 110 |
| sa ownership of all Agent jobs | High | All SQL files |
| Legacy email domains (wirecard.com, northlane.com) | High | Multiple SQL files |
| SMTP plaintext (EnableSsl=False) | High | `20201207_SQ-307_p-db07_Warehouse_update_package_configs.sql` |
| LOGON trigger executes as sa | High | `20200821_WDNAMCBTS-322_DB07 Alter server trigger...sql` |
| No version-controlled SSIS package source | Medium | SSIS packages in SSISDB not in repo |
| No CI/CD pipeline | Medium | Repo contains no pipeline definitions |
| Hardcoded *.nam.wirecard.sys DNS names | Medium | All connection manager scripts |
| Ad-hoc DW dimension corrections (SQ-2600, SQ-3539) | Medium | Direct DELETE on dim.DimTransactionType |
| 90-day audit retention vs 12-month PCI requirement | Medium | `20200917_WDNAMCBTS-517_003_SQLAgent-DBMP...sql` line 48 |

## Gen-3 Migration Requirements
1. Replace SQL Agent + SSIS with a cloud-native orchestrator (Azure Data Factory, Airflow, or Prefect).
2. Migrate SSIS package logic to ADF pipelines or Python/Spark-based ETL.
3. Replace LOGON trigger IP control with network security groups / Azure AD Conditional Access policies.
4. Replace SMTP relay with authenticated, TLS-enabled mail service.
5. Rotate all SQL Agent job ownership away from `sa` to dedicated service accounts.
6. Update all recipient email addresses to `onbe.com` domain.
7. Replace `*.nam.wirecard.sys` DNS with current infrastructure hostnames before migration.
8. Implement a proper migration runner (Flyway/Liquibase) for schema changes.
9. Increase audit log retention to minimum 12 months (PCI Req 10.7).

## Code-Level Risks (File:Line References)
| Risk | File | Approx Line |
|---|---|---|
| LOGON trigger WITH EXECUTE AS 'sa' | `20200821_WDNAMCBTS-322_DB07 Alter server trigger TR_check_ip_address_functional_user.sql` | 8 |
| SMTP EnableSsl=False | `20201207_SQ-307_p-db07_Warehouse_update_package_configs.sql` | 1 |
| sa job ownership pattern | `20191211_NAMDATASVC-592_SQLAGENTJob_Salesforce_to_Atlys.sql` | 28 (and all job scripts) |
| Old email recipients (wirecard.com) | `20191008_namdatasvc-1393_SQLAgentJobAlerts.sql` | 40 |
| Direct DELETE on Prepaid_Warehouse dim | `20210511_SQ-3539_DB07 Remove unused Transaction Codes for Same Day ACH.sql` | 71 |
| DBAdmin compat level 110 (SQL 2012 EOL) | `20200821_WDNAMCBTS-322_DB07 Create DBAdmin database.sql` | 12 |
