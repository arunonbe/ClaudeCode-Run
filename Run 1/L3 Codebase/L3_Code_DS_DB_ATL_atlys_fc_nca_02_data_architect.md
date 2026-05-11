# Data Architect Analysis — DS_DB_ATL_atlys_fc_nca (atlys_fc_nca)

## Database Configuration (from atlys_fc_nca.sqlproj)

| Property | Value |
|---|---|
| Compatibility mode | 90 (SQL Server 2005) |
| Default collation | SQL_Latin1_General_CP1_CI_AS |
| Recovery model | BULK_LOGGED |
| Page verify | CHECKSUM |
| Snapshot isolation | OFF |
| Read committed snapshot | OFF |
| Encryption at rest (TDE) | `<IsEncryptionOn>False</IsEncryptionOn>` — **NOT ENABLED** |
| Parameterisation | SIMPLE |
| Trustworthy | False |
| Change tracking | OFF |

---

## Tables

### cursforecast (`dbo/Tables/cursforecast.sql`)
The master program record table. 107 columns. Selected sensitive/critical columns:

| Column | Type | Business Meaning | Sensitivity |
|---|---|---|---|
| prg_id | VARCHAR(10) | Program identifier (PK) | — |
| prg_name | VARCHAR(50) | Program name | Business confidential |
| bin | VARCHAR(7) | Bank Identification Number | **CDE-adjacent — BIN data** |
| card_type | VARCHAR(10) | Card type (Visa/MC/etc.) | — |
| bank_code | VARCHAR(10) | Issuing bank code | — |
| issue_fee | DECIMAL(6,3) | Issuance fee rate | Financial — confidential |
| card_fee | DECIMAL(5,3) | Card production fee | Financial — confidential |
| load_fee | FLOAT | Load transaction fee | Financial — confidential |
| fvd_rate | FLOAT | Face value discount rate | Financial — confidential |
| def_rate | DECIMAL(8,5) | Deferred revenue rate | Financial — confidential |
| util | DECIMAL(5,2) | Utilisation rate assumption | Financial — confidential |
| util_atm / util_ach / util_ret / util_ck / util_pin | DECIMAL(5,2) | Spend type utilisation rates | — |
| claim_rate | NUMERIC(5,2) | Breakage claim rate | Financial — confidential |
| cust_name | VARCHAR(50) | Customer/client name | **PII — business contact** |
| cust_num | VARCHAR(15) | Customer number | Business identifier |
| updated_by | VARCHAR(15) | Last modified by | Audit field |
| approved_by / reviewed_by | VARCHAR(15) | Workflow approvers | Audit field |
| notes | NTEXT | Free-text notes | May contain sensitive data |

**Trigger:** `trg_exclude` — fires on UPDATE of the `exclude` column. Inserts a row into `tblForecastChangeLog` capturing the change actor and revenue impact. This is the only automated audit trail in the fee-calculation database.

**Indexes:**
- Clustered PK on `prg_id`
- Non-clustered on `ext_id INCLUDE(win_date)`

### tblForecast_data (`dbo/Tables/tblForecast_data.sql`)
Monthly forecast revenue by program and line code.

| Column | Type | Notes |
|---|---|---|
| ID | INT IDENTITY | Surrogate |
| aff_id | VARCHAR(10) | FK → cursforecast.prg_id |
| date_1 | DATETIME | Period end date (last day of month check constraint) |
| line_cde | VARCHAR(10) | Revenue line code (e.g., ISSUE01, MAIN01, INTRCHG) |
| forecast_amt | FLOAT(53) | Forecast revenue amount |
| notes | TEXT | Analyst notes |
| update_dttm | DATETIME | Last updated timestamp |
| updated_by | VARCHAR(15) | Last updated by user |
| rev_adj | FLOAT(53) | Revenue adjustment amount |
| date_2 | AS COMPUTED | Month-start normalised date |

**Indexes:** Clustered PK on (date_2, date_1, aff_id, line_cde); unique non-clustered on (date_1, aff_id, line_cde); non-clustered on aff_id INCLUDE(forecast_amt, rev_adj).

### tblIssuance (`dbo/Tables/tblIssuance.sql`)
Monthly issuance volume assumptions per program.

| Column | Type | Notes |
|---|---|---|
| aff_id | VARCHAR(10) | FK → cursforecast.prg_id |
| issue_date | DATETIME | Issuance period |
| forecast_amt | FLOAT | Forecast issuance amount (dollar value) |
| forecast_pmts | FLOAT | Forecast payment count |
| forecast_avg | FLOAT | Forecast average payment size |
| def_rate | FLOAT | Deferred revenue rate for period |
| fvd_rate / fvd_amt | FLOAT | Face value discount rate and amount |
| def_bal | FLOAT | Deferred revenue balance |
| date_2 / date_1 | COMPUTED | Month-normalised dates |

### tblPlastics (`dbo/Tables/tblPlastics.sql`)
Physical card production volume per program per period.

### tblSpend (`dbo/Tables/tblSpend.sql`)
Card spend volume by transaction type per program per period.

### tblCommissions (`dbo/Tables/tblCommissions.sql`)
Sales representative commission records.

| Column | Type | Notes |
|---|---|---|
| sales_rep | VARCHAR(30) | Sales rep name |
| comm_date1 / comm_date2 | DATETIME | Commission period |
| rev_amt | NUMERIC(11,2) | Revenue basis amount |
| rev_item | VARCHAR(50) | Revenue item description |
| comm_rate | NUMERIC(5,2) | Commission rate |
| comm_amt | NUMERIC(11,2) | Computed commission amount |
| aff_id | VARCHAR(10) | Program ID |
| channel | VARCHAR(30) | Distribution channel |

### tblAmort_Tables_1 / tblAmort_Tables_2
Dormancy/maintenance fee recognition schedule lookup tables. Used in `sys_calc_dormancy` to determine the amortisation rate per month of card age.

### tblControls (`dbo/Tables/tblControls.sql`)
Period control dates — fiscal year start, forecast version date, lock status.

### tblForecast_Version (`dbo/Tables/tblForecast_Version.sql`)
Named forecast versions with metadata (created by, approved by, lock status).

### tblForecast_Fees (`dbo/Tables/tblForecast_Fees.sql`)
Fee assumption overrides specific to a named forecast version.

### tblForecastChangeLog
Audit trail of program include/exclude changes. Populated by `trg_exclude` trigger.

### tblDash_data (`dbo/Tables/tblDash_data.sql`)
Pre-aggregated data for the management dashboard.

### tblPrgDflt (`dbo/Tables/tblPrgDflt.sql`)
Default fee and behaviour assumptions for new program creation.

### cursforecast_snapshot (implied by `sys_copy_table_data` usage)
Snapshot copies of `cursforecast` may be created dynamically by `sys_copy_table_data` for comparison/archival purposes.

---

## Views (from atlys_fc_nca.sqlproj `<Build>` elements — selected)

| View | Purpose |
|---|---|
| vProgram / vPrograms / vPrograms_C / vPrograms_P | Program master perspectives |
| vProgramsCardType / vProgramsLocked | Card type and lock status |
| vRevenue / vRevenueD / vRevenueSum / vRevenueDSum | Revenue actual and summary |
| vFCRevenue / vFCRevenueSum / vFCSum | Forecast revenue views |
| vIssuance / vIssuanceD / vFCIssuance | Issuance actual and forecast |
| vPlastics / vPlasticsD / vFCPlastics | Plastics actual and forecast |
| vSpend / vSpendD / vFCSpend / vFCSpendSum | Spend actual and forecast |
| vCommissionsT / vCommissionsSum / vCommissionsRates | Commission perspectives |
| vCosts / vCosts_lines / vCostsSum | Cost views |
| vDash1 / vDash2 / vDashD1 / vDashD2 | Dashboard views |
| vAmort_Tables_1 / vAmort_Tables_2 / vAmortTables1 / vAmortTables2 | Amortisation schedule views |
| vForecast_lines / vForecast_Fees / vForecast_Version / vForecastChangeLog | Forecast management |
| vGL / vFVD | GL and face value discount views |
| vControls / vControls1 / vControlsRev | Period control views |
| vVarianceSum / vVarianceDSum / vVarianceCommissions | Variance reporting |
| vsfdc_extract | Salesforce data extract view |
| vFirst12Revenue / vFirst12Revenue1 / vFirstRevenue | First-year revenue projections |
| vActualDates_* | Actual data date boundaries |
| vActualIssuanceD/T / vActualPlasticsD/T / vActualRevenueD / vActualSpendD | Actual performance views |
| vPeriods | Fiscal period boundaries |
| vUsageType | Transaction type enumeration |
| vFees / vFeesUtilTypes | Fee and utilisation type references |
| vPlasticsDPhysical / vPlasticsDVirtual | Physical vs. virtual card split |

---

## Functions

| Function | Purpose |
|---|---|
| sys_prg_info | Returns program metadata summary |

Cross-database functions from `ATLYS_E.dbo.*` are heavily used throughout stored procedures.

---

## Stored Procedures (complete list from atlys_fc_nca.sqlproj)

### Fee Calculation Engine
- `sys_calc_issue` — issuance fee calculation
- `sys_calc_dormancy` — maintenance fee / FVD amortisation
- `sys_calc_comm` — commission calculation
- `sys_calc_interchange` — interchange income calculation
- `sys_calc_plastic` — plastic cost calculation
- `sys_calc_recur` — recurring fee calculation
- `sys_calc_reissue` — reissuance calculation

### Forecast Management
- `sys_create_forecast` — create new forecast record
- `sys_create_issuance` — initialise issuance data
- `sys_create_plastics` — initialise plastics data
- `sys_new_program` — new program wizard
- `sys_newforecastversion` — create new forecast version
- `sys_recalc_forecast` / `sys_recalc_forecast_s` — recalculate all forecast lines
- `sys_forecast_update` — update forecast assumptions
- `sys_forecast_version` — manage forecast versions
- `sys_forecast_info` / `sys_forecast_lines` / `sys_forecast_notes` / `sys_forecast_summary` / `sys_forecast_details` / `sys_forecast_fees` — forecast CRUD
- `sys_program` / `sys_program_update` / `sys_program_search` / `sys_program_filter` / `sys_program_chk` / `sys_program_delete` / `sys_program_ext` / `sys_program_lock` — program management

### Reporting
- `sys_actual_summary` — actual revenue summary
- `sys_revenue_cross_tab` / `sys_revenue_lines_cross_tab` / `sys_revenue_lines_sum_cross_tab` / `sys_revenue_pipeline_cross_tab` / `sys_revenue_pipeline_lines_cross_tab` / `sys_revenue_pipeline_status_cross_tab` / `sys_revenue_pipeline_version_cross_tab` / `sys_revenue_forecast_cross_tab` / `sys_revenue_forecast_pipeline_cross_tab` / `sys_revenue_cross_tab_info3` / `sys_revenue_issue` / `sys_revenue_lines_details` — revenue reporting
- `sys_issuance_cross_tab` / `sys_issuance_pipeline_cross_tab` / `sys_issuance_forecast_cross_tab` / `sys_issuance_forecast_pipeline_cross_tab` / `sys_issuance_update` / `sys_issuance_summary` / `sys_issue_details_cross_tab` — issuance reporting
- `sys_plastics_cross_tab` / `sys_plastics_pipeline_cross_tab` / `sys_plastics_forecast_cross_tab` / `sys_plastics_forecast_pipeline_cross_tab` / `sys_plastics_update` — plastics reporting
- `sys_spend_cross_tab` / `sys_spend_details_cross_tab` / `sys_spend_issue` / `sys_spend_lines` / `sys_spend_pipeline_cross_tab` — spend reporting
- `sys_costs_cross_tab` / `sys_costs_details_cross_tab` / `sys_costs_forecast` / `sys_costs_lines` / `sys_costs_lines_cross_tab` / `sys_costs_lines_sum_cross_tab` / `sys_costs_pipeline_cross_tab` / `sys_costs_pipeline_lines_cross_tab` / `sys_costs_post` / `sys_costs_print` — costs reporting
- `sys_comm` / `sys_comm_cross_tab` / `sys_comm_revenue_cross_tab` / `sys_comm_pipeline_cross_tab` / `sys_comm_revenue_pipeline_cross_tab` / `sys_comm_payable_revenue_pipeline_cross_tab` / `sys_comm_type_cross_tab` — commission reporting
- `sys_dash` / `sys_dash_cross_tab` / `sys_dash_details_cross_tab` / `sys_dash_details2_cross_tab` / `sys_dash1_cross_tab` / `sys_dash1_version_cross_tab` — dashboard
- `sys_deferredrevenue_cross_tab` / `sys_deferredrevenue_balance_cross_tab` / `sys_deferredrevenue_pipeline_cross_tab` — deferred revenue
- `sys_forecast_cross_tab` / `sys_forecast_details_cross_tab` / `sys_forecast2_cross_tab` — forecast reporting
- `sys_variance_details` / `sys_variance_lines` / `sys_variance_lines_pipeline` / `sys_variance_summary` — variance analysis
- `sys_amortization` / `sys_amortization_dorm` / `sys_amortization_issuance_post` / `sys_amortization_print` / `sys_amortization_rev_post` — amortisation
- `sys_no_comm_cross_tab` / `sys_no_comm_pipeline_cross_tab` — programs without commissions
- `sys_prg_cnt_cross_tab` — program count reporting
- `sys_probability` — pipeline probability reporting
- `sys_report_revenue` — revenue report

### Utilities
- `sys_controls` — period control management
- `sys_copy_table_data` — dynamic table copy
- `sys_renumber` — program ID renumbering
- `sys_user_cols` — user column configuration
- `sys_util_tables` — utility table management
- `sys_custnames` / `sys_custnums` — customer name/number lookups

---

## Sensitive Data Fields — Summary

| Field | Table | Classification |
|---|---|---|
| `bin` | cursforecast | CDE-adjacent BIN data |
| `cust_name` | cursforecast | PII — client business name |
| `notes` (NTEXT) | cursforecast | May contain sensitive free-text |
| `notes` (TEXT) | tblForecast_data | May contain sensitive free-text |
| `comm_amt` / `rev_amt` | tblCommissions | Financial — compensation data |
| `updated_by`, `approved_by` | cursforecast | PII — staff names in audit fields |

---

## PCI DSS CDE Scope Assessment

`atlys_fc_nca` contains BIN data (`bin` column in `cursforecast`) and models revenue from card programmes by transaction type (ATM, ACH, POS). While it does not store full PANs, it:
1. Models financial behaviour of cardholder accounts (spend utilisation by card type).
2. Is connected to `atlys_e` which authenticates access to this data.
3. Contains commission data tied to card programme revenues.

**Assessment: Connected-system scope with indirect CDE relevance. BIN data presence warrants evaluation under PCI DSS Req 3 for data minimisation.**

---

## Encryption at Rest
TDE is not enabled (`<IsEncryptionOn>False</IsEncryptionOn>`). No column-level encryption. Financial forecast amounts, fee rates, and BIN data are stored in plaintext in database files and backups.

---

## Data Retention
No purge or archival procedures are defined in the codebase. `tblForecastChangeLog` accumulates indefinitely. `tblCommissions` has no TTL. Historical forecast versions in `tblForecast_Version` are retained permanently. A formal data retention schedule should be defined and implemented.
