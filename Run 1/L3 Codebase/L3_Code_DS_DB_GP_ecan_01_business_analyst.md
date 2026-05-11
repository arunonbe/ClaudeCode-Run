# DS_DB_GP_ecan — Business Analyst View

## 1. Repository Identity

| Attribute | Value |
|-----------|-------|
| Repo name | DS_DB_GP_ecan |
| Project file | `ecan.sqlproj` (SSDT, DSP Sql100) |
| Solution file | `ecan.sln` |
| README | One line: "ecan" |
| Database name | ECAN — GP Canada company database |
| Regions served | Canadian operations |

---

## 2. Business Purpose

`DS_DB_GP_ecan` is the **Microsoft Dynamics GP company database for Onbe's Canadian operations**. Within GP's multi-company architecture, ECAN represents a distinct legal entity operating under Canadian financial and regulatory requirements. This database:

- Records all **financial transactions** for Onbe Canada: accounts payable (AP), accounts receivable (AR), general ledger (GL), payroll, fixed assets, purchasing (POP), and sales order processing (SOP).
- Hosts **Banker SVC integration** — a rich set of custom stored procedures and views (`banker_*`) that expose GP financial data to the Banker API, enabling real-time balance queries, document lookups, and payment verification for Onbe's prepaid card disbursement programs operating in Canada.
- Supports **budget management** through the SLB budget table series and associated views.
- Provides **financial reconciliation** between GP-recorded payments and the prepaid card program balances managed by EcountCore.
- Manages **client refund processing** via the `client_refund_*` function series.
- Handles **ACH / check / cash payment classification** through the `BankerACH`, `BankerCashReceipts`, `BankerPayment` views.
- Supports **1099 tax reporting** through `DYN_FUNC_1099_*` functions (relevant for US vendors in the Canadian entity, or cross-border compliance).

---

## 3. Business Processes Supported

### 3.1 Prepaid Program Financial Ledger
The core purpose of the Banker SVC integration layer is to serve as the **financial ledger of record** for prepaid card programs operated by Onbe Canada. Each prepaid program is modelled as a GP "customer" (in the RM/AR module), with:
- **Invoices** representing card loads / disbursements billed to the program sponsor.
- **Payments** representing sponsor funding receipts (ACH, wire, check).
- **Credit memos** representing refunds or adjustments.
- **Program balance** = sum of unmatched payments minus outstanding invoices (managed through the `BankerProgram`, `BankerAllSOView`, `BankerSOView` views and supporting functions).

### 3.2 Banker SVC Integration
The `banker_*` stored procedures are the primary integration interface with the Banker API (`banker_API` repo). Key capabilities:
- `banker_get_program_info` — Returns credit limit, currency, and current balance for a program.
- `banker_get_documents` — Returns all GP Sales Order documents (invoices, credits, orders) for a program, filtered by job ID.
- `banker_get_payments` — Returns all payment receipts for a program.
- `banker_get_free_funds` / `banker_get_unsettled_funds` — Computes available funding after netting payments against obligations.
- `banker_get_321_days_payments` / `banker_get_x_days_payments` — Queries payments within configurable date windows for float management.
- `banker_get_active_promotions` — Returns active promotion/promo codes for a program.
- `banker_insert_multiple_so` / `banker_delete_multiple_sos` — Creates or removes Sales Orders (invoices) on behalf of the Banker service.
- `banker_get_gp_job_info`, `banker_get_gp_payment_info`, `banker_get_gp_program_info`, `banker_get_gp_promoexception_info` — Unified info-retrieval procedures for job-level GP data.

### 3.3 Financial Reconciliation
The `eCountBankTransactions`, `eCountBankHistTransactions`, `eCountBankTrxUnPosted`, and `eCountBatchGLTrx` views expose GL journal entries for bank account reconciliation between GP and the EcountCore cardholder account system.

### 3.4 Client Refund Processing
`client_refund_parseStringToTable` parses delimited refund instruction strings into table format for batch processing — supporting the client refund workflow in the Banker SVC.

### 3.5 ACH Payment Delay Management
`banker_get_ach_delay` — Returns the configured ACH settlement delay (days to usable funds); `banker_get_required_deposit_date` — Calculates the deposit date required for a payment to be usable by a target date, accounting for Canadian banking business days.

### 3.6 Budget and Financial Reporting
Standard GP views (AccountSummary, AccountTransactions, GLPOSTEDSUMMARY, PayablesTransactions, ReceivablesTransactions) plus the custom `eCountCOA` (Chart of Accounts), `CitiPrepaidAPAgeTBbyAccNum` (AP ageing by account number), and RSM custom reporting views (`rsm_citidirect_ACH_DTS`, `rsm_citidirect_drawdown_DTS`, `RSM_UNPOSTED_SALES_DOCS`, `rsmCitiDirectTrx`, `rsmCDTRXView`) support financial reconciliation with Citi Direct banking infrastructure.

### 3.7 Tax and 1099 Reporting
The `DYN_FUNC_1099_Box_Type` and `DYN_FUNC_1099_Type` functions support IRS 1099 classification for vendor payments — relevant for cross-border US-Canada vendor operations and contractor payments.

---

## 4. Data Stored

Key GP standard tables (live data in production ECAN database):

| Table Series | Module | Data |
|-------------|--------|------|
| `GL00100`, `GL20000`, `GL30000` | General Ledger | Chart of accounts, journal entries (current + history) |
| `SOP10100`, `SOP30200` | Sales Orders | Program invoices (open and history), void status, job IDs, tracking numbers |
| `SOP10106`, `SOP10107` | Sales Order Extensions | Job ID (`USERDEF1`), file tracking number (`Tracking_Number`) |
| `RM00101`, `RM00103`, `RM00303` | Receivables | Customer (program) master, balances, addresses, full legal name (`COUNTRY` field alias) |
| `PM*` series | Payables | Vendor invoices, payments, AP ageing |
| `POP*` series | Purchasing | Purchase orders, receipts |
| `UPR*` series | Payroll | Employee pay data (Canadian payroll) |
| `FA*` series | Fixed Assets | Asset master, depreciation |
| `SLB*` series | Budgets | Budget amounts, categories, ranges |
| Custom | Banker / RSM | `rsm_customer_rollup` — maps GP customer numbers to program IDs, GFCID, and base numbers for consolidated reporting |

---

## 5. Regulatory Relevance

| Regulation | Relevance |
|------------|-----------|
| **PIPEDA / Quebec Law 25** | ECAN processes Canadian consumer data; PIPEDA and Quebec Law 25 (privacy) apply to any personal information stored in employee, vendor, or cardholder-related records. |
| **SOX** | Financial transaction records (GL, AP, AR) for a public/regulated company's Canadian entity are subject to SOX financial reporting controls. Change management to financial stored procedures is a SOX ITGC. |
| **GLBA** | Canadian operations may be subject to GLBA if handling US-connected consumer financial data. |
| **PCI DSS** | ECAN is a **connected system** to the prepaid card CDE (via Banker SVC). Not a CDE itself, but Requirement 6 (patch management) and Requirement 7/8 (access controls) apply. |
| **NACHA** | ACH payment functions (`banker_get_ach_delay`, `BankerACH` view) are subject to NACHA operating rules for electronic fund transfers. |
| **Canadian AML / FINTRAC** | Financial disbursement records may be subject to FINTRAC reporting for large cash transactions or suspicious activity in the Canadian entity. |

---

## 6. Data Flows

```
Banker API (banker_API)
    │
    ▼ Calls banker_get_* stored procedures
DS_DB_GP_ecan (ECAN company database)
    │  reads SOP10100/SOP30200 (invoices)
    │  reads/writes RM00101/RM00103 (program balances)
    │  reads CM/PM (payments, receipts)
    ▼
DYNAMICS (SY01400 user auth, SY01500 company lookup)
    │
    ▼
Finance WebService / ETL pipelines
    ├── DS_ETL_finance-gp
    └── DS_ETL_great-plains → Data Warehouse
```

---

## 7. Integration with Onbe Services

- **Banker API** — primary consumer; reads all `banker_*` views and calls all `banker_*` procedures via `NAM\PPA_PRD_CLU` (Banker service account), `NAM\PPA_PRD_FinSVC` (Finance service), and the `Banker_execute` role (granted to `NAM\PROD`).
- **Finance WebService** — consumes standard GP views for financial reporting.
- **DS_ETL_finance-gp / DS_ETL_great-plains** — ETL extraction from GL, AP, AR for data warehouse.
- **accounting-workflow_WAPP** — Finance approval workflow consuming GP data.
- **Atlys** — `ATLYS_APP_GRP` and `NAM_PPA_PRD_ATLYS` grant indicate Atlys reads ECAN data.
- **ordersvc** — `ordersvc` login and role membership suggest the Order Service reads/writes ECAN.
- **raf (Refer-a-Friend)** — `raf` login indicates the Refer-a-Friend service accesses ECAN financial data.
