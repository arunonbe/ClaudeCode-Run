# autofile_SVC — Data Architect View

## Data Stores

The service connects to two Microsoft SQL Server databases, both resolved via JNDI:

| JNDI Name | Env Variable (JDBC URL) | Purpose |
|---|---|---|
| `java:comp/env/jdbc/JobSvcDataSource` | `${JOBSVC_JDBC_URL}` | Primary operational DB — job tracking, file state, ingest metadata |
| `java:comp/env/jdbc/CbaseappDataSource` | `${CBASEAPP_JDBC_URL}` | User/member lookup DB |

Both are configured in `autofile-service/config/server.xml` as HikariCP connection pools (factory: `com.zaxxer.hikari.HikariJNDIFactory`) with:
- `maxIdle=10`, `maxTotal=30`, `maxWaitMillis=30000`
- JDBC driver: `com.microsoft.sqlserver.jdbc.SQLServerDriver` (version 12.5.0.jre11-preview)
- Credentials injected via environment variables: `AUTOFILESVC_JOBSVCDB_PASSWORD`, `AUTOFILESVC_CBASEAPPDB_USERNAME`, `AUTOFILESVC_CBASEAPPDB_PASSWORD`

## Schema & Tables

### JobSvcDataSource tables (inferred from stored procedures and inline SQL)

| Table | Access Pattern | Key Columns Known |
|---|---|---|
| `autofile_job` | R/W via stored procs + inline SQL | `job_id`, `status_id`, `program_id`, `phase_id`, `instance_id`, `step_name`, `retry_attempts`, `retry_schedule_name`, `pause_status`, `retry_step_id`, `repo_file_id` |
| `autofile_status` | Read (JOIN) | `status_id`, `status_description` |
| `job_file_ingest` | Read (JOIN for ordering) | `job_id`, `upload_time_utc` |
| `dbo.job_file` | Read (inline SQL) | `job_id`, `caller_member_id` |
| `dbo.autofile_funds_retry_queue` | R/W (inline SQL) | `id` (IDENTITY), `program_id`, `context` (VARCHAR 4000), `status`, `created_utc` (DATETIME2) |

Full DDL for `autofile_funds_retry_queue` is embedded in the Javadoc of `FundsRetryQueueEntry.java`:
```sql
CREATE TABLE dbo.autofile_funds_retry_queue (
    id          INT IDENTITY(1,1) PRIMARY KEY,
    program_id  INT NOT NULL,
    context     VARCHAR(4000) NULL,
    status      VARCHAR(100) NOT NULL,
    created_utc DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()
);
```

### CbaseappDataSource tables (inferred from stored procedures)

| Table | Access Pattern | Key Columns Known |
|---|---|---|
| User/member table | Read via `dbo.get_user_by_member_id`, `dbo.get_user_ecount_info` | `ecount_member_id`, `ecount_id`, `ecount_status`, `dda` (DDA bank account field) |

### Stored Procedures (all in `dbo` schema)

| Stored Procedure | Operation | DataSource |
|---|---|---|
| `dbo.autofile_get_file_list_details` | SELECT (batch) | JobSvc |
| `dbo.autofile_get_job_list_details` | SELECT (batch) | JobSvc |
| `dbo.autofile_get_job_details` | SELECT by job_id | JobSvc |
| `dbo.autofile_update_job_info` | UPDATE job status | JobSvc |
| `dbo.autofile_get_file_info` | SELECT by repo_file_id | JobSvc |
| `dbo.autofile_insert_file_info` | INSERT job record | JobSvc |
| `dbo.autofile_update_file_info` | UPDATE file fields | JobSvc |
| `dbo.autofile_update_file_pause_info` | UPDATE pause_status | JobSvc |
| `dbo.autofile_get_jobsvc_job_info` | SELECT from job service tables | JobSvc |
| `dbo.get_user_by_member_id` | SELECT user by member | CbaseApp |
| `dbo.get_user_ecount_info` | SELECT user by user_id (returns `ecount_member_id`, `ecount_id`, `ecount_status`, `dda`) | CbaseApp |

## Sensitive Data Handling

| Data Element | Location | Sensitivity |
|---|---|---|
| `dda` field | Returned by `StoredProcGetUserInfo` (`ecount_status`, `dda` output params) | Potentially a DDA (Demand Deposit Account / bank account number) — **high sensitivity** |
| `caller_member_id` | Read from `dbo.job_file`, passed as `callerId` in workflow context | Member ID — moderate sensitivity |
| `ecount_member_id` | Retrieved from CbaseApp and used as `callerId` | Member identifier |
| `userId`, `applicationId` | Integer IDs used for Banker authorization | Low sensitivity, but conveys authorization privilege level |
| Job amounts | Passed via `ClientSourceDTO` (loan/promotion amounts from Job Service batch info) | Financial data — sensitive |

**Concern**: The `dda` field is declared as a `SqlOutParameter` in `StoredProcGetUserInfo` but the current implementation in `AutofileDAOImpl.getUserInfo` only reads `ecount_member_id` and discards the DDA value. However, the field is still fetched from the database, meaning DDA data transits the application memory. If logging were ever added at that point, DDA exposure would result.

**Concern**: No field-level encryption or masking is applied to any data retrieved from either database within this service. The service relies entirely on database-level access controls.

## Encryption & Protection

1. **TLS for downstream services** — `Dockerfile` imports a QA certificate (`certfile_qa.crt`) into the JVM truststore, indicating downstream HTTPS calls. The `Dockerfile` line: `keytool -import -trustcacerts -file /tmp/certfile_qa.crt`.
2. **JDBC credentials via environment variables** — database passwords are injected as `${AUTOFILESVC_CBASEAPPDB_PASSWORD}` and `${AUTOFILESVC_JOBSVCDB_PASSWORD}` from the container environment (not hardcoded). Managed via AKS secrets/env at deployment.
3. **No application-layer encryption** — no Java crypto, no column-level encryption is implemented in any DAO or domain class.
4. **No TLS on HTTP connector** — Tomcat `server.xml` defines only a plain HTTP/1.1 connector on port 80. The SSL connector block is commented out. TLS termination is expected upstream (load balancer or ingress controller).
5. **JNDI connection strings** — connection URLs (`${CBASEAPP_JDBC_URL}`, `${JOBSVC_JDBC_URL}`) are environment-variable-injected. The `EnvironmentPropertySource` is enabled in Tomcat's `catalina.properties` via the Dockerfile.

## Data Flow

```
External Caller (Workflow Engine / AJL)
    ↓ HTTP GET /AutoFile.do (params: EXEC_AGENT, CALLER_ID, STEP_NAME, FILE_ID, JOB_ID)
AutoFileServiceAdapter (servlet)
    ↓ validate → WorkflowInputContext
AutofileServiceImpl.execute()
    ↓ WorkflowStepFactory → WorkflowStep bean
WorkflowStep (e.g., BankerAuthorizeJob, RunJobServiceJob)
    ↓                           ↓
AutofileDAOImpl            External RPC helpers
  ↓                          ↓               ↓              ↓
JobSvcDataSource       BankerServiceAPI  JobServiceHelper  WorkflowServiceHelper
(MSSQL)               (SOAP/Axis)       (SOAP/Axis)       (cbase WorkflowManager)
    ↑
CbaseappDataSource
(MSSQL, user lookups)

InsufficientFundsRetryScheduler (background thread)
    → reads autofile_funds_retry_queue (JobSvcDataSource)
    → calls WorkflowServiceHelper.startProcessingPreparationWorkflow
```

## Data Quality & Retention

1. **Batch size cap** — `AutoFileConstants.BATCH_SIZE = 30`. Bulk status queries send at most 30 file/job IDs per stored procedure call. This limits query parameter size but could cause silent truncation if callers pass more IDs than the array is sized for (observed in `AutofileServiceImpl.getFileDetailList` where the array is allocated with an extra buffer of `(fileIds.length/30)+1`).
2. **Status ID integer codes** — ~25 distinct status ID integers are hardcoded as constants in `AutoFileConstants`. These must stay in sync with the `autofile_status` database table; there is no runtime validation that DB codes match constants.
3. **Retry queue archival** — `autofile_funds_retry_queue` rows are transitioned to `STATUS_ARCHIVED` ("Archived"), not deleted. No purge/retention policy is implemented in the codebase. Over time this table will grow unbounded.
4. **No soft-delete or versioning** — `autofile_job` updates are in-place (no history table). The `previous_status_id` parameter to `dbo.autofile_update_job_info` suggests the stored procedure may record prior state, but this is internal to the DB layer.
5. **Nullable `context` column** — `autofile_funds_retry_queue.context` is `VARCHAR(4000) NULL`. The application stores a compact `jobId:N;instanceId:N` string; maximum length is far below 4000, so overflow risk is negligible.

## Compliance Gaps

1. **DDA field fetched but not used or masked** — `StoredProcGetUserInfo` declares `dda` as a SQL output parameter. If DDA represents a bank account number, fetching it even transiently without explicit masking is a concern under PCI DSS Requirement 3 (protect stored cardholder data) and GLBA (financial data handling). The current code discards the value but it exists in the result set.
2. **No audit log for financial state changes** — job status transitions (especially authorization approvals/rejections and insufficient-funds decisions) write to the database but no dedicated audit event stream or log record is written with user identity, timestamp, and old/new value. The `AUDIT |` log markers in `InsufficientFundsRetryScheduler` are log-file only and not durable.
3. **No data classification annotations** — DTOs (`JobInfo`, `FundsRetryQueueEntry`, `WorkflowInputContext`) carry no annotations indicating data sensitivity (e.g., PII, financial). This makes it difficult to enforce data-handling policies programmatically.
4. **Queue table lacks index evidence** — `autofile_funds_retry_queue` queries filter on `program_id` and `status`. Without confirmed indexes, table scans would degrade performance as the table grows. No DDL index statements are present in the codebase.
5. **Shared JDBC template for inline SQL and stored procs** — `AutofileDAOImpl` injects `autofileJobSvcJdbcTemplate` for both stored-procedure wrappers and direct inline SQL (fund-retry queue queries). This means the same connection pool credential is used for all queries, preventing row-level or operation-level privilege separation.
