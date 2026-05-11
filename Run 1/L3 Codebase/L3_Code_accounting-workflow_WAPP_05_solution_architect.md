# accounting-workflow_WAPP — Solution Architect View

## Technical Architecture

### Stack Summary
| Layer | Technology |
|---|---|
| UI framework | Windows Forms (WinForms), .NET Framework 3.5, MDI pattern |
| Language | C# 3.0 (targeting .NET 3.5) |
| Concurrency | `BackgroundWorker` (`BW`) used only in `Login.cs`; all other DB calls are synchronous on the UI thread |
| Data access | `System.Data.SqlClient` (parameterised `SqlCommand` + stored procedures); legacy `ADODB.Connection` / `ADODB.Command` for Excel report path |
| Database | Microsoft SQL Server (version unknown), three databases: `ATLYS_E`, `ATLYS_RvCR`, `AcctgWf` |
| Report output | `Microsoft.Office.Interop.Excel v11.0` (Office 2003 PIA) via COM automation |
| Document management | Filesystem paths stored as VARCHAR(900) in database; `System.Diagnostics.Process.Start` to open files |
| XML parsing | `System.Xml.XmlDocument` + `Command.ExecuteXmlReader()` for hierarchical tree data |
| External controls | `SchCalendar.dll` v1.0.0.0 (custom calendar), `Microsoft.VisualBasic.PowerPacks.Vs v10.0` |
| Installer | `IWshRuntimeLibrary` (WSH COM) for shortcut creation; legacy `.vdproj` MSI; ClickOnce UNC publish |

### Architectural Pattern
The application is a **Monolithic WinForms Fat Client** with an **Action-Dispatcher Stored Procedure** pattern on the backend. There are three effective layers:

1. **Presentation:** WinForms forms (all in the `AccountingWorkflow` namespace). Forms contain all presentation logic, event handlers, and data-access calls directly. No separation between controller and view.
2. **Data access shim:** `SQLData.cs` is the only shared class; it provides a `Conn(int)` factory and an `ADODBConn(int)` factory. No DAL, repository, or service classes exist.
3. **Business logic in SQL:** All domain rules, validation, access control, and state transitions are implemented inside stored procedures on the `AcctgWf` database (`sys_user`, `sys_tasks`, `sys_wp`, `sys_docs`, `sys_schedules`, `sys_types`, `sys_accts`, `sys_openitems`, `sys_companies`).

### Form Inventory
| Form Class | Purpose |
|---|---|
| `MDIParent1` | Shell MDI container; holds global `sid`, `cid`, `comp`, `opt` state; routes menu commands |
| `Login` | Credential entry; background-worker async login; routes to `Balance` or `TaskMon` based on `Appr` setting |
| `ChPwd` | Forced or voluntary password change |
| `TaskMon` | Primary task-monitor mode view; calendar + day-task grid; task completion; schedule/workpaper navigation |
| `TasksList` | Full task list by company/user; CRUD entry point for `Task` |
| `Task` | Task create/edit; schedule association (`PickSched`, `TasksOnSched`) |
| `Schedule` | Schedule create/edit (daily/weekly/monthly); frequency picker |
| `PickSched` | Schedule selection dialog for assigning to a task |
| `TasksOnSched` | View tasks assigned to a given schedule |
| `TaskDoc` | Document and attachment management per task history entry; prepare/review/sign workflow |
| `WPForm` | Workpaper form; document rows with prepare/review/sign-off; notes; Excel export |
| `AcctList` | Account list for a company; account type assignment; bulk update |
| `AcctDetails` | Transaction detail for a specific account; date-range filter; Excel export |
| `OpenItems` | Open-item entry, P&L classification, clearing, and notes |
| `StMaint` | Financial statement tree editor (drag-drop); calls `sys_types` |
| `Notes` | Workpaper non-conformance comments with account linkage |
| `NoteAccts` | Popup to reassign account associations on a note |
| `Comment` | Rich-text comment entry dialog; optionally persists to `sys_wp` |
| `CompNote` | Simple completion note dialog (task completion) |
| `NewDoc` | File picker + description dialog for adding documents |
| `UserAccess` | User list; entry point to `UserDetails` |
| `UserDetails` | User create/edit; group assignment; company access; enable/disable/lock; password reset |
| `AppSet` | Application settings: mode switch (FinSt/TaskMon), colour preferences |
| `PBForm` | Progress bar shown during login background operation |
| `Form1` | Stub form (no logic in `Form1.cs`); appears unused |
| `Attach` | Stub form (no logic in `Attach.cs`); appears unused |
| `DatePickerColumn` | Custom `DataGridViewColumn` subclass for date-picker cells |
| `ErrorHandler` | Hooks `Application.ThreadException` and `AppDomain.UnhandledException`; delegates to `ErrorLog` |
| `ErrorLog` | Static helper to write error details to `<StartupPath>\Errors\errlog.txt` |
| `SQLData` | Static connection factory: `Conn(int)` → `SqlConnection`, `ADODBConn(int)` → `ADODB.Connection` |

---

## API Surface

**There is no API surface.** The application exposes no REST endpoints, SOAP services, gRPC, or message-queue interfaces. All interaction is:

- Inbound: User input via WinForms controls.
- Outbound: Direct SQL Server stored procedure calls and COM automation.

The stored-procedure "API" on the `AcctgWf` database is the closest thing to an interface contract:

| Stored Procedure | Actions (as observed from client code) |
|---|---|
| `dbo.sys_user` | `login`, `logout`, `changepwd`, `resetpwd`, `enable`, `disable`, `resetlocked`, `list`, `detail`, `update`, `list_groups` |
| `sys_companies` | `list`, `list_access`, `add_access`, `remove_access`, `add_accees` (sic) |
| `sys_accts` | `list`, `types`, `update`, `import_accts` |
| `sys_types` | `tree`, `add_node`, `update_node`, `delete_tree`, `delete_node`, `move_tree` |
| `sys_tasks` | `details`, `update`, `list`, `list_c`, `list_users`, `list_users_c`, `list_docs`, `list_comments`, `new_doc`, `new_comment`, `remove_doc`, `complete`, `taskhist_details`, `status`, `status_month`, `new_comment` |
| `sys_tasks_execsched` | (no action param) — called from `TaskMon.Execsched()` which is commented out at call site |
| `sys_schedules` | `list_sched`, `list_freqid`, `list_freqonid`, `update_sched`, `pick_sched`, `list_tasks` |
| `sys_wp` | `new_wp`, `list_acctscomm`, `list_comments`, `new_comment`, `clear`, `update_commentsaccts`, `list_commentsaccts`, `prepare`, `review`, `close` (inferred from `GetStatus` calls in `WPForm`) |
| `sys_docs` | `list_attachments`, `update`, `prepare_doc`, `review_doc`, `sign_doc`, `add_attachment`, `move_attachments_tree`, `remove_attachment`, `remove_attachments_tree`, `update_attachment`, `getdescr`, `getattdescr` |
| `sys_openitems` | `list_items`, `list_notes`, `new_item`, `update_item`, `clear`, `total_items`, `new_note` |

All SPs follow the pattern: accept `@s_id` (session token) + `@action` (routing) + `@company_id` (scope) + domain-specific parameters; return a result set with an `sError` column (empty string = success; non-empty = error message to display).

---

## Security Posture

### Critical Findings

| Finding | Severity | Location |
|---|---|---|
| **Plaintext password on wire** | Critical | `Login.cs:106` — `pwd.Value = PasswordTextBox.Text.Trim()` passed as `VarChar(256)` to SQL; SHA512 hash code commented out in lines 93–138 |
| **Hardcoded shared database credentials** | Critical | `SQLData.cs:34,56` — `User Id=raf;Pwd=[REDACTED — rotate immediately]` in connection string; cannot be rotated without recompile and redeployment |
| **No TLS on SQL connection** | Critical | Connection string has no `Encrypt=true`; `SQL Native Client` ODBC driver used for ADODB path |
| **Disabled assembly signing** | High | `AccountingWorkflow.csproj:19` — `<SignManifests>false</SignManifests>`; no code integrity verification |
| **Local error log with sensitive data** | Medium | `ErrorLog.cs:62-65` — writes OS username, computer name, and full stack traces; no ACL enforcement |
| **Debug MessageBox.Show in production code** | Medium | `AcctList.cs:88` — `MessageBox.Show(gvAcctList.Rows[e.RowIndex].Cells["AcctType"].Value.ToString())` left in production; `UserDetails.cs:172` — `MessageBox.Show(dsUser.Tables[0].Rows[0]["uid"].ToString())` debug popup on form closing |
| **No client-side RBAC** | Medium | `MDIParent1.Opt` controls menu visibility but this is purely cosmetic; all access control is SP-side only |
| **Password transmitted to reset SP as VarBinary(256) vs VarChar(256) inconsistency** | Medium | `UserDetails.cs:211` — reset uses `SqlDbType.VarBinary`; login uses `SqlDbType.VarChar(256)` — likely indicates no consistent hashing |
| **`Process.Start` with user-supplied path** | Medium | `TaskDoc.cs:691` — `Process.Start(gvDoc[DocLink.Index,e.RowIndex].Value.ToString())` — opens arbitrary filesystem path stored in database |
| **`FileAttributes.ReadOnly` as access control** | Low | `TaskDoc.cs:675` — setting file to read-only as "sign-off" protection; trivially bypassed by any user with write permissions to the directory |
| **`TrustUrlParameters=true`** | Low | `AccountingWorkflow.csproj:39` — ClickOnce parameter trust enabled |

### Authentication Summary
- Custom username/password stored in `AcctgWf` database.
- No multi-factor authentication.
- Password expiry enforced by `pwd_expired` byte from login SP.
- Account lockout via `LockedOut` column; admin unlocks via `UserDetails.chbLock_CheckedChanged → sys_user @action='resetlocked'`.
- External users (`ExtType != 0`) are treated as read-only in the UI.
- Session token (`s_id`) is an opaque VARCHAR(50) generated server-side.

---

## Technical Debt

| Category | Specific Debt | Location |
|---|---|---|
| **Commented-out code** | SHA512 hashing — planned but never activated | `Login.cs:93-138` (multiple commented blocks) |
| **Commented-out exception handlers** | `try/catch` blocks commented out in `Program.cs:17-30` and `MDIParent1_Load:37-64`; `ErrorHandler` exists but top-level exception handling is bypassed | `Program.cs`, `MDIParent1.cs` |
| **Debug MessageBox.Show calls** | Two confirmed in production code paths | `AcctList.cs:88`, `UserDetails.cs:172` |
| **Commented-out alternate code paths** | Multiple fragments of alternative implementations left in files | Throughout `Login.cs`, `MDIParent1.cs`, `TaskMon.cs`, `TaskDoc.cs` |
| **Typo in SP action name** | `add_accees` (missing 's') used in `UserDetails.cs:151` | `UserDetails.cs:151` |
| **Typo in form name check** | `case "TasksLiist"` (extra 'i') in `Task.btnOK_Click` — this case will never match the real form name `"TasksList"` | `Task.cs:352` |
| **`Form1` and `Attach` stub forms** | Empty form classes with no logic; appear to be scaffolding leftovers | `Form1.cs`, `Attach.cs` |
| **`ehash` project missing** | Referenced in `AccountingWorkflow.sln` but directory absent from repository | Solution file line 10 |
| **God-Form pattern** | All DB calls, event handlers, and display logic colocated in each Form class; no separation of concerns | All form files |
| **No null checks on MDI parent casts** | `((MDIParent1)this.MdiParent)` cast is unchecked throughout; if form is shown outside MDI context it throws | Every form file |
| **ADODB dependency** | Legacy COM PIA used alongside modern `SqlClient`; two code paths for DB access | `SQLData.cs:39-59`, `AcctDetails.cs:88-162` |
| **Synchronous DB on UI thread** | All forms except `Login` block the UI thread during database operations | All forms except `Login.cs` |
| **`sys_tasks_execsched` dead call** | `TaskMon.Execsched()` exists but is commented out at call site in `TaskMon_Load:36` | `TaskMon.cs:36,137-146` |
| **`vdproj` duplicated** | Both `AWSetup\AWSetup.vdproj` and `AWSSetup\AWSSetup.vdproj` present with no clear distinction | Solution root |
| **Hardcoded document directory** | `"F:\\Daily_Recons1"` in three places | `TaskDoc.cs:346,703`, `NewDoc.cs:48` |
| **XML seed files contain placeholder data** | `liab.xml` has hardcoded account numbers `2343434`/`2343555` and balances `3445.56`/`5555.56` | `liab.xml:7-53` |

---

## Gen-3 Migration Requirements

A migration to a Gen-3 (cloud-native, API-first, containerised) platform requires addressing the following:

### Must-Have (Blockers)

1. **Extract stored-procedure business logic into an application service layer.** All `sys_*` SPs contain domain logic that must be catalogued, documented, and reimplemented in a service (e.g., .NET 8 Web API or similar). The `@action` routing pattern can guide decomposition into individual endpoint methods.

2. **Implement proper credential management.** Replace `raf`/`none` hardcoded credentials with a secrets manager (Azure Key Vault, AWS Secrets Manager, or HashiCorp Vault). Rotate the `raf` database account immediately.

3. **Implement password hashing.** The commented SHA512 code must be activated or replaced with bcrypt/PBKDF2. Existing passwords in `AcctgWf` must be rehashed as part of migration.

4. **Replace COM automation (Excel, ADODB).** Use a non-COM reporting library (e.g., ClosedXML, EPPlus) or a reporting service (SSRS, Power BI Embedded) for Excel output.

5. **Migrate document storage to a managed blob store** (Azure Blob Storage, S3, or equivalent). Replace filesystem path references with URIs and implement access-controlled document retrieval. Existing `F:\Daily_Recons1` content requires migration.

6. **Enable TLS on all database connections.** Configure `Encrypt=true; TrustServerCertificate=false` (or CA-validated certificate) for all SQL Server connections.

### Should-Have (High Priority)

7. **Replace WinForms MDI with a web UI.** A React, Angular, or Blazor frontend would provide the calendar, task grid, tree editor, and workpaper lifecycle views.

8. **Replace custom session token with OAuth2/OIDC.** Integrate with an identity provider (Azure AD, Okta) for SSO and MFA.

9. **Containerise the application tier.** Separate the API service from the database; deploy via container orchestration (AKS, ECS) with proper secrets injection.

10. **Replace `SchCalendar.dll`** with a modern open-source or licensed calendar component.

11. **Implement structured logging** (Serilog / Application Insights / CloudWatch) to replace the plain-text `errlog.txt`.

12. **Add database connection string configuration** via environment variables or secrets manager; remove all compile-time IP embedding.

### Nice-to-Have

13. **Introduce an ORM or micro-ORM** (Entity Framework Core, Dapper) to replace raw `SqlCommand` / `SqlDataAdapter` patterns.

14. **Add automated test coverage** for domain logic extracted from SPs.

15. **Implement soft-delete pattern** across entities to support audit trails and data recovery.

16. **Implement proper RBAC** at the application service layer, not just cosmetic UI hiding.

---

## Code-Level Risks

| Risk | Severity | File : Line | Detail |
|---|---|---|---|
| `Process.Start` with DB-sourced path | High | `TaskDoc.cs:691` | Opens arbitrary file from a path stored in the database. If the path is tampered with (e.g., `cmd.exe`), arbitrary process execution results. |
| `FileAttributes.ReadOnly` sign-off bypass | Medium | `TaskDoc.cs:675` | Setting read-only attribute is not a meaningful access control; any user with directory write permission can clear it. |
| SQL connection string in memory | High | `SQLData.cs:34,56` | Connection string with `raf`/`none` constructed at runtime; visible in memory dumps and process inspection tools. |
| Unchecked MDI parent cast | Medium | All form files | `((MDIParent1)this.MdiParent)` throws `InvalidCastException` or `NullReferenceException` if form lifecycle differs from expectation. |
| `TasksLiist` typo — dead code branch | Low | `Task.cs:352` | The `case "TasksLiist"` branch in `btnOK_Click` never executes; `TasksList` is never refreshed after saving a task from this path. Functional defect. |
| ADODB `cnn.Open` with `raf`/`none` visible | High | `SQLData.cs:56-58` | Same credential embedded in ADODB connection string passed to COM layer; COM layer may log or expose this string. |
| Debug `MessageBox.Show(uid)` on form close | Medium | `UserDetails.cs:172` | `MessageBox.Show(dsUser.Tables[0].Rows[0]["uid"].ToString())` fires every time `UserDetails` is closed, exposing internal user ID to the screen. |
| Synchronous DB calls on UI thread | Medium | All forms except `Login.cs` | Long-running queries will freeze the application; no cancellation support; multiple simultaneous SP calls from one form are serial. |
| Password VarChar/VarBinary inconsistency | High | `Login.cs:104` vs `UserDetails.cs:211` | Login sends password as VarChar(256); reset sends as VarBinary(256). If the SP hashes or stores differently based on type, password comparison will fail silently or operate on different encodings. |
| `acct` string comma-removal without guard | Low | `Notes.cs:203`, `Notes.cs:424` | `acct.Remove(acct.LastIndexOf(","))` throws `ArgumentOutOfRangeException` if `acct` is empty (no accounts selected). |
| No `SqlDataReader.Close()` before `SqlConnection.Close()` | Low | Multiple forms | Pattern `Conn.Close()` called while `LReader` is open; relies on connection close to implicitly close reader. Causes "connection still open" warnings under some pooling conditions. |
| `adodb.dll` hint path to developer machine | Build-breaking | `AccountingWorkflow.csproj:70` | `HintPath` points to `C:\...\Program Files\Microsoft.NET\Primary Interop Assemblies\adodb.dll`; build will fail if GAC does not contain this assembly. |
| Excel `ApplicationClass` COM object not released | Medium | `AcctDetails.cs:118-158` | `Excel.Application xl` and workbook/worksheet COM objects are not explicitly released (no `Marshal.ReleaseComObject`); orphaned Excel processes will accumulate. |
