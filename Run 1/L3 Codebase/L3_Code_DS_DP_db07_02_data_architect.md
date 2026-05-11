# DS_DP_db07 — Data Architect View

## Data Stores Touched
| Store | Server | Role |
|---|---|---|
| SSISDB | p-db07-ha.nam.wirecard.sys\DB07 | SSIS catalog — package param store, execution history |
| DBAdmin | p-db07-ha.nam.wirecard.sys\DB07 | Admin database — IP audit, job schedule cache |
| master | DB07 | SQLAgentJobAlerts_scheduled_jobs table |
| msdb | DB07 | SQL Agent job/schedule/server metadata |
| Prepaid_Warehouse | DB07 (implied) | Data warehouse — DimTransactionType dimension |
| ATLYS_FcCR | P-DB08-HA.nam.wirecard.sys\DB08 | Finance — Atlys forecast credit/receivable |
| ATLYS_RvCR | q-db04.nam.wirecard.sys\db04,2232 | Atlys revenue credit/receivable (dev/QA) |
| ODS | q-db03.nam.wirecard.sys\db03,2232 | Operational Data Store (referenced in ETL package) |
| Ecountcore_Process | p-db02-ha.nam.wirecard.sys\db02 | Core eCount processing database |
| Vendor | p-db06-ha.nam.wirecard.sys\db06 | Vendor data |

## Schema / Tables Known from Scripts
| Table | Database | Columns / Notes |
|---|---|---|
| dbo.Audit_blocked_ip_user | DBAdmin | created (datetime), IP_Address (varchar 48), Host_Name (nvarchar 256), Original_Login (nvarchar 256), Program_Name (nvarchar 256) |
| dbo.SQLAgentJobAlerts_scheduled_jobs | master | name (sysname), job_id (uniqueidentifier), next_scheduled_run_date (datetime), session_id (int) |
| dim.DimTransactionType | Prepaid_Warehouse | source_id (smallint), facility_id (smallint), fee_flag (tinyint), transaction_type_desc_level1 (varchar 50) |
| dbo.ValidIPAddress | master (implied by LOGON trigger) | ip (column) — stores approved IPs for functional accounts |
| dbo.usernames_functional_accounts | master (implied) | functional_user (column) |

## Sensitive Data Assessment
- `Audit_blocked_ip_user` stores IP addresses, hostnames, and SQL login names — classified as **infrastructure operational data**, not PAN/SAD; low cardholder-data risk.
- No PAN, account numbers, or cardholder PII observed in DB07 DDL directly. DB07 scripts orchestrate movement of such data through SSIS packages that touch DB02/DB06/DB08.
- File-path references to `\\p-na-bat03.nam.wirecard.sys\c-base\runtime\BankProcessQueue\mbprod\upload\DailyRecon\` suggest daily reconciliation files containing bank/program balance data — potential financial data on a file share (no encryption observed).

## Encryption
- No TDE or column-level encryption configured on the DBAdmin or master tables visible in scripts.
- SSIS connections use `Integrated Security=SSPI` (Windows auth) — no embedded passwords in connection strings.
- DBAdmin file paths: data on `E:\MSSQL11.DB07\MSSQL\DATA\` and log on `F:\MSSQL11.DB07\MSSQL\Data\` — no mention of BitLocker or disk-level encryption in scripts.
- SMTP configured with `EnableSsl=False` — all SQL Server email is sent in plaintext.

## Data Flow Diagram (Logical)
```
Source DBs (DB02/DB04/DB06/DB08)
        |
        v (SSIS packages invoked by SQL Agent on DB07)
    DB07 SSIS Execution
        |
        |---> Prepaid_Warehouse (DW on DB07 or DB08)
        |---> File Share (DailyRecon PBR files)
        |---> ATLYS_FcCR (Finance forecast)
        |---> ODS
```

## Data Quality / Retention
- `Audit_blocked_ip_user` retention = 90 days (weekly cleanup job).
- `SQLAgentJobAlerts_scheduled_jobs` table in `master` is truncated and reloaded every hour — no historical retention.
- DimTransactionType corrections are applied via ad-hoc scripts with no automated rollback; backup copy saved as `DimTransactionType_SQ3539` in DBAdmin.
- No data quality checks observed in DB07 DDL itself; quality is the responsibility of the individual SSIS packages.

## Compliance Gaps
1. **PCI DSS Req 10.7.1** — audit log retention for operational security events is 90 days; PCI requires 12 months.
2. **PCI DSS Req 4.2.1** — SMTP over plaintext (`EnableSsl=False`) for job alert emails is non-compliant where emails contain system information.
3. **PCI DSS Req 7/8** — `@owner_login_name='sa'` on all agent jobs violates least-privilege principles.
4. File shares (`DailyRecon`) holding financial data are not confirmed to be encrypted at rest; encryption posture unknown from source.
5. Database compatibility level 110 (SQL Server 2012) is end-of-life; no extended security updates after July 2022.
