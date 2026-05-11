# Data Architect Report — DS_DB_GP_ecnt

## 1. Repository Structure and Build System

`DS_DB_GP_ecnt` is an **SSDT SQL Server Database Project** (`ecnt.sqlproj`).

**Key project properties:**
- **Project GUID**: `{2bdc609a-320c-4ac6-83d9-67b9d5dcaa68}`
- **DSP**: `Microsoft.Data.Tools.Schema.Sql.Sql100DatabaseSchemaProvider` — SQL Server 2008 compatible
- **CompatibilityMode**: `90` (SQL Server 2005)
- **DefaultCollation**: `SQL_Latin1_General_CP1_CI_AS`
- **PageVerify**: `TORN_PAGE_DETECTION` — older checksum method (not `CHECKSUM`)
- **TDE**: `IsEncryptionOn=False`
- **Recovery**: `BULK_LOGGED` (risk for point-in-time recovery)
- **Broker**: `DisableBroker`
- **Query Store**: enabled (`QueryStoreCaptureMode=Auto`)
- **`AnsiNulls=False`**, **`QuotedIdentifier=False`**, **`ArithAbort=False`** — all non-ANSI settings

This is a **Microsoft Dynamics GP company database** — a Microsoft ERP system database that follows the GP schema conventions. Unlike other databases in this analysis batch, ECNT is structured by GP's internal data model (module-based: GL, RM, PM, SOP, POP, UPR, FA, IV, etc.) with Onbe-specific custom stored procedures, views, and functions layered on top.

---

## 2. Schema Composition

Single schema: `dbo`. The ECNT database has two functional layers:

**Layer 1 — Microsoft Dynamics GP Standard Tables**: Hundreds of GP-defined tables following GP naming conventions:
- `GL10000` (GL open transactions), `GL20000` (GL history)
- `RM00101` (customer master), `RM20101` (RM open transactions), `RM30101` (RM history)
- `PM00200` (vendor master), `PM20000` (PM open transactions)
- `SOP10100` (SOP header), `SOP10200` (SOP line items)
- `POP10100` (POP header), `POP30100` (POP history)
- `UPR00100` (employee master), `UPR10400` (payroll transactions)
- `FA00100` (fixed asset master)
- `SLB10000` (budget master)
- `SY40100` (fiscal period setup)

**Layer 2 — Onbe/RSM Custom Objects**: Onbe-specific stored procedures, views, and functions layered on the GP schema:
- Banker SVC integration procedures
- Prepaid program financial procedures
- Citi Direct banking integration
- Meridian banking integration
- Missing refund tracking view
- Contract pricing and kit inventory

---

## 3. Key Object Inventory

### 3.1 Onbe Custom Stored Procedures (Procs1 folder)

| Procedure | Purpose | Key Data Accessed |
|---|---|---|
| `Banker_available_balance(@program, @promo)` | Real-time available balance for US prepaid programs | Reads `ecnt.dbo.rm00103` (customer balance history) |
| `Account_Balance_Aging` | AR ageing by balance bucket | RM tables |
| `banker_get_gp_job_history` | Job history for Banker SVC | GP job/order tables |
| `PrepaidProgramBankingUpdate` | Updates banking information for prepaid programs | Prepaid program records |
| `RSM_CitiDirect_ACH_WithBank` | Citi Direct ACH processing with multi-bank email notification (modified 2019 to use `namsupport@wirecard.com`) | GP ACH/payment tables |
| `RSM_CitiDirect_Drawdown_WithBank` | Citi Direct drawdown processing | GP payment tables |
| `RSM_Wirecard_Fees_ACH` / `RSM_Wirecard_Fees_Drawdown` | Wirecard fee ACH and drawdown processing | Fee records |
| `RSM_TotalAccountBalance` | Total account balance aggregation | RM tables |
| `CitiPrepaidONUS_RevCSA_INSERT` / `_RevJobSvc_INSERT` / `_RevOrderSvc_INSERT` | Citi Prepaid OnUS revenue insertion | Revenue records |
| `CitiPrepaid_ZeroTotalSOBatch` | Zero-total sales order batch processing | SOP tables |
| `Client_Digital_Invoice` | Digital invoice generation for clients | SOP/RM tables |
| `Customer_Balance_w_Address` | Customer balance with address detail | RM + address tables |
| `PrepaidProgramBankingUpdateAllPrograms` | Batch banking update for all programs | Program master |
| `Prepaid_ONUS_BankInformationExport` | OnUS bank information export | Banking integration |
| `PP_Batch_Total` / `PP_Remove_History` | Payroll processing batch totals and history management | UPR tables |
| `ExtPricingGetFunctionalCurrency` / `GetPromoItems` / `GetPromoPrice` | Contract pricing functions | Pricing/inventory |

### 3.2 Onbe Custom Views

| View | Purpose | Sensitivity |
|---|---|---|
| `VW_MISSING_REFUNDS` | Identifies unfulfilled refund obligations | **HIGH — compliance: Reg E error resolution** |
| `VRFMERIDIAN` | Meridian bank transaction verification | MEDIUM |
| `AR_VIEW` / `ARTOTALVIEW` / `ARVIEW` | Enhanced AR reporting | MEDIUM — financial |
| `OPENITEMS` | Open AR items tracking | MEDIUM |
| `PAYMENTVIEW` | Payment history view | MEDIUM |
| `RMAPPY` / `RMDOCS` | RM application documents | MEDIUM |
| `SOPDETAILVIEW` / `SOPHEADERVIEW` | Sales order detail/header views | MEDIUM |
| `CustomerBalance_w_Address` | Customer balance with address | MEDIUM |
| `ItemPricePerContractPlusKit` | Contract pricing with kit | LOW |
| `CONTRACTPRICING` | Contract price lookup | LOW |
| `CPVMStockInventoryAuto` | Automatic contract price inventory | LOW |
| `GMTEST` | Test view (GM = Great Plains module?) | LOW |
| `rsm_citidirect_ACH_DTS_old` / `rsm_citidirect_drawdown_DTS_old` | Legacy Citi Direct views (retained as reference) | LOW |
| `rsm_customer_rollup` | Program-to-GFCID mapping | LOW |

### 3.3 Onbe Custom Functions

| Function | Purpose |
|---|---|
| `banker_get_required_deposit_date(@current_date, @num_days_to_usable)` | Business day deposit date calculation (check=3, ACH=2, cash=0 days) |
| `banker_get_sum_saved_credit_memos` | Credit memo amount summation |
| `banker_get_sum_saved_invoices_per_program_promo` | Invoice amount summation |
| `banker_get_sum_saved_usable_payments` | Usable payment amount summation |
| `banker_get_x_days_payments` | X-day payment window summation |
| `DYN_FUNC_*` (100+ functions) | Standard Dynamics GP decode functions for GP enumerated values |

---

## 4. Sensitive Data Assessment

| Data Category | Tables/Fields | Sensitivity |
|---|---|---|
| **GL journal entries** | `GL10000`, `GL20000` — debit/credit amounts, account codes, journal references | **HIGH — SOX financial reporting** |
| **SOP sales orders** | `SOP10100/SOP10200` — US program invoices, job IDs | HIGH — commercially sensitive |
| **RM receivables** | `RM00101` — US program customer masters, balances, credit limits | HIGH — commercially sensitive |
| **PM payables** | `PM00200`, `PM20000` — vendor invoices, ACH/check payments | HIGH — financial |
| **UPR payroll** | `UPR00100` — US employee master; `UPR10400` — payroll transactions | **CRITICAL — PII: full employee personal and financial data; GLBA; SOX** |
| **GP customer addresses** | `RM00101.ADDRESS1/2`, `CITY`, `STATE`, `ZIPCODE`, `PHONE1` | MEDIUM — program sponsor contact data |
| **`VW_MISSING_REFUNDS`** | DDA-linked refund obligations | HIGH — Reg E compliance; cardholder refund data |
| **Banking integration** | `rsm_citidirect_*` — ACH routing and account data | **HIGH — bank routing/account numbers** |
| **Payroll tax** | UPR tables — federal/state withholding amounts | HIGH — tax regulatory |

**PCI DSS scope**: ECNT is a **connected system** to the CDE via the Banker SVC (`Banker_available_balance` reads `rm00103` which is queried by Banker). The GP database itself does not store PANs, but it stores program-level financial data that maps to cardholder programs.

---

## 5. Encryption

| Control | Status |
|---|---|
| TDE | `IsEncryptionOn=False` — data at rest unencrypted |
| Column-level encryption | None |
| `PageVerify=TORN_PAGE_DETECTION` | Older page verification method; `CHECKSUM` is recommended |

**Critical gap**: Employee payroll data (`UPR` tables) is unencrypted at rest. This data includes employee names, Social Security Numbers (SSNs), addresses, salary, and payroll history — all subject to GLBA NPI protection.

---

## 6. Cross-Database References

`Banker_available_balance` procedure directly queries the ECNT database by name:
```sql
select top 1 @CUSTBLNC = CUSTBLNC * -1 
from ecnt.dbo.rm00103 
where custnmbr like @customer
-- (Banker_available_balance.sql:37)
```

This is a self-referential query using the database name explicitly. If the database is ever renamed or hosted on a different server, this hard-coded reference will break.

`RSM_CitiDirect_ACH_WithBank` has been modified by multiple developers (Greg Couto 2017, Nick Doan 2018, Van Nguyen 2019, Julia Ginzburg 2019) — confirming it is an actively maintained procedure with external integration dependencies.

---

## 7. Security — Access Model

The Security scripts define an exceptionally large number of named individual user logins. The `Security/` directory contains 100+ files including:
- Named individual logins (e.g., `G.Couto.sql`, `Amber.Lukacko.sql`, `Kate.Rebar.sql`, `J.Hillard.sql`)
- Employee ID-based logins (e.g., `AA10644`, `AD12345`, `AG29025`, `GK42747`)
- Service accounts: `DYNGRP`, `DYNSA`, `DYNWORKFLOWGRP`, `ACCTGWF_APP_GRP`, `ATLYS_APP_GRP`, `Banker_execute`
- FortiDB monitoring: `FortiDBRptRole`
- NAM service accounts: implied by ATLYS and Banker groups

**Named individual user logins in a production database** are a governance risk:
- Access does not automatically revoke when employees leave
- No visible periodic access review in source control
- Individual access creates non-repudiation concerns for SOX

---

## 8. Data Flow Summary

```
GP Finance Team ──────────────────────► ECNT (invoices, payments, journal entries)
                                              │
Banker API ◄───────────────────────── Banker_available_balance
                                              │
Finance WebService ◄──────────────── AR views, SOPDETAILVIEW
                                              │
Compliance reporting ◄───────────── VW_MISSING_REFUNDS
                                              │
Bank reconciliation ◄────────────── VRFMERIDIAN, rsm_citidirect_*
                                              │
DS_ETL_finance-gp / DS_ETL_great-plains ◄─ All GP tables → Warehouse
```

---

## 9. Compliance Gaps

| Gap | Description | Regulation |
|---|---|---|
| Employee PII unencrypted | UPR payroll tables with SSN-equivalent data unencrypted at rest | GLBA NPI; SOX |
| No TDE | `IsEncryptionOn=False` for a database containing payroll, AR, and financial records | PCI DSS Req 3.5; GLBA |
| TORN_PAGE_DETECTION | Older page integrity verification; not CHECKSUM | SQL Server best practice |
| Named individual user logins | 100+ individual login files in Security scripts | SOX access review; PCI DSS Req 7, 8 |
| BULK_LOGGED recovery | No point-in-time restore during bulk loads | SOX; availability; RPO |
| SQL 2005 compat mode | CompatibilityMode=90 | Maintenance risk; performance ceiling |
| Hard-coded database name in stored procedure | `ecnt.dbo.rm00103` in `Banker_available_balance.sql:37` | Portability; operational risk |
