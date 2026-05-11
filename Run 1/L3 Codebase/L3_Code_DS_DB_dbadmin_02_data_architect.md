# Data Architect View — DS_DB_dbadmin

## Data Stores
Single SQL Server database: **DBAdmin**. The project also cross-references `master`, `msdb`, and named application databases (ecountcore, ordersvc, etc.) through dynamic SQL in stored procedures.

## Schema / Tables (selected key tables from sqlproj)

### Index and Performance
| Table | Purpose |
|---|---|
| `indexstats` | Fragmentation snapshots per index per database |
| `indexstats_latest` | Current fragmentation view |
| `indexstats_backup20100926` | Historical snapshot (should be archived/removed) |
| `IndexMaintenanceControl` | Per-index maintenance override flags |
| `Index_Columns_Usage` | Column-level index usage data |
| `Missing_Index_Usage_Stats` | Missing index DMV output |
| `CompileIndexesShowContig` | Legacy DBCC SHOWCONTIG output |
| `dba_db_stats_history` | Database size statistics over time |

### Job and Process Monitoring
| Table | Purpose |
|---|---|
| `job_monitor` | Current running jobs with start time and threshold |
| `job_monitor_log` | Historical alert records |
| `job_monitor_settings` | Threshold configuration per job |
| `business_job_history` | Business process job audit trail |
| `Exec_Requests_History` | Historical snapshot of `sys.dm_exec_requests` |

### Storage and Capacity
| Table | Purpose |
|---|---|
| `DriveSize` | Physical drive capacity (manually or periodically updated) |
| `DriveSpaceFree` | Latest free space per drive (populated by `xp_fixeddrives`) |
| `DBGrowthRate` | Database growth rate history |
| `dba_log_stats` | Transaction log space usage over time |
| `EcountCore_TableGrowth` | Per-table growth in ecountcore |
| `TableGrowth` | Generic table growth tracking |

### Blocking / Deadlock / Session Audit
| Table | Purpose |
|---|---|
| `audit_collection_deadlocks` | Deadlock XML from extended events / system health |
| `Audit_sessions` | Session-level audit snapshots |
| `blocked` / `blocking_ripped` | Blocking session captures |
| `blocking_correlation1` | Blocking chain correlation analysis |
| `qs_BlockingList_results` | BlockingList procedure output staging |

### QS Diagnostic Staging (60+ tables)
Prefix `qs_*` / `QS_*`: staging tables for DMV, trace, replication, and configuration diagnostic results. Examples: `qs_dbcc_fraginfo`, `qs_dbcc_loginfo`, `qs_dbcc_memorystatus`, `QS_SysPerfInfo`, `qs_replication_agents`, `QS_TraceData`, etc.

### Application-Specific Archives
- `so_fee_add_funds_5_29_2018`, `so_fee_add_funds_5_30_2018`, `so_fee_add_funds_5_31_2018`: Snapshots of fee add-funds data from May 2018 — production data captured for investigation, never removed.
- `fdr_process_card_auto_emboss_results`, `fdr_process_card_emboss_balance_results`: FDR card processing result captures.
- `profiler_fcaj_update_4_26_2018`, `trace_4_16_2018`, `trace_4_18_9pm`: SQL Profiler trace result tables.
- `vsqlprod1b*` tables: Point-in-time server performance captures from 2010.
- `TMW_location`: Location reference data (TMW = Transportation Management System).

## Sensitive Data Handling
- **`so_fee_add_funds_*` tables**: These are snapshots of live financial transaction data (fee amounts, add-funds operations) from a production database. Their presence in a DBA monitoring database is a data-handling concern. They should be reviewed for PII or financial data content and removed if no longer needed.
- **`fdr_process_card_*` tables**: May contain card processing reference data. Contents should be verified against PCI DSS scope.
- The `app_func_in_same_fdr_cycle` function encodes FDR processing cycle logic — FDR is a major card processor; this function likely supports cardholder data environment operations.
- No SSN, PAN, CVV, or direct cardholder data fields are visible in table definitions present in this repo.

## Encryption and Protection
- No TDE configuration in the SSDT project.
- `QS_DA_Check_SA_Password` procedure uses `WITH ENCRYPTION` — body is not visible in source control. This is a dual-edged control: protects the check logic from casual inspection but also makes the procedure opaque to code review.
- `QS_CheckCmdShell` uses `WITH ENCRYPTION` — similarly opaque.

## Data Flow
```
SQL Server DMVs (sys.dm_*, sys.dm_os_*, sys.databases, etc.)
  <- QS_* stored procedures
       -> QS_* staging tables in DBAdmin

msdb.dbo.sysjobactivity / sysjobs
  <- sp_job_monitor / usp_GetJobStatus
       -> job_monitor / job_monitor_log

master.dbo.xp_fixeddrives (via utl_dba_drive_space_alert)
  -> DriveSpaceFree in DBAdmin

Application databases (ecountcore, ordersvc, etc.)
  <- Collect_Index_Information (cross-database dynamic SQL)
       -> indexstats in DBAdmin
```

## Data Quality / Retention
- Multiple point-in-time investigation tables from 2010–2018 remain in the project — no lifecycle or retention policy is enforced.
- `job_monitor_log` grows without bound; no purge procedure is present.
- `CommandLog` (in `master`) and corresponding DBAdmin tables have no TTL defined.
- `dba_log_stats` and `dba_db_stats_history` accumulate indefinitely.

## Compliance Gaps
1. **Stale investigation data in source**: `so_fee_add_funds_*`, `fdr_process_card_*` tables likely originated from production incident investigations. Retaining table definitions (and potentially row data if populated) in a DBA database without a data retention policy violates PCI DSS Req 3.2 (data retention policy) and GLBA data minimisation.
2. **No data retention/purge policy**: No scheduled cleanup procedures for any historical DBAdmin tables.
3. **No TDE on DBAdmin**: If the database is in-scope for PCI DSS (it monitors CDE databases), absence of TDE could be noted in a QSA assessment.
4. **Encrypted procedures obscure compliance verification**: `WITH ENCRYPTION` on `QS_DA_Check_SA_Password` prevents code review by auditors — PCI DSS Req 6.2 (secure development) requires code review visibility.
