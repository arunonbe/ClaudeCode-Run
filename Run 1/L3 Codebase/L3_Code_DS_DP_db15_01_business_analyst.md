# Business Analyst Report — DS_DP_db15

## Repository Identity

**Repository:** DS_DP_db15  
**Classification:** Data Processing — Database Shard 15  
**Technology:** Microsoft SQL Server (T-SQL), stored procedure parameters  
**Script count:** 9 SQL change scripts  
**Date range:** February 2021 – January 2023  

---

## Business Purpose

DS_DP_db15 is the change-script repository for **Processing Database Shard 15**, which appears to be a specialised analytics and risk-management shard distinct from the transaction-processing shards (db01–db08). The primary database referenced is `RiskDB`, with secondary cross-shard references to `cf_report`, `ECountcore_ss`, and `reportingdbserver2008`.

Based on the scripts present, shard 15's primary business functions are:

1. **ATM fleet management and cash forecasting** — The largest script (`20210503_SQ-3028_CREATE - OnbeATM_CashForecastDetail.sql`, 53 KB) creates the `OnbeATM_CashForecastDetail` report inside `RiskDB`, consuming ATM terminal data from the DMT (Data Management Tool) infrastructure.

2. **Financial reporting for prepaid card programs** — Stored procedure reports covering emboss/stock reconciliation, build rollbacks, and POD (Point-of-Disbursement) transition tracking.

3. **Face Value Discount (FVD) contract configuration** — Structured contract terms for FVD tiers are maintained in the `EUC_DMT_ContractSummary_FIELDS` and related tables.

4. **SPAMAP (Special Program Account Mapping) configuration** — The `spamap_update_query.sql` file updates program-to-account mappings in `EUC_DMT_SPAMAP_DATA`.

5. **Program ID management** — `2023011023_US-567963 - 211 - Update Program IDs for TXU.sql` updates program identifiers for a specific client (TXU Energy, a utility rebate client).

---

## Key Business Processes Supported

### 1. OnbeATM Cash Forecast Detail Reporting
The `OnbeATM_CashForecastDetail` query (file: `20210503_SQ-3028_CREATE - OnbeATM_CashForecastDetail.sql`) is a complex multi-join analytical query registered in `RiskDB.dbo.qryReports` via the `rpt_qryReports_QRY_Insert` stored procedure. It:
- Aggregates ATM terminal cash dispense data from `EUC_DMT_ATM_DATACACHE`, `EUC_DMT_ATM_DATAChangesetCACHE`, and `EUC_DMT_ATM_DATA` tables
- Builds cash forecast detail by terminal, including removal states (permanent codes 4 and 5)
- References `reportingdbserver2008` via linked server for historical data access
- Uses `OPENQUERY` against the linked server for specific data retrieval (lines 75–84)

This report supports **ATM network cash management decisions** — specifically, forecasting how much cash each terminal needs for replenishment, which is a critical operational function for Onbe's ATM fleet supporting prepaid cardholders.

### 2. Face Value Discount Tier Configuration
File `20210201_SQ-1841_DB15 Face Value Discount Percentage update in DMT CSF.sql` (15.7 KB):
- Renames the "Face Value Discount" category to "Face Value Discount Flat" in `EUC_DMT_ContractSummary_FIELDS`
- Inserts a new "Face Value Discount Percentage" category hierarchy with approximately 30+ discount tier bands (e.g., `$0.00–$4.99`, `$0.00–$29.99`, through `$100+`)
- Items are identified by numeric codes in the 85000 series

FVD is a key commercial term in Onbe's retailer and issuer relationships — the discount tier configuration directly governs revenue recognition and client billing.

### 3. Emboss and Stock Reporting
File `20210315_SQ-1820_ALTER - 131 - Stock - No Change Balance.SQL` updates a stored report query (`qryReports ID 131`) that tracks:
- Plastic card emboss history vs. vendor balance changes
- Identifies stock items where the vendor balance has not changed despite expected emboss activity (fraud/discrepancy detection)
- References `cf_report.dbo.JAX_Plastic_Volumes`, `cf_report.dbo.HJ_Forms_Volumes`, `ECountcore_ss.dbo.psx_inventory_file`, and `ECountcore_ss.dbo.fdr_process_report_inventory_management`
- Parameters: 21-day period span, 7-day vendor padding, 90% emboss accountability threshold, 50-unit minimum

This report supports the **inventory reconciliation** process, detecting potential emboss discrepancies that could indicate fraudulent card production.

### 4. Build DB Rollback and POD Transition Reporting
Files `20210315_SQ-1820_ALTER - 191 - Build DB Roll Backs.SQL` and `20210315_SQ-1820_ALTER - 216 - Emboss Report - POD Transition.SQL` update additional operational reports for card inventory build management and point-of-disbursement transitions.

### 5. Program and Account Mapping
The `spamap_update_query.sql` file maps programs to accounts in `EUC_DMT_SPAMAP_DATA` by joining with `EUC_DMT_Separation_DATACACHE` on field ID 16, then running `EUC_DMT_updaterelated` to cascade the change. This maintains the relationship between card programs and their corresponding bank accounts.

### 6. State/Territory Program Restrictions
File `20221102_US-560043_ALTER - 122 - Remove selected States and Territories.sql` removes specific US states or territories from a program, likely reflecting regulatory or compliance restrictions on card distribution in those jurisdictions.

### 7. TXU Energy Program Configuration
File `2023011023_US-567963 - 211 - Update Program IDs for TXU.sql` updates program identifiers for TXU, a utility company client offering prepaid rebate or incentive cards. This represents the **client program onboarding/modification** process.

---

## Regulatory Relevance

### PCI DSS
- `RiskDB` contains ATM transaction and card account data via linked-server references to `ECountcore_ss` (which contains `fdr_card_account`, `fdr_card_account_detail`, `core_card_account_emboss_history` tables). These tables are within the **Cardholder Data Environment (CDE)** scope. PCI DSS Req 3 (protect stored cardholder data) applies.
- The emboss history query joins on `fdr_card_account.dda_number` (lines 52–54 of the Stock query), extracting the first 8 digits (`LEFT(fca.dda_number,8)`) as a program identifier. The full `dda_number` field could constitute a card account number — this should be formally scoped and classified.

### NACHA
- DDA (Demand Deposit Account) number references in card account queries suggest ACH account linkage. NACHA data handling requirements apply.

### GLBA
- ATM cash forecast data contains terminal-level financial data that constitutes financial institution operational data under GLBA.

### SOX
- FVD tier configuration directly affects revenue recognition calculations. Changes to these tiers should be subject to SOX change control procedures.

---

## Change Management Observations

The repository is sparse (9 files over 2 years) compared to DB08, suggesting DB15 is a lower-volume analytical shard with infrequent configuration changes. The ticket prefix `SQ-` (2021) transitioning to `US-` (2022–2023) aligns with the Onbe platform ticket migration observed across other repos. The absence of rollback scripts continues the same pattern observed in DB08.
