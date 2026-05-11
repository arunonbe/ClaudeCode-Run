# DS_DB_jobsvc — DevOps & Operations Report

## 1. Project Build Configuration

| Attribute | Value | Source |
|-----------|-------|--------|
| Project type | SQL Server Database Project (SSDT) | `jobsvc.sqlproj` |
| MSBuild schema provider | `Microsoft.Data.Tools.Schema.Sql.Sql110DatabaseSchemaProvider` | `jobsvc.sqlproj` line 7 |
| Target SQL Server version | SQL Server 2012 (compat 110) | `jobsvc.sqlproj` |
| Target framework | .NET 4.6.1 | `jobsvc.sqlproj` line 20 |
| Output type | Database (DACPAC) | `jobsvc.sqlproj` |
| Solution file | `jobsvc.sln` | Repo root |

This is a more modern SSDT target than the GP databases (SQL 2012 vs SQL 2008), but still not current.

## 2. Build and Deployment Process

The project builds to a DACPAC via MSBuild. No committed CI/CD pipeline files (`.gitlab-ci.yml`, Jenkinsfile) were found. Deployment pattern is presumed to match Onbe's Jenkins-based platform standard.

The presence of a `Storage/` folder (not seen in GP databases) suggests custom filegroup definitions are used — the `Ordersvc_FG_1`-style filegroup reference seen in `request_detail.sql` (ordersvc) has a parallel in jobsvc's storage configuration. This means deployment must account for the existence of named filegroups on the target server.

## 3. Change Management

Unlike GP databases, jobsvc does **not** have a `DeltaSql/` folder. All schema changes are managed via DACPAC diff. However, jobsvc also uses in-file `IF NOT EXISTS` alter patterns:

```sql
-- dbo/Tables/job_action_register_user.sql, last lines
IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.COLUMNS 
               WHERE TABLE_SCHEMA = 'dbo' 
               AND TABLE_NAME='job_action_register_user' 
               AND COLUMN_NAME='recipient_screening_status')
 ALTER TABLE [dbo].job_action_register_user 
 ADD recipient_screening_status varchar(40) null
```

This pattern — embedding idempotent ALTER statements in the table definition file — is a hybrid approach that allows columns to be added without DACPAC-generated DROP+RECREATE cycles. It is pragmatic but creates drift between the authoritative DDL in the file and what DACPAC would generate, making DACPAC diff less reliable as a change verification tool.

## 4. Quartz Scheduler Operations

The `QRTZ_*` tables are managed by the Quartz scheduler runtime, not by manual DBA operations. Key operational considerations:

| Table | Operational Risk |
|-------|-----------------|
| `QRTZ_FIRED_TRIGGERS` | Orphaned rows if scheduler crashes — must be cleaned by recovery procedure |
| `QRTZ_LOCKS` | Lock table rows can block scheduler if not released after crash |
| `QRTZ_SCHEDULER_STATE` | Must be monitored for cluster node health |
| `QRTZ_JOB_DETAILS.JOB_DATA` | IMAGE column; if corrupted, job cannot fire |

Quartz version implied: Quartz 1.x (the schema structure with `IS_VOLATILE`, `IS_STATEFUL` columns indicates Quartz 1.x, which is end-of-life). Modern Quartz 2.x uses `IS_NONCONCURRENT` and `IS_UPDATE_DATA` instead.

## 5. Archive and Purge Patterns

The database includes archival and purge infrastructure:

| Object | Purpose |
|--------|---------|
| `job_action_history_Archive` | Archived completed action records |
| `CDC_*_bk` tables | Change Data Capture backup tables (CDC history snapshots) |
| `CodeArchive` | Archived code records |
| `usp_Table_Purge_action_notification_result` (in ordersvc) | Pattern for purge SPs |

Several `zzz_` prefixed tables (`zzz_work_instance_log_old`, `zzz_work_item`, etc.) represent deprecated tables kept for reference but not actively written to. These should be formally retired.

## 6. Security Model

The Security folder contains service accounts and role assignments appropriate for a production job processing database:

Observed patterns from sibling repos (ordersvc, notificationsvc share the same `NAM_PPA_PRD_*` service account pattern):
- `NAM_PPA_PRD_BMCSVC` — BMC monitoring service
- `NAM_ppa_prd_mon` — Production monitoring
- `NAM_GTS_gpatmon` — GTS database monitoring
- `NAM_ICG_DBA_Default` — DBA default account
- `FortiDBRptRole` — Database Activity Monitoring (FortiDB)
- `ifs_infosec` — Information Security access

FortiDB presence confirms that DAM is active on jobsvc — an important PCI DSS control given the potential PAN presence in `instant_issue_card`.

## 7. Operational Risks

| Risk | Severity | Description |
|------|----------|-------------|
| `card_number` plaintext in `instant_issue_card` | **CRITICAL** | Potential PAN in plaintext — PCI DSS violation |
| `parent_dda` in `instant_issue_card` | **CRITICAL** | Potential DDA/account number |
| `exp_month/exp_year` in `job_action_issue_card` | **HIGH** | SAD retained post-authorization |
| SQL 2012 compatibility level | **HIGH** | Outdated; SQL 2012 is end of extended support (2022) |
| No CI/CD pipeline committed | **HIGH** | Manual deployment risk |
| Quartz 1.x QRTZ schema | **HIGH** | End-of-life; Quartz 2.x migration needed |
| `IF NOT EXISTS` ALTER drift | **MEDIUM** | DACPAC diff not authoritative |
| `zzz_` deprecated tables still present | **MEDIUM** | Schema clutter; risk of accidental queries |
| `IMAGE` datatype on `QRTZ_JOB_DETAILS.JOB_DATA` | **MEDIUM** | Deprecated type; cannot be indexed or searched |
| `job_action_memo_secure.field_secure_ref` | **MEDIUM** | Vault token references — confirm vault availability and rotation |
| CDC backup tables (`CDC_*_bk`) | **LOW** | Historical snapshots may contain PII |

## 8. Data Volume and Performance Considerations

Job service tables are high-write-throughput:
- `job_action_history` and `job_action_history_Archive` accumulate historical records — require periodic archival.
- `QRTZ_FIRED_TRIGGERS` can grow rapidly under high-frequency job execution — requires regular cleanup.
- `work_instance_log` is the primary execution audit log — must be monitored for growth.
- Multiple tables use `FILLFACTOR = 90` — appropriate for write-heavy workloads.
- Filtered indexes with specific WHERE clauses (`job_status < 250`) show thoughtful query optimisation.

## 9. Monitoring

FortiDB is confirmed (role present in Security folder). Additional monitoring:
- `NAM_ppa_prd_mon` and `NAM_GTS_gpatmon` service accounts for health monitoring.
- HP SiteScope likely monitoring connection pool and database availability.
- Job execution monitoring should alert on:
  - Stuck `QRTZ_FIRED_TRIGGERS` rows
  - `work_instance` records in error state > SLA threshold
  - `job_file` records in non-terminal status beyond expected processing time
  - `ach_transfer_detail` rows with `result_code` indicating ACH rejects (NACHA return codes)

## 10. Recovery Considerations

Given the PCI-scope risk of `instant_issue_card.card_number`, backup files for this database must be:
1. Encrypted at rest (align with PCI DSS Req 3 for backup media)
2. Stored with restricted access (PCI DSS Req 9.4.7)
3. Tested for restore capability quarterly (PCI DSS Req 12.5.2)
