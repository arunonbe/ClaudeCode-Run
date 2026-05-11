# accounting-workflow_WAPP — Data Architect View

## Data Stores

| Store | Purpose | Connection Index |
|---|---|---|
| `ATLYS_E` | Source ERP/general ledger data (read; used for account import) | `SQLData.Conn(0)` |
| `ATLYS_RvCR` | Secondary ERP/reconciliation source | `SQLData.Conn(1)` |
| `AcctgWf` | Primary application database — all workflow, user, task, workpaper, and open-item data | `SQLData.Conn(2)` |
| Local filesystem (`F:\Daily_Recons1`) | Document attachments referenced by path; default directory hardcoded in `TaskDoc.cs` line 346 and `NewDoc.cs` line 48 | N/A |
| Local error log (`<StartupPath>\Errors\errlog.txt`) | Unhandled exception traces written by `ErrorLog.WriteToErrorLog` | N/A |
| `assets.xml` / `liab.xml` | Seed data for asset and liability chart-of-account tree structure, shipped with the application binary | Embedded content files |

All active runtime reads and writes flow through **`AcctgWf`**. `ATLYS_E` and `ATLYS_RvCR` are accessed only via the `sys_accts @action='import_accts'` path on the server side.

---

## Schema & Tables

The C# client interacts exclusively via stored procedures. The following tables/logical entities are inferred from SP names and parameter patterns:

| Inferred Table / Object | Evidence (SP + action) | Key Columns Observed |
|---|---|---|
| `sys_users` / users | `sys_user`: login, logout, changepwd, resetpwd, enable, disable, resetlocked, list, detail, update, list_groups | `s_id` (session token), `uid` (VARCHAR 15), `UName`, `Email`, `Enabled`, `LockedOut`, `GroupId`, `ExtType`, `pwd_expired` |
| `sys_sessions` | `sys_user @action='login'` returns `s_id`; `logout` invalidates it | `s_id` (VARCHAR 50) |
| `sys_groups` | `sys_user @action='list_groups'` | `GroupId`, `GroupName` |
| `sys_companies` | `sys_companies`: list, list_access, add_access, remove_access, add_accees (note typo) | `id`, `co_name`, `ctype` |
| `sys_accounts` | `sys_accts`: list, types, update, import_accts | `AcctId` (Int), `AcctNum`, `AcctDescr`, `AcctType` (TinyInt), `TypeId`, `TypeDescr` |
| `sys_account_types` / FS tree | `sys_types`: tree, add_node, update_node, delete_tree, delete_node, move_tree | `type_id` (SmallInt), `new_type_id`, `level`, `descr` |
| `sys_tasks` | `sys_tasks`: details, update, list, list_c, list_users, list_users_c, list_docs, list_comments, new_doc, new_comment, remove_doc, complete, taskhist_details, execsched | `TaskId` (BigInt), `TaskName`, `Enabled` (TinyInt), `WpTypeId`, `UserId`, `CompanyId` |
| `sys_task_history` | `sys_tasks @action='status'`, `status_month`; `HistId` returned | `HistId`, `Status` ("NOT COMPLETED" / "COMPLETED" / "SCHEDULED"), `CompletedBy`, `CompletedDt`, `Note`, `DocsAttached` (0/1) |
| `sys_schedules` | `sys_schedules`: list_sched, list_freqid, list_freqonid, update_sched, pick_sched, list_tasks | `SchedId` (Int), `SchedName`, `Descr`, `Enabled`, `StartDate`, `EndDate` (9999-12-31 = no end), `FreqID`, `Freq`, `FreqOn` |
| `sys_workpapers` | `sys_wp`: new_wp, list_acctscomm, list_comments, new_comment, clear, update_commentsaccts, list_commentsaccts | `WpId` (BigInt), `WpTypeId` (TinyInt), `WpStatus` (PREPARED / REVIEWED / CLOSED), `NCComments`, `company_id` |
| `sys_documents` | `sys_docs`: list_attachments, update, prepare_doc, review_doc, sign_doc, add_attachment, move_attachments_tree, remove_attachment, remove_attachments_tree, update_attachment, getdescr, getattdescr | `DocId` (BigInt), `DocName` (VARCHAR 50), `DocDescr` (VARCHAR 400), `DocLink` (VARCHAR 900 path), `PrepareBy`, `PrepareDt`, `ReviewBy`, `ReviewDt`, `SignBy`, `SignDt`, `Attachments` (0/1) |
| `sys_open_items` | `sys_openitems`: list_items, list_notes, new_item, update_item, clear, total_items, new_note | `ItemId` (BigInt), `Date`, `Amount` (Decimal 19), `Descr` (VARCHAR 8000), `PnL` (TinyInt), `ClrBy`, `ClrDt` |
| `sys_wp_comments` | `sys_wp @action='list_comments'`, `new_comment`, `clear`, `update_commentsaccts` | `id`, `Date`, `UserName`, `Comment` (VARCHAR 8000), `ClrBy`, `ClrDt` |
| `sys_task_comments` | `sys_tasks @action='list_comments'`, `new_comment` | `Date`, `UserName`, `Comment` |
| `sys_attachment_tree` | `sys_docs @action='list_attachments'` returns XML via `ExecuteXmlReader`; tree navigated in `TaskDoc.GetTree` | Hierarchical XML with `id` and `l` (link) attributes |

---

## Sensitive Data Handling

| Data Category | Location | Risk |
|---|---|---|
| **Application username / password (plaintext)** | `Login.cs` line 106: `pwd.Value = PasswordTextBox.Text.Trim()` passed as `SqlDbType.VarChar(256)` to SP | Password transmitted in cleartext to SQL Server over the network |
| **Database credentials (hardcoded)** | `SQLData.cs` lines 34 and 56: `User Id=raf;Pwd=[REDACTED — rotate immediately]` embedded in source and compiled into binary | Extractable by any user who can run `strings` on the EXE |
| **Session ID (VARCHAR 50)** | Stored in `MDIParent1.sid`; passed on every SP call as `@s_id` | Session fixation/hijacking possible if token predictable or reused |
| **User display name, email** | Returned from `sys_user @action='detail'`; bound directly to `DataSet` in memory | No explicit scrubbing on form close |
| **Cardholder Liability account balances** | `liab.xml` seeds `Cardholder_Liability (id=13)` and `Other_Customer_Liability (id=21)` with sample balances; live balances fetched from `AcctgWf` via `sys_wp` | Cardholder float/liability is reconciled within the application |
| **Financial transaction amounts** | `OpenItems` rows: `Amount` (Decimal 19 precision), `Descr` (VARCHAR 8000) | Stored and displayed in the working database |
| **Document file paths** | `DocLink` stored as VARCHAR 900 (internal filesystem path, e.g., `F:\Daily_Recons1\...`) | Path leakage; documents may contain reconciliation evidence |
| **Error log** | `ErrorLog.cs` writes computer name, OS username, exception message, and stack trace to `<StartupPath>\Errors\errlog.txt` | Potential leakage of internal logic, usernames |
| **New user password (admin reset)** | `UserDetails.tbPassword_TextChanged` sends new password as `SqlDbType.VarBinary(256)` to `sys_user @action='resetpwd'` — inconsistently typed vs login flow (VarChar) | Possible double-encoding or no hashing |

---

## Encryption & Protection

| Area | Status |
|---|---|
| SQL connection encryption (TLS) | Not configured in client. Connection string uses `Server=<IP>;Database=...;User Id=raf;Pwd=[REDACTED — rotate immediately]` with no `Encrypt=true` or `TrustServerCertificate` flag. Wire encryption is unknown and likely absent. |
| Password hashing | SHA512 hashing code is **commented out** throughout `Login.cs` (lines 93–138 contain multiple commented `SHA512Managed` snippets). Passwords are sent and presumably stored without hashing. |
| Document files | No encryption; files are plain filesystem objects. Sign-off sets `FileAttributes.ReadOnly` on the file (`TaskDoc.cs` line 675) — this is access-control via OS attribute, not encryption. |
| Application manifest code signing | `AccountingWorkflow.csproj` line 16 references `AccountingWorkflow_TemporaryKey.pfx` with `SignManifests=false` — **manifest signing is disabled**. |
| Settings encryption | `app.config` stores `Server` IP in plaintext; no `System.Security.SecureString` or DPAPI usage. |
| Error log | Plaintext file, no encryption, no ACL enforcement in code. |

---

## Data Flow

```
[Client WinForms App]
        |
        | SQL Server Named Pipes / TCP (no TLS confirmed)
        v
[SQL Server @ 192.168.10.200]
   |---> AcctgWf         (primary application database — all workflow data)
   |---> ATLYS_E         (source GL — account import only)
   |---> ATLYS_RvCR      (secondary GL — referenced but no client code directly exercises it)

[Client Filesystem]
   <---> F:\Daily_Recons1\   (document attachments — read and linked by path)
   ---->  <StartupPath>\Errors\errlog.txt  (error log written by client)

[Excel COM]
   <---- AcctgWf (via ADODB recordset opened in AcctDetails.adReport() and WPForm)
   ----> User workstation Excel  (report rendered in Excel instance)

[Deploy/Install]
   \\devserv2\apps\AWf\   (ClickOnce-style UNC publish target — not an automated pipeline)
```

---

## Data Quality & Retention

1. **No client-side retention policy:** The application writes to the database indefinitely; no archiving or purging logic is visible in any form.
2. **No data validation beyond SP error returns:** Field widths in the SP parameters define maximum lengths (e.g., `@comment VARCHAR(8000)`, `@name VARCHAR(50)`), but no client-side length enforcement exists — truncation or SP errors are displayed via `MessageBox.Show(LReader["sError"])`.
3. **Amount precision:** Open items use `SqlDbType.Decimal` with precision 19 (`Com.Parameters.Add("@amount", SqlDbType.Decimal, 19)`), adequate for financial values.
4. **Date handling:** All dates are `SqlDbType.DateTime`; no timezone handling is present. Dates are local machine time (`DateTime.Now`, `DateTime.Today`).
5. **XML tree data:** The `assets.xml` and `liab.xml` files contain seed/sample data with hardcoded account numbers (`2343434`, `2343555`) and balances (`3445.56`, `5555.56`) — these appear to be test/placeholder values shipped with the application.
6. **Document links as paths:** `DocLink` stores a local or UNC filesystem path. If the file is moved or the drive mapping changes, the link becomes stale with no reconciliation mechanism.
7. **No soft-delete pattern confirmed:** Delete operations (`remove_doc`, `delete_tree`, etc.) are called without visible undo support.

---

## Compliance Gaps

| Gap | Regulatory Reference | Detail |
|---|---|---|
| Plaintext password transmission | PCI DSS v4.0 Req 8.3 (strong cryptography for authentication) | `Login.cs:106` — password sent as VarChar without hashing |
| Hardcoded shared database credentials | PCI DSS v4.0 Req 8.2.2 (no shared/generic accounts) | `SQLData.cs:34,56` — `raf`/`none` in source |
| Disabled code-signing | General software integrity; PCI DSS v4.0 Req 6.3 | `SignManifests=false` in `.csproj` |
| No SQL connection encryption | PCI DSS v4.0 Req 4.2 (encrypt transmission over open networks) | No `Encrypt=true` in connection string |
| No field-level encryption for cardholder-related balances | PCI DSS v4.0 Req 3 (protect stored account data) | `Cardholder_Liability` balances stored/reconciled in `AcctgWf` without evidence of encryption |
| Error log contains stack traces with usernames | GLBA / general data minimisation | `ErrorLog.cs:62-65` — computer name and OS user written to local file |
| No access control on local error log | General secure configuration | Directory created with default OS permissions |
| SHA512 hashing commented out | Suggests password hashing was planned but never activated | Multiple commented blocks in `Login.cs` |
