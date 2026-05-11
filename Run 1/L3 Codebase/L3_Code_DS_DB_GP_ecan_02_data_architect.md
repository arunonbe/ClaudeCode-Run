# DS_DB_GP_ecan — Data Architect View

## 1. Database Object Inventory

### 1.1 Functions (dbo schema — 195 functions)

The function library divides into four logical groups:

**Banker Functions (custom — 8 functions):**
| Function | Return Type | Purpose |
|----------|-------------|---------|
| `banker_get_required_deposit_date` | DATETIME | Calculates deposit date N business days before a target date |
| `banker_get_sum_saved_credit_memos` | BIGINT | Sums non-voided credit memos for a program/promo (×100 for cents) |
| `banker_get_sum_saved_invoices_per_program_promo` | BIGINT | Sums non-voided invoice subtotals for a program/promo |
| `banker_get_sum_saved_usable_payments` | BIGINT | Sums usable (settled) payments for a program |
| `banker_get_x_days_payments` | BIGINT | Sums payments within a configurable day window |
| `client_refund_parseStringToTable` | TABLE | Parses a delimited string into a table of refund instruction rows |
| `DYN_FUNC_1099_Box_Type` | Scalar | Returns the 1099 box type description for a code |
| `DYN_FUNC_1099_Type` | Scalar | Returns the 1099 type description |

**DYN_FUNC_* series (~155 scalar functions):** GP enumeration/code translation functions. Each takes a numeric code and returns the corresponding GP enumeration string (e.g., `DYN_FUNC_Document_Status_GL_Trx(1)` → 'Posted'). These are view-layer helpers used by SmartList and external reporting tools. No sensitive data is exposed; they are pure code-to-description translators.

**FA_FUNC_* series (11 functions):** Fixed asset code translation (asset type, depreciation method, averaging convention, retirement type, etc.).

**FS_FUNC_* series (15 functions):** Field service code translation (billing cycle, contract period, service record type, etc.).

**Other:**
- `SVC_Calc_Cont_Billing_Amount` — Contract billing amount calculation.
- `taeConnectVersionInfo` — Returns eConnect version metadata.

### 1.2 Views (dbo schema — ~150 views)

**Banker SVC Views (custom — 12 views):**
| View | Purpose | Sensitive Data |
|------|---------|----------------|
| `BankerAllSOView` | Union of open (SOP10100) + history (SOP30200) Sales Orders; includes JobID (USERDEF1) and tracking file name | Program IDs, job IDs, document amounts |
| `BankerSOView` | Open Sales Orders only | Same as above, filtered to open |
| `BankerHistSOView` | Historical Sales Orders | Same, history |
| `BankerMultSOSView` | Multi-promo Sales Orders | Same |
| `BankerSOLineView` | Sales Order line items | Line-level amounts |
| `BankerProgram` | GP customer master as program: ProgramNumber, ProgramName, CreditLimitAmount, CurrencyID, ProgramBalance | **Financial** — credit limits and outstanding balances |
| `BankerPayment` | Payment receipts | Payment amounts, dates |
| `BankerCashReceipts` | Cash receipt documents | Cash amounts |
| `BankerACH` | ACH payment documents | ACH payment amounts and dates |
| `banker_default_promo_exception` | Promo exception rules | Program-level configuration |
| `eCountBankTransactions` | GL journal entries for bank accounts | **Financial** — debit/credit amounts, exchange rates, GL account numbers |
| `eCountBankHistTransactions` | Historical GL bank transactions | Same as above, history |
| `eCountBankTrxUnPosted` | Unposted GL bank transactions | **Financial — pre-posting data** |
| `eCountBatchGLTrx` | Batch GL transactions | Journal batch data |
| `eCountCOA` | Chart of accounts view | Account structure |
| `PROGRAMS` | Alias for BankerProgram with program manager, parent ID, GFCID, full legal name | **Financial** — includes `FullLegalName` (sourced from `RM00303.COUNTRY`) |

**Standard GP Views (135+ views):** Full set of GP-standard views including AccountSummary, AccountTransactions, Accounts, Customers, CustomerAddress, Vendors, VendorAddress, Employees, EmployeeSummary, PayablesTransactions, ReceivablesTransactions, SalesTransactions, SalesLineItems, SalesDistributions, PurchaseOrders, PurchaseLineItems, ReceivingsTransactions, ReceivingsLineItems, PayrollTransactions, PayrollCheckAndDistributionHistory, PayrollHistoricalTrx, FixedAssets, FixedAssetsDepreciation, MultidimensionalAnalysis, TaxDetailTransactions, GLPOSTEDSUMMARY, etc.

**RSM Custom Views (6 views):**
- `rsm_citidirect_ACH_DTS` — Citi Direct ACH data
- `rsm_citidirect_drawdown_DTS` — Citi Direct drawdown transactions
- `RSM_UNPOSTED_SALES_DOCS` — Unposted Sales Orders (RSM reporting)
- `rsmCitiDirectTrx` — Citi Direct transaction detail
- `rsmCDTRXView` — Citi Direct transaction view
- `CitiPrepaidAPAgeTBbyAccNum` — Citi Prepaid AP ageing trial balance by account

### 1.3 Stored Procedures (dbo schema — 100+ procedures across Procs1–Procs18)

**Banker Procedures (custom — ~25 procedures):**
| Procedure | Purpose |
|-----------|---------|
| `banker_get_program_info` | Returns program credit limit, currency, and balance (OUTPUT params) |
| `banker_get_documents` | Returns SOP documents by program + job + doc type (XML input) |
| `banker_get_payments` | Returns payment receipts for a program |
| `banker_get_free_funds` | Calculates available (unsettled) balance |
| `banker_get_unsettled_funds` | Returns unsettled payment amounts |
| `banker_get_all_unsettled_funds` | All-program unsettled fund summary |
| `banker_get_321_days_payments` | Payments within 321-day window |
| `banker_get_ach_delay` | Returns ACH settlement delay configuration |
| `banker_get_active_promotions` | Active promo codes for a program |
| `banker_get_multiple_sos` | Multiple Sales Order lookup |
| `banker_insert_multiple_so` | Creates Sales Orders (invoices) in GP |
| `banker_delete_multiple_sos` | Deletes Sales Orders |
| `banker_get_gp_job_info` | Job-level GP data |
| `banker_get_gp_payment_info` | Payment-level GP data |
| `banker_get_gp_program_info` | Program-level GP data |
| `banker_get_gp_promoexception_info` | Promo exception data |
| `banker_get_jobsvc_job_info` | Job service integration data |

**Standard GP Procedures (80+):** Full set including `aagCreateSubWorkDist`, `aagSubAssignUpdate`, `amAutoGrant`, `APOReconcile`, `ASIDeleteSerialLot`, `ASISaveSerialLot`, `ASIUpdateUnallocated`, and the full GP Dexterity stored procedure library.

**Report procedures (in `report/`):**
- `rpt_check_issuance.sql` — Check issuance report procedure.

### 1.4 Tables

The `ecan.sqlproj` uses `DeployToDatabase = True` with `IncludeCompositeObjects = True`, meaning all referenced tables from the standard GP library are included. The `dbo/Tables` folder was found to be empty in the directory listing (no `.sql` files), suggesting table definitions are inherited from the base GP schema or managed separately. The production ECAN database contains the full complement of GP tables (GL, SOP, RM, PM, POP, UPR, FA, SLB, etc.).

### 1.5 Security Objects

The `Security/` folder contains ~220 SQL files covering:
- **Logins**: `crystal.sql`, `report.sql`, `report_full.sql`, `DYNSA.sql` (WITHOUT LOGIN), and all `NAM_*` Windows logins
- **Roles**: `DYNGRP`, `DYNWORKFLOWGRP`, `RAPIDGRP`, `Banker_execute`, `PPA_FinSVC_GRP`, `ATLYS_APP_GRP`, `ACCTGWF_APP_GRP`
- **Individual named user login scripts**: ~120 SQL Authentication login scripts
- **Permissions**: `Permissions.sql` (large file, 118 KB), `RoleMemberships.sql`

---

## 2. Sensitive Data Fields

| Field | Context | Classification | Flag |
|-------|---------|---------------|------|
| `SOP10100.SUBTOTAL`, `SOP30200.SUBTOTAL` | Invoice amounts in BankerAllSOView | Financial — program-level | Not PAN/SAD; financial data subject to SOX |
| `RM00101.CRLMTAMT` | Credit limit amounts in BankerProgram | Financial | Program sponsor credit limits — commercially sensitive |
| `RM00101.CUSTBLNC` | Program balance in BankerProgram | Financial | Real-time program funding balance |
| `GL20000.DEBITAMT`, `GL20000.CRDTAMNT` | Journal entry amounts | Financial | GL entries subject to SOX |
| `GL20000.ORMSTRID` | Master record ID in journal entries | Reference | Can link to customer/vendor IDs |
| `UPR*` tables | Payroll data | **PII — PIPEDA scope** | Employee SSN equivalents, salaries, deductions |
| `RM00303.COUNTRY` | Full legal name (via alias) | Corporate identity | Legal entity name for Canadian compliance |
| `SOP10106.USERDEF1` | Job ID (used as source identifier) | Operational reference | Links GP transactions to Onbe job numbers |
| `SOP10107.Tracking_Number` | File tracking reference | Operational reference | SFTP or batch file tracking |
| `PASSWORD` | SQL Authentication login scripts | **Credentials** | Plaintext in `crystal.sql`, `report.sql` |

**PCI DSS CDE Assessment**: ECAN is **not a CDE database** — it contains no PANs, CVVs, or track data. However, it is a **Tier 2 connected system** providing financial account balances and payment information used by the card issuing process. PCI DSS Requirements 6, 7, and 8 apply.

---

## 3. Encryption at Rest

- No column-level encryption in DDL.
- TDE: not declared in repo DDL; assessed at instance level.
- `credit.sql` / `report.sql` SQL Auth passwords are plaintext — see Section 5_solution_architect.md.

---

## 4. Data Retention

No retention DDL present. GP historical data is managed through GP's year-end close and archive utilities. The `eCountBankHistTransactions` and `BankerHistSOView` views indicate historical transaction data is retained in GP history tables (GL30000, SOP30200) separately from open-period tables.

---

## 5. Index Notes

GP tables use Dexterity-generated indexes (prefix `PK*`, `AK2*`) on natural keys. The `BankerAllSOView` union query joins `SOP10100`/`SOP30200` to `SOP10106`/`SOP10107` on `SOPNUMBE` — this join should be covered by the standard GP `PKXXX` clustered index on `SOPNUMBE`. No custom indexes for Banker SVC views are defined in the repo.
