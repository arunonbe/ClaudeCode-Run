# Business Analyst View — DS_ETL_finance

## Repository Overview

**Repo path:** `E:\OnbeEast363\repos\DS_ETL_finance`
**Solution file:** `Finance.sln`
**SSIS project:** `Finance\Finance.dtproj` (Project Deployment Model)
**Git branch:** `development`
**README:** Empty (9 bytes — placeholder only)

This repository contains the core **financial reporting and reconciliation ETL** for the Onbe prepaid card platform. It houses SSIS packages that compute monthly account balances, identify negative-balance accounts, perform Cambridge bank reconciliation, export GP/CCP billing data, and update Salesforce forecasting data for the Atlys card programme.

---

## Business Purpose

The Finance ETL pipeline serves two primary business functions:

1. **Month-end financial reporting** — Extracting, computing, and delivering month-end account balance snapshots to banking partners (Sunrise, Peoples, MB Financial) and internal stakeholders. These reports are required by card programme agreements and banking partner contracts.

2. **Reconciliation** — The Cambridge reconciliation package ensures Onbe's internal ledger balances match Cambridge's external records. This is a core financial control required under both Reg E (consumer prepaid account accuracy) and SOX (financial statement accuracy).

---

## Packages and Business Processes

### `MonthEnd_NegativeBalance.dtsx` (307 KB — largest package)
**Business process:** Month-end negative balance extraction for all banking partners. Calls a stored procedure (likely `dbo.rpt_Monthly_Account_Balance` with negative filter logic) and exports account-level balance data to a pipe-delimited CSV file on the batch file server (`\\q-na-bat03.nam.wirecard.sys\c-base\runtime\CAS_CSL\`). The output columns are `Account Number`, `Balance` (decimal 18,2), and `Balance EffectiveDate` — financial data.

**Parameters:**
- `Bank` — banking institution name (Sunrise, Peoples, MB)
- `MonthEndStoredProcedure` — stored procedure name (default: `dbo.rpt_Monthly_Account_Balance`)
- `Product` — 4 = US, 6 = Canada, Null = ALL

**Regulatory relevance:** Account balance data for cardholders is subject to **Reg E** accuracy requirements. Negative balances may indicate fee overdrafts, requiring reversal or write-off processes. Under **SOX**, month-end balance reports feed into financial statement preparation.

### `MonthEnd_NonZeroBalance.dtsx` (26 KB)
**Business process:** Extracts all accounts with non-zero balances at month-end. The flat file connection manager (dtsx line 34–66) shows the output schema: `Account Number` (string, 30 chars), `Balance` (decimal 18,2), `Balance EffectiveDate` (datetime). The file naming pattern `MonthlyBalance_YYYYMMDD.csv` is driven by an expression on the connection string.

### `MonthEnd_PositiveBalance.dtsx` (24 KB)
**Business process:** Companion to `MonthEnd_NonZeroBalance` — extracts only positive-balance accounts. Used for reconciliation against banking partner settlement files.

### `NegativeBalance_Snaphot.dtsx` (3.7 KB)
**Business process:** Rolling snapshot of negative-balance accounts. Calls `dbo.usp_rpt_negative_balance_monthly_snapshot` (dtsx line 45) with a parameter `MonthsToKeep` (default 12 months). This enables trend analysis of negative balances over time — relevant for assessing programme health and fee exposure.

### `Cambridge_ReconFile.dtsx` (113 KB)
**Business process:** Generates the Cambridge bank reconciliation file. Cambridge is likely a banking partner providing ACH or wire transfer settlement services. This package extracts transaction-level data and formats it for reconciliation against Cambridge's records.

### `Atlys_RfCks.dtsx` (123 KB)
**Business process:** Atlys programme reverse-fee checks. The "RfCks" abbreviation likely means "Refund Checks" or "Reversal Fee Checks." Processes Atlys card programme refunds or fee reversals against the `ATLYS_FcCR` (Fee Charge Reconciliation) and `ATLYS_RvCR` (Revenue Reconciliation) databases.

### `Export_GP_CCP_PBR.dtsx` (72 KB)
**Business process:** Exports financial data for the GP (Great Plains) / CCP (Client Card Programme) Pre-billing Reconciliation (`PBR`). This feeds the billing cycle for client invoicing — a revenue-generating process.

### `Atlys_recalc_forecast.dtsx` (5 KB)
**Business process:** Recalculates financial forecasts for the Atlys programme. Lightweight package, likely a trigger for a stored procedure that refreshes forecast figures in the reporting database.

### `Salesforce_Update_Atlys_Forecast.dtsx` (73 KB)
**Business process:** Pushes updated Atlys forecast data into Salesforce CRM. This is a CRM integration package — financial forecast data (likely revenue projections, card activation forecasts) is written back to Salesforce for sales/account management visibility.

### `Monthly_Account_Balance.dtsx` (672 bytes — empty stub)
**Status:** Empty package (no executables defined). Created 2021-01-21 by `INT\david.tran`. This appears to be a placeholder or work-in-progress.

---

## Data Flows

```
SQL Server (ATLYS_FcCR / ATLYS_RvCR / cf_report databases)
  → SSIS Transform
    → CSV flat files on \\q-na-bat03.nam.wirecard.sys\c-base\runtime\CAS_CSL\
    → Salesforce (via HTTP/REST in Salesforce_Update_Atlys_Forecast)
    → Great Plains ERP (via Export_GP_CCP_PBR)
```

---

## Schedule / Frequency

Based on package naming:
- **Monthly** — MonthEnd_* packages run at month-end close, likely on the last business day of each month (scheduled via SQL Agent or manual trigger)
- **Daily/On-demand** — `NegativeBalance_Snaphot` and `Cambridge_ReconFile` may run more frequently (daily reconciliation is common for ACH settlement)
- **On-demand** — `Salesforce_Update_Atlys_Forecast` likely runs when forecast models are refreshed (weekly or monthly)

No explicit schedule configuration is present in the repository.

---

## Business Rules Encoded in ETL Transforms

| Rule | Package | Parameter/Logic |
|---|---|---|
| Balance categorisation (positive/negative/non-zero) | `MonthEnd_*.dtsx` | Separate packages per balance type |
| Bank-specific extraction | `MonthEnd_NegativeBalance.dtsx` | `Bank` parameter: Sunrise, Peoples, MB |
| Product segmentation (US/Canada) | `MonthEnd_NegativeBalance.dtsx` | `Product` parameter: 4=US, 6=CA |
| Negative balance retention policy | `NegativeBalance_Snaphot.dtsx` | `MonthsToKeep` default 12 months |
| File naming convention | Multiple packages | Date-stamped CSV filenames via SSIS expressions |

---

## Regulatory Relevance

| Regulation | Relevance |
|---|---|
| **Reg E** | Account balance accuracy — negative balance detection directly supports dispute and fee reversal obligations |
| **SOX** | Month-end balance reports and GP export feed financial statement processes; accuracy controls required |
| **PCI DSS** | `Account Number` column in balance files — if these are card account numbers or PANs, PCI DSS Requirement 3 (protect stored data) applies. Files are written to a UNC share; encryption of the flat file output is not visible in this package |
| **GLBA** | Cardholder financial data (balances) is non-public personal information subject to GLBA safeguarding rules |

**FLAG:** The `Account Number` field (MonthEnd_NonZeroBalance.dtsx line 44) flowing to unencrypted CSV files on a network share (`\\q-na-bat03.nam.wirecard.sys\...`) is a **PCI DSS data-at-rest risk** if these numbers are PANs or truncated PANs. This must be verified and either confirmed as masked/non-PAN values or remediated.
