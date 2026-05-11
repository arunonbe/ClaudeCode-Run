# DS_DB_ecountcore_service — Business Analyst View

## 1. Repository Identity
| Attribute | Value |
|-----------|-------|
| Repo name | DS_DB_ecountcore_service |
| Project file | `Ecountcore_service.sqlproj` (SQL Server Data Tools, DSP SQL110) |
| Solution file | `Ecountcore_service.sln` |
| Active branch | `development` |
| README content | One line: "ecountcore_service" — no extended documentation |

---

## 2. Business Purpose

`ecountcore_service` is the **asynchronous task-dispatch layer** for the EcountCore prepaid-card platform. It does not hold cardholder accounts directly; instead, it acts as a **SQL Server Service Broker message bus** that queues, routes, and logs long-running batch operations that execute against the main `ecountcore` database. Its value lies entirely in the reliable, transactional delivery of work items to background worker processes.

Business scenarios directly enabled by this database:

| Business Event | Triggered By | Dispatched Task |
|---|---|---|
| Monthly dormancy / maintenance fee run | Scheduled job | `fdr_process_dormancy_fee` / `fdr_process_maintenance_fee` in `ecountcore` |
| Escheatment enqueue | Compliance calendar | `app_process_escheatment_enqueue` in `ecountcore` |
| Escheatment due-diligence letters | State unclaimed-property deadlines | `app_process_escheatment_due_diligence` in `ecountcore` |
| Escheatment commit (transfer to state) | State filing | `app_process_escheatment_commit` in `ecountcore` |
| Card-account purge | Data-retention schedule | `fdr_process_card_account_purge_request` in `ecountcore` |

---

## 3. Processes Supported

### 3.1 Dormancy and Maintenance Fee Processing
Stored procedures `app_task_manager_dormancy_fee` and `app_task_manager_maintenance_fee` iterate over all active prepaid programs (product/brand/affiliate triplets) that are configured with fee structures, build an XML `<task>` payload containing the target stored procedure name and parameters, and enqueue each via `app_task_enqueue`. The task agent (`app_task_agent`) dequeues and executes each task with `sp_executesql`. This design allows the platform to fan out fee processing across many programs concurrently (queue readers = 2 by default, configurable in `TaskQueue`).

The maintenance fee procedure (`app_task_manager_maintenance_fee`, introduced 2018-06-27, last updated 2020-12-17) incorporates logic to exclude accounts with open authorisations drawn from a DCAF file staging table in `ecountcore_process`, reflecting Reg E obligations around cardholder balance protection.

### 3.2 Escheatment Life-cycle Management
Three manager procedures handle the three-phase unclaimed-property cycle required by US state laws:
- **Enqueue** (`app_task_manager_escheatment_enqueue`) — identifies programs tagged `statesmart-channel` for products 4 and 5 and queues initial identification work.
- **Due Diligence** (`app_task_manager_escheatment_due_diligence`) — dispatches due-diligence letter tasks for cards in status 10 (pending escheatment) in the queue table.
- **Commit** (`app_task_manager_escheatment_commit`) — dispatches final transfer tasks with state-specific rule-set IDs.

This supports compliance with NAUPA/state unclaimed-property regulations — a regulatory obligation for Onbe as a prepaid card issuer.

### 3.3 Card Account Purge
`app_task_manager_card_account_purge_request` dispatches data purge work for all programs to satisfy data-minimisation obligations. Purge mode (recurring vs. one-time) is driven by the `app_profile_promotion_label` table in `ecountcore`.

### 3.4 Task Logging
All manager procedures write start and end records to `dbo.TaskLog` via `app_task_log` / `app_task_log_update`, providing an audit trail of when each batch was triggered and what happened.

---

## 4. Data Stored

The database's own schema is intentionally thin:

| Object | Data Held |
|--------|-----------|
| `dbo.TaskLog` | Task name, message text, return code, SQL process ID, created/updated timestamps |
| Service Broker objects | In-flight XML task messages (transient, in queue tables managed by SQL Server) |
| `Assemblies/EcountUtility.dll` | CLR assembly backing the `programCount` SQL-CLR function |

All card account data, fee configuration, escheatment queues, and program profiles reside in **`ecountcore`** and **`ecountcore_process`**, which this database calls via three-part names (e.g. `ecountcore..fdr_dda_account`).

---

## 5. Regulatory Relevance

| Regulation | Relevance |
|------------|-----------|
| **Reg E (EFTA)** | Dormancy and maintenance fee logic must comply with Reg E fee-disclosure and fee-application rules for payroll / general-purpose prepaid cards. |
| **NAUPA / State Unclaimed Property Laws** | The three-phase escheatment process is a direct regulatory obligation; failures in enqueue or commit steps create state reporting risk. |
| **PCI DSS v4.0.1** | This database does not store PANs, CVVs, or track data. It is **not** in scope for CDE classification on its own, but it dispatches processes that touch cardholder account data in `ecountcore`. Its integrity is therefore relevant to PCI DSS Requirement 6 (secure systems) and Requirement 10 (audit logging). |
| **SOX** | Not directly applicable — this is an operational database, not a financial ledger. However, if fee-charging accuracy is a SOX control, the correctness of task dispatch affects the SOX control chain. |
| **GLBA** | Dormancy and purge operations process NPI (consumer account data); GLBA safeguards requirements apply to the overall platform. |

---

## 6. Data Flows

```
Scheduled Job Trigger (SQL Agent or external)
    │
    ▼
app_task_manager_* (ecountcore_service)
    │  reads program/config from ecountcore
    │  builds XML <task> payload
    ▼
app_task_enqueue  ──→  Service Broker: TaskManagerService
                                       ↓
                              TaskContract
                                       ↓
                         TaskAgentService / TaskQueue
                                       ↓
                    app_task_agent (activated, max 2 readers)
                         │  executes sp_executesql(@taskstr)
                         ▼
                   ecountcore..fdr_process_* / app_process_*
                         │
                         ▼
                   ecountcore_process (DCAF staging, open-auth tables)
```

Task results and errors are written back to `dbo.TaskLog`.

---

## 7. Integration with Onbe Services

- **ecountcore** — primary dependency: all program configuration, cardholder accounts, and fee execution live there. The service database is tightly coupled via three-part cross-database calls.
- **ecountcore_process** — DCAF file staging tables (`fdr_process_dcaf_chd_data`, `fdr_process_dcaf_maint_fee_open_auth_accounts`) are read and written from `app_task_manager_maintenance_fee`.
- **SQL Agent / Scheduling** — External scheduled jobs invoke the manager stored procedures; no scheduling metadata is stored in this repo.
- **Banker SVC** — No direct integration found; the Banker service consumes GP databases (see GP repo analyses) rather than ecountcore_service.
