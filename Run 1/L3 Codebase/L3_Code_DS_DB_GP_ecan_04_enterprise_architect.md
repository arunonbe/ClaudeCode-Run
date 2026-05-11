# DS_DB_GP_ecan — Enterprise Architect View

## 1. Platform Generation

`DS_DB_GP_ecan` is a **Microsoft Dynamics GP company database** for Onbe's Canadian legal entity. It is a fully populated SSDT project containing:
- The standard GP Dexterity library (functions, views, stored procedures) as exported from the GP application.
- Custom Onbe extensions: the `banker_*` procedure and view layer for Banker SVC integration.
- RSM third-party customisations (`rsm_*` views, `GP-RSM-Customization` repo).

The schema provider `Sql100` targets SQL Server 2008 R2 compatibility — appropriate for GP 10.x/12.x era installations. GP 18.x (current) runs on SQL Server 2016–2022; the schema provider setting should be updated.

---

## 2. Architectural Role

ECAN is the **financial ledger of record** for all Canadian prepaid program operations. In the broader Onbe architecture:

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Banker SVC Architecture                          │
│                                                                     │
│  banker_API ──────────────────────────────────────────────────────► │
│                 │                                                   │
│       ┌─────────▼────────────────────────────────────────────────┐  │
│       │  ECAN (DS_DB_GP_ecan)                                    │  │
│       │  - banker_get_* procedures (real-time balance/payment)   │  │
│       │  - banker_insert/delete_multiple_so (write ops)          │  │
│       │  - BankerProgram view (credit limits, balances)          │  │
│       │  - BankerAllSOView (invoices + history)                  │  │
│       │  - eCountBankTransactions (GL reconciliation)             │  │
│       └──────────────────────────────────────────────────────────┘  │
│                 │                                                   │
│       DYNAMICS  │  (auth + company registry)                       │
│                 │                                                   │
│       DS_ETL_finance-gp ──► Data Warehouse / Reporting             │
│       DS_ETL_great-plains                                           │
└─────────────────────────────────────────────────────────────────────┘
```

ECAN serves as the **single source of truth** for Canadian program funding balances, invoice obligations, and payment receipts. The Banker API queries ECAN in real time to determine whether sufficient funds exist before authorising card loads and disbursements.

---

## 3. Dependencies

### 3.1 Upstream Systems Writing to ECAN
- **GP Client Application** — Finance team enters invoices, payments, credit memos, and journal entries.
- **Banker API** — `banker_insert_multiple_so` creates invoices programmatically.
- **eConnect** — Potential automated document creation via eConnect integration.
- **RSM (third-party GP customisation)** — Citi Direct banking integration (`rsm_citidirect_*`).

### 3.2 Downstream Consumers Reading ECAN
| Consumer | Objects Accessed | Access Method |
|----------|-----------------|---------------|
| `banker_API` | `banker_get_*` procedures, `BankerProgram`, `BankerAllSOView`, `BankerACH`, `BankerPayment` | `Banker_execute` role, `NAM\PPA_PRD_CLU` |
| `finance-webservice_API` | Standard GP views, `eCountBankTransactions`, `PROGRAMS` | `NAM\PPA_PRD_FinSVC` |
| `accounting-workflow_WAPP` | GP document tables | `ACCTGWF_APP_GRP` |
| `DS_ETL_finance-gp` | All GP tables | Service account |
| `DS_ETL_great-plains` | GL, AP, AR, payroll tables | Service account |
| `atlys_WAPP` | `ATLYS_APP_GRP` role | Service account |
| `order_SVC` | `ordersvc` login | Order service |

---

## 4. Banker SVC Dependency Analysis

The Banker SVC is the **highest-criticality consumer** of ECAN. The following dependency chain shows how a failure in ECAN would propagate:

```
ECAN database unavailable
    │
    ▼
banker_get_program_info → returns null / error
    │
    ▼
Banker API cannot verify available funds
    │
    ▼
Card load / disbursement requests rejected or stalled
    │
    ▼
Cardholder unable to access funds → Reg E violation risk (Requirement 11: prompt resolution of EFT errors)
```

**Recovery Time Objective (RTO) for ECAN should be very low** — any outage directly impacts cardholder fund access.

---

## 5. Migration Complexity Assessment

| Factor | Assessment |
|--------|-----------|
| Schema complexity | High — 195 functions, 150 views, 100+ SPs, full GP table set |
| Custom Banker integration | High — 25 custom procedures/views are critical to Banker SVC operation |
| RSM third-party dependency | Medium — RSM views depend on `rsm_customer_rollup` custom table |
| Canadian regulatory compliance | Medium — PIPEDA, Quebec Law 25 requirements for data handling |
| GP end-of-life risk | High — GP mainstream support ends 2025 |
| Cloud migration complexity | High — full GP stack migration to D365 Business Central or Azure SQL MI |

**Migration path**: D365 Business Central (Microsoft's GP successor) for the GP financial layer. The `banker_*` procedure integration would need to be re-implemented against the D365 Business Central API or a replacement financial system. This is a significant programme requiring parallel operation and Banker SVC refactoring.

---

## 6. Cross-Regional Data Isolation

ECAN represents a distinct legal entity (Onbe Canada). Data isolation from ECNT (Central/US) and EMEAM (EMEA) is enforced at the GP company database level — each company database is a separate SQL database. However:
- DYNAMICS credentials are shared across all companies.
- The `rsm_customer_rollup` custom table may contain cross-company program data.
- Windows Authentication service accounts (`NAM\PROD`) have access to multiple company databases.

**Gap**: A compromised service account with DYNGRP or Banker_execute privileges could query financial data across ECAN, ECNT, and EMEAM simultaneously. Regional data isolation is logical (database-level) but not physical.
