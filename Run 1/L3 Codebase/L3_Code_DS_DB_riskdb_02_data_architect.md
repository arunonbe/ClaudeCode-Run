# DS_DB_riskdb — Data Architect Assessment

## 1. Schema Architecture

RiskDB uses a single `dbo` schema with a very large, heterogeneous object set. The database has grown organically over many years — the table folder structure (`Tables1`, `Tables2`, `Tables3`) with hundreds of tables, the `_archived` folder with named-user subdirectories, and the presence of date-stamped tables all confirm this is a long-lived operational/analytical database that has accumulated significant technical debt.

---

## 2. Key Table Groups

### 2.1 Daily Risk Monitoring Tables

| Table | Purpose | Sensitive Fields |
|---|---|---|
| `monitor_transaction_velocity_report` | Accounts with velocity anomalies | `dda_number` CHAR(16), `merchant_state`, transaction count |
| `monitor_fee_reversals` | Fee reversal audit | `dda_number`, `source` (transaction type), `amount`, `description` |
| `monitor_cvv_mismatch_report` | CVV mismatch incidents | `dda_number`, `transaction_amount`, `auth_merchant_name`, `auth_merchant_city`, `auth_merchant_state` |
| `monitor_high_dollar_report` | High-dollar transaction accounts | `dda_number`, `total_transaction_value` |
| `monitor_manual_key_report` | Manual POS entry incidents | `dda_number`, `total_transactions`, `total_attempts` |
| `monitor_high_dollar_credits` | Unpaired credit transactions | `dda_number`, `created`, `amount`, `description` |
| `monitor_direct_deposit` | High direct deposits | `dda_number`, `total_direct_deposit` |
| `monitor_ach_detail` | ACH device changes + cardholder PII | **`dda_number`, `first_name`, `last_name`, `home_email`** — PII stored in risk monitoring |
| `monitor_ach_summary` | ACH change frequency per account | `dda_number`, `number_of_changes` |

**Critical finding:** `monitor_ach_detail` (`DailyRiskReports.sql`, lines 388–407) stores **cardholder first name, last name, and home email address** alongside DDA numbers in a risk monitoring table. This PII is pulled from `fdr_card_account_registration_unique` via linked server and stored in RiskDB. This table must be covered by PII access controls and retention policies.

### 2.2 AML Case Management Tables

| Table | Purpose | Sensitive Fields |
|---|---|---|
| `EUC_DMT_AMLCase_DATA` | AML case field-value store (EAV model) | **DDA numbers, cardholder names, balances, bank names** — high sensitivity |
| `EUC_DMT_AMLCase_DATACache` | Read cache of AML case data | Same |
| `EUC_DMT_AMLCase_DATAchangesetcache` | Pending change data for AML cases | Same |
| `EUC_DMT_AMLCase_Fields` | Field definitions for AML case EAV model | None |
| `EUC_DMT_AMLCDD_DATA` | AML Customer Due Diligence records | **PII — high sensitivity** |
| `EUC_DMT_AMLCDD_DATACache` | CDD cache | Same |

The AML case data uses an **Entity-Attribute-Value (EAV) model** — case fields are stored as rows with `[Key Name]`, `[Key Value]`, `[Field Name]`, `[Field Value]` columns rather than a traditional relational schema. This is a flexible but difficult-to-query and difficult-to-secure pattern. The `[Field Value]` VARCHAR(MAX) column can contain any data — DDA numbers, names, dates, and other PII — making column-level access control impossible.

### 2.3 Fraud Case Management Tables

| Table | Purpose | Sensitive Fields |
|---|---|---|
| `EUC_DMT_CASE_DATA` | Fraud/dispute case EAV store | Case fields include claim type, Reg E flag, dates, cardholder data |
| `EUC_DMT_CASE_DATACache` | Read cache | Same |
| `EUC_DMT_CASE_DATAchangesetcache` | Pending change cache | Same |
| `EUC_dmt_casearchive_dataCACHE` | Archived case cache | Same |
| `EUC_dmt_casearchive_DATA` | Archived case data | Same |

### 2.4 Ancillary DMT Tables (Partial List)

The DMT back-end stores data for every business domain managed in the tool. Partial list:
- `EUC_DMT_ATM_DATA` — ATM management records
- `EUC_DMT_BUILD_DATA` — program build records
- `EUC_DMT_CARRIERTEMPLATE_DATA` — carrier templates
- `EUC_DMT_CLIENT_DATA` — client records
- `EUC_DMT_CONTRACT*_DATA` — contract management
- `EUC_DMT_Pricing_DATA` — pricing records
- `EUC_DMT_Subpoena_DATA` — subpoena tracking records (legal/compliance)
- `EUC_DMT_VendorMGMT_DATA` — vendor management
- `EUC_DMT_Entitlements_DATA` — user entitlements

### 2.5 Analytical / Staging Tables

The `Tables1`, `Tables2`, `Tables3` subfolders contain hundreds of tables that appear to be:
- **Ad-hoc analytical staging tables** (e.g., `04012388_JAN2012.sql`, `2008-12.sql`, `2009-12.sql`) — dated tables from historical analyses
- **Program-specific staging tables** (e.g., `0328240_Grifols_Letters.sql`)
- **ATM residual staging** (`ATM_Residuals_Staging1` through `ATM_Residuals_Staging9`)
- **Analytics summary tables** (`Analytics_tbl_BREAKAGE_SUMMARY`, `Analytics_tbl_FRAUD_REPORT_173_output`)
- **Export staging tables** (various `_STG` variants)

The presence of tables named for specific clients (e.g., Grifols) with data going back to 2008 confirms that RiskDB has been used for ad-hoc data storage over 15+ years without governance.

---

## 3. Sensitive Data Field Catalogue

| Table | Field(s) | Classification |
|---|---|---|
| `monitor_ach_detail` | `first_name`, `last_name`, `home_email` | PII — cardholder |
| `monitor_ach_detail` | `dda_number` | Account identifier |
| `monitor_*` tables | `dda_number` throughout | Account identifiers |
| `EUC_DMT_AMLCase_DATA` | `[Field Value]` (EAV — contains DDA, names, balances) | **High — AML/BSA protected data** |
| `EUC_DMT_AMLCDD_DATA` | `[Field Value]` | **High — CDD protected data** |
| `EUC_DMT_CASE_DATA` | `[Field Value]` | **High — Reg E / dispute data** |
| `EUC_DMT_Subpoena_DATA` | Subpoena records | **Critical — legal hold data** |

---

## 4. Stored Procedures — Compliance-Critical

### 4.1 DailyRiskReports
File: `dbo/Stored Procedures/DailyRiskReports.sql`
- Truncates and repopulates 8 monitoring tables daily
- Accesses `first_name`, `last_name`, `home_email` from operational systems (lines 388–399)
- Uses `OPTION (LOOP JOIN)` hints — performance tuning applied
- No parameterisation concerns — uses date variable parameters throughout

### 4.2 Analytics_sp_AML_Case_Module
File: `dbo/Stored Procedures/Analytics_sp_AML_Case_Module.sql`
- Hardcoded threshold `@Threshold int = 0` (line 7) — any positive balance triggers consideration
- Hardcoded case owner `Nathan.Sandiford` (line 512) — operational risk
- Hardcoded region code `@Region varchar(4) = '0401'` (line 8) — only monitors one region
- Hardcoded verticals: `'Maritime Payroll','Payroll','Sales Incentive'` (line 37) — other verticals excluded

### 4.3 sp_FRAUD_REPORT_124
File: `dbo/Stored Procedures/sp_FRAUD_REPORT_124_Chargebacks_Previous_Day_Recieved.sql`
- Pivots case data from `EUC_dmt_case_dataCACHE` and `EUC_dmt_casearchive_dataCACHE`
- Handles both active and archived cases
- Returns Reg E flag and claim type breakdown

---

## 5. Functions (dbo schema)

| Function | Purpose |
|---|---|
| `app_func_get_credits_by_date` | Get credits for an account by date range |
| `app_func_get_fee_by_date` | Get fees for an account by date range |
| `BusinessDaysAdd` | Add N business days to a date |
| `BusinessDaysSubtract` | Subtract N business days |
| `CalLandOnBusinessSubtract` | Land on business day after subtraction |
| `Convert_SOEID` | Convert SOEID (employee ID) format |
| `fCalcNumBusDays` | Calculate number of business days between dates |
| `fnCalcDistanceMiles` | Calculate distance in miles (lat/lon) — likely for ATM proximity analysis |
| `fn_calculateCommon` | String matching common character calculation (Jaro-Winkler component) |
| `fn_calculateCommon2` | Variant |
| `fn_calculateMatchWindow` | String match window calculation |
| `fn_calculatePrefixLength` | String prefix length for matching |
| `fn_calculateTranspositions` | Transposition count for string matching |
| `fn_GetCommonCharacters` | Common character extraction for string matching |

The presence of Jaro-Winkler string matching functions (`fn_calculate*`, `fn_GetCommonCharacters`) confirms that **name-matching for OFAC/sanctions screening** or AML name matching is implemented within this database. These are the core algorithms used to fuzzy-match cardholder names against sanctions lists.

---

## 6. Views

The `dbo/Views` folder contains reporting views that provide pre-aggregated or filtered perspectives on the case management and monitoring data.

---

## 7. Key Data Architecture Observations

1. **EAV model for case data** — The `EUC_DMT_*_DATA` tables use an EAV schema where all case fields are stored as rows. This is flexible but prevents column-level security, makes data masking impossible, and creates complex querying requirements. All sensitive case data — including cardholder names, DDA numbers, and AML investigation details — is stored in `[Field Value] VARCHAR(MAX)` rows.

2. **Hundreds of ad-hoc staging tables** — The database has been used as a scratch space for data analysis over 15+ years. Tables named by date (2008-12, 2009-12, 2010-12), by client (Grifols), and by employee (archived folders) represent ungoverned data accumulation.

3. **String matching functions for AML** — The presence of Jaro-Winkler algorithm components confirms this database implements the fuzzy name-matching logic for sanctions/AML screening.

4. **No evidence of a local OFAC SDN list table** — Despite the string matching functions and AML infrastructure, there is no visible table storing a local copy of the OFAC SDN list. Screening appears to rely on the external NESS system (via the Vendor database).
