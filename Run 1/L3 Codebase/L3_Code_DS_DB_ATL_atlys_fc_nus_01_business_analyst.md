# Business Analyst Analysis — DS_DB_ATL_atlys_fc_nus (atlys_fc_nus)

## Repository Identity
- **Database name:** atlys_fc_nus
- **Project GUID:** (from atlys_fc_nus.sqlproj, not read in full but structurally identical to fc_nca)
- **Region scope:** United States (NUS)
- **SQL Server compatibility:** level 90 (SQL Server 2005 target)
- **Active git branch:** `development`

---

## Business Purpose

`atlys_fc_nus` is the **United States fee-calculation and revenue-forecasting database** for the Atlys platform. It is structurally and functionally identical to `atlys_fc_nca` (North/Central America), but operates on a separate database instance dedicated to programs originating or operating in the United States market. The separation exists to provide data isolation between US and broader NCA portfolio data, likely driven by regulatory or legal-entity reporting requirements.

The same financial processes that operate in `atlys_fc_nca` apply here: program lifecycle management, issuance fee calculation, dormancy fee and FVD amortisation, interchange income modelling, sales commission calculation, recurring fee calculation, and plastic cost forecasting.

---

## Key Business Processes

All processes are structurally identical to `atlys_fc_nca`. The following US-specific business considerations apply:

### US Regulatory Context for Fee Calculations
US prepaid card programs are subject to:
- **Regulation E (12 CFR Part 1005)** — Prepaid Account Rule. Dormancy fee rules are directly relevant: Reg E limits dormancy fees to one per month after 12 months of inactivity and requires fee disclosure. The `dorm_wait INT` parameter in `cursforecast` (minimum months before dormancy fees begin) is directly related to Reg E compliance.
- **State unclaimed property / escheatment laws** — The `unclaimed_keep`, `unclaimed_months`, and `claim_rate` columns in `cursforecast` model the breakage and escheatment assumptions. US states have varying dormancy periods (typically 1–5 years) after which unredeemed card balances must be escheated to the state. These assumptions directly impact financial forecasts for US programs.
- **NACHA Operating Rules** — Programs with `util_ach` utilisation include ACH-enabled reload or disbursement features subject to NACHA origination and return rules.

### Program Configuration (`cursforecast`)
Same 107-column program record table as `atlys_fc_nca`. The `country_code` field defaults to `'CA'` in the NCA database (`cursforecast.sql` line 11 of NCA) — for the NUS database, US programs would use `'US'` as the country code. This is the primary differentiator between the two instances at a data level.

### Issuance Fee Calculation (`sys_calc_issue`)
Identical to NCA. Computes issuance fee revenue based on `issue_type` (percentage of load vs. per-payment count).

### Dormancy Fee / FVD Amortisation (`sys_calc_dormancy`)
Identical procedure. The server-name-based SSAS cube detection (`CAST(@@SERVERNAME AS char(1)) IN ('Q', 'P', 'C')`) is present in this database too, indicating the same operational risk for US calculation accuracy.

### Commission Calculation
Identical to NCA. Sales rep commissions calculated against US program revenues.

### Reporting
Full suite of revenue, spend, issuance, plastics, costs, commission, and variance cross-tab reports — identical to NCA.

### Salesforce Integration
`cursforecast.ext_id` links US programs to Salesforce opportunity IDs. The `vsfdc_extract` view provides Salesforce extract data for US portfolio.

### Forecast Versioning
`tblForecast_Version` and `tblForecastChangeLog` (trigger-populated) provide forecast version history for US programs.

---

## Key Differences from atlys_fc_nca

| Dimension | atlys_fc_nca | atlys_fc_nus |
|---|---|---|
| Region | North/Central America | United States |
| Regulatory overlay | Multi-country (CA, MX, etc.) | US-specific (Reg E, state escheatment) |
| Default country code | 'CA' (Canada default) | 'US' expected for US programs |
| Stored procedure set | Identical | Identical |
| Table set | Identical | Identical (confirmed from sqlproj) |
| Security files | No APAC CPP variant | No APAC CPP variant |
| Distinction vs. NCA | Separate data for US programs | — |

**Note:** The `atlys_fc_nus.sqlproj` includes `sys_dash1_cross_tab.sql` and `sys_dash1_version_cross_tab.sql` as Build items, which are also present in NCA. Both databases also include `vPlasticsDPhysical` and `vPlasticsDVirtual` views that distinguish physical card programmes from virtual card programmes — relevant for US programmes where virtual prepaid products (e.g., single-use digital cards for insurance disbursements, healthcare reimbursements) are significant.

---

## Regulatory Relevance

### PCI DSS
Same as `atlys_fc_nca`. BIN data in `cursforecast.bin`, card type and bank code fields. Connected-system CDE scope.

### Reg E — Prepaid Account Rule (US-Specific Emphasis)
The `dorm_wait` configuration directly models the 12-month inactivity threshold after which Reg E permits a single monthly dormancy fee. The dormancy calculation engine in `sys_calc_dormancy` must produce fee projections consistent with Reg E disclosures. Discrepancies between the modelled dormancy assumptions and actual product terms represent a potential Reg E disclosure violation.

### UDAAP (Unfair, Deceptive, Abusive Acts or Practices)
Incorrect fee forecasting assumptions that are used to present misleading program economics to clients could create UDAAP exposure if they influence contract pricing or client communications. The `notes` field in `cursforecast` may contain client negotiation details requiring UDAAP-aware data governance.

### State Unclaimed Property
`unclaimed_keep` (the percentage of unclaimed balances Onbe retains vs. eschwats to state) is a financially and legally material assumption. Incorrect modelling here could understate escheatment liabilities.

### GLBA
US user data (staff names, emails) in atlys_e that has access to this database. Financial data in this database is non-public customer financial information subject to GLBA safeguards.

---

## Key Business Entities

All entities identical to `atlys_fc_nca`. See that document for the full entity list. The US-specific programme register is maintained in `cursforecast` with US country codes.

---

## Summary Assessment

`atlys_fc_nus` is financially and operationally critical for Onbe's US prepaid card business. Its fee forecasting assumptions directly drive revenue recognition, sales compensation, and GL amortisation entries for the US portfolio. The US-specific regulatory environment (Reg E dormancy rules, state escheatment, NACHA) means that errors in fee assumption configuration carry greater regulatory exposure in the US than in other markets. The database is a structural clone of `atlys_fc_nca`, and all findings from that analysis apply equally here.
