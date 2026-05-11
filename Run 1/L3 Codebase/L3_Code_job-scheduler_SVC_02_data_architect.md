# Data Architect View — job-scheduler_SVC

## Data Stores

Two databases are accessed, configured via `JobScheduler-datasource.xml`:

| Bean | Purpose | Database |
|---|---|---|
| `jobSchedulerJobSvcDS` | Primary scheduling data | `jobsvc` (SQL Server, Director-configured) |
| `jobSchedulerCbaseappDS` | User/member lookup | `cbaseapp` (SQL Server, Director-configured) |

Both data sources are obtained at runtime from the **Director service** — a central configuration server that provides JDBC connection strings and credentials. This means no connection strings are stored in the WAR artifact itself.

## Key Database Tables — jobsvc DB

### Schedule Management Tables

**`sch_job_exec_status`** — Core table tracking per-job scheduling state. Columns inferred from DAO layer (`StoredProcGetSchJobStatus`, `StoredProcInsertJobExecInfo`, `StoredProcUpdateJobInfo`):
- `job_id` (int, PK — FK to `job_file`)
- `schedule_status_id` (int — status like `STATUS_ID_READY_TO_RUN=1`, `STATUS_ID_AWAITING_SCHEDULED_EXECUTION=2`)
- `schedule_task_id` (varchar — external scheduler task identifier)
- `schedule_mode` (varchar — IMMEDIATE/SCHEDULE/NOSCHEDULE)
- `schedule_time` (datetime — when to execute)
- `vol_flex_flag` (varchar — YES/NO, determines blackout type applicability)
- `affiliate_id` (int)
- `user_id` (varchar)
- `sys_agent_name` (varchar)

**`sch_schedule_info`** — Program-level recurring schedule definitions. Columns from `StoredProcGetScheduleInfo`, `StoredProcInsertScheduleInfo`, `StoredProcUpdateScheduleInfo`:
- `schedule_id` (int, PK)
- `affiliate_id` (int — program identifier)
- `schedule_mode` (varchar)
- `schedule_time` (datetime)
- Additional frequency/day-of-week fields

**`sch_schedule_history`** — Immutable audit log of all schedule changes, written by `StoredProcInsertScheduleHistory`.

**`sch_job_actions_log`** — Per-action audit log written by `StoredProcInsertJobActionsLog`. Every `scheduleJob()`, `removeSchedule()`, `reapplySchedule()`, `unAuthorizeSchedule()` call writes a log entry here.

### Blackout Tables (from `JobScheduler-datasource.xml` lines 122–213)

**`blackout_info`** — Master blackout definition record. Written by `InsertBlackoutInfo`, `UpdateBlackoutInfo`.

**`blackout_schedule`** — Computed schedule record for each blackout, tracking next start/end times and current `in_effect` status (YES/NO/PROGRESS/TERMINATING). Written by `InsertBlackoutSchedule`, `UpdateBlackoutSchedule`.

**`blackout_job`** — Junction table tracking which specific jobs were paused by which blackout. Written by `InsertBlackoutJob`, deleted by `DeleteBlackoutJob`.

**`blackout_actions_log`** — Immutable blackout audit log written by `InsertBlackoutActionsLog`.

### cbaseapp Tables

**User/member lookup**: `StoredProcGetUserInfo` (`GET_USER_INFO` stored proc) queries `cbaseapp` to resolve a numeric `userId` to a `memberId` string. Used when a system-level blackout action needs to record the acting member identity. This is a cross-database join between scheduling and member identity.

## Sensitive Data Handled

The scheduler itself does **not directly process** PANs, CVVs, or account numbers. However:

1. **`job_id` references**: Every `job_id` tracked by the scheduler corresponds to a batch file that may contain cardholder data. The scheduler is therefore within the **indirect scope** of the CDE (Cardholder Data Environment) — specifically, it controls the timing of when CDE data is processed.

2. **`member_id` / `user_id`**: The `sch_job_exec_status` table stores user identifiers of who authorized, scheduled, and executed jobs. These are operational identity records, not cardholder data, but they are subject to access control requirements under PCI DSS Requirement 7/8.

3. **`affiliate_id`** and **`program_id`**: These business identifiers link scheduling records to client programs and are commercially sensitive.

## Stored Procedure Inventory

All database access is through stored procedures — no inline SQL except where Spring `JdbcTemplate` StoredProcedure wrappers are used:

| DAO Class | Stored Proc Property Key | Operation |
|---|---|---|
| `StoredProcGetScheduleInfo` | `GET_SCH_INFO` | Retrieve program schedule |
| `StoredProcGetSchJobStatus` | `GET_SCH_JOB_STATUS` | Get current job scheduling status |
| `StoredProcInsertJobExecInfo` | `INSERT_SCH_JOB_EXEC_INFO` | Insert job execution record |
| `StoredProcInsertJobActionsLog` | `INSERT_JOB_ACTION_LOG` | Write scheduling action audit entry |
| `StoredProcInsertScheduleHistory` | `INSERT_SCHEDULE_HISTORY` | Write schedule change history |
| `StoredProcInsertScheduleInfo` | `INSERT_SCHEDULE_INFO` | Create program schedule |
| `StoredProcUpdateScheduleInfo` | `UPDATE_SCHEDULE_INFO` | Update program schedule |
| `StoredProcUpdateJobInfo` | `UPDATE_JOB_INFO` | Update job status/schedule task ID |
| `StoredProcUpdatePriority` | `UPDATE_PRIORITY` | Change job priority on AJL |
| `StoredProcGetUserInfo` | `GET_USER_INFO` | Resolve user to member ID (cbaseapp) |
| `RetrieveBlackoutData` | `blackout_retrieve_blackout_info` | Get blackout records |
| `RetrieveBlackoutJob` | `blackout_retrieve_blackout_job` | Get paused jobs for a blackout |
| `RetrieveProcessingJobList` | `blackout_get_processing_job_list` | Jobs currently in processing status |
| `InsertBlackoutInfo` | `blackout_insert_blackout_info` | Create blackout record |
| `InsertBlackoutSchedule` | `blackout_insert_blackout_schedule` | Create blackout schedule record |
| `InsertBlackoutJob` | `blackout_insert_blackout_job` | Record paused job |
| `UpdateBlackoutInfo` | `blackout_update_blackout_info` | Update blackout definition |
| `UpdateBlackoutSchedule` | `blackout_update_blackout_schedule` | Update blackout schedule timing |
| `UpdateJobStatus` | `blackout_update_job_status` | Bulk-update job statuses after blackout end |
| `DeleteBlackoutJob` | `blackout_delete_blackout_job` | Remove paused-job records |
| `InsertBlackoutActionsLog` | `blackout_insert_blackout_actions_log` | Blackout audit log |

## Data Retention and Audit Trail

- `sch_schedule_history`: Append-only; no archival logic in this codebase. Should be retained for the life of the program plus the regulatory minimum (typically 7 years for payment records under NACHA/EFTA).
- `sch_job_actions_log`: Same retention requirement.
- `blackout_actions_log`: Same.
- `blackout_job`: Transient — records are inserted when a job is paused and deleted when the blackout ends. No long-term retention needed beyond what is captured in `blackout_actions_log`.

## JDBC Timeout Configuration

The `JobDataSources.xml` in `jobmanager-war` sets a 600-second (10-minute) SQL timeout via `SqlTimeoutManager`. The scheduler's own data source configuration does not explicitly set query timeouts — stored procedures executing long aggregation queries against large `sch_job_exec_status` tables could block indefinitely under load.
