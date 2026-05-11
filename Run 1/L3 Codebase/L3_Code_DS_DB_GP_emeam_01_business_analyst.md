# Business Analyst View — DS_DB_GP_emeam

## Business Purpose
DS_DB_GP_emeam is the Microsoft Dynamics GP (Great Plains) EMEAM (Europe, Middle East, Africa, Mexico) regional database for Onbe/Wirecard Data Services. It is the ERP back-office database for financial operations in these geographies, managing general ledger, accounts payable, accounts receivable, payroll, inventory, purchasing, sales order processing, and field service management. It is distinct from the North American GP database and contains financial records for EMEAM regional entities.

## Capabilities
1. **General Ledger (GL)**: Multi-currency, multi-period account management; `GL*` table prefix; `SE_Get_*` procedures for account detail and period balances.
2. **Accounts Payable (PM — Payables Management)**: Vendor management, invoice processing, payment runs, 1099 reporting.
3. **Accounts Receivable (RM — Receivables Management)**: Customer invoicing, cash receipts, aging, deductions.
4. **Sales Order Processing (SOP)**: Sales orders, invoices, back-orders, multi-bin fulfillment.
5. **Purchase Order Processing (POP)**: Purchase orders, vendor receipts, three-way match.
6. **Inventory (IV)**: Item master, lot/serial tracking, cost calculation, bin management.
7. **Payroll (PP)**: Payroll batch processing, batch totals, payroll history removal.
8. **Field Service Management (SVC)**: Service calls, contracts, work orders, technician scheduling, parts allocation, depot repair — an extensive module with 200+ service procedures.
9. **Cash Management (CM)**: Bank reconciliation, cash receipts.
10. **Multi-currency (MC)**: Transaction state management across currencies.
11. **SmartList/Report-writer integration**: `rpt_*` roles for role-based reporting access across 20+ business roles.
12. **Workflow**: `DYNWORKFLOWGRP` role for Dynamics GP workflow automation.

## Key Entities
| Entity | GP Module | Description |
|---|---|---|
| `GL00105` | General Ledger | Account master |
| `GL10111` | General Ledger | Transaction history by period |
| `SE000401` | Management Reporter / SE | Account detail for reporting session |
| `PP400000` / `PP400001` | Payroll | Payroll batch headers and transactions |
| `AF*` tables | Analytical Accounting | Analytical account segments |
| `ASI*` tables | Advanced Serial/Lot inventory | Serial/lot tracking |
| `B*` tables | Business Portal / Bank rec | Various |
| `SOP*` | Sales Order Processing | Order lines and fulfillment |
| `SVC*` procedures | Field Service | 200+ service management stored procedures |

## Business Rules (observed)
1. **FDR cycle awareness**: The `app_func_in_same_fdr_cycle` function (also present in DBAdmin) governs FDR processing window boundaries — 7 PM cutoff, Sunday 2-day lookback.
2. **GP defaults binding**: `BindDynamicsDefaults` assigns default values to all date, char, int, and money columns across all user tables using `GPS_DATE`, `GPS_CHAR`, `GPS_INT`, `GPS_MONEY` — standard GP database initialisation.
3. **1099 vendor classification**: `DYN_FUNC_1099_Type` — vendors classified as Dividend, Interest, Miscellaneous, or Not a 1099 vendor.
4. **Multi-currency**: Separate functional-currency and originating-currency columns throughout transaction tables.
5. **Payroll batch reconciliation**: `PP_Batch_Total` recalculates batch totals from transaction detail after any change.
6. **Payroll history cleanup**: `PP_Remove_History` — procedure to purge historical payroll data (contents not fully visible but pattern indicates controlled data disposal).
7. **Service contract billing**: Complex multi-step contract lifecycle with escalation schedules, billing, revenue recognition, and cancellation rules.

## Key Roles and User Access
| Role/User | Purpose |
|---|---|
| `DYNGRP` | Main Dynamics GP application group (~25 named users) |
| `DYNWORKFLOWGRP` | GP workflow automation |
| `RAPIDGRP` | RAPID add-on module users |
| `ISAUser` | ISA (Information Security) read access |
| `NAM\PROD` / `NAM\UAT` | Production and UAT environment access |
| `NAM\PROD_ITOPS` | IT Operations read access |
| `report` / `report_full` | Read-only report access |
| `rpt_*` (20 roles) | Granular read access by business function (accounting manager, AP coordinator, AR coordinator, bookkeeper, payroll, HR, etc.) |
| Named individual users | AF73484, AK46193, AM78768, etc. — employee ID-style SQL logins |

## Process Flows
1. **Financial period close**: GL journal entry → `GL10111` → `SE_Get_Acc_Detail_Hist` / `SE_Get_Period_Balances_*` → Management Reporter.
2. **AP payment run**: Vendor invoice → PM tables → payment selection → check/EFT generation.
3. **Payroll cycle**: Payroll batch entry → `PP400001` → `PP_Batch_Total` (recalculate) → post → history.
4. **Service contract lifecycle**: `SVC_AddContractToCall` → contract billing → `SVC_Calc_Contract` → revenue recognition → invoicing.
5. **Inventory receipt**: POP receipt → `ASI*/IV*` lot/serial → cost update (`IVLotUpdateUnitCostForReceipt`).

## Compliance Concerns
- **1099 reporting**: Functions for 1099 box types and vendor classification must be accurate for IRS compliance.
- **Payroll data**: PP tables contain compensation data; access restricted to `rpt_payroll` role. GLBA and state privacy laws apply to employee records.
- **Multi-region**: EMEAM scope includes GDPR jurisdictions (EU), PIPEDA (Canada for Mexican operations?), and potentially CCPA. Financial data retention periods vary by country.
- **Named individual logins**: 20+ employee-ID-style SQL logins (`AF73484`, `AK46193`, etc.) — individual accountability is maintained but SQL logins are inherently weaker than Windows auth; password rotation not enforced at the database level.
- **Audit trail**: GP maintains `DEX_ROW_ID` audit columns on every table; the `SE_Get_Acc_Detail_*` procedures show direct GL transaction access, which must be controlled under SOC 1 (financial reporting controls).

## Risks
- **Payroll history in CDE-adjacent database**: If payroll tables contain employee SSNs or bank routing numbers, this database may be in scope for GLBA and/or state privacy regulation.
- **SQL logins for named individuals**: If employees leave, SQL logins must be manually disabled — no automated deprovisioning visible.
- **`sdmello`, `tlal`, `tdhruv` SQL logins in DYNGRP**: These appear to be individual employee usernames without the standardised ID format. Lifecycle management risk.
- **Compatibility mode 100 (SQL Server 2008)**: The `emeam.sqlproj` sets `CompatibilityMode=100` — SQL Server 2008 compatibility level. The database is not taking advantage of modern query optimiser improvements.
