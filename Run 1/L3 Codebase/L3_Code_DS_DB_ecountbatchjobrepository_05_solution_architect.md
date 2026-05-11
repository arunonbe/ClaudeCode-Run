# DS_DB_ecountbatchjobrepository — Solution Architect View

## Technical Debt Summary

`EcountBatchJobRepository` is architecturally clean with minimal technical debt in the schema itself. The main concerns are in access control, operational gaps (no purge, no monitoring), and the SQL Server 2012 version target. There are no security vulnerabilities in the schema DDL itself.

---

## All Objects — Names and Purpose

### Tables (9 total)

| Object Name | Schema | File | Purpose |
|---|---|---|---|
| `BATCH_JOB_INSTANCE` | dbo | `dbo/Tables/BATCH_JOB_INSTANCE.sql` | One row per unique job+parameter combination. Prevents duplicate job runs via JOB_KEY uniqueness constraint. |
| `BATCH_JOB_EXECUTION` | dbo | `dbo/Tables/BATCH_JOB_EXECUTION.sql` | One row per execution of a job instance. Tracks status, timestamps, exit code, exit message. |
| `BATCH_JOB_EXECUTION_CONTEXT` | dbo | `dbo/Tables/BATCH_JOB_EXECUTION_CONTEXT.sql` | Serialised execution context for job-level restart. Contains Java-serialised ExecutionContext as text/CLOB. |
| `BATCH_JOB_EXECUTION_SEQ` | dbo | `dbo/Tables/BATCH_JOB_EXECUTION_SEQ.sql` | Sequence table for JOB_EXECUTION_ID generation (Spring Batch cross-DB compatibility pattern). |
| `BATCH_JOB_INSTANCE` | dbo | `dbo/Tables/BATCH_JOB_INSTANCE.sql` | See above |
| `BATCH_JOB_PARAMS` | dbo | `dbo/Tables/BATCH_JOB_PARAMS.sql` | Job parameters per instance — used for identifying unique runs and for restart. |
| `BATCH_JOB_SEQ` | dbo | `dbo/Tables/BATCH_JOB_SEQ.sql` | Sequence table for JOB_INSTANCE_ID generation. |
| `BATCH_STEP_EXECUTION` | dbo | `dbo/Tables/BATCH_STEP_EXECUTION.sql` | Step-level execution metadata. Tracks read/write/skip/rollback counts per step. Indexed on JOB_EXECUTION_ID. |
| `BATCH_STEP_EXECUTION_CONTEXT` | dbo | `dbo/Tables/BATCH_STEP_EXECUTION_CONTEXT.sql` | Serialised step context for step-level restart. |
| `BATCH_STEP_EXECUTION_SEQ` | dbo | `dbo/Tables/BATCH_STEP_EXECUTION_SEQ.sql` | Sequence table for STEP_EXECUTION_ID generation. |

### Database Roles

| Role | File | Permissions |
|---|---|---|
| `EcountBatchJobRepository_delete` | `Security/EcountBatchJobRepository_delete.sql` | DELETE on all tables |
| `EcountBatchJobRepository_execute` | `Security/EcountBatchJobRepository_execute.sql` | EXECUTE (stored procedures) |
| `EcountBatchJobRepository_insert` | `Security/EcountBatchJobRepository_insert.sql` | INSERT on all tables |
| `EcountBatchJobRepository_select` | `Security/EcountBatchJobRepository_select.sql` | SELECT on all tables |
| `EcountBatchJobRepository_update` | `Security/EcountBatchJobRepository_update.sql` | UPDATE on all tables |
| `FortiDBRptRole` | `Security/FortiDBRptRole.sql` | FortiDB monitoring read access |
| `gers_role` | `Security/gers_role.sql` | GERS reporting role |
| `gers_read` | `Security/gers_read.sql` | GERS read-only role |

### Users (selected — from Security scripts)

30+ users are defined. Key ones:

| User | File | Notes |
|---|---|---|
| `b2c`, `b2c_1` | `Security/b2c.sql`, `b2c_1.sql` | B2C application users |
| `NAM\PPA_PRD_ECORESVC` | `Security/NAM_PPA_PRD_ECORESVC.sql` | Core EcountCore service — most privileged batch consumer |
| `NAM\PPA_PRD_ECAPSVC` | `Security/NAM_PPA_PRD_ECAPSVC.sql` | ECAP service |
| `NAM\PROD`, `NAM\PROD_1` | `Security/NAM_PROD.sql`, `NAM_PROD_1.sql` | Generic prod access |
| `NAM\PROD_CPP`, `NAM\PROD_CPP_APAC` | `Security/NAM_PROD_CPP*.sql` | Card processing platform |
| `emer_*` (14 accounts) | Various `Security/emer_*.sql` | Emergency/break-glass access |
| `ifs_gidadb`, `ifs_infosec` | `Security/ifs_gidadb*.sql`, `ifs_infosec*.sql` | InfoSec monitoring |
| `NAM\ISA_SQL_SECADMIN` | `Security/NAM_ISA_SQL_SECADMIN.sql` | SQL security admin |
| `scpardb` | `Security/scpardb*.sql` | Storage/compute platform |
| `FortiDBRptRole` | `Security/FortiDBRptRole.sql` | FortiDB DAM |

---

## Security Findings

### HIGH: Excessive db_accessadmin and db_securityadmin Grants

**File**: `Security/RoleMemberships.sql`, lines 1–37

The following accounts are granted `db_accessadmin` AND `db_securityadmin`:
- `NAM\PROD_CPP_APAC`
- `NAM\ISA_SQL_SECADMIN`
- `ifs_infosec`
- `ifs_gidadb`
- `scpardb`

`db_accessadmin` can add and remove database users. `db_securityadmin` can manage role memberships. Granting these to service/monitoring accounts on a database that is a gateway to batch processing metadata violates least-privilege principles.

**Remediation**: Remove `db_accessadmin` and `db_securityadmin` from all accounts except DBA administrative accounts. Security monitoring accounts (`ifs_infosec`, `FortiDBRptRole`) need only `db_datareader`.

---

### MEDIUM: 14 Emergency Access Accounts (`emer_*`) with Write Access

**Files**: `Security/emer_*.sql`

Fourteen `emer_*` accounts (e.g., `emer_mt24088`, `emer_sk14163`, `emer_rp32654`, `emer_rb27292`, `emer_sp10000`, `emer_sr14161`) are granted `db_datawriter` (lines 81–101 of `RoleMemberships.sql`). Emergency access accounts should be read-only by default and escalated to write only via a time-bounded access request process.

**Remediation**: Revoke `db_datawriter` from all `emer_*` accounts. Implement a PAM (Privileged Access Management) process for break-glass write access.

---

### LOW: SQL Server 2012 Version Target

The `.sqlproj` targets `Sql110DatabaseSchemaProvider` (SQL Server 2012). SQL Server 2012 reached end-of-life in July 2022. This does not directly create a vulnerability in the schema, but the SQL Server instance hosting this database should be upgraded to SQL Server 2019 or 2022 to receive security patches.

---

### LOW: No Purge Mechanism

No stored procedure, table, or script for purging historical execution data is defined in this repository. Long-running tables without purge may eventually cause index fragmentation and query performance degradation on the sequence tables, potentially delaying batch job startup in high-throughput scenarios.

---

## Remediation Priority Matrix

| Priority | Finding | Action |
|---|---|---|
| P1 — Within 30 days | db_accessadmin/db_securityadmin on service/monitoring accounts | Remove elevated roles; restrict to db_datareader for monitoring accounts |
| P1 — Within 30 days | emer_* accounts with db_datawriter | Revoke db_datawriter; implement PAM break-glass process |
| P2 — Within 90 days | SQL Server 2012 target | Upgrade SQL Server; update .sqlproj DSP to Sql150 or Sql160 |
| P2 — Within 90 days | No table purge | Implement scheduled purge of executions > 18 months old |
| P3 — Within 180 days | Shared single-schema JobRepository | Plan per-service isolation as part of microservices roadmap |
| P3 — Within 180 days | Sequence table pattern | Evaluate migration to IDENTITY columns for SQL Server-specific deployment |
