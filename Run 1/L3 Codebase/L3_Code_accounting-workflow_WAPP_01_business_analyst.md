# accounting-workflow_WAPP — Business Analyst View

## Business Purpose

AccountingWorkflow is an internal Windows desktop application (WinForms, .NET 3.5) that provides accounting staff with a structured, multi-company reconciliation and close-management platform. It was originally authored circa 2009 (AssemblyInfo.cs copyright 2009) and published to a UNC share (`\\devserv2\apps\AWf\`). The system supports two primary operating modes, selectable per-user:

- **Mode 1 (Financial Statements / "FinSt"):** Balance-sheet-oriented account reconciliation with workpaper preparation, review, and sign-off workflow.
- **Mode 2 (Task Monitor / "TaskMon"):** Day-level task tracking against configurable schedules for one or more companies.

The application connects to a Microsoft SQL Server instance at a hard-coded IP (`192.168.10.200`) and operates against three databases: `ATLYS_E`, `ATLYS_RvCR`, and `AcctgWf`.

---

## Business Capabilities

| Capability | Key Forms / Classes |
|---|---|
| User authentication and session management | `Login.cs`, `ChPwd.cs`, `UserAccess.cs`, `UserDetails.cs` |
| Multi-company selection | `TaskMon.cs` (`cbComp` combo), `TasksList.cs` |
| Task definition and enablement | `Task.cs`, `TasksList.cs` |
| Schedule management (daily/weekly/monthly) | `Schedule.cs`, `PickSched.cs`, `TasksOnSched.cs` |
| Daily task monitoring and completion | `TaskMon.cs` (`GetDayTasks`, `gvTasks_CellContentClick`) |
| Account list and type classification | `AcctList.cs` (calls `sys_accts`) |
| Account detail / transaction drill-down | `AcctDetails.cs` (calls `sys_wp`) |
| Financial statement tree maintenance | `StMaint.cs` (calls `sys_types`) |
| Workpaper preparation, review, sign-off | `WPForm.cs` (`btnPrepared_Click`, `btnReviewed_Click`, `btnSignedOff_Click`) |
| Document/attachment management per task | `TaskDoc.cs`, `NewDoc.cs` (calls `sys_docs`, `sys_tasks`) |
| Open-item tracking and clearing | `OpenItems.cs` (calls `sys_openitems`) |
| Notes and comment threads on workpapers | `Notes.cs`, `Comment.cs`, `NoteAccts.cs` (calls `sys_wp`) |
| Completion notes on tasks | `CompNote.cs` |
| Excel export of account details | `AcctDetails.adReport()`, `WPForm` via `Microsoft.Office.Interop.Excel` |
| User and group administration | `UserAccess.cs`, `UserDetails.cs` (calls `sys_user`, `sys_companies`) |
| Application settings | `AppSet.cs` (user preference: FinSt vs TaskMon launch mode) |
| Print and print-preview of task list | `TaskMon.DailyTasks_PrintPage`, `MDIParent1.btnPrint_Click` |

---

## Business Entities

| Entity | Evidence |
|---|---|
| **User / Session** | `sys_user` SP with actions: `login`, `logout`, `changepwd`, `resetpwd`, `enable`, `disable`, `resetlocked`, `list`, `detail`, `list_groups`, `update`. Session ID (`s_id`) is a VARCHAR(50) token passed on every call. |
| **Company** | `sys_companies` SP: `list`, `list_access`, `add_access`, `remove_access`. Companies identified by a `company_id` (SmallInt). The `MDIParent1` holds `cid` and `comp` as global state. |
| **Account** | `sys_accts` SP: `list`, `types`, `update`, `import_accts`. Columns include `AcctNum`, `AcctDescr`, `AcctType`, `AcctId`. |
| **Account Type / FS Structure** | `sys_types` SP with tree operations (`tree`, `add_node`, `update_node`, `delete_tree`, `delete_node`, `move_tree`). Structure seeds from `assets.xml` and `liab.xml` shipped with the application. |
| **Task** | `sys_tasks` SP: `details`, `update`, `list`, `list_c`, `list_users`, `list_users_c`, `list_docs`, `list_comments`, `new_doc`, `new_comment`, `remove_doc`, `taskhist_details`, `complete`. Task has name, enabled flag, company, assigned user, WP type link. |
| **Schedule** | `sys_schedules` SP: `list_sched`, `list_freqid`, `list_freqonid`, `update_sched`, `pick_sched`, `list_tasks`. Frequency types: Daily, Weekly, Monthly (with "The Nth weekday" variant). |
| **Task History / Completion** | `HistId` column returned by `sys_tasks`; `status_month` action returns daily colour-coded status across a calendar month. |
| **Workpaper (WP)** | `sys_wp` SP: `new_wp`, `list_acctscomm`, `list_comments`, `new_comment`, `clear`, `update_commentsaccts`, `list_commentsaccts`. WP has `WpId` (BigInt), `WpTypeId`, `WpStatus` (PREPARED / REVIEWED / CLOSED), `NCComments`. |
| **Document** | `sys_docs` SP: `list_attachments`, `update`, `prepare_doc`, `review_doc`, `sign_doc`, `add_attachment`, `move_attachments_tree`, `remove_attachment`, `remove_attachments_tree`, `update_attachment`, `getdescr`, `getattdescr`. Each doc has PrepareBy/Dt, ReviewBy/Dt, SignBy/Dt. |
| **Open Item** | `sys_openitems` SP: `list_items`, `list_notes`, `new_item`, `update_item`, `clear`, `total_items`, `new_note`. Items have date, amount, description, P&L flag, clear flag. |
| **Group** | Referenced in `UserDetails.cs` via `list_groups`; drives access control. |

---

## Business Rules & Validations

1. **Login gate:** Application launches a `Login` form immediately inside `MDIParent1_Load`. If `pwd_expired == 1`, user is forced to `ChPwd` before any other form opens (`Login.cs` line 144–152).
2. **Password change validation:** `ChPwd.cs` requires old password, new password, and confirmation to be non-empty and new == confirm before calling the SP.
3. **Password expiry enforcement:** The `pwd_expired` byte is returned from `dbo.sys_user` with action `login`; the client enforces the redirect.
4. **Session token propagation:** Every stored procedure call passes `@s_id` (the session ID), enabling server-side session validation and audit.
5. **Company-scoped data access:** Every data-retrieval SP call includes `@company_id`; the current company is held globally in `MDIParent1.Cid`. Switching company in `TaskMon.cbComp_SelectionChangeCommitted` closes all other MDI children.
6. **Task completion note:** `TaskMon.gvTasks_CellContentClick` requires a `CompNote` dialog before calling `sys_tasks` with action `complete`.
7. **Workpaper status progression:** Prepare → Review → Sign-off is enforced in sequence. `WPForm.btnReviewed_Click` checks `!btnPrepared.Enabled` before allowing review. Sign-off makes the document file read-only (`FileInfo.Attributes = FileAttributes.ReadOnly` in `TaskDoc.cs` line 675).
8. **Document prepare-before-review-before-sign gate:** `WPForm.btnPrepared_Click` checks that all rows have a `Prept` value; same check for `Revt` before `btnReviewed_Click`.
9. **Account type update:** `AcctList.gvAcctList_CellEndEdit` supports bulk update of multiple selected rows in one operation.
10. **Open-item new entry validation:** `OpenItems.gvItem_RowLeave` requires date, amount, and description to be non-empty before persisting.
11. **User enable/disable/lock:** `UserDetails.cs` fires SPs `enable`, `disable`, `resetlocked` immediately on checkbox change — no deferred save.
12. **External user read-only:** `UserDetails.GetData` line 100 disables all controls when `ExtType != 0` (external authentication).

---

## Business Flows

### Authentication Flow
1. `MDIParent1_Load` launches `Login` form.
2. User enters credentials; `BW_DoWork` calls `dbo.sys_user @action='login'`.
3. If `pwd_expired=1` → `ChPwd` shown. After successful change → `TaskMon` shown.
4. If mode is `Appr=1` → `Balance` (FinSt mode); `Appr=2` → `TaskMon` (task-monitor mode).
5. On application close, `MDIParent1_FormClosing` calls `dbo.sys_user @action='logout'` with the session ID.

### Task Completion Flow (Task Monitor Mode)
1. User selects date on calendar (`TaskCal`) or mini-calendar (`mCal`).
2. `GetDayTasks` loads tasks for that date into `gvTasks`.
3. `ChStatus` colours rows: green = COMPLETED, red = NOT COMPLETED.
4. User checks the `Complete` checkbox; `CompNote` dialog collects a note.
5. `sys_tasks @action='complete'` is called; result updates status, completed-by, and completed-date cells.

### Workpaper Lifecycle Flow (FinSt Mode)
1. User navigates to account; `WPForm` opened with `WpId`.
2. Documents added with `NewDoc`; each document prepared via `sys_docs @action='prepare_doc'`.
3. After all docs prepared, `btnPrepared_Click` fires `sys_wp @action='prepare'`, captures a `Comment`.
4. Reviewer clicks Review; `sys_wp @action='review'` called.
5. Sign-off via `sys_wp @action='close'`; signed documents become read-only on the filesystem.
6. `Notes` form used for non-conformance comments, each tied to one or more accounts.

### Account Import Flow
`AcctList.btnImpAcct_Click` calls `sys_accts @action='import_accts'` which presumably imports from `ATLYS_E` or `ATLYS_RvCR` into `AcctgWf`.

---

## Compliance & Regulatory Concerns

1. **Cardholder Liability in chart-of-accounts:** `liab.xml` contains a `Cardholder_Liability` node (id=13) and `Other_Customer_Liability` (id=21). These are balance-sheet categories with placeholder amounts, indicating the application reconciles accounts that include cardholder float — directly relevant to Onbe's prepaid card business.
2. **Credential handling (plaintext):** `Login.cs` line 106 passes the raw password text directly as `@pwd` to SQL Server: `pwd.Value = PasswordTextBox.Text.Trim()`. This is transmitted over the SQL wire in cleartext.
3. **Hardcoded database credential:** `SQLData.cs` lines 34 and 56 embed `User Id=raf;Pwd=none` in the connection string in source code. This is a PCI DSS v4.0 Requirement 8 violation (shared/hardcoded credentials).
4. **No MFA / RBAC in the client:** User identity is enforced entirely by the server-side stored procedures; no client-side role enforcement exists.
5. **File path exposure:** `TaskDoc.cs` and `NewDoc.cs` default to `F:\Daily_Recons1` as the initial file dialog directory — this UNC or local path may contain reconciliation evidence files.
6. **Error log on local disk:** `ErrorLog.WriteToErrorLog` writes stack traces containing internal logic to `<StartupPath>\Errors\errlog.txt` without access controls.
7. **Audit trail:** Session IDs are passed to every SP, providing a server-side audit trail per the stored-procedure design; however, the client-side error log may expose session or user data.
8. **Password storage:** `UserDetails.tbPassword_TextChanged` sends the password as `SqlDbType.VarBinary` to `resetpwd` SP — contradicted by other flows that use VarChar(50/256), suggesting inconsistent hashing.

---

## Business Risks

1. **Single point of failure — IP-hardcoded server:** `app.config` and `Settings.settings` both hardcode `192.168.10.200`. A server migration or IP change requires a redeployment of the client application.
2. **Plaintext password transmission:** Passwords travel in cleartext on the SQL connection; TLS on the SQL connection is not confirmed in source.
3. **Hardcoded shared database credential:** `raf`/`none` is embedded in source; any developer or user with access to the binary or code can extract it.
4. **No input sanitisation beyond stored-procedure parameterisation:** All DB calls use parameterised SPs (no SQL injection risk from C# code), but no field-length enforcement at the UI layer for most fields.
5. **Excel COM dependency:** `AcctDetails.adReport()` and `WPForm` invoke `Microsoft.Office.Interop.Excel`, requiring Microsoft Office installed on each client. Versioning mismatch will crash exports.
6. **ADODB legacy COM dependency:** Both `SQLData.ADODBConn` and `AcctDetails.adReport()` use ADODB COM interop, a technology deprecated since .NET 1.x.
7. **Manual publish to UNC share:** No automated CI/CD; publish URL `\\devserv2\apps\AWf\` is checked into the project file.
8. **No automated testing:** No test projects or test frameworks are present in the solution.
