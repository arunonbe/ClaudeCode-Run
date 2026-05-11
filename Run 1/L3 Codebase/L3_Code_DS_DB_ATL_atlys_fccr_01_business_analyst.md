# Business Analyst Analysis — DS_DB_ATL_atlys_fccr (atlys_fccr)

## Repository Identity
- **Database name:** atlys_fccr
- **Project GUID:** 8ddae437-ee85-49ae-8ed6-27e94f3a391e
- **Variant:** Fee calculation — credit (fccr = fee calculation credit)
- **SQL Server compatibility:** level 90 (SQL Server 2005 target)
- **Active git branch:** `development`
- **Solution file:** `atlys_fccr.sln` (one of only two repos in this batch with a `.sln` file, alongside `atlys_rv_nca`)

---

## Business Purpose

`atlys_fccr` is the **credit-variant fee-calculation database** for the Atlys platform. The `cr` suffix distinguishes it from the standard debit/prepaid fee-calculation databases (`atlys_fc_nca`, `atlys_fc_nus`). This database handles fee calculation and revenue forecasting for **credit-type card programs** or for programs that have specific credit-related fee structures that differ from standard prepaid debit/load programs.

The database shares the same operational backbone as the NCA and NUS fee-calculation databases (same stored procedure architecture, same reporting framework) but contains additional capabilities not present in those databases:
1. **Salesforce bi-directional integration** (`sys_sf_import.sql`, `sys_sf_upload.sql`, `Salesforce_to_Atlys` table)
2. **Extended dashboard views** (`sys_dash_details2_cross_tab`)
3. **Forecast views management** (`sys_forecastviews`, `tblForecastReports`, `tblForecastViews`)
4. **Report management** (`sys_reports`, `sys_sf_upload` revenue reporting)
5. **Deferred revenue pipeline** (all `sys_deferredrevenue_*` procedures present)
6. Additional security file: `Prod_Support_Schema_View.sql`, `Prod_Support_Select.sql`, `Prod_Support_Update.sql`, `Prod_Support_execute.sql` — same extended Prod_Support role set as `atlys_e`
7. `NAM_PROD_CPP_APAC.sql` — APAC CPP variant present (unlike NCA/NUS)

---

## Key Business Processes

### 1. Credit Programme Fee Calculation
Unlike prepaid debit programs where revenue comes from load fees, issuance fees, and dormancy, credit programs may generate revenue from:
- **Interchange fees** on credit transactions (`sys_calc_interchange`)
- **Recurring service fees** (`sys_calc_recur`)
- **Issuance/setup fees** (`sys_calc_issue`)
- **Commission on credit volume** (`sys_calc_comm`)

Note: The `sys_amortization` procedure is present but variants like `sys_amortization_dorm` (dormancy-specific) are **not listed** in the `atlys_fccr.sqlproj`, suggesting credit programs may not have traditional dormancy/maintenance fee structures. This is consistent with credit products that have different expiry and inactivity rules compared to prepaid debit.

### 2. Salesforce Integration (Enhanced vs. NCA/NUS)
`atlys_fccr` has two Salesforce-related features not present in the basic NCA/NUS databases:

**`Salesforce_to_Atlys` table (`dbo/Tables/Salesforce_to_Atlys.sql`):**
A staging table for inbound Salesforce data containing:
- `Opportunity Name`, `Account Name`, `Program ID`
- `Average Amount Per Card Per Load`, `Annual Account Volume`
- `Close Date`, `BIN Sponsor`, `Stage`, `Last Modified Date`, `Import Date`

This table is a direct Salesforce import staging area. The `Import Date` column (defaulting to `GETDATE()`) is used to track when each import batch was received. The clustered index on `(Program ID, Last Modified Date)` supports incremental synchronisation.

**`sys_sf_import` procedure:** Imports data from the `Salesforce_to_Atlys` staging table into the main `cursforecast` program master.

**`sys_sf_upload` procedure (`dbo/Stored Procedures/sys_sf_upload.sql`):** Generates a revenue cross-tab report in a format suitable for upload back to Salesforce (`@report = 's'` parameter returns the schema; when executed, calls `sys_revenue_cross_tab` with Salesforce-specific parameters). This implements a two-way integration where Atlys revenue forecasts are pushed back into Salesforce opportunities to populate deal economics.

### 3. Forecast Report Configuration
`tblForecastReports` and `tblForecastViews` are unique to `atlys_fccr`. These tables configure which report views and layouts are available in the Atlys UI for the credit portfolio. `sys_forecastviews` manages this configuration. `sys_reports` is a report registry procedure.

### 4. Extended Dashboard
`sys_dash_details2_cross_tab` provides a second level of dashboard detail drill-down not present in the standard NCA/NUS databases, suggesting the credit portfolio dashboard has more detailed reporting requirements.

### 5. Deferred Revenue Management
All `sys_deferredrevenue_*` procedures are present, managing the recognition of deferred revenue balances over time for credit program fee income.

### 6. Commission and Revenue Reporting
Full suite of commission, revenue, spend, issuance, plastics, and variance cross-tab reports as in NCA/NUS.

---

## Regulatory Relevance

### PCI DSS
`cursforecast.bin VARCHAR(7)` stores BIN data for credit card programmes. **Credit card BINs are in-scope for PCI DSS CDE evaluation** — a credit card BIN directly identifies the card network and product type, and credit programs by definition involve payment card data. The database is connected-system scope at minimum; depending on what data flows through the GL integration and the Salesforce integration, scope may be broader.

### Reg E
Credit card programs are generally **not** subject to Regulation E's prepaid account rules (Reg E applies to electronic fund transfers from deposit accounts). However, if `atlys_fccr` models any programs that have both credit and prepaid/debit features (e.g., secured credit cards with prepaid elements), those programs may have mixed regulatory treatment.

### Truth in Lending Act (TILA) / Reg Z
Credit card programs are subject to Regulation Z (Truth in Lending). Fee structures modelled in `atlys_fccr` — setup fees, annual fees, service charges — may need to comply with Reg Z disclosure requirements. The `sys_sf_upload` procedure feeds Atlys fee economics back to Salesforce for client-facing communications; if these figures are used in credit card pricing disclosures, accuracy is a TILA compliance requirement.

### NACHA
Less directly relevant for credit programs, but commission calculations tied to payment volumes on credit accounts may involve ACH settlement amounts.

### ASC 606 / Revenue Recognition
The deferred revenue management (`sys_deferredrevenue_*`) and amortisation procedures support ASC 606 revenue recognition for credit programme fees. Setup fees, annual fees, and recurring service charges must be recognised appropriately over the service period.

---

## Unique Features vs. NCA/NUS

| Feature | atlys_fccr | atlys_fc_nca/nus |
|---|---|---|
| Salesforce_to_Atlys staging table | YES | NO |
| sys_sf_import procedure | YES | NO |
| sys_sf_upload procedure | YES | NO |
| tblForecastReports / tblForecastViews | YES | NO |
| sys_forecastviews / sys_reports | YES | NO |
| sys_cblists procedure | YES | NO |
| sys_dash_details2_cross_tab | YES | YES (NCA/NUS also have it) |
| sys_amortization_dorm (dormancy-specific) | NO | YES |
| sys_create_issuance / sys_create_plastics | NO | YES (NCA only) |
| sys_costs_post / sys_costs_print | NO | YES |
| sys_probability | YES | YES |
| NAM_PROD_CPP_APAC.sql | YES | NO (NCA also has it) |
| Prod_Support role files | YES | NO |
| .sln file | YES | NO |

---

## Key Business Entities

Same as NCA/NUS plus:

| Entity | Table | Purpose |
|---|---|---|
| Salesforce opportunity | `Salesforce_to_Atlys` | Inbound CRM opportunity staging |
| Forecast report config | `tblForecastReports` | Report layout configuration |
| Forecast view config | `tblForecastViews` | View layout configuration |

---

## Summary Assessment

`atlys_fccr` is a more feature-rich variant of the Atlys fee-calculation platform, extending the standard NCA/NUS capabilities with Salesforce bi-directional integration, forecast configuration management, and credit-specific program handling. The Salesforce integration makes it the primary system for capturing new deal information from the CRM pipeline into Atlys financial models, and for pushing Atlys forecast revenue data back into Salesforce for deal management. This bidirectional data flow creates additional data governance requirements beyond those of the standard fee-calculation databases.
