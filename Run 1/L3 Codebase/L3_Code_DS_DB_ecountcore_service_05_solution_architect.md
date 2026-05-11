# DS_DB_ecountcore_service — Solution Architect View

## 1. Technical Debt Register

| ID | Debt Item | Location | Severity | Effort to Remediate |
|----|-----------|----------|----------|---------------------|
| TD-1 | `sp_executesql` on unvalidated queue message payload | `app_task_agent.sql` line 47 | Critical | High |
| TD-2 | `TEXT` column in `TaskLog` | `TaskLog.sql` | Medium | Low |
| TD-3 | No queue poison-message handling | `TaskQueue.sql` (POISON_MESSAGE_HANDLING = OFF) | High | Low |
| TD-4 | `@StateString varchar(4000)` concatenated into XML task payload | `app_task_manager_escheatment_commit.sql` line 69, `app_task_manager_escheatment_due_diligence.sql` line 66 | High | Medium |
| TD-5 | Hard-coded cross-database three-part name references | All manager SPs | Medium | High |
| TD-6 | Binary CLR assembly committed without source | `Assemblies/EcountUtility.dll` | Medium | Medium |
| TD-7 | `GOTO` control flow in `escheatment_func_get_status` | `escheatment_func_get_status.sql` lines 81–82 | Low | Low |
| TD-8 | No CI/CD pipeline | Repository root | High | Medium |
| TD-9 | Individual SQL logins (`emer_*`) in Security scripts | `Security/emer_*.sql` | Medium | Low |
| TD-10 | No `TaskLog` retention / purge policy | `TaskLog.sql` | Medium | Low |

---

## 2. Security Vulnerabilities

### 2.1 CRITICAL — Dynamic SQL Injection via Service Broker Message Body

**File**: `dbo/Stored Procedures/app_task_agent.sql`, **line 47**

```sql
exec sp_executesql @taskstr;
```

`@taskstr` is extracted directly from the XML body of a Service Broker message (line 42: `@task.value('(/task)[1]', 'nvarchar(max)')`). The message body originates from the `app_task_enqueue` procedure which accepts an XML parameter — but there is no validation that the XML content does not itself contain arbitrary T-SQL before it reaches the queue.

**Attack vector**: Any database principal with `SEND` privilege on `TaskManagerService` can place a crafted `<task>EXEC xp_cmdshell 'net user ...'</task>` message. The task agent executes under `EXECUTE AS OWNER` (the queue definition), meaning it runs as `dbo` of the database — effectively unrestricted T-SQL execution.

**Remediation**:
1. Implement an allowlist of permitted stored procedure names extracted from the task XML and validate before execution.
2. Replace the generic `sp_executesql` pattern with a case-dispatching pattern (CASE/IF block) that only routes to known, approved procedures.
3. Audit and restrict `SEND` privilege on `TaskManagerService` to the minimum set of application service accounts.

### 2.2 HIGH — StateString Injection Risk

**Files**: `app_task_manager_escheatment_commit.sql` line 69, `app_task_manager_escheatment_due_diligence.sql` line 66

`@StateString varchar(4000)` is concatenated into the XML task string using string concatenation:
```sql
+ ', @StateString=''' + @Statestring + ''''
```
If `@StateString` contains a single quote or SQL fragment, the resulting XML task payload could contain unexpected content. When `app_task_agent` then executes this via `sp_executesql`, the injection travels through two layers.

**Remediation**: Validate `@StateString` against a regex allowing only two-character US state codes (and pipe-delimited combinations). Use `REPLACE(@StateString, '''', '''''')` at minimum.

### 2.3 MEDIUM — Service Broker Encryption Disabled

**File**: `dbo/Stored Procedures/app_task_enqueue.sql`, **line 17**
```sql
WITH ENCRYPTION = OFF
```
Acceptable for same-instance communication. If the Service Broker is ever configured for cross-instance delivery (e.g. disaster-recovery or migration scenario), this must be changed to `WITH ENCRYPTION = ON`.

### 2.4 MEDIUM — `db_accessadmin` / `db_securityadmin` for Monitoring Accounts

**File**: `Security/RoleMemberships.sql`, **lines 1–18**

`NAM\PROD_CPP_APAC`, `NAM\ISA_SQL_SECADMIN`, `ifs_gidadb`, `scpardb`, and `ifs_infosec` are members of both `db_accessadmin` and `db_securityadmin`. These roles can add/remove database users and manage security, which exceeds the permissions needed for monitoring or reporting. This violates the principle of least privilege.

### 2.5 LOW — GOTO Statement in UDF

**File**: `dbo/Functions/escheatment_func_get_status.sql`, **line 81**

Use of `GOTO done:` is an unstructured control-flow pattern. Not a security vulnerability, but makes the function harder to audit and test.

---

## 3. All Object Names with Purpose

### Tables
- `dbo.TaskLog` — Operational log of task dispatches; one row per enqueue/execute cycle.

### Stored Procedures
- `dbo.app_task_agent` — Service Broker activation proc; dequeues and executes tasks via `sp_executesql`.
- `dbo.app_task_enqueue` — Sends a Service Broker message (XML task) from TaskManagerService to TaskAgentService.
- `dbo.app_task_log` — Inserts a TaskLog start record; returns `@logID` output.
- `dbo.app_task_log_update` — Updates a TaskLog record with task string and/or return code.
- `dbo.app_task_manager_card_account_purge_request` — Iterates programs, dispatches card-purge tasks.
- `dbo.app_task_manager_dormancy_fee` — Iterates programs, dispatches dormancy-fee tasks monthly.
- `dbo.app_task_manager_escheatment_commit` — Dispatches escheatment final-transfer tasks per state.
- `dbo.app_task_manager_escheatment_due_diligence` — Dispatches due-diligence letter tasks.
- `dbo.app_task_manager_escheatment_enqueue` — Dispatches initial escheatment identification tasks.
- `dbo.app_task_manager_maintenance_fee` — Iterates programs (with DCAF open-auth exclusion), dispatches maintenance-fee tasks.

### Functions
- `dbo.escheatment_func_get_status` — Returns 0 (active) or 1 (pending escheatment) for a DDA number.
- `dbo.getValidStringFromFrench` — Normalises French characters for bilingual string handling.
- `dbo.programCount` — SQL-CLR scalar function delegating to `EcountUtility.dll`.

### Service Broker
- `dbo.TaskQueue` — Worker queue; activation-enabled; max 2 concurrent readers.
- `dbo.TaskManagerQueue` — Manager-side initiator queue.
- `dbo.TaskAgentService` — Target service for task messages.
- `dbo.TaskManagerService` — Initiator service that sends task messages.
- `dbo.TaskContract` — Governs message exchange pattern.
- `dbo.TaskMessage` — Message type for XML task payloads.

---

## 4. Remediation Priority

| Priority | Item | Action |
|----------|------|--------|
| P0 | TD-1 / 2.1 — `sp_executesql` on queue payload | Implement allowlist-based procedure dispatch; revoke excess SEND privileges |
| P0 | TD-4 / 2.2 — StateString injection | Validate and escape `@StateString` before XML construction |
| P1 | TD-3 — Poison message handling off | Enable `POISON_MESSAGE_HANDLING = ON` on `TaskQueue` |
| P1 | TD-8 — No CI/CD pipeline | Add SSDT build + DACPAC deploy pipeline with SQL static analysis |
| P2 | 2.4 — `db_accessadmin`/`db_securityadmin` for monitoring accounts | Revoke elevated roles; grant minimum required permissions |
| P2 | TD-9 — Individual SQL logins | Migrate `emer_*` to time-boxed AD group membership |
| P3 | TD-2 — TEXT column | Migrate `task_msg` to NVARCHAR(MAX) |
| P3 | TD-10 — No log retention | Implement scheduled purge of `TaskLog` older than 90 days |
| P4 | TD-5 — Three-part names | Introduce synonyms or service layer abstraction |
| P4 | TD-6 — Binary CLR | Add source code to repo; move to versioned build artefact |
