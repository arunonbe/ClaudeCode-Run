# atlys_WAPP — Business Analyst View

## Business Purpose

Atlys (version 1.0.9.1) is an internal financial management and reporting platform for a prepaid card business. Its core purpose is to provide finance, sales, and operations teams with a unified tool to manage prepaid card programs across multiple companies and regions, forecast revenues and costs, reconcile financial data, manage commissions, generate GL (General Ledger) interface files, and perform audits. The application is branded under "Synevation" (logos reference `Synevation2-sm.jpg`, `synevation_16x16.jpg`) suggesting it was built by or for a third party that Onbe may have acquired or inherited.

## Business Capabilities

The following capabilities are directly evidenced by the XAML views and WCF service operations in `wsAtlys.svc.cs` and `wsReporting.svc.cs`:

**Program Management**
- Create, search, view, rename, lock/unlock, recalculate, and delete prepaid card programs (`Views\Program.xaml`, `ProgramList.xaml`, `ProgramSearch.xaml`)
- Store program metadata: channel, product, sales rep, partner, first-issue date, frequency (`PrgListItem.cs`)

**Financial Forecasting (FC)**
- Multi-version forecast cross-tab views: revenue, issuance, plastics, spend, costs, deferred revenue, pipeline (`GetCrossTab` / `GetCT` method, `wsAtlys.svc.cs` lines 2144–2605)
- Forecast controls configuration and versioning (`FCControls.xaml`, `GetFCControls`)
- Forecast change management (`FCChange.xaml`, `UpdateFVD`)

**Revenue & Gross Profit (GP) Reporting**
- Gross profit by product, by program, with cost breakdown: processing, stock, royalty, CS, tel, IVR, ATM, ACH, merchant (`GPItem.cs`, `GPMetricsItem.cs`)
- Revenue actuals vs. forecast variance (`VarItem.cs`, `Views\FCVariance.xaml`)
- Revenue detail and line-level reporting (`Views\RevenueDetail.xaml`)

**Commissions**
- Commission calculation, manual commission entry, commission detail by sales rep and program (`CommItem.cs`, `Views\Comm.xaml`, `CommDtl.xaml`, `CommPrgDtl.xaml`)
- Commission revenue targets (`Views\CommRevTarget.xaml`, `CommRevTargetDtl.xaml`)
- Commission statement reporting (`wsReporting.svc.cs`: `GetCommStmts`)

**GL Interface & Accounting**
- GL batch mapping (debit/credit, source, facility, fee flags, card type) (`GLBatchItem.cs`, `Views\GLBatch.xaml`, `GLBatchBin.xaml`, `GLBatchFeeTax.xaml`)
- GL account mapping with approval workflow (`GLMapItem.cs`, `AprGLMap` operation)
- Trial balance with allocation method (`TBItem.cs`, `Views\TB.xaml`)
- GL file and journal entry file generation (`wsReporting.svc.cs`: `RptGLFile`, `RptJEFile`)
- Manual revenue adjustments (`ManualItem.cs`, `Views\ManualAdj.xaml`, `ManualAdjList.xaml`)

**Reconciliation**
- Bank reconciliation (`Views\BankReconcile.xaml`)
- BIN reconciliation (`Views\BinRecon.xaml`)
- CL (card load) reconciliation (`Views\CLRecon.xaml`)
- Interface/file reconciliation (`Views\InterfaceRecon.xaml`, `InterfaceGL.xaml`)
- Cube reconciliation (OLAP vs. transactional data) — stored proc `dbo.sys_cube_reconcile`

**Audit**
- Audit creation, line-item review, and comment threads (`AuditItem.cs`, `AuditLogItem.cs`, `AuditCommentItem.cs`, `Views\Audit.xaml`, `AuditComments.xaml`)

**Durbin Amendment Compliance**
- Maintain BIN-level Durbin exemption flags (`DurbinListItem.cs` with `Bin` and `Exempt` fields; `Views\DurbinList.xaml`)

**Administration**
- User management: create, update, reset password, enable/disable, lock out (`Views\UserList.xaml`, `UserDtl.xaml`)
- Company, region, country, currency, interface, and TX instance administration (`Views\CompList.xaml`, `CompDtl.xaml`)
- Sales rep, relationship manager, and account manager management
- Period (fiscal period) locking (`Views\Periods.xaml`, `PeriodItem.cs`)
- Product list maintenance with GL account linkage (`ProductItem.cs`, `Views\ProductList.xaml`)
- Holiday schedule and withdrawal schedule (`Views\HolidaySchedule.xaml`)
- Job controls monitoring (`JobsControlsItem.cs`, `Views\JobsControls.xaml`)

**Messaging**
- Internal user-to-user messaging with inbox, sent, importance, read status, and references to program items (`MsgBoxItem.cs`, `Views\UMessages.xaml`, `UNewMsg.xaml`)

**Reporting & Export**
- Export all views to Excel via custom XML spreadsheet builder (`C2XlsBook.cs`, `C2XlsCell.cs`, `C2XlsStyle.cs`)
- Amortization reports (`wsReporting.svc.cs`: `RptAmortization`, `RptAmortizationDates`)
- Recon file export, GL map log report, user reports, audit reports

## Business Entities

| Entity | Key Class / Table Reference | Description |
|---|---|---|
| Program | `PrgListItem`, `dbo.sys_program_search` | A prepaid card program with channel, product, sales rep, partner |
| Company / Region | `CompListItem`, `dbo.sys_companies`, `dbo.sys_regions` | Multi-entity hierarchy; type flag `C`=company, `R`=region (read-only) |
| Product | `ProductItem`, `dbo.sys_products` (implied) | Card product with revenue type, GL account, line code |
| Commission | `CommItem`, `dbo.sys_comm` | Sales rep commission with effective rate, fee tiers, payment type |
| GL Batch | `GLBatchItem`, `dbo.sys_gl_batch` (implied) | GL journal entry mapping rules |
| GL Map | `GLMapItem`, `dbo.sys_glmap` (implied) | Chart of accounts mapping with approval status |
| Trial Balance | `TBItem` | Account balances with allocation method |
| Manual Adjustment | `ManualItem` | Manual revenue/cost entries by program and account |
| Audit | `AuditLogItem`, `AuditItem`, `AuditCommentItem` | Financial audit with period range, reviewer, comments |
| Period | `PeriodItem` | Fiscal period with lock status |
| BIN / Durbin | `DurbinListItem` | Card BIN with Durbin Act exemption flag |
| User | `MsgUser` (used for user admin), `dbo.sys_user` | Internal user with group/role, enabled/locked status |
| Sales Rep | `MsgUser` (rep_type variant), `dbo.sys_sales_reps` | Sales representative with manager, rep code, commission flag |
| Exchange Rate | `RateItem`, `dbo.sys_exchange_rates` (implied) | Currency pair rate for specified date range |
| File TX ID | `FileTxIdItem` | Transaction file date range markers by company |
| Job Control | `JobsControlsItem`, `dbo.sys_jobs_controls` (implied) | Batch job scheduling entries |
| Message | `MsgBoxItem`, `dbo.sys_msgs` | Internal messages with to/cc lists and program references |

## Business Rules & Validations

- **Version enforcement**: Every service call validates client version matches server version (`"1.0.9.1"`). Mismatch forces page refresh / app close. (`VersionVer` method, `wsAtlys.svc.cs` lines 672–680)
- **Password expiry**: Login returns a `pwd_expired` flag; expired passwords force immediate change via `ChPwd` dialog before the app is accessible. (`Login.xaml.cs` lines 70–74)
- **Session-based authorization**: Every operation passes a session ID (`s_id`), company type (`ctype`), and company ID (`cid`). All stored procedures gate access by session. (`wsAtlys.svc.cs`, session dictionary pattern throughout)
- **Read-only company access**: Companies of type `R` (region) are flagged read-only in the UI; write operations on Finance, GL, Import, Recon, etc. are hidden for read-only contexts. (`MainPage.xaml.cs` lines 135–181)
- **User rights**: Menu items and sub-menus are shown/hidden based on server-returned rights list (strings such as `"View Forecast"`, `"Finance"`, `"Admin"`, `"GL Map"`, `"Bank Recon"`, `"Companies Admin"`, `"Users Admin"`). (`MainPage.xaml.cs` lines 147–195)
- **Program locking**: `PrgLock` / `SetPrgLock` prevents concurrent edits to a program.
- **Forecast recalculation**: `Recalc` / `DoPrgAction("recalc_forecast")` triggers server-side recalculation.
- **Period locking**: Periods can be locked to prevent retroactive data changes (`UpdatePeriod`).
- **GL Map approval**: GL account mappings require explicit approval (`AprGLMap`).
- **Durbin exemption**: BINs must be individually marked exempt or non-exempt.

## Business Flows

1. **Login**: User enters UID/password → client encrypts password with AES/`WJKGRSCQ3#4yujfg` key → `wsAtlys.Login` → `dbo.sys_user` SP validates → session ID (`s_id`), group ID, version returned → company selection → user rights loaded → menu built.

2. **Program Lifecycle**: Search (`ProgramSearch`) → open (`Program.xaml`) → edit parameters → save → lock program → recalculate forecast → view FC cross-tab → review variance → export to Excel.

3. **Commissions**: Calculate commissions (`CommCalc`) for a date range → review (`Comm.xaml`) → edit rates / tiers → save → generate commission statements (`wsReporting.GetCommStmts`).

4. **GL Interface**: Map GL accounts (`GLMap.xaml`) → approve mappings → set GL batch rules (`GLBatch.xaml`) → generate GL file (`RptGLFile`) → post journal entries (`RptJEFile`).

5. **Reconciliation**: Import actuals (`Import.xaml`) → run reconciliation view (`BankReconcile`, `BinRecon`, `CLRecon`) → review variances → export recon file (`RptReconFile`).

6. **Audit**: Create audit for a date range (`NewAudit`) → review audit items and lines → add comments → export audit report (`RptAudit`).

## Compliance & Regulatory Concerns

- **Durbin Amendment (Reg II)**: The application explicitly manages BIN-level Durbin exemption flags (`DurbinListItem`, `dbo.sys_durbin` stored proc, `Views\DurbinList.xaml`). This is a direct compliance function under Dodd-Frank/Reg II requiring accurate exemption tracking for debit interchange.
- **Financial period controls**: Period locking prevents retroactive changes — relevant to SOX-style controls and audit trail requirements.
- **Audit trail**: The audit module (`AuditLogItem`, `AuditCommentItem`) provides a formal review mechanism with user attribution and date ranges.
- **Credential handling**: Passwords are transmitted AES-encrypted over the WCF transport. However, a hardcoded symmetric key is used (see Security Posture section). This is a PCI DSS concern if application user credentials are co-mingled with cardholder system access.
- **Data scope**: The application manages BINs (Bank Identification Numbers), which are partial PANs. BIN lists are stored and transmitted via `DurbinListItem.Bin` and `dbo.sys_durbin`. This is card data — PCI DSS scoping implications apply if full PANs are present in underlying tables.

## Business Risks

- **Silverlight EOL**: The entire UI is Microsoft Silverlight 4.0, a technology discontinued by Microsoft in October 2021. All major browsers have dropped the NSAPI plugin. The application cannot be accessed with a modern browser without legacy infrastructure (IE 11 with Silverlight plugin on legacy OS). This is the most severe business risk — the application is effectively inaccessible or running on unsupported infrastructure.
- **Single hardcoded encryption key**: The password encryption key `"WJKGRSCQ3#4yujfg"` and passphrase `"theSLAPPass"` are hardcoded in source. If the source is compromised, all transmitted credentials are decryptable.
- **No CI/CD, no containerization**: No build pipeline, Dockerfile, or deployment automation is present. Deployment is entirely manual.
- **No audit log for data changes**: The `ErrorLog` method writes to a flat file (`errlog.txt`). Data mutation audit trails depend entirely on SQL stored procedures — no application-level change log is visible.
- **Version-lock fragility**: Tight version coupling means any server deployment forces all connected users to reload simultaneously, creating operational disruption.
