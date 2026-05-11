# DS_DB_acctgwf — Data Architect Report

## 1. Database Object Inventory

### 1.1 Tables (27 total)

| Table | Purpose | Sensitive Fields | PCI/Privacy Flag |
|---|---|---|---|
| `tblAWCompanies` | Company registry with GL database pointer (`GlDbName VARCHAR(256)`) | `GlDbName` (infra) | Low |
| `tblAWUsers` | Application user accounts | `uid VARCHAR(15)`, `pwd VARBINARY(256)` (SHA-1 hash), `Email VARCHAR(100)` | Medium — password hash, PII email |
| `tblAWUserGroups` | User group definitions | None | Low |
| `tblAWUsersC` | Company-user mapping | None | Low |
| `tblCompanies` | Core company registry (`ExtId` FK to `tblAWCompanies`) | None | Low |
| `tblUsers` | Core user table (linked from `tblAWUsers` via trigger) | `ExtId INT` (maps to AWUsers.UserId) | Low |
| `tblUsersS` | User session/state table (referenced by triggers) | Session state | Low |
| `tblUserGroups` | Core user groups | None | Low |
| `tblUserGroupRights` | RBAC mapping table | None | Low |
| `tblUserRightTypes` | Right type definitions | None | Low |
| `tblAW_Tasks` | Task definitions per company | None | Low |
| `tblAW_TaskSchedules` | Schedule-to-task mapping | None | Low |
| `tblAW_TaskHistory` | Task completion log | `Note VARCHAR(900)` (may contain operational text) | Low |
| `tblAW_TaskComments` | Free-text comments on tasks | `Comment VARCHAR(8000)` | Low |
| `tblAW_TaskDocs` | Task-to-document link | None | Low |
| `tblAW_WPs` | Workpaper header (4-signature workflow) | None | Low |
| `tblAW_WPAccts` | GL accounts attached to workpaper | `AcctNum` reference | Low |
| `tblAW_WPComments` | Workpaper comments | Free text | Low |
| `tblAW_WPCommentsAccts` | WP comment-to-account mapping | None | Low |
| `tblAW_WPDocs` | WP-to-document link | None | Low |
| `tblAW_Docs` | Document registry (links to external doc storage) | `DocLink VARCHAR(900)` (file path/URL) | Low |
| `tblAW_DocAtts` | Document attachment metadata | `DocAttLink VARCHAR(900)` | Low |
| `tblAW_DocAttTree` | Nested-set tree for doc hierarchy | None | Low |
| `tblAW_DocDates` | Per-period document signing metadata | None | Low |
| `tblAW_OpenItems` | Open reconciliation items with amount and P&L flag | `Amount NUMERIC(19,5)` | Low |
| `tblAW_OpenItemNotes` | Notes on open items | Free text | Low |
| `tblAW_Accts` | GL account definitions per company | `AcctNum VARCHAR(50)` | Low |
| `tblAW_Schedules` | Frequency schedule definitions | None | Low |
| `tblAW_Frequency` | Frequency type lookup | None | Low |
| `tblAW_FrequencyOn` | Frequency day-of-week mapping | None | Low |
| `tblAW_Types` | Workflow type definitions | None | Low |
| `combine_dtl` | ETL staging (minimal definition) | Unknown | Low |
| `combine_log` | ETL log (minimal definition) | Unknown | Low |

**Total tables**: 33 (including combine tables and core infrastructure tables).

### 1.2 Views (26 total)

| View | Purpose |
|---|---|
| `vAW_Accts` | GL account display with company join |
| `vAW_DocAttTree` | Hierarchical document tree rendering |
| `vAW_Docs` | Document list with signing status |
| `vAW_Frequency` / `vAW_FrequencyOn` | Frequency lookup displays |
| `vAW_OpenItemNotes` | Open item notes with user names |
| `vAW_OpenItems` | Open items with account and user info |
| `vAW_Schedules` | Schedule definitions with frequency names |
| `vAW_TaskComments` | Task comments with user display names |
| `vAW_TaskDocs` | Task documents with signing status |
| `vAW_TaskHistory` | Task history with schedule and WP join |
| `vAW_Tasks` | Task list with company and user names |
| `vAW_TaskSchedules` | Task-schedule mapping |
| `vAW_Types` / `vAW_TypesTree` | Type hierarchy |
| `vAW_WPAccts` | Workpaper GL accounts |
| `vAW_WPComments` | WP comments with user names |
| `vAW_WPCommentsAccts` | WP comment-account join |
| `vAW_WPDocs` | WP documents with signing status |
| `vAW_WPs` | Workpaper summary with status derivation |
| `vCompanies` | Company list |
| `vUserGroups` | User groups |
| `vUsers` | User list (cross-type) |
| `vUsersA` | All users |
| `vUsersC` | Company-scoped users |
| `vUsersLoggedIn` | Active sessions |
| `vUsersS` | Session-state users |

### 1.3 Stored Procedures (14 total)

| Stored Procedure | Purpose |
|---|---|
| `sys_accts` | GL account CRUD and querying |
| `sys_chkglviews` | Validates whether eCount or GP views exist in target DB |
| `sys_companies` | Company list/CRUD |
| `sys_docs` | Document management (create, list, attach, tree ops) |
| `sys_import` | ETL import placeholder |
| `sys_openitems` | Open item CRUD and reconciliation |
| `sys_periods` | Fiscal period management |
| `sys_schedules` | Schedule CRUD |
| `sys_tasks` | Task CRUD, completion, commenting, document attachment |
| `sys_tasks_execsched` | Execute scheduled task generation |
| `sys_types` | Type hierarchy CRUD |
| `sys_user` | Authentication, password management, session management |
| `sys_wp` | Workpaper CRUD with 4-signature workflow |
| `sys_wpreports` | Workpaper reporting |

### 1.4 Functions (11 total)

| Function | Return Type | Purpose |
|---|---|---|
| `sys_aggr_date` | Scalar `DATETIME` | Aggregates dates across a range |
| `sys_chkstr` | Scalar `INT` | Validates string for SQL-injection-safe characters |
| `sys_chkuser` | Scalar `INT` | RBAC user-company access check |
| `sys_chkuserrights` | Scalar `INT` | User right-type check |
| `sys_cinfo` | Scalar `NVARCHAR` | Returns GL database name for company |
| `sys_clist` | Table-valued | Returns company list for session |
| `sys_sched` | Table-valued | Generates schedule date series (recursive CTE) |
| `sys_strGLAcctActive` | Scalar `NVARCHAR(MAX)` | Dynamic SQL string for active GL accounts |
| `sys_strGLAccts` | Scalar `NVARCHAR(MAX)` | Dynamic SQL string for GL COA |
| `sys_strGLAcctTx` | Scalar `NVARCHAR(MAX)` | Dynamic SQL string for GL transactions |
| `sys_strGLAcctUnposted` | Scalar `NVARCHAR(MAX)` | Dynamic SQL string for unposted GL entries |
| `sys_uinfo` | Table-valued | Returns user info for session ID |

### 1.5 Triggers (2 total)

| Trigger | On Table | Event | Purpose |
|---|---|---|---|
| `trgAWUsers` | `tblAWUsers` | AFTER INSERT, UPDATE | Syncs user to `tblUsers`; hashes password with SHA-1 on UPDATE(pwd) |
| `trgAWCompanies` | `tblAWCompanies` | AFTER INSERT | Inserts corresponding row into `tblCompanies` |

## 2. Schema Design Analysis

### 2.1 Referential Integrity
Foreign key constraints are well-defined throughout. Key relationships:
- `tblAW_Tasks.CompanyId` → `tblCompanies.CompanyId`
- `tblAW_Tasks.UserId` → `tblUsers.UserId`
- `tblAW_Tasks.WpTypeId` → `tblAW_Types.TypeId`
- `tblAW_WPs` has four separate FK references to `tblUsers` (PrepareBy, ReviewBy, SignBy, AuditBy)
- `tblAW_OpenItems.AcctId` → `tblAW_Accts.AcctId`
- `tblAWUsers.GroupId` → `tblUserGroups.GroupId`

**On-delete behaviour**: Most FKs use default (NO ACTION), appropriate for an audit/workflow database. No CASCADE DELETE is used, preserving historical data.

### 2.2 Indexing Strategy
- Clustered indexes are generally on the most-queried column combinations (e.g., `tblAW_OpenItems`: clustered on `[AcctId, Date, ClrBy]`).
- `tblAW_WPs`: unique clustered on `WpId` with a compound primary key on `(CompanyId, TypeId, Date)` — supports the typical workpaper query pattern.
- `tblAW_Tasks`: clustered primary on `TaskId`; non-clustered on `(CompanyId, UserId)` for user-task lookups.
- The `sys_sched` function uses `OPTION (MAXRECURSION 0)` which disables the recursion limit — this is a minor risk for runaway queries if date ranges are very large.

### 2.3 Sensitive Data Fields

| Table | Field | Data Type | Classification | PCI Relevance |
|---|---|---|---|---|
| `tblAWUsers` | `pwd` | `VARBINARY(256)` | Credential hash (SHA-1) | **Flag**: SHA-1 is deprecated (NIST SP 800-131A). Not PCI CHD but is an auth credential. |
| `tblAWUsers` | `Email` | `VARCHAR(100)` | PII (employee) | GDPR/CCPA internal staff |
| `tblAWUsers` | `uid` | `VARCHAR(15)` | Username (not consumer) | Low |
| `tblAW_Docs` | `DocLink` | `VARCHAR(900)` | File path/URL to external document | May reference shared drives with sensitive content |

**No PANs, CVVs, SSNs, DOBs, or full account numbers are present in this database.** This database is **not in PCI DSS CDE scope**.

### 2.4 Encryption at Rest
- Database-level: `IsEncryptionOn = False` per `acctgwf.sqlproj` line 51. **Transparent Data Encryption (TDE) is disabled.**
- Column-level: No `ENCRYPTBYKEY` or Always Encrypted usage detected.
- Password storage: SHA-1 HASHBYTES used in the trigger at `tblAWUsers` line 37. SHA-1 is **cryptographically weak** by current standards.

### 2.5 Data Retention
- No `DELETE` stored procedures include time-based purge logic. Open items are cleared by setting `ClrBy`/`ClrDt` but not deleted.
- Task history rows accumulate indefinitely. No archiving or partition-based retention detected.
- **Gap**: No data retention policy is implemented in the schema. Historical task and workpaper data will grow without bound.

### 2.6 PCI DSS CDE Scope Assessment
This database is **out of scope for PCI DSS CDE**. No cardholder data elements (PAN, CVV, expiry, track data) are stored. The closest connection to payment data is the GL account references, which reference account codes (e.g., `AcctNum VARCHAR(50)`) — these are GL ledger identifiers, not card numbers.

## 3. Cross-Database Dependencies

| Referenced Database | How Referenced | Purpose |
|---|---|---|
| `ATLYS_E` | `EXEC ATLYS_E.dbo.sys_user` | User authentication delegation |
| `[GlDbName]` (dynamic) | Dynamic SQL built in `sys_strGLAccts*` functions | Read GL COA and transactions from GP |
| `[GlDbName].dbo.GL00100` | Dynamic SQL | GP General Ledger master |
| `[GlDbName].dbo.eCountBankTransactions` | Dynamic SQL | eCount bank transaction view |

## 4. Schema Quality Observations

- The `combine_dtl` (155 bytes) and `combine_log` (108 bytes) table definitions are extremely minimal — likely stub/legacy tables that should be reviewed for removal.
- `tblAW_Docs_old` (408 bytes) is explicitly named as an old table — this is dead schema that should be deprecated.
- The `sys_sched` function is used with `OPTION (MAXRECURSION 0)` in `sys_tasks` — a potential performance risk if called with very wide date ranges.
- `tblAW_WPs` has a compound natural primary key `(CompanyId, TypeId, Date)` which is enforced as `PRIMARY KEY NONCLUSTERED`, with a separate unique clustered index on `WpId`. This is an unusual pattern that may complicate future partitioning.
