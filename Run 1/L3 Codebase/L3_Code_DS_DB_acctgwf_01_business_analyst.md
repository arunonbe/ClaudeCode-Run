# DS_DB_acctgwf — Business Analyst Report

## 1. Database Overview and Business Purpose

`acctgwf` (Account Workflow) is a **financial accounting workflow management database** that supports the internal back-office operations of the Atlys payments platform. It is not a cardholder-facing system; rather, it orchestrates the operational tasks, approvals, document management, and general ledger reconciliation processes required by the Finance and Accounting teams managing prepaid card programs and client accounts.

The database is deployed as a Microsoft SQL Server Database Project (SSDT, `.sqlproj`, schema version 2.0, targeting SQL Server 2008+ via `Sql100DatabaseSchemaProvider`). It is tightly coupled to the `ATLYS_E` entity database via cross-database references (e.g., `EXEC ATLYS_E.dbo.sys_user`) and reads General Ledger data from Microsoft Dynamics GP (`GL00100`, `eCountBankTransactions`) via linked-server or cross-database queries.

## 2. Business Processes Supported

### 2.1 Task Management and Scheduling
The database tracks **recurring operational tasks** assigned to users within each company entity. Tasks can be scheduled on fixed frequencies (daily, weekly, monthly) via `tblAW_Schedules` and `tblAW_TaskSchedules`. Completion, status, and auditing of each task occurrence is recorded in `tblAW_TaskHistory`. This supports SOX-style evidence gathering: tasks have a prepared-by, reviewed-by, signed-by, and audited-by workflow enforced at the `tblAW_WPs` (Workpapers) level.

### 2.2 Workpapers (WP) Management
The workpapers module (`tblAW_WPs`, `sys_wp` stored procedure, 23 KB) implements a **four-signature workflow**: PrepareBy → ReviewBy → SignBy → AuditBy. Each workpaper is typed (`tblAW_Types`), dated, and associated with a company entity. Supporting documents are managed through a hierarchical tree structure (`tblAW_DocAttTree`, `tblAW_DocAtts`, `tblAW_Docs`, `tblAW_DocDates`). This supports internal control evidence requirements under **SOC 1 / SOC 2** audit frameworks.

### 2.3 Open Items / Reconciliation Tracking
`tblAW_OpenItems` stores financial open items (debit/credit amounts with P&L flag) tied to GL accounts (`tblAW_Accts`). Items are cleared (`ClrBy`, `ClrDt`) when reconciled, supporting **account reconciliation workflows** common in prepaid card program management for intercompany settlements and float account balancing.

### 2.4 General Ledger Account Integration
The `sys_strGLAccts`, `sys_strGLAcctActive`, `sys_strGLAcctTx`, and `sys_strGLAcctUnposted` scalar functions construct dynamic SQL strings to query the company's linked GL database (either `eCountCOA` / `eCountBankTransactions` views or raw Dynamics GP tables `GL00100` / `GL10000`). This bridges the workflow database to the authoritative accounting system.

### 2.5 User and Group Management
A parallel user store (`tblAWUsers`, `tblAWUserGroups`, `tblAWUsersC`) exists alongside the core `tblUsers` / `tblUserGroups` tables. A trigger (`trgAWUsers`) automatically synchronises user records into the core user table on insert/update. Passwords are stored as SHA-1 hashes of the supplied VARBINARY in `tblAWUsers.pwd`. Role-based access is enforced in every stored procedure via `dbo.sys_chkuser` and `dbo.sys_chkuserrights` function calls before any data operation.

### 2.6 Document Attachment Tree
`tblAW_DocAttTree` implements a **nested-set (left/right boundary) tree model** for hierarchical document attachments. The `sys_docs` procedure (21 KB) manages create, read, update, delete, and tree-structure operations on documents linked to both tasks and workpapers.

### 2.7 Schedules and Frequency Engine
`tblAW_Frequency` and `tblAW_FrequencyOn` define recurrence patterns (e.g., weekly on specific days). The `sys_sched` table-valued function (`sys_sched.sql`, 2.9 KB) generates a calendar of scheduled dates using recursive CTE logic (`OPTION (MAXRECURSION 0)`), supporting projection of future task occurrences across any time range.

## 3. Data Stored and Processed

| Category | Tables |
|---|---|
| Task definitions | `tblAW_Tasks`, `tblAW_TaskSchedules`, `tblAW_TaskHistory`, `tblAW_TaskComments`, `tblAW_TaskDocs` |
| Workpapers | `tblAW_WPs`, `tblAW_WPAccts`, `tblAW_WPComments`, `tblAW_WPCommentsAccts`, `tblAW_WPDocs` |
| Documents | `tblAW_Docs`, `tblAW_DocAtts`, `tblAW_DocAttTree`, `tblAW_DocDates` |
| Open items | `tblAW_OpenItems`, `tblAW_OpenItemNotes` |
| GL accounts | `tblAW_Accts` |
| Companies | `tblAWCompanies`, `tblCompanies` |
| Users | `tblAWUsers`, `tblAWUserGroups`, `tblAWUsersC`, `tblUsers`, `tblUsersS` |
| Scheduling | `tblAW_Schedules`, `tblAW_Frequency`, `tblAW_FrequencyOn` |
| Types | `tblAW_Types`, `tblUserRightTypes`, `tblUserGroupRights`, `tblUserGroups` |
| ETL staging | `combine_dtl`, `combine_log` |

## 4. Business Rules Encoded in SQL

- **Password expiry**: `sys_user.sql` line 95 enforces a 30-day password reset policy (`preset < GETDATE() - 30`).
- **Task completion gate**: A task cannot be completed if any attached documents have `PrepareDt IS NULL` (`sys_tasks.sql` lines 430–440) — enforcing the document preparation step.
- **Workpaper four-eyes principle**: `tblAW_WPs` has PrepareBy, ReviewBy, SignBy, and AuditBy columns all referencing `tblUsers`, enforcing segregation of duties.
- **Company-scoped access**: Every stored procedure validates `dbo.sys_chkuser(@s_id, @company_id, 'C')` before any data operation; the EMEA_ATLYS login is the only exempted system account (`sys_tasks.sql` line 19).
- **Task replication**: `repli_comp_tasks` action in `sys_tasks` can copy all tasks assigned to a user from one company to another, preserving schedule assignments.
- **Nested-set tree integrity**: The document attachment tree uses left/right boundary values to maintain hierarchy without recursive parent-child queries.

## 5. Regulatory Relevance

| Regulation | Relevance |
|---|---|
| **SOC 1 / SOC 2** | Workpapers module directly supports internal control evidence. PrepareBy/ReviewBy/SignBy/AuditBy workflow is analogous to SOC control attestation. |
| **PCI DSS** | This database does **not** appear to store PANs, CVVs, or track data. No CDE-scope tables detected. However, it does reference `eCountBankTransactions`, which may contain settlement data in linked GP databases. |
| **GLBA / SOX** | Open-items reconciliation and GL account workflow are relevant to financial reporting controls. |
| **GDPR / CCPA** | User email addresses (`tblAWUsers.Email`, `tblUsers`) and names (`UName`) are stored. These are internal employee/contractor identifiers, not consumer data, but are in scope for data-subject rights if EU staff are involved. |

## 6. Integration Points

- **ATLYS_E database**: Cross-database calls to `ATLYS_E.dbo.sys_user` for authentication delegation. The `sys_user` procedure in acctgwf (line 66) proxies login to the ATLYS_E user store.
- **Microsoft Dynamics GP**: The `sys_strGLAccts` function and `sys_chkglviews` procedure build dynamic SQL strings targeting the company's `GlDbName` field (stored in `tblAWCompanies`) to retrieve GL account data from either eCount custom views or raw GP tables.
- **ATLYS_RvNCA / other revenue databases**: `sys_wp` references `dbo.sys_wp` object existence checks and calls cross-database reporting views.

## 7. Data Flows

```
[ATLYS Application UI]
        |
        v (session_id, company_id, action params)
[acctgwf stored procedures: sys_tasks, sys_wp, sys_docs, sys_openitems]
        |
        |---> [tblAW_Tasks / tblAW_WPs / tblAW_OpenItems] (write/update)
        |---> [ATLYS_E.dbo.sys_user] (auth delegation)
        |---> [Company GlDbName].dbo.GL00100 (read GL accounts)
        |---> [Company GlDbName].dbo.eCountBankTransactions (read bank txns)
```

## 8. Business Risk Observations

- The `tblAWCompanies.GlDbName` field stores the target database name as a `VARCHAR(256)`, and this value is passed into dynamic SQL string builders. If this field is modified by a malicious or mistaken admin, the GL query would target an incorrect database.
- Password reset emails are not managed in this database — only `PReset` timestamps and SHA-1 hashes. There is no evidence of email notification logic in this repo.
- The `combine_dtl` and `combine_log` tables appear to be ETL staging tables with minimal definition (155 bytes and 108 bytes respectively), suggesting they may be remnants or placeholders.
