# accounting-workflow_WAPP — Enterprise Architect View

## Platform Generation (Gen-1 / Gen-2 / Gen-3)

**Classification: Gen-1**

Evidence basis:
- .NET Framework 3.5 (released 2007; end of mainstream support 2013). The solution is formatted for Visual Studio 2010.
- Windows Forms (WinForms) desktop UI; MDI (Multiple Document Interface) pattern.
- Direct SQL Server connectivity via `System.Data.SqlClient` and legacy ADODB COM PIA — no ORM, no service layer, no REST/SOAP API surface.
- Hardcoded IP address for the database server; no service discovery, no environment abstraction.
- Manual UNC-share deployment (ClickOnce variant); no container, no cloud, no pipeline.
- COM automation dependencies (ADODB, Microsoft.Office.Interop.Excel, IWshRuntimeLibrary).
- AssemblyInfo copyright 2009; version 1.0.0.46 after approximately 46 manual releases.
- No dependency injection, no async/await, no modern .NET patterns.
- The `ehash` project referenced in the solution but missing from the repository suggests an aborted attempt to introduce password hashing — the SHA512 code in `Login.cs` is entirely commented out.

This is a first-generation internal tool built directly against a SQL Server database with no architectural separation between presentation, business logic, and data access.

---

## Business Domain

**Finance / Accounting Operations — Internal Tool**

The application sits within Onbe's internal finance and accounting function. Specific sub-domains served:

| Sub-domain | Forms / Features |
|---|---|
| Accounting close management | `TaskMon`, `TasksList`, `Task`, `Schedule` — daily task tracking against close schedules |
| Balance sheet reconciliation | `Balance` (referenced in code but form not present in repo), `AcctList`, `AcctDetails`, `WPForm`, `StMaint` — workpaper lifecycle |
| Cardholder liability reconciliation | `liab.xml` contains `Cardholder_Liability (id=13)` and `Other_Customer_Liability (id=21)`; these accounts are reconciled through the workpaper workflow — directly tied to Onbe's prepaid card business |
| Open item management | `OpenItems` — tracking and clearing of unresolved general ledger items |
| User and company access administration | `UserAccess`, `UserDetails` |

The application bridges data from production GL systems (`ATLYS_E`, `ATLYS_RvCR`) into an accounting workflow database (`AcctgWf`), enabling reconcilers to classify accounts, attach supporting documents, prepare and review workpapers, and track completion status.

---

## Role in Platform

AccountingWorkflow is an **internal operational tool** with no customer-facing functions. It is not part of the payment processing or disbursement pipeline. Its role in the Onbe platform:

1. **Reconciliation consumer:** Imports account data from the production GL (`ATLYS_E`) via `sys_accts @action='import_accts'`. It reads but does not write back to the production GL.
2. **Close-process orchestrator:** Provides the scheduling and task-completion tracking layer for the monthly/periodic accounting close, particularly for accounts that include cardholder float and liability.
3. **Evidence store:** Documents (prepare/review/sign-off) and workpapers stored in `AcctgWf` constitute the evidentiary record of reconciliation completeness, which may be referenced in SOC 1 / SOC 2 audits.
4. **Isolated island:** No API surface, no event bus, no message queue integration. The application is a standalone island connected only to SQL Server.

---

## Dependencies

### Upstream (data consumed from)
| System | Data | Interface |
|---|---|---|
| `ATLYS_E` (production GL) | Chart of accounts, transaction data | SQL Server stored procedure (`sys_accts @action='import_accts'` executes server-side cross-database query) |
| `ATLYS_RvCR` (secondary GL) | Unknown; connection string defined but not directly called from client code | SQL Server |

### Downstream (data produced for)
| Consumer | Data | Interface |
|---|---|---|
| Microsoft Excel (on client workstation) | Account detail reports, workpaper exports | COM automation via `Microsoft.Office.Interop.Excel` |
| Local filesystem | Document attachments linked by path | `F:\Daily_Recons1\` directory |
| External auditors (indirect) | Workpaper completion evidence stored in `AcctgWf` | Manual extraction / screen review |

### Runtime dependencies
| Component | Version | Risk |
|---|---|---|
| .NET Framework 3.5 SP1 | 3.5 | End of extended support; requires Windows feature enablement |
| SQL Server | Unknown | Single instance at `192.168.10.200` |
| Microsoft Office / Excel | 11.0 (2003 PIA) | Very old; may conflict with modern Office installs |
| ADODB COM PIA | 7.0.3300.0 | Deprecated since .NET 1.x; fragile on modern Windows |
| `SchCalendar.dll` | 1.0.0.0 | External control not in repository |
| Windows Script Host | 1.0 | Used only for shortcut creation in `Install` project |

---

## Integration Patterns

| Pattern | Evidence | Assessment |
|---|---|---|
| **Direct database coupling** | All data access via `SqlConnection` + stored procedures in `SQLData.Conn()` | Tight coupling to SQL Server; no service layer |
| **Stored-procedure action pattern** | Single SP per domain (e.g., `sys_tasks`, `sys_wp`, `sys_user`) with `@action` parameter routing to different logic branches | Centralises business logic in the database; client is thin orchestrator |
| **Session token passing** | `@s_id` VARCHAR(50) passed on every call | Rudimentary stateless-style session management within a stateful desktop app |
| **XML reader from SQL** | `StMaint.GetTree()` and `TaskDoc.GetTree()` use `Command.ExecuteXmlReader()` for hierarchical tree data | SQL Server FOR XML path used server-side |
| **COM automation** | `AcctDetails.adReport()` opens ADODB connection and calls Excel COM | Legacy integration with no API equivalent |
| **Filesystem as document store** | `DocLink` paths stored in DB; files read directly from local/network path | No document management system; no versioning |
| **MDI child update broadcast** | After save operations, parent form iterates `MdiChildren` and calls typed update methods (e.g., `((TaskMon)child).daytasksupdate()`) | Ad-hoc inter-form messaging; tight coupling between form classes |
| **UNC share deployment** | `\\devserv2\apps\AWf\` publish target | No container registry, no artifact repository |

---

## Strategic Status

**Status: End-of-Life / Retirement Candidate**

| Factor | Assessment |
|---|---|
| Technology currency | .NET 3.5 WinForms is a 15+ year old technology stack; Microsoft has de-emphasised WinForms for internal business applications. |
| Security posture | Multiple critical security deficiencies (plaintext passwords, hardcoded credentials, disabled code-signing) make this application non-compliant with current PCI DSS v4.0 requirements without significant remediation. |
| Maintainability | Single-file God-Forms with embedded SQL calls; no layering; no tests. |
| Operational model | Manual deployment to UNC share; no CI/CD; no monitoring. |
| Platform fit | Isolated island with no API surface; cannot participate in event-driven or microservice architectures. |
| Business criticality | Reconciles cardholder liability accounts — relevant to financial reporting accuracy and SOC 1 / SOC 2 scope. |
| Replacement readiness | No documented replacement identified in this codebase; however, the application's scope is narrow enough to be replaced by a modern web-based close-management tool. |

---

## Migration Blockers

| Blocker | Detail | Effort |
|---|---|---|
| **No API layer** | All business logic is in SQL Server stored procedures (`sys_tasks`, `sys_wp`, `sys_user`, etc.). A migration requires either extracting SP logic into a service or rewriting it. | High |
| **ADODB COM dependency** | `AcctDetails.adReport()` and `WPForm` use ADODB recordsets to feed Excel. Replacing requires either a new reporting mechanism or an ADODB-free Excel export library. | Medium |
| **Excel COM automation** | Direct Excel `ApplicationClass` manipulation. No replacement report format is defined. | Medium |
| **Hardcoded server IP** | `192.168.10.200` is in both `app.config` and `Settings.settings`. Migration to a new DB server or cloud SQL requires config changes and redeployment to all clients. | Low (config) |
| **`SchCalendar.dll` custom control** | External binary not in the repository; source unknown. A web migration must replace this calendar UI component. | Medium |
| **Filesystem document store** | Documents stored as local/UNC paths (`F:\Daily_Recons1\`). Migration requires a document management system or blob store and data migration of all existing path references. | High |
| **Stored-procedure business logic** | All validation, access control, and state transitions are in the SP layer of `AcctgWf`. Full inventory and extraction of SP logic is required before decommission. | High |
| **Session management model** | Current `s_id` VARCHAR(50) token model is ad-hoc. A web platform requires OAuth2/OIDC or equivalent. | Medium |
| **Multi-company state in MDI parent** | `MDIParent1` holds `cid`, `sid`, and `comp` as mutable global state shared across all child forms. A stateless web architecture requires this to move to request context or user session. | Medium |
| **Password handling** | SHA512 code is commented out; plaintext passwords in the pipeline. Must implement proper credential hashing before any migration that retains the user store. | High (security-critical) |
