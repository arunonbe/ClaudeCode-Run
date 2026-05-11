# DS_DB_ecountbatchjobrepository — Data Architect View

## Database Overview

- **Database Name**: `EcountBatchJobRepository`
- **SQL Server Version**: SQL Server 2012 (`Sql110DatabaseSchemaProvider`)
- **Project Type**: SQL Server Database Project (SSDT)
- **Schema**: `dbo` only
- **Object Count**: 9 tables, 4 custom database roles, 30+ user/login grants

---

## Complete Table Inventory

All tables reside in the `dbo` schema. This is the standard Spring Batch 2.x/3.x `JobRepository` schema.

### BATCH_JOB_INSTANCE
**File**: `dbo/Tables/BATCH_JOB_INSTANCE.sql`

| Column | Type | Nullable | Description |
|---|---|---|---|
| `JOB_INSTANCE_ID` | BIGINT | NOT NULL (PK) | Surrogate key for job instance |
| `VERSION` | BIGINT | NULL | Optimistic locking version |
| `JOB_NAME` | VARCHAR(100) | NOT NULL | Name of the batch job |
| `JOB_KEY` | VARCHAR(32) | NOT NULL | MD5 hash of job parameters — prevents duplicate runs |

Unique constraint on `(JOB_NAME, JOB_KEY)`.

---

### BATCH_JOB_EXECUTION
**File**: `dbo/Tables/BATCH_JOB_EXECUTION.sql`

| Column | Type | Nullable | Description |
|---|---|---|---|
| `JOB_EXECUTION_ID` | BIGINT | NOT NULL (PK) | Surrogate key |
| `VERSION` | BIGINT | NULL | Optimistic locking |
| `JOB_INSTANCE_ID` | BIGINT | NOT NULL (FK) | Links to BATCH_JOB_INSTANCE |
| `CREATE_TIME` | DATETIME | NOT NULL | When execution record was created |
| `START_TIME` | DATETIME | NULL | When job started |
| `END_TIME` | DATETIME | NULL | When job ended (null if still running) |
| `STATUS` | VARCHAR(10) | NULL | COMPLETED, FAILED, STARTED, STOPPING, STOPPED, ABANDONED |
| `EXIT_CODE` | VARCHAR(100) | NULL | Application-defined exit code |
| `EXIT_MESSAGE` | VARCHAR(2500) | NULL | Detailed exit message / error |
| `LAST_UPDATED` | DATETIME | NULL | Last heartbeat update |

---

### BATCH_JOB_EXECUTION_CONTEXT
**File**: `dbo/Tables/BATCH_JOB_EXECUTION_CONTEXT.sql`

Stores serialised execution context (Spring Batch `ExecutionContext`) for the job. Used for restartability — Spring Batch can re-hydrate job state from this context on restart.

Note: This table may contain **serialised Java objects** that include job parameters. If any job passes file paths, date ranges, or program codes as parameters, those will appear here as serialised strings.

---

### BATCH_JOB_SEQ
**File**: `dbo/Tables/BATCH_JOB_SEQ.sql`

Single-row sequence table used by Spring Batch to generate `JOB_INSTANCE_ID` values. Equivalent to an Oracle sequence or SQL Server IDENTITY for cross-DB compatibility.

---

### BATCH_JOB_PARAMS
**File**: `dbo/Tables/BATCH_JOB_PARAMS.sql`

| Column | Type | Description |
|---|---|---|
| `JOB_INSTANCE_ID` | BIGINT (FK) | Links to BATCH_JOB_INSTANCE |
| `TYPE_CD` | VARCHAR(6) | Parameter type: STRING, DATE, LONG, DOUBLE |
| `KEY_NAME` | VARCHAR(100) | Parameter name |
| `STRING_VAL` | VARCHAR(250) | String parameter value |
| `DATE_VAL` | DATETIME | Date parameter value |
| `LONG_VAL` | BIGINT | Long parameter value |
| `DOUBLE_VAL` | FLOAT | Decimal parameter value |

**Note**: Job parameters passed to batch jobs are stored here. Depending on job design, sensitive values such as file paths, account ranges, or processing dates may be stored. If any batch job receives a program code or file name that could indirectly identify cardholder data, this table may be considered in-scope for data classification review.

---

### BATCH_STEP_EXECUTION
**File**: `dbo/Tables/BATCH_STEP_EXECUTION.sql`

| Column | Type | Description |
|---|---|---|
| `STEP_EXECUTION_ID` | BIGINT (PK) | Surrogate key |
| `VERSION` | BIGINT | Optimistic locking |
| `STEP_NAME` | VARCHAR(100) | Step name within job |
| `JOB_EXECUTION_ID` | BIGINT (FK) | Links to BATCH_JOB_EXECUTION |
| `START_TIME` | DATETIME | Step start |
| `END_TIME` | DATETIME | Step end |
| `STATUS` | VARCHAR(10) | COMPLETED, FAILED, etc. |
| `COMMIT_COUNT` | BIGINT | Number of commits |
| `READ_COUNT` | BIGINT | Records read |
| `FILTER_COUNT` | BIGINT | Records filtered |
| `WRITE_COUNT` | BIGINT | Records written |
| `READ_SKIP_COUNT` | BIGINT | Records skipped on read error |
| `WRITE_SKIP_COUNT` | BIGINT | Records skipped on write error |
| `PROCESS_SKIP_COUNT` | BIGINT | Records skipped in processing |
| `ROLLBACK_COUNT` | BIGINT | Number of rollbacks |
| `EXIT_CODE` | VARCHAR(100) | Step exit code |
| `EXIT_MESSAGE` | VARCHAR(2500) | Step exit message |
| `LAST_UPDATED` | DATETIME | Heartbeat |

Index: `IX_BATCH_STEP_EXECUTION_JOB_EXECUTION_ID` on `JOB_EXECUTION_ID`.

---

### BATCH_STEP_EXECUTION_CONTEXT
**File**: `dbo/Tables/BATCH_STEP_EXECUTION_CONTEXT.sql`

Serialised step-level execution context. Used for step-level restart — Spring Batch can resume a failed step from its last committed chunk.

---

### BATCH_STEP_EXECUTION_SEQ
**File**: `dbo/Tables/BATCH_STEP_EXECUTION_SEQ.sql`

Sequence table for `STEP_EXECUTION_ID` generation.

---

## Custom Database Roles

Defined in Security scripts:

| Role Name | File | Purpose |
|---|---|---|
| `EcountBatchJobRepository_delete` | `Security/EcountBatchJobRepository_delete.sql` | Grants DELETE on all tables |
| `EcountBatchJobRepository_execute` | `Security/EcountBatchJobRepository_execute.sql` | Grants EXECUTE on stored procedures (if any) |
| `EcountBatchJobRepository_insert` | `Security/EcountBatchJobRepository_insert.sql` | Grants INSERT on all tables |
| `EcountBatchJobRepository_select` | `Security/EcountBatchJobRepository_select.sql` | Grants SELECT on all tables |
| `EcountBatchJobRepository_update` | `Security/EcountBatchJobRepository_update.sql` | Grants UPDATE on all tables |
| `FortiDBRptRole` | `Security/FortiDBRptRole.sql` | FortiDB database activity monitoring read role |
| `gers_role` | `Security/gers_role.sql` | GERS reporting role |
| `gers_read` | `Security/gers_read.sql` | GERS read-only role |

---

## Sensitive Data Fields

This database contains **no cardholder data, no PAN, no SSN, no CVV, no DOB**. All fields are operational metadata.

However, `BATCH_JOB_PARAMS.STRING_VAL` and the CONTEXT tables (serialised Java objects as CLOB/text) could theoretically contain data passed as job parameters. A query of the live production database against `BATCH_JOB_PARAMS` for `KEY_NAME` values would confirm whether any sensitive parameters are inadvertently stored.

---

## Encryption at Rest

No column-level encryption is applied or required — no sensitive data fields exist. TDE (Transparent Data Encryption) status of the database server is unknown from this repository alone and should be confirmed via the server configuration.

---

## PCI DSS CDE Scope

This database is **supporting scope** for PCI DSS — it does not store cardholder data but supports systems that do. Under PCI DSS v4.0.1 scoping methodology, this database's server should be considered in-scope for network segmentation controls if it resides on the same network segment as CDE databases.

---

## Data Retention

Spring Batch does not natively purge `JobRepository` tables. Without a scheduled purge job, the `BATCH_JOB_EXECUTION` and `BATCH_STEP_EXECUTION` tables grow indefinitely. No purge stored procedure or scheduled cleanup is defined in this repository. For a production system running daily batch jobs across dozens of job types, these tables could accumulate millions of rows over years of operation. Recommend: implement a quarterly purge of executions older than 18 months while retaining summary/audit records.
