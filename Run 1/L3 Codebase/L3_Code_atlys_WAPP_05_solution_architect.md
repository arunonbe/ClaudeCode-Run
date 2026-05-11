# atlys_WAPP — Solution Architect View

## Technical Architecture

The application is a classic 2-tier RPC client-server architecture with an OLAP query layer:

```
┌─────────────────────────────────────────────────────┐
│  CLIENT TIER (Browser + Silverlight 4.0 Plugin)     │
│  AtlysSL.xap (Silverlight application)              │
│                                                     │
│  App.xaml.cs (Application entry point)             │
│  MainPage.xaml.cs (Shell, navigation, menu)        │
│  70+ Views/*.xaml (XAML pages and child windows)   │
│  Converters/ (12 IValueConverter classes)          │
│  Enc.cs (AES client-side encryption)               │
│  wsdAtlys proxy (WCF client stub, auto-generated)  │
│  wsdReporting proxy (WCF client stub)              │
└──────────────────┬──────────────────────────────────┘
                   │ WCF custom binding
                   │ binaryMessageEncoding + httpTransport
                   │ (HTTP, NOT HTTPS)
┌──────────────────▼──────────────────────────────────┐
│  SERVICE TIER (IIS, ASP.NET 4.0, .NET Framework)   │
│                                                     │
│  wsAtlys.svc.cs (~6069 lines, 60+ [OperationContract]) │
│  wsReporting.svc.cs (~large, 20+ operations)       │
│  SQLData.cs (connection factory, 3 DB targets)     │
│  Items/ (28 [DataContract] DTOs)                   │
│  C2Xls/ (custom Excel XML writer)                  │
└──────────────────┬──────────────────────────────────┘
                   │ ADO.NET Integrated Security
                   │ SqlConnection + SqlCommand + StoredProcedure
┌──────────────────▼──────────────────────────────────┐
│  DATA TIER (SQL Server ppamwdcdifsql1\ppamwdcdifsql1) │
│                                                     │
│  ATLYS_E      (core entities, users, companies)    │
│  ATLYS_FcCR   (forecast, cross-tab reporting)      │
│  ATLYS_RvCR   (revenue actuals, GP, commissions)   │
│                                                     │
│  + SSAS cubes (cube1_name, cube2_name per company) │
└─────────────────────────────────────────────────────┘
```

### Component Details

**AtlysSL (Silverlight client)**
- Entry: `App.xaml.cs` — registers `ShutdownManager` as scriptable, sets root visual to `MainPage`
- Shell: `MainPage.xaml.cs` — company selector, navigation frame, menu tree, 1-minute heartbeat timer
- 70+ views as `Page` (full-page navigation) or `ChildWindow` (modal overlays)
- Navigation via `ContentFrame.Navigate(new Uri("/Home", UriKind.Relative))` — Silverlight navigation framework
- Session state stored in `App.Current.Resources["sess"]` (a `Dictionary<string, object>` with keys: `sid`, `version`, `groupid`, `cid`, `ctype`, `cname`)
- All WCF calls are async (event-driven callback pattern: `wsc.LoginCompleted += ...`, `wsc.LoginAsync(...)`)

**AtlysSL.Web (WCF services)**
- `wsAtlys`: primary service, handles all CRUD and data retrieval (~60 `[OperationContract]` methods)
- `wsReporting`: handles report generation, Excel export, commission statements, reconciliation file output
- Both services share the version string `"1.0.9.1"` and the `iCommTimeout = 7200` constant
- `SQLData.Conn(int)` is the sole connection factory — returns a new `SqlConnection` per call, relying on ADO.NET connection pooling

## API Surface

### wsAtlys Service (`AtlysSL.Web\wsAtlys.svc.cs`)

Approximately 60 `[OperationContract]` methods. Key groupings:

| Group | Operations |
|---|---|
| Auth | `Login`, `Logout`, `ChPWD` |
| Companies/Regions | `GetComp`, `GetCompList`, `UpdateComp`, `CompOrd` |
| Users/Roles | `GetUserList`, `GetUserRights`, `UpdateUser`, `GetRelMgrId`, `GetMsgUserList` |
| Programs | `GetPrgs`, `GetComparePrgs`, `GetPrgList`, `popProgInfo`, `SavePar`, `Recalc`, `DeletePrg`, `PrgLock`, `PrgRenumber` |
| Financial Data | `GetCrossTab`, `GetCrossTabs`, `GetVariances`, `GetProbability`, `GetPrgActuals`, `GetPrgFees`, `SaveFcTable`, `SaveFeesTable` |
| GP | `GetGP`, `GetGPMetrics` |
| Commissions | `GetCommissions`, `SaveComm`, `CommCalc` |
| GL | `GetGLMap`, `UpdateGLMap`, `AprGLMap`, `GetGLBatch`, `UpdateGLBatch`, `UpdateGLBatchCopy`, `GetTB`, `UpdateTBAllocMeth` |
| Reconciliation | `GetBRCBList`, `GetTxList`, `GetTxInstances` |
| Periods / Controls | `GetPeriods`, `UpdatePeriod`, `GetFCControls`, `UpdateFCControls` |
| Audit | `GetAuditLog`, `GetAuditLines`, `GetAuditItems`, `GetAuditComments`, `NewAuditComment`, `UpdateAuditComment`, `NewAudit` |
| Messaging | `GetMsgs`, `MsgStatus`, `SMsg`, `GMsg`, `CntUnreadMsg` |
| Reference Data | `GetCBLists`, `GetSalesReps`, `GetLines`, `GetFeeUtilTypes`, `GetProducts`, `UpdateProduct`, `GetImportList`, `Import`, `GetExRates`, `UpdateExRates`, `GetDayList`, `GetJobsControlsList` |
| Maintenance | `UpdateUtil`, `UpdateDurbin`, `GetDurbin`, `UpdateDelHoliday`, `UpdateDelTxId`, `UpdateDelJobsControls`, `UpdateFVD` |
| Utility | `ErrLog` (client error reporting) |

**Note**: `UpdateUCols` at line 412 has `[OperationContract]` but is declared `private` — this is a bug; private WCF operation contracts are silently ignored by the WCF runtime.

### wsReporting Service (`AtlysSL.Web\wsReporting.svc.cs`)

~20 `[OperationContract]` methods for report generation:

| Operation | Output |
|---|---|
| `Xls` | Generic Excel XML from `C2XlsSheetSettings` |
| `RptCrossTab`, `RptMCrossTab` | Cross-tab pivot Excel files |
| `CompareChartExport` | Compare chart Excel |
| `GetCommStmts` | Commission statement Excel files |
| `RptAmortization`, `RptAmortizationDates` | Amortization schedule Excel |
| `RptImportTxn` | Import transaction report |
| `RptAudit` | Audit report Excel |
| `RptGLMap`, `RptGLMapLog`, `RptGLBatch` | GL mapping/batch reports |
| `RptManualList`, `RptVariances` | Manual adjustments and variance reports |
| `RptReconFile` | Reconciliation file |
| `RptUser` | User report |
| `RptGLFile`, `RptGLFileDetail` | GL interface files |
| `RptJEFile` | Journal entry file |

All report operations return a `string` — the path/URL of the generated `.xml` file in `//Logs//`.

### Stored Procedure Naming Convention

All stored procedures use the pattern `dbo.sys_<entity>` with an `@action` parameter for dispatch. This is a single-SP multi-action pattern that bundles all CRUD operations per entity:

- `dbo.sys_user` handles: `login`, `logout`, `changepwd`, `resetpwd`, `update`, `msg_list`, `list`, `list_access`, `list_groups`, `detail`, `loggedin`, `add`, `enable`, `disable`, `lockout`
- `dbo.sys_companies` handles: `list`, `list_all`, `detail`, `update`, `add`, `remove`
- `dbo.sys_msgs` handles: `inbox`, `sent`, `cnt_unread`, `cnt_item`, `details`, `new`, `update_status`

## Security Posture

### Authentication & Authorization

- **Authentication**: Windows Integrated Authentication (`Web.config` line 75: `<authentication mode="Windows"/>`). IIS validates Windows identity before allowing access to the web application. WCF service itself does not independently authenticate — relies on IIS front-end.
- **Session management**: After Windows auth and login SP validation, server generates a `s_id` (session token, 50-char VarChar) stored in `ATLYS_E.tblUsersS`. Every subsequent call passes `s_id` as a parameter; stored procedures validate the session and derive user context. Session invalidated on logout via `dbo.sys_user` action `logout`.
- **Authorization**: Server-side authorization is entirely within stored procedures. Client-side menu visibility is controlled by a rights list string array (`GetUserRights` / `dbo.sys_userrights`). The UI correctly hides options, but the service operations themselves rely on SP-level access control — not independently verifiable from C# code alone.
- **Password policy**: Enforced within `dbo.sys_user` SP (not visible from C#). Client forces password change when `pwd_expired==1` (Login.xaml.cs line 70).

### Identified Security Vulnerabilities

**Critical:**

1. **No transport security (HTTPS)**
   - WCF binding uses `httpTransport`, not `httpsTransport` (`Web.config` lines 111–119)
   - Session IDs, user IDs, all financial data transmitted in cleartext HTTP
   - Even though passwords are AES-encrypted before transmission, the session token and all subsequent data are unprotected
   - PCI DSS Requirement 4.2.1 violation

2. **Hardcoded symmetric encryption key**
   - `"WJKGRSCQ3#4yujfg"` used as salt for AES key derivation — present in `Enc.cs` line 24, `wsAtlys.svc.cs` line 6053, `Login.xaml.cs` line 40, `ChPwd.xaml.cs` line 40, `UserDtl.xaml.cs` line 89
   - `"theSLAPPass"` hardcoded as PBKDF2 passphrase in both `Enc.cs` line 24 and `wsAtlys.svc.cs` line 6053
   - Anyone with source access can decrypt any captured password transmission
   - PCI DSS Requirement 3.7.1; NIST SP 800-57

**High:**

3. **SQL injection vector**
   - `RelMgrId` method (`wsAtlys.svc.cs` line 847):
     ```csharp
     SqlCommand Com = new SqlCommand(String.Format(
         "SELECT id FROM vRelMgrs vrm INNER JOIN dbo.tblUsersS us ON vrm.user_id = us.user_id WHERE us.s_id = '{0}'",
         dic["sid"]), Conn1);
     ```
   - `dic["sid"]` is the session ID value from the client. While session IDs are server-generated, if the `s_id` field can contain special characters, this is a SQL injection point. All other queries use parameterized stored procedures — this is the sole inline dynamic SQL.

4. **Debug mode and full error disclosure**
   - `compilation debug="true"` in `Web.config` line 68 — enables ASP.NET debug mode in what appears to be a production/committed configuration
   - `customErrors mode="Off"` in `Web.config` line 67 — returns full .NET stack traces to any client on unhandled errors
   - PCI DSS Requirement 6.3.1 (protect against information leakage)

5. **MEX endpoints enabled**
   - Both `wsAtlys` and `wsReporting` expose metadata exchange endpoints (`mex`) with `httpGetEnabled="true"`
   - Full WSDL, service contracts, and data contracts are publicly discoverable
   - Facilitates reconnaissance and automated exploit development

**Medium:**

6. **Temp files and error logs in web-accessible directory**
   - Report `.xml` files (`//Logs//R{GUID}.xml`) and `errlog.txt` are in a web-accessible path
   - `errlog.txt` contains exception messages and stack traces
   - If the `Logs/` directory is not explicitly excluded from IIS directory listing, financial report data and error details are accessible by URL guessing

7. **Server hostname committed to source control**
   - `ppamwdcdifsql1\ppamwdcdifsql1` in `Web.config` — infrastructure reconnaissance enablement

8. **Private developer IP in project file**
   - `<CustomServerUrl>http://192.168.1.201</CustomServerUrl>` in `AtlysSL.Web.csproj` line 155 — suggests deployment to a specific server was done via this IP

### Security Controls Present

- Parameterized stored procedures for all DB calls except one (`RelMgrId`)
- Windows Integrated Authentication — prevents anonymous access
- Session-based authorization at DB layer
- Password expiry enforcement
- Account lockout (via `dbo.sys_user` lockout action)
- Client-side AES password encryption (despite key management weakness)
- Temp file auto-deletion after 11 minutes

## Technical Debt

| Item | Location | Debt Level |
|---|---|---|
| Silverlight 4.0 UI — entirely EOL technology | All of `AtlysSL/` | Critical |
| .NET Framework 4.0 — EOL since April 2016 | `AtlysSL.Web.csproj` | Critical |
| WCF binary binding — not cloud-friendly | `Web.config`, both .svc files | High |
| `wsAtlys.svc.cs` — 6069-line monolithic class | Single file | High |
| No unit tests | Entire repo | High |
| Hardcoded version string `"1.0.9.1"` in 2 places | `wsAtlys.svc.cs:23`, `Login.xaml.cs:18` | Medium |
| `private [OperationContract]` on `UpdateUCols` (wsAtlys.svc.cs:412) | Bug — dead code | Medium |
| Session dictionary uses string keys (`dic["sid"]`, `dic["cid"]`) throughout with no type safety | All view code-behind | Medium |
| Commented-out logout in `Application_Exit` (`App.xaml.cs:31–36`) | Logout not called on browser close | Medium |
| `iCommTimeout = 7200` (2-hour DB timeout) | `wsAtlys.svc.cs:24`, `wsReporting.svc.cs:24` | Medium |
| `CompListItem.s[]` string array used as untyped property bag (13-element array for txinstance detail) | `wsAtlys.svc.cs:1388–1392`, `CompListItem.cs` | Medium |
| `CBListItem.Val`, `Val1`, `Val2`, `Val3` — overloaded general-purpose DTO | `CBListItem.cs` | Medium |
| `MsgUser` class used for users, sales reps, rel managers, acct managers — 8+ different shapes | `wsAtlys.svc.cs:1012–1113` | Medium |
| Error log rotation by size only (100KB), no date-based rotation | `wsAtlys.svc.cs:6024–6028` | Low |
| Temp file cleanup triggered on service calls only (opportunistic, not guaranteed) | `wsAtlys.svc.cs:5953–5957` | Low |
| `ExpressionBlendVersion` 3.0.1927.0 in project file — 15+ year old design tool | `AtlysSL.csproj:36` | Low |

## Gen-3 Migration Requirements

To migrate this application to a Gen-3 (cloud-native, modern stack) architecture, the following work is required:

### Must-Have (Prerequisite)

1. **Database schema documentation**: No DDL is in the repo. All ~60 stored procedures must be reverse-engineered and documented before any migration begins. Cross-database dependencies between `ATLYS_E`, `ATLYS_FcCR`, `ATLYS_RvCR` must be mapped.

2. **SSAS cube inventory**: The cube topology (`cube1_name`, `cube2_name`, MDX format strings, company dimension) must be fully documented. Options: migrate to Azure Analysis Services, Power BI Premium, or Synapse Analytics.

3. **REST API design**: Replace `wsAtlys` and `wsReporting` WCF services with ASP.NET Core 8 minimal API or controller-based API with proper resource modeling. The current ~60 RPC operations map to roughly 15–20 REST resource endpoints.

4. **Modern SPA or Blazor UI**: Replace 70+ Silverlight XAML views. React or Angular is the typical Gen-3 choice; Blazor WebAssembly is a lower-rewrite option given the C# codebase.

5. **Identity migration**: Replace Windows Integrated Auth with OAuth2/OIDC using Microsoft Entra ID (Azure AD). The `s_id` session model should be replaced with JWT bearer tokens.

6. **Secrets management**: Remove all hardcoded keys (`"WJKGRSCQ3#4yujfg"`, `"theSLAPPass"`, server name) and inject via Azure Key Vault or equivalent.

7. **HTTPS enforcement**: TLS termination at load balancer/API gateway; all internal service calls on HTTPS.

8. **Fix SQL injection**: Replace inline SQL in `RelMgrId` with a parameterized stored procedure call.

### Should-Have

9. **CI/CD pipeline**: GitHub Actions or Azure DevOps pipeline for build, test, and deployment automation.

10. **Test coverage**: Unit and integration tests for business logic (GP calculation, commission calculation, period locking rules, Durbin exemption management).

11. **Structured logging**: Replace flat-file `errlog.txt` with structured logging (Serilog/Application Insights).

12. **Database access modernization**: Replace raw ADO.NET with Dapper (lightweight) or Entity Framework Core for non-SP data access.

13. **Configuration management**: `appsettings.json` with environment-specific overrides and secrets management; remove all hardcoded values.

### Nice-to-Have

14. **API documentation**: OpenAPI/Swagger spec generated from ASP.NET Core controllers.

15. **Containerization**: Dockerize the API for cloud deployment (Azure App Service, AKS, or Azure Container Apps).

16. **Report modernization**: Replace custom C2Xls XML writer with EPPlus or ClosedXML for Excel generation; consider Power BI Embedded for interactive reporting.

## Code-Level Risks

| Risk | File | Line | Description |
|---|---|---|---|
| SQL Injection | `wsAtlys.svc.cs` | 847 | `String.Format("SELECT id FROM vRelMgrs... WHERE us.s_id = '{0}'", dic["sid"])` — sole inline SQL with user-supplied value |
| Hardcoded encryption key | `Enc.cs` | 24 | `"theSLAPPass"` passphrase hardcoded |
| Hardcoded encryption key | `wsAtlys.svc.cs` | 620, 913, 915, 1157, 1165, 6053 | `"WJKGRSCQ3#4yujfg"` salt hardcoded; `"theSLAPPass"` in `DecQS` |
| Dead/broken WCF operation | `wsAtlys.svc.cs` | 412 | `private string UpdateUCols(...)` marked `[OperationContract]` but private — unreachable from client |
| 2-hour SQL timeout | `wsAtlys.svc.cs` | 24 | `iCommTimeout = 7200` — DB connections can be held open for 2 hours |
| No connection disposal | `wsAtlys.svc.cs` | throughout | `SqlConnection Conn1` is a class-level field; not wrapped in `using` or `try/finally` in most methods — connection leak risk if `Conn1.Close()` is not reached |
| Server name in config | `Web.config` | 56 | `ppamwdcdifsql1\ppamwdcdifsql1` — production server committed |
| Debug mode on | `Web.config` | 68 | `compilation debug="true"` |
| Custom errors off | `Web.config` | 67 | `customErrors mode="Off"` |
| Temp files web-accessible | `wsReporting.svc.cs` | 190 | GUID `.xml` files written to `//Logs//` under web root |
| Error log web-accessible | `wsAtlys.svc.cs` | 6021 | `errlog.txt` written under `ApplicationPhysicalPath//Logs//` |
| Version hardcoded twice | `wsAtlys.svc.cs:23`, `Login.xaml.cs:18` | — | Version `"1.0.9.1"` must be synchronized manually between client and server |
| Logout disabled | `App.xaml.cs` | 31–36 | Logout logic commented out in `Application_Exit` — sessions may remain valid after browser close |
| Untyped DTO overloading | `wsAtlys.svc.cs` | 1012–1113 | `MsgUser` class carries 8+ different data shapes based on action string — no type safety |
