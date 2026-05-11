# Business Analyst View — DS_DB_dbadmin

## Business Purpose
DS_DB_dbadmin is the DBA administration database for the Onbe (Wirecard Data Services) SQL Server estate. It is a dedicated `DBAdmin` database — a Gen-2 SSDT project — that consolidates DBA tooling: operational monitoring, index management, job monitoring, drive-space alerting, performance diagnostics, replication monitoring, SQL trace capture, and security provisioning. It does not hold production business data but acts as the observability and control plane for all SQL Server instances in the environment.

## Capabilities
1. **Blocking and deadlock monitoring**: Detect and report blocking sessions; kill blocking roots on demand.
2. **Index intelligence**: Collect, store, and analyse index statistics and fragmentation across all databases.
3. **Job monitoring**: Track running SQL Agent jobs, alert on long-running jobs exceeding configurable thresholds via Database Mail.
4. **Drive space alerting**: Poll fixed drives and send email alerts at 75% and 85% full thresholds.
5. **Database performance diagnostics**: ~100+ `QS_*` stored procedures exposing DMV data — buffer cache, wait statistics, locks, configurations, error logs, file stats, replication state.
6. **Security auditing**: `QS_DA_Check_SA_Password` (encrypted), `QS_DA_Find_Orphaned_Users`, `QS_DA_Check_Non_DBO_Objects`, `QS_DA_DBOptions`.
7. **SQL Trace management**: Start, stop, filter, and collect extended trace data into local tables.
8. **Replication monitoring**: Inspect replication agent status, reinitialise subscriptions.
9. **FDR cycle awareness**: `app_func_in_same_fdr_cycle` function encodes business knowledge of the FDR (First Data Resources) card processing day boundary (7 PM cutoff, Sunday lookback).

## Key Entities
| Entity | Type | Description |
|---|---|---|
| `indexstats` | Table | Index fragmentation snapshots across databases |
| `IndexMaintenanceControl` | Table | Controls which indexes are eligible for maintenance |
| `job_monitor` | Table | Running-job tracking with duration thresholds |
| `job_monitor_log` | Table | Historical alert log for long-running jobs |
| `dba_db_stats_history` | Table | Database-level size/growth history |
| `dba_log_stats` | Table | Log file size and usage over time |
| `DriveSize` / `DriveSpaceFree` | Tables | Drive capacity and free space snapshots |
| `audit_collection_deadlocks` | Table | Deadlock XML captured from system health session |
| `Audit_sessions` | Table | Session-level audit data |
| `blocking_correlation1` | Table | Blocking chain correlation data |
| `QS_*` tables | ~60 tables | Staging/result tables for diagnostic procedures |
| `app_func_in_same_fdr_cycle` | Function | Determines if two datetimes fall in the same FDR processing cycle |

## Business Rules
1. FDR day cycle: cutoff is 7 PM; Sunday lookback is 2 days (to account for weekend processing gap).
2. Drive alerts: 75% triggers email-only notification; 85% triggers escalation to DBA team.
3. Job monitor: alerts every 15 minutes if a job exceeds its duration threshold; logs each alert.
4. Blocking monitor: configurable wait-time threshold; can return session SQL text for both blocker and blocked sessions.
5. Security: `QS_DA_Check_SA_Password` is a WITH ENCRYPTION procedure — implementation not visible; exists to verify `sa` password state.

## Process Flows
1. **Ongoing index maintenance**: `Gather_Index_Stats` populates `indexstats` → `Collect_Index_Information` enriches with column metadata → `Defragment_DB` acts on fragmentation data.
2. **Job monitoring loop**: `sp_job_monitor` queries `msdb` running jobs → compares duration vs. threshold → sends Database Mail alert → writes to `job_monitor_log`.
3. **Drive space monitoring**: `utl_dba_drive_space_alert` → `xp_fixeddrives` → compares `DriveSize` vs. `DriveSpaceFree` → `sp_send_cdosysmail` for alerts.
4. **DBA diagnostics**: `QS_*` procedures query DMVs and return result sets consumed by monitoring tools (SiteScope, FortiDB, or direct DBA use).

## Compliance Concerns
- `QS_DA_Check_SA_Password` (encrypted): directly relates to PCI DSS Req 8.3.6 (strong passwords for accounts).
- `QS_DA_Find_Orphaned_Users`: supports PCI DSS Req 8.3.4 (remove inactive accounts) by identifying orphaned DB users.
- `ifs_infosec` and `ifs_gidadb` users have `db_securityadmin` and `db_accessadmin` roles — third-party InfoSec tool access for PCI compliance scans.
- `vascan` user: vulnerability scanning account with limited access.
- FortiDB report role: PCI-mandated database activity monitoring integration.
- `NAM\ISA_SQL_SECADMIN`: ISA (Information Security Administrator) account with security admin rights.

## Risks
- Many service accounts (APISVC, ORDERSVC, CSASVC, etc.) are assigned `db_owner` on DBAdmin — overprovisioned for what is a monitoring database.
- `dba-notify@ecount.com` email domain in `utl_dba_drive_space_alert` is the legacy Wirecard/ecount domain — may no longer route to active mailboxes post-acquisition.
- Ad hoc trace capture tables (`trace_4_16_2018`, `trace_4_18_9pm`, `so_fee_add_funds_*`) are dated 2010–2018 — historical snapshots never cleaned up from the project.
