# Data Architect View — job-order-synchronization_LIB

## Data Stores Accessed

The library connects to **two distinct databases** via Spring-injected JDBC `DataSource` beans defined in `dataSource.xml` and referenced in `applicationContext.xml`:

| Bean ID | Role | Tables Accessed |
|---|---|---|
| `jobDataSource` | jobsvc SQL Server DB (read) | `job_file`, `job_order_sync_event`, `job_order` |
| `orderDataSource` | Order Service DB or HTTP client | `file_order` (via `FileOrderManager` HTTP Invoker) |

## Key Database Tables

### `job_file` (jobsvc DB, read-only from this component)
Primary source table. Queried via `JdbcJobDao.getFileJob(jobId)` and `JdbcJobDao.getFileJobs(fromDate, toDate)`. Contains per-job state machine data.

Critical columns inferred from domain class `FileJob.java` (`domain/FileJob.java`):
- `job_id` (int, PK)
- `file_id` (varchar — the client-facing file identifier)
- `file_name` (varchar)
- `received_dt` (datetime — used as the sync window key)
- `job_status_id` (int, FK to status table — maps to `JobStatus` enum)
- `program_id` (varchar)
- `caller_id` (varchar — the member/user who submitted the job)

### `job_order_sync_event` (jobsvc DB, read/write)
Audit and control table for this synchronizer. Each run of the synchronizer creates or updates a row here. SQL schema is defined in `src/main/sql/job_order_sync_event.sql`.

Grants are defined in `src/main/sql/grants.sql`:
```sql
GRANT SELECT ON job_order_sync_event TO Jobsvc_Select
GRANT DELETE ON job_order_sync_event TO Jobsvc_DELETE
GRANT INSERT,UPDATE ON job_order_sync_event TO Jobsvc_Update
```

Columns inferred from `JobOrderSyncEvent.java` domain object:
- `sync_event_id` (PK)
- `from_date` (datetime — run window start)
- `to_date` (datetime — run window end)
- `total_count` (int — jobs examined)
- `create_count` (int — orders created)
- `update_count` (int — orders updated)
- `fail_count` (int — failures)
- `attempt_count` (int — retry counter)
- `status` (varchar — COMPLETE / FAILED)
- `created_dt` (datetime)

### `job_order` / `job_order_actuals` (jobsvc DB)
Referenced via SQL files `job_order_by_jobid_brokendown.sql` and `job_order_actuals_by_jobid_brokendown.sql`. Used to check for original job IDs in the case of split/re-batched jobs. Domain objects: `JobOrderWithOrigJobId.java`, `JobOrderActualWithOrigJobId.java`.

### `file_order` (Order Service — via HTTP)
The destination/target system. Accessed through `JdbcOrderDao` backed by `FileOrderManager` HTTP Invoker client (configured in `applicationContext.xml` lines 60–71 with configurable timeouts). Contains:
- `job_id` (int, nullable — linked after initial processing)
- `file_id` (varchar)
- `order_status` (varchar, maps to `OrderStatus` enum)
- `program_id` (varchar)

## Sensitive Data Handling

This library does **not directly process** Primary Account Numbers (PANs), CVVs, or ACH routing/account numbers. Its data surface is limited to:
- Job identifiers (`job_id`, `file_id`)
- Program identifiers (`program_id`)
- Order status strings
- Timestamps

However, the `file_id` values it references **correspond to batch disbursement files that contain cardholder PAN data** processed upstream. The indirect reference creates a chain-of-custody obligation: audit trails of which files were synchronized, when, and with what outcome are subject to PCI DSS Requirement 10 (audit log retention) and SOC 1 control objectives around completeness and accuracy of disbursement processing.

The `caller_id` field in `job_file` may contain a member UUID that links to cardholder identity records in `cbaseapp`. This is not processed by the synchronizer but is carried in the `FileJob` value object.

## Data Retention

The `job_order_sync_event` table accumulates one row per synchronizer run. There is no explicit TTL or archival logic in this codebase. Retention of these records falls under the general `jobsvc` database retention policy, which should be at minimum 12 months for PCI DSS audit trail purposes (Requirement 10.7).

## Data Flow Diagram (Logical)

```
[jobsvc DB]                          [Order Service]
job_file  ──────── JdbcJobDao ──────► JobOrderSynchronizer ──► FileOrderManager (HTTP)
job_order_sync_event ◄──────────────────────────────────────       │
                                                                    ▼
                                                             file_order (update/create)
```

## Database Role Separation

The grants SQL confirms a least-privilege model is intended:
- `Jobsvc_Select` — read-only SELECT
- `Jobsvc_Update` — INSERT + UPDATE (no DELETE on job_file)
- `Jobsvc_DELETE` — DELETE only on `job_order_sync_event`

The synchronizer does not hold DDL privileges. However, the `forceStatus` mode writes directly to the Order DAO via `updateFileOrderStatus()`, bypassing the Order Service API — this is a non-standard write path that should be documented as a compensating control.

## Job Ordering and Split-Job Complexity

The `JobOrderByJobidBrokendown` and `JobOrderActualByJobidBrokendown` SQL queries (referenced in `JdbcJobDao`) handle the case where a job is split or re-batched with a different `orig_job_id`. The synchronizer at `JobOrderSynchronizer.java` lines 346–362 iterates over these breakdown records and updates parent order statuses. This multi-join data access is a complex area prone to race conditions when two synchronizer instances run concurrently.
