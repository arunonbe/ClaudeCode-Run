# Business Analyst Analysis — DS_DB_ATL_atlys_fc_nca (atlys_fc_nca)

## Repository Identity
- **Database name:** atlys_fc_nca
- **Project GUID:** a3ba0317-9350-47c3-9850-fe273567c4ae
- **Region scope:** North/Central America (NCA)
- **SQL Server compatibility:** level 90 (SQL Server 2005 target)
- **Active git branch:** `development`

---

## Business Purpose

`atlys_fc_nca` is the **fee-calculation and revenue-forecasting database** for Atlys programs operating in the North and Central America region. It performs financial modelling and actuarial calculations that determine how much revenue Onbe expects to earn from prepaid card programs over their lifetime. This database is the financial engine of the Atlys platform for the NCA region and feeds management reporting, sales pipeline valuations, and GL amortisation entries.

---

## Key Business Processes

### 1. Program Lifecycle and Fee Configuration (`cursforecast` table)
The central table `cursforecast` (`dbo/Tables/cursforecast.sql`) holds one row per prepaid card program, capturing all fee and behavioural assumptions:
- **Issuance fee:** `issue_fee DECIMAL(6,3)` — fee charged per card issued (percentage of load amount when `issue_type=1`, or per-payment count otherwise).
- **Card fee:** `card_fee DECIMAL(5,3)` — plastic production cost per card.
- **Load fee:** `load_fee FLOAT` — reload/load transaction fee.
- **Recurring fee:** `rec_fee DECIMAL(4,2)` — periodic maintenance fee.
- **Face Value Discount (FVD):** `fvd_rate FLOAT` — percentage of card face value retained as fee income upon expiry/dormancy.
- **Dormancy parameters:** `dorm_wait INT`, `dorm_table SMALLINT`, `dorm_db_rate NUMERIC(3,2)`, `dorm_db_months SMALLINT` — dormancy fee recognition schedule.
- **Utilisation rates:** `util`, `util_ret`, `util_atm`, `util_ach`, `util_ck`, `util_pin` — spend pattern assumptions by transaction type.
- **Unclaimed/breakage:** `claim_rate`, `unclaimed_keep`, `unclaimed_months` — breakage income projections.
- **BIN and card type:** `bin VARCHAR(7)`, `card_type VARCHAR(10)`, `bank_code VARCHAR(10)`.
- **Salesforce integration fields:** `ext_id VARCHAR(10)` links to external CRM system.

### 2. Issuance Fee Calculation (`sys_calc_issue.sql`)
`sys_calc_issue` (`dbo/Stored Procedures/sys_calc_issue.sql`) computes forecast issuance fee revenue for a program by:
1. Joining `vFCIssuance` (forecast issuance volumes) to `cursforecast` fee assumptions.
2. Applying the fee formula: if `issue_type=1` → percentage of issuance amount; otherwise → payment count times issue fee.
3. Upserting results into `tblForecast_data` (`line_cde = 'ISSUE01'` or similar).

### 3. Dormancy Fee and Face Value Discount Calculation (`sys_calc_dormancy.sql`)
One of the most complex procedures in the codebase. It models the expected maintenance fee and FVD revenue from unredeemed card balances over time using an amortisation schedule derived from `tblAmort_Tables_1` / `tblAmort_Tables_2`. The procedure:
- Retrieves actual maintenance fee data from the SSAS cube (via `ATLYS_E.dbo.sys_cinfo` → `sys_execcview`) for already-issued cards.
- Constructs a declining-balance dormancy schedule parameterised by `dorm_db_rate` and `dorm_db_months`.
- Accounts for breakage (claimed vs. unclaimed portions) using `claim_rate` and `util`.
- Handles fiscal-period-based programmes separately from calendar-month programmes.
- Writes amortisation rows into the temporary table `#cursDorm` which is consumed by calling procedures.
- Supports both actual-date reconciliation and forward-looking forecast.

### 4. Commission Calculation (`sys_calc_comm.sql`)
Calculates sales-representative commissions payable on program revenue, writing results to `tblCommissions`. Commission is driven by `cursforecast.comm_new_fee`, `comm_pmt_fee`, `comm_issue_fee` and the revenue amounts from `tblForecast_data`.

### 5. Interchange Fee Calculation (`sys_calc_interchange.sql`)
Models network interchange income based on spend utilisation rates and card-programme interchange schedules.

### 6. Recurring Fee Calculation (`sys_calc_recur.sql`)
Computes periodic (monthly/annual) maintenance fee revenue based on `rec_fee` and active card counts.

### 7. Plastic (Physical Card) Cost Calculation (`sys_calc_plastic.sql`)
Forecasts card production costs using `card_fee` and projected issuance volumes from `tblPlastics`.

### 8. Reissuance Calculation (`sys_calc_reissue.sql`)
Models replacement card issuance costs and associated fee income on card renewals.

### 9. Forecast Versioning and Management
The system supports multiple named versions of a forecast (`tblForecast_Version`), a change log (`tblForecastChangeLog` — triggered automatically when `exclude` flag changes on `cursforecast`), and a dashboard summary table (`tblDash_data`). Procedures include `sys_newforecastversion`, `sys_create_forecast`, `sys_recalc_forecast`, `sys_forecast_update`, `sys_forecast_version`.

### 10. Revenue Reporting
The `sys_revenue_cross_tab`, `sys_spend_cross_tab`, `sys_issuance_cross_tab`, `sys_plastics_cross_tab`, `sys_costs_cross_tab` family of procedures produce pivoted month-column reports consumed by the Atlys UI for actual-vs-forecast analysis.

### 11. Costs Tracking
`tblCosts` and related procedures (`sys_costs_post`, `sys_costs_print`, `sys_costs_forecast`, `sys_costs_lines`) track external costs (e.g., card production vendor invoices) associated with a program.

### 12. Amortisation Posting
`sys_amortization`, `sys_amortization_dorm`, `sys_amortization_issuance_post`, `sys_amortization_rev_post` handle the period-end accounting amortisation entries that feed into the GL.

### 13. Salesforce Data Copy
`sys_copy_table_data` is a generic dynamic table-copy procedure used for data migration between tables. It contains cross-database calls to `ATLYS_E.dbo.sys_chkstr` for SQL-injection validation.

---

## Regulatory Relevance

### PCI DSS
`atlys_fc_nca` contains a `bin VARCHAR(7)` column in `cursforecast` (line 106). This BIN (Bank Identification Number) field identifies the card network and issuing bank prefix. While a BIN alone is not a PAN, its presence in conjunction with program financial data means this database has **indirect CDE adjacency**. The `card_type` and `bank_code` fields further describe card characteristics. Under PCI DSS v4.0.1, any system that stores BIN data associated with cardholder programmes should be evaluated for CDE scope.

The `util_atm`, `util_ach`, `util_ret`, `util_pin` utilisation rate columns model spend behaviour across transaction types including ATM withdrawals and ACH transfers — confirming this database works with prepaid debit/payment card programmes subject to Reg E and NACHA rules.

### NACHA
The presence of `util_ach` (ACH utilisation rate) in `cursforecast` and the ACH-related fee projections confirm these programs include ACH-enabled prepaid products. The financial models in this database therefore underpin revenue projections for products subject to NACHA Origination and Return rules.

### Reg E
Prepaid card programs with the features modelled here (load, reload, ATM, point-of-sale utilisation) are Regulation E-governed products. The dormancy and FVD income modelling directly relates to Reg E prepaid account rules regarding fee transparency and expiry.

### ASC 606 / Revenue Recognition
The amortisation and deferred revenue tables (`tblForecast_Fees`, `sys_amortization_rev_post`) suggest this database supports ASC 606 / IFRS 15 revenue recognition accounting — specifically, the recognition of breakage income and FVD income over the expected card utilisation period. This is a key financial reporting obligation.

---

## Key Business Entities

| Entity | Table/View | Purpose |
|---|---|---|
| Program (affiliate) | `cursforecast` | Core program record with all fee assumptions |
| Forecast version | `tblForecast_Version` | Named snapshot of forecast for period |
| Issuance data | `tblIssuance` | Monthly issuance volumes (cards, amounts, payments) |
| Plastic data | `tblPlastics` | Physical card production volumes |
| Spend data | `tblSpend` | Card spend transaction volumes |
| Forecast revenue | `tblForecast_data` | Monthly forecast revenue by line code |
| Forecast fees | `tblForecast_Fees` | Fee assumption overrides per forecast |
| Costs | `tblCosts` | External/vendor cost items |
| Commissions | `tblCommissions` | Sales rep commission payables |
| Amortisation tables | `tblAmort_Tables_1`, `tblAmort_Tables_2` | Dormancy recognition schedules |
| Dashboard data | `tblDash_data` | Pre-aggregated management dashboard data |
| Program defaults | `tblPrgDflt` | Default fee assumptions for new programs |
| Controls | `tblControls` | Period control dates (fiscal year start/end, version date) |
| Forecast change log | `tblForecastChangeLog` | Audit trail of forecast exclusions/inclusions |

---

## Summary Assessment

`atlys_fc_nca` is a financially critical system supporting revenue forecasting, sales commission management, GL amortisation, and management reporting for Onbe's NCA prepaid card portfolio. Its calculations directly impact how revenue is recognised in financial statements and how sales incentives are paid. Errors or unauthorised changes to fee assumptions in `cursforecast` could materially misstate financial reporting or improperly inflate commission payouts.
