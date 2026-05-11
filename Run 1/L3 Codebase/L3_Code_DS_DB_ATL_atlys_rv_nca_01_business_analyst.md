# DS_DB_ATL_atlys_rv_nca — Business Analyst View

## Business Purpose
This database is the **revenue and cost accounting engine** for the ATLYS platform, North and Central America (NCA) region. Its primary role is to capture, reconcile, and report on all revenue streams, GL entries, commissions, settlement data, spend volumes, card issuance activity, and fee allocations for the prepaid card programs managed in this region. It feeds downstream general-ledger systems (Microsoft Dynamics GP) and supports the ATLYS analytics application used by finance and sales operations teams.

## Business Capabilities
- **Revenue recording and reporting**: captures every revenue event by affiliate/program, revenue type, GL account, product, and channel; supports multi-currency conversion via exchange-rate helpers in the linked ATLYS_E database.
- **GL batch configuration and reconciliation**: manages the mapping of transaction types to debit/credit GL account codes; supports CitiBank, ACH, FDR, Mellon, and network settlement batches.
- **Commission calculation**: tracks commission rates, commission amounts, and sales-rep attribution by affiliate and date range.
- **Settlement import and reconciliation**: stores net spend, interchange, pass-through, chargeback, representment, and clearing amounts received from card networks.
- **Card issuance and plastic tracking**: records the number and dollar value of cards issued per program and item type.
- **Fee and cost allocation**: computes and apportions vendor costs and stock costs across programs.
- **Audit trail**: logs every revenue-recalculation run with start/end dates and user identity for SOX-adjacent traceability.
- **FDR file reconciliation**: stores FDR system files (SD090, SD091, SD902, DD442, CD083) for cost and settlement matching against the card-processor ledger.
- **Metrics aggregation**: captures program performance metrics for management reporting.
- **IVR call data**: records inbound call-data attributed to programs for revenue attribution purposes.

## Business Entities
| Entity | Table(s) | Description |
|---|---|---|
| Revenue line | `revenue`, `tblFVD_Revenue` | Individual revenue event with GL account, amount, commission, source |
| Affiliate / Program | `vAffiliates` (view), `tblProgramsBank`, `tblProgramsBin` | Client prepaid program and linked bank/BIN |
| GL account | `tblGL` | Chart-of-accounts entries |
| GL batch mapping | `tblGLBatch`, `tblGLBatchFeeTax` | Transaction-type-to-account mapping |
| GL entry | `tblGLEntry`, `tblGLEntryIDs` | Posted GL journal entries |
| Settlement | `tblSettle`, `tblSettleDtl` | Network settlement amounts |
| Commission | `tblCommissions`, `tblCommissionsRates` | Sales-rep commission by period |
| Spend | `tblSpend` | Cardholder spend volume by type |
| Issuance | `tblIssuance` | Card issuance quantities and values |
| FDR cost | `tblfdr`, `tblfdrcosts`, `tblFDR_SD090/91/902/DD442/CD083` | FDR processor cost records |
| Audit | `tblAuditLog`, `tblAuditDetails`, `tblAuditComments` | Reconciliation audit trail |
| Product | `tblProducts` | Revenue product/item master |
| Program comp plan | `tblProgramCompPlan`, `tblProgramCompPlanFees` | Client compensation plans |
| Cost allocation | `tblCostsAlloc`, `tblCostsRates` | Fee distribution rules |
| Period | `tblPeriods` | Reporting period master |
| FVD (Face Value Discount) | `tblFVD`, `tblFVD_DefFVD`, `tblFVD_Rev` | Promotional discount accounting |

## Business Rules & Validations
- The `revenue` table carries a `FOR INSERT, UPDATE` trigger (`trg_revenue`) that automatically back-fills `gl_channel`, `gl_product`, `first`, `item`, `gp_product`, `gl_acct_num`, and `gl_acct` from program and product master data on every write, ensuring derived GL coding is always consistent.
- `tblGLBatch` enforces a CHECK constraint (`CK_tblGLBatch_batch`) requiring that any non-'GL%' batch passes a validation function (`sys_chk_glbatch`), preventing arbitrary batch codes from entering the mapping table.
- The `sys_revenue` procedure checks `ATLYS_E.dbo.sys_chkuser` at entry; if the calling session user is not `dbo` and the session is unauthorised, the procedure returns `'Access Denied.'` and halts, enforcing application-layer authorisation in the database.
- GL accounts follow a structured format (`NNNN-PP-CC-VVV-00`) where segments represent account number, product, channel, vendor, and sub-code; the trigger and proc logic construct this from master data segments.
- Commission amounts are validated against commissionable rates per rev-type before population into `tblCommissions`.
- Settlement rows in `tblSettle` are clustered by `c_id` (company), `PROCESSOR`, `RDATE`, and `ICA_BIN`, reflecting a multi-company, multi-processor model.
- The `tblGLBatch` unique clustered index prevents duplicate batch configurations for the same source/facility/fee combination.

## Business Flows
1. **Revenue import**: External feeds (FDR processor files, IVR, SSIS jobs) insert rows into `revenue`; the trigger fires and resolves GL coding.
2. **GL batch setup**: Finance configures debit/credit account mappings in `tblGLBatch`; `sys_glbatch` auto-generates derived CitiBank, ACH, FDR, and network-settlement batches from the configured prototype rows.
3. **Revenue reporting**: `sys_revenue` is called by the ATLYS web application with date, program, type, and region filters; it returns summary or detail depending on the `@report` code.
4. **Audit reconciliation**: `sys_audit` and related procs compare cube (ATLYS_E) quantities and amounts to GP actuals, writing discrepancies to `tblAuditDetails`.
5. **Settlement import**: Network settlement files are loaded into `tblSettle`; `sys_fdr` and `sys_fdrcosts` reconcile against processor data.
6. **Commission calculation**: `sys_comm_calc` aggregates revenue and applies rates from `tblCommissionsRates` to produce commission amounts.
7. **GL entry generation**: `sys_gl_entry` and `sys_glbatch_complete` produce posted journal entries in `tblGLEntry`.

## Compliance & Regulatory Concerns
- **Revenue recognition**: Incorrect GL coding (e.g., trigger failure silently producing blank GL accounts) could result in mis-stated financials — a SOX risk.
- **Audit trail**: `tblAuditLog` logs who ran reconciliation and when, but the log captures session ID (`audit_uid`) rather than a named user credential; in a shared-service or service-account context this may not satisfy SOX access review requirements.
- **Multi-currency**: Exchange-rate application is deferred to runtime; if exchange rates in `ATLYS_E` are stale, reported amounts will be wrong — a financial-accuracy risk.
- **Cross-database dependency**: The database calls `ATLYS_E.dbo.*` and `ATLYS_E.dbo.sys_chkuser` as its authorisation gate; if that linked-server relationship is broken, all security checks fail open (the code returns 'Access Denied' but the calling convention could be bypassed at the SQL layer).
- **Settlement data**: `tblSettle` stores monetary amounts but no PAN or SAD; it is not in-scope CDE on its own, but it links to FDR processor BINs, making it relevant to PCI DSS scope discussions.
- **Chargeback amounts**: Stored as raw numeric values in `tblSettle`; no chargeback-monitoring or threshold logic is present in this database.

## Business Risks
- **Single-trigger GL derivation**: The `trg_revenue` trigger is the sole mechanism for GL coding accuracy; any error in the trigger (e.g., missing `vAffiliates` or `vProducts` join) silently produces blank GL accounts, causing GL mismatches at period close.
- **No stored-procedure versioning or audit**: The `sys_glbatch` SP auto-inserts new GL batch rows; if called erroneously it can proliferate unwanted mapping rows with no rollback mechanism.
- **Recovery model is BULK_LOGGED**: Bulk import operations run in minimally logged mode, which means point-in-time recovery may be impossible for revenue data loaded via bulk operations.
- **Compatibility level 90 (SQL Server 2005)**: The SQLPROJ targets schema provider `Sql100` (SQL Server 2008) but the project `CompatibilityMode` is set to `90`; this limits available features and indicates the schema has not been modernised.
- **FLOAT columns**: `tblEC_Txns` uses FLOAT(53) for monetary amounts (`amount`, `fee`), which introduces floating-point rounding risk for financial calculations.
