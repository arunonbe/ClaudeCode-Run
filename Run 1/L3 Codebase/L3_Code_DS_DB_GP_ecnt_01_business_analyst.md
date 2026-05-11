# DS_DB_GP_ecnt — Business Analyst View

## 1. Repository Identity

| Attribute | Value |
|-----------|-------|
| Repo name | DS_DB_GP_ecnt |
| Project file | `ecnt.sqlproj` (SSDT, DSP Sql100) |
| Solution file | `ecnt.sln` |
| README | One line: "ecnt" |
| Database name | ECNT — GP Central company database |
| Regions served | US Central / primary US operations |

---

## 2. Business Purpose

`DS_DB_GP_ecnt` is the **Microsoft Dynamics GP company database for Onbe's Central / primary US operations**. As the largest and most mature of the GP company databases, ECNT:

- Records all **financial transactions** for US Central operations: AP, AR, GL, payroll, fixed assets, purchasing, and sales order processing.
- Provides the **primary Banker SVC integration layer** for US domestic prepaid card programs — containing a superset of the ECAN Banker procedures plus additional US-specific procedures.
- Supports **financial reconciliation** between GP financial records and EcountCore cardholder balances.
- Houses **additional US-specific business intelligence views** not present in ECAN, including: `AR_VIEW`, `ARTOTALVIEW`, `ARVIEW` (enhanced AR reporting), `OPENITEMS`, `PAYMENTVIEW`, `RMAPPY`, `RMDOCS`, `SOPDETAILVIEW`, `SOPHEADERVIEW`, `CustomerBalance_w_Address`, `ItemPricePerContractPlusKit`, `GMTEST`, `VW_MISSING_REFUNDS`, `VRFMERIDIAN`.
- Manages **Meridian and Citi Direct** banking integrations via `VRFMERIDIAN`, `rsm_citidirect_*` views.
- Tracks **missing refund identification** via the `VW_MISSING_REFUNDS` view — a compliance/customer-service view for identifying unfulfilled refund obligations.
- Supports an expanded **contract pricing** capability (`CONTRACTPRICING`, `ItemPricePerContractPlusKit`, `CPVMStockInventoryAuto`).

---

## 3. Business Processes Supported

### 3.1 US Prepaid Program Financial Ledger (Primary)
ECNT is the **primary financial ledger** for Onbe's US domestic prepaid programs, modelling each program as a GP customer with invoices, payments, and credit memos. The Banker SVC reads ECNT for real-time fund verification before card load authorisations.

### 3.2 Enhanced Banker SVC Integration
ECNT includes **all ECAN procedures** plus additional US-specific capabilities:
- `Banker_available_balance` — A dedicated procedure for real-time available balance computation (not present in ECAN, suggesting higher query volume or different balance computation logic for US programs).
- `Account_Balance_Aging` — Accounts receivable ageing by balance bucket for programme management.
- `banker_get_gp_job_history` — Job history (additional to ECAN's job info).

### 3.3 Accounts Receivable Management
ECNT has a richer AR view set: `AR_VIEW`, `ARTOTALVIEW`, `ARVIEW`, `OPENITEMS`, `RMAPPY`, `RMDOCS` — supporting detailed AR analysis, open item tracking, and collection management for US program sponsors.

### 3.4 Missing Refund Tracking
`VW_MISSING_REFUNDS` is a compliance-critical view identifying cases where a refund obligation has been recorded but the corresponding payment has not been issued. This directly supports Onbe's consumer protection obligations under Reg E (electronic fund transfer error resolution) and state money transmitter refund laws.

### 3.5 Meridian Banking Integration
`VRFMERIDIAN` — a verification view for Meridian bank transactions, supporting reconciliation between GP financial records and Meridian bank data.

### 3.6 Contract Pricing
`CONTRACTPRICING`, `ItemPricePerContractPlusKit`, `CPVMStockInventoryAuto` — Support pricing calculations for contracts with kit-level inventory — relevant for prepaid card manufacturing, personalization, and fulfillment contracts.

### 3.7 Historical RSM Citi Direct Integration
`rsm_citidirect_ACH_DTS_old` and `rsm_citidirect_drawdown_DTS_old` (old versions of the Citi Direct views) suggest a migration has occurred within the Citi Direct integration layer, with old views retained for reference.

---

## 4. Data Stored

ECNT holds all GP standard tables plus US-specific operational data:

| Category | Content | Sensitivity |
|----------|---------|-------------|
| GL (journal entries) | Debit/credit amounts, account numbers, journal references | SOX financial |
| SOP (sales orders) | US program invoices, job IDs, tracking files | Commercially sensitive |
| RM (receivables) | US program customer masters, balances, credit limits | Commercially sensitive |
| PM (payables) | US vendor invoices, ACH/check payments | Financial |
| POP (purchasing) | Purchase orders for card stock, personalization services | Operational |
| UPR (payroll) | US employee payroll data | **PII — GLBA, SOX** |
| FA (fixed assets) | US asset base | Financial |
| SLB (budgets) | US budget amounts | Financial |
| Custom | `rsm_customer_rollup` — program-to-GFCID mapping | Reference data |

---

## 5. Regulatory Relevance

| Regulation | Relevance |
|------------|-----------|
| **SOX** | Primary US financial entity; GL, AP, AR records are core SOX financial reporting data. Change management for financial SPs is a SOX ITGC. |
| **Reg E (EFTA)** | `VW_MISSING_REFUNDS` directly supports Reg E error resolution compliance. Missing refunds must be resolved within statutory timeframes (5-10 business days). |
| **GLBA** | US employee payroll data (UPR tables) and program sponsor financial data are NPI subject to GLBA safeguards. |
| **PCI DSS** | Connected system to CDE via Banker SVC; Requirements 6, 7, 8 apply. |
| **NACHA** | ACH payment procedures and Citi Direct integration subject to NACHA operating rules. |
| **State Money Transmitter Laws** | Missing refund identification and resolution directly supports compliance with state money transmitter refund obligations (typically 3–5 business days for electronic refunds). |

---

## 6. Data Flows

```
GP Finance Team ──────────────────► ECNT (invoices, payments, journal entries)
                                         │
Banker API ◄──────────────────────── banker_get_* / Banker_available_balance
                                         │
Finance WebService ◄──────────────── AR views, payment views
                                         │
Compliance reporting ◄───────────── VW_MISSING_REFUNDS
                                         │
Bank reconciliation ◄─────────────── eCountBankTransactions, VRFMERIDIAN
                                         │
DS_ETL_finance-gp / DS_ETL_great-plains ◄── All GP tables → Data Warehouse
```

---

## 7. Integration with Onbe Services

- **Banker API** — primary consumer for US program balance/payment queries; same role as ECAN but for US programs.
- **Order Service** (`ordersvc` login) — reads/writes ECNT for order-to-GP linkage.
- **Accounting Workflow** (`ACCTGWF_APP_GRP`) — finance approval workflows.
- **Atlys** (`ATLYS_APP_GRP`, `NAM_PPA_PRD_ATLYS`) — Atlys reporting reads ECNT.
- **Finance WebService** — `NAM_PPA_PRD_FinSVC` reads ECNT for financial reporting.
- **Refer-a-Friend** (`raf` login) — reads ECNT for financial validation.
- **onus** (`onus` login) — an internal service (likely Operations/Unified) with ECNT access.
- **NAM_sql_svc** — SQL Server service account with database access (backup, maintenance).
- **NAM_ppa_prd_ABAT** — An additional production service account unique to ECNT.
