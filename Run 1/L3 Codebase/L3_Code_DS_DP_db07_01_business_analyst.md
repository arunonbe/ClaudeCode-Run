# DS_DP_db07 — Business Analyst View

## Business Purpose
DB07 is a SQL Server 2012 (MSSQL11) Data Platform node that acts as the **SSIS execution host** for the Onbe/NorthLane data services estate. It is the central SQL Server Agent job scheduler responsible for launching SSIS packages that feed the Prepaid Warehouse, Finance, ETL, BINBANK, and third-party ATM/vendor data pipelines. It does not own application databases directly; its primary value is orchestration and proactive job monitoring.

## Capabilities
- Hosts the SSISDB catalog (SSIS Integration Runtime) and runs SSIS packages by reference.
- Schedules and monitors SQL Agent jobs across multiple data pipelines (Finance, Warehouse, ETL, ATM/Cardtronics/Maritime, Salesforce-to-Atlys, IVR/NTT, Sykes call-summary, GP Export).
- Provides proactive email alerting for cancelled or missed SQL Agent jobs (SQLAgentJobAlerts job, runs hourly).
- Enforces login IP-address restrictions for functional accounts via a server-level LOGON trigger (`TR_check_ip_address_functional_user`).
- Hosts the `DBAdmin` database used for IP-block audit logging and support tables.
- Stores and cleans audit records of blocked login attempts (90-day retention, weekly Saturday job).
- Maintains SSISDB parameter configurations for environment-specific connection strings (D/Q/P tiers).

## Key Entities
| Entity | Location | Notes |
|---|---|---|
| DBAdmin | SQL Server database on DB07 | Audit tables, SQLAgentJobAlerts support tables |
| Audit_blocked_ip_user | DBAdmin.dbo | IP/hostname/login blocked by LOGON trigger |
| SQLAgentJobAlerts_scheduled_jobs | master.dbo | Rolling next-run schedule cache for alerting |
| Prepaid_Warehouse.dim.DimTransactionType | p-db07-ha | Warehouse dimension table updated by ad-hoc scripts |
| SSISDB | p-db07-ha | SSIS catalog; stores package parameters and execution logs |

## Business Rules
1. SQL Agent jobs on the CITI/Cloud environment (`@@SERVERNAME LIKE 'C%'`) are created in disabled state by all deployment scripts; only production/test environments are active.
2. Functional accounts are blocked from SQL Server login unless the originating IP is in the `ValidIPAddress` allow-list.
3. Blocked login events are logged and retained for 90 days.
4. Job scheduling uses environment-conditional server names — development uses `q-db04`, production uses `P-DB07-HA` or `P-DB08-HA`.
5. SSIS package parameters are set individually per project (`Finance`, `Warehouse`, `ETL`, `BINBANK`) via `SSISDB.catalog.set_object_parameter_value`.
6. Email notifications use the `DataServicesGroup-Operator` operator and SMTP server `nl-smtp-01.nam.wirecard.sys`.

## Data Flows
- SQL Agent job fires → calls `dtexec` via SSIS subsystem → SSIS package runs on DB07 → reads from source DB (DB02/DB04/DB06/DB08) → writes to target DB or file share.
- SQLAgentJobAlerts job → reads `msdb.sysjobs`, `sysjobservers`, `sysjobschedules` → sends email via `msdb.sp_send_dbmail` to `NAMSupport@wirecard.com` / `namds@wirecard.com`.
- LOGON trigger fires → reads `ValidIPAddress` → blocks or permits → inserts into `DBAdmin.dbo.Audit_blocked_ip_user`.
- File-system output: PBR daily recon files exported to `\\p-na-bat03.nam.wirecard.sys\c-base\runtime\BankProcessQueue\mbprod\upload\DailyRecon\`.

## Compliance Relevance
- IP restriction/LOGON audit is a compensating control relevant to **PCI DSS Req 7/8** (access control, identification/authentication).
- 90-day audit-log retention partially aligns with PCI DSS Req 10.5/10.7 but falls short of the 12-month requirement.
- Job monitoring (SQLAgentJobAlerts) supports **availability monitoring** expectations under PCI DSS Req 10 and SOC 2 availability criteria.
- SSISDB configuration contains plaintext server names and SMTP server names but no credentials visible in source.

## Risks (Business)
1. All SMTP references still use old `wirecard.com` / `northlane.com` domain addresses — alerts may go to inactive mailboxes post-Onbe rebranding.
2. No business-owner documentation; the only README says "db07".
3. Several scripts contain ad-hoc data corrections to `Prepaid_Warehouse.dim.DimTransactionType` (SQ-2600, SQ-3539) executed directly on production — no approval/audit trail in code.
4. `@owner_login_name = 'sa'` on all SQL Agent jobs is a PCI/least-privilege concern.
