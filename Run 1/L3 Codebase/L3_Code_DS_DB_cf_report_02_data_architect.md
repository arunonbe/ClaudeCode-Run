# DS_DB_cf_report — Data Architect View

## 1. Repository Structure and Build System

`DS_DB_cf_report` is **not an SSDT project**. There is no `.sqlproj` file. The repository stores SQL scripts in a directory layout that mirrors schema/object-type hierarchy under `cf-report/`. Change management is handled through the `DeltaSql/` delta-script pattern (dated folders with forward and rollback scripts). This means the database cannot be deployed from a DACPAC; all deployments are script-based.

Schemas present in the repository:
- `dbo` — primary schema (100+ stored procedures, 80+ tables, 80+ functions, 70+ views)
- `BINBANK` — Bank Integration file generation schema
- `mantas` — Oracle FCRM / Mantas AML integration schema
- `ECNT_AB` — eCount AB plastic renewal processing
- `ISA` — ISA program profile events
- `NAOT` — North America OTC procurement tracking
- `NA_ATLYS` — Atlys views for North America BIN reporting
- `CB_OFFICE_BLogano`, `CB_OFFICE_HNaylor`, `CB_OFFICE_JWu`, `CB_OFFICE_SQuarshie` — individual analyst workspace schemas

---

## 2. Complete Table Inventory

### 2.1 BINBANK Schema Tables

| Table | Key Columns | Sensitivity |
|---|---|---|
| `BINBANK.Account` | `id` INT IDENTITY, `Bank` CHAR(50), `file_date` CHAR(10), **`dda_number` CHAR(16) PK**, `created` DATETIME, `card_id` INT, `card_number` CHAR(4), `card_exp_date` DATETIME, `BIN` CHAR(6), `card_status`, `first_name`, `middle_name`, `last_name`, `address1/2`, `City`, `State`, `ZipCode`, `Country`, `home_phone`, `email`, `program_id`, `program_name`, `channel_name`, `secure_profile` | **HIGH — dda_number CHAR(16) as PK; full cardholder PII; email; phone** |
| `BINBANK.Account_Staging` | Same columns as Account (staging variant) | HIGH |
| `BINBANK.AccountBalance` | `Bank` CHAR(50), `file_date`, **`dda_number` CHAR(16) PK**, `post_balance` INT, `available_balance` INT | HIGH — balance data |
| `BINBANK.CardStatus` | `dda_number`, `card_id`, `card_number` CHAR(4), `card_status`, `card_exp_date` | MEDIUM |
| `BINBANK.Transaction` | **`transactionID` VARCHAR(64) PK**, `bank`, `file_date`, `settlement_date`, `transaction_date`, `amount` INT, `fee` INT, `description`, `transaction_code`, **`dda_number` CHAR(16)**, `merchant_category_code`, `merchant_country_code`, `foreign_activity_flag`, `card_number` CHAR(4), `addenda`, `network`, `DDI` CHAR(17) | **HIGH — dda_number; transaction amounts; DDI field** |
| `BINBANK.nacha_file_entry_detail` | `entry_detail_id` INT IDENTITY PK, `batch_id` FK, `transaction_code`, `receiving_DFI_ID` VARCHAR(8), `check_digit`, **`dfi_account_number` VARCHAR(17)**, `amount` BIGINT, `id_number` VARCHAR(15), **`individual_name` VARCHAR(22)**, `discretionary_data`, `addenda_record_indicator`, `trace_number` | **CRITICAL — dfi_account_number (bank account number) + individual_name: NACHA CHD** |
| `BINBANK.nacha_file_batch` | `batch_id` INT PK, `file_id` FK, batch header fields | LOW |
| `BINBANK.nacha_file_source` | `file_source_id`, `file_id`, `source_id`, `nacha_source_data_staging_id` | LOW |
| `BINBANK.nacha_file_status` | `file_id`, `file_date`, `bank_name`, `status_id`, override dates | LOW |
| `BINBANK.nacha_source_data_staging` | Staging for NACHA source data | MEDIUM |
| `BINBANK.nacha_source_data_staging_mapped` | Mapped NACHA staging | MEDIUM |
| `BINBANK.nacha_config_value` | Config key-value pairs for NACHA file generation | LOW |
| `BINBANK.nacha_config_labels` | Labels for NACHA config entries | LOW |
| `BINBANK.nacha_bank_source` | Bank-to-source mapping for NACHA routing | LOW |
| `BINBANK.nacha_source` | NACHA source definitions | LOW |
| `BINBANK.nacha_status` | NACHA status code table | LOW |
| `BINBANK.nacha_transaction_mapping` | Maps eCount transaction types to NACHA codes | LOW |
| `BINBANK.nacha_transaction_mapping_history` | Audit history of NACHA mapping changes | LOW |
| `BINBANK.Tcode_Lookup` | Transaction code lookup: `source_id`, `facility_id`, `t_code` | LOW |
| `BINBANK.Tcode_Lookup_Addenda` | Transaction code lookup for addenda records | LOW |
| `BINBANK.FileNames` | File name tracking for BI file generation | LOW |
| `BINBANK.ManualDates` | Manual date overrides for file generation runs | LOW |
| `BINBANK.ProcessLog` | Process execution log for BINBANK procedures | LOW |
| `BINBANK.ProcessStatus` | Process status tracking for BI file generation | LOW |
| `BINBANK.sykesreports_summary` | Sykes call center report summary data | LOW |
| `BINBANK.sykesreports_summary_stage` | Sykes report staging | LOW |

### 2.2 dbo Schema — Selected High-Sensitivity Tables

| Table | Key Columns | Sensitivity |
|---|---|---|
| `dbo.Escheatment_ny_audit_customer_info_details` | `dda_number` CHAR(16), `created`, `first_name`, `middle_name`, `last_name`, `suffix_name`, `home_email`, `business_email`, `mobile_email`, `address1/2`, `city`, `state`, `postal`, `country`, `home_phone`, `business_phone`, `mobile_phone`, `card_id`, `attention_line`, `company_name` | **HIGH — full cardholder PII: name, 3 email addresses, 3 phone numbers, full address** |
| `dbo.Escheatment_ny_audit_transactions_detail` | `dda_number`, transaction details for NY audit | HIGH |
| `dbo.Fincen_process_export` | `Full Name`, `first_name`, `middle_name`, `last_name`, `address1/2`, `city`, `state`, `postal`, `country`, `home_phone`, `business_phone`, `channel_name`, `dda_number` CHAR(16), `created`, `block_code`, `block_code_modified` | **HIGH — FinCEN export: full cardholder PII for BSA/AML reporting** |
| `dbo.Fincen_process_import` | FinCEN import data | HIGH |
| `dbo.CustomerAddress` | Cardholder address data | HIGH |
| `dbo.DimAccountHolder_onetime` | Account holder dimensional data | HIGH |
| `dbo.MantasTempFOTPParty` | Mantas Front Office Transaction Party temp data | HIGH |
| `dbo.DWStg_Step1` through `DWStg_Step13` | Datamart staging steps | MEDIUM |
| `dbo.ETL_Master` | ETL job execution tracking | LOW |
| `dbo.ETL_Master_History` | ETL history | LOW |
| `dbo.EscheatmentReversal_Programs` | Programs eligible for escheatment reversal | LOW |
| `dbo.Holiday` / `dbo.HolidaySet` | Calendar reference tables | LOW |
| `dbo.MaritimeATM_*` (12 tables) | ATM transaction data: adjustment, adjustment STG, dispensed, dispensed STG, electronic journal, electronic journal STG, interchange, interchange STG, replenishment, replenishment STG, surcharge, surcharge STG, device performance, profile, switch balance | LOW-MEDIUM |
| `dbo.CodeArchive` | Archived code/script objects | LOW |
| `dbo.DimProgram` | Program dimension table | LOW |

### 2.3 mantas Schema Tables

| Table | Sensitivity |
|---|---|
| `mantas.AccountHolder` | **HIGH — dda_number CHAR(16); address; AccountDisplayName VARCHAR(8000); RiskRating; exchange rate data** |
| `mantas.AccountFrontOfficeTransactions` | MEDIUM — transaction data for AML |
| `mantas.Front_Office_Transaction_Party` | MEDIUM — party data for AML |
| `mantas.CountryRegionMapping` | LOW |
| `mantas.Jurisdictions` | LOW |
| `mantas.RiskRatings` | LOW |
| `mantas.TCodesLookup` | LOW |
| `mantas.worldlink_fxrate` | LOW |
| `mantas.FileNames`, `mantas.ManualDates`, `mantas.ProcessLog`, `mantas.ProcessStatus`, `mantas.ProcessRegionSummary` | LOW |
| `mantas.GPCompany` | LOW |
| `mantas.SourceFailityMapping` | LOW |
| `mantas.mantas_e2e_status` | LOW |

### 2.4 Analyst Workspace Tables (Governance Risk)

| Schema | Table | Notes |
|---|---|---|
| `CB_OFFICE_BLogano` | `dim_partner_affiliate_delta1` | Personal workspace table in production DB |
| `CB_OFFICE_HNaylor` | `_hwnivRsData` | Underscore-prefixed name; likely ad-hoc result set |
| `CB_OFFICE_SQuarshie` | `enrollment_extract_process_status_temp2` | Contains "temp2" — iteration artifact |

### 2.5 Other Schema Tables

| Schema | Tables | Notes |
|---|---|---|
| `ECNT_AB` | `ab_process_plastics_renewal_Temp`, `ab_process_plastics_renewal_Temp_MR` | Plastic renewal temp working tables |
| `ISA` | `Program_Profile_Event_Types` | ISA event type reference |
| `NAOT` | `FL_procurement_ProcurementUsageHistory`, `OH_procurement_ProcurementUsageHistory`, `TX_procurement_ProcurementUsageHistory`, `T_Item_Master`, `T_Item_Master_CITI`, `T_Stored_Item`, `T_Tran_Log` | OTC procurement tracking |

---

## 3. Sensitive Data Field Inventory

| Table.Column | Data Type | Classification | Regulatory Flag |
|---|---|---|---|
| `BINBANK.Account.dda_number` | CHAR(16) | DDA/account number | **HIGH: if unprotected PAN, PCI CDE scope; if DDA token, GLBA NPPI** |
| `BINBANK.Account.first_name/last_name` | VARCHAR(25) | PII — Cardholder name | PCI DSS CHD; GDPR/CCPA |
| `BINBANK.Account.address1/2`, `City`, `State`, `ZipCode`, `Country` | VARCHAR | PII — Address | GDPR/CCPA |
| `BINBANK.Account.home_phone` | VARCHAR(16) | PII — Phone | GDPR/CCPA |
| `BINBANK.Account.email` | VARCHAR(50) | PII — Email | GDPR/CCPA |
| `BINBANK.Account.secure_profile` | VARCHAR(250) | Unknown — named "secure_profile" | **Requires classification — may contain encoded PII** |
| `BINBANK.Transaction.dda_number` | CHAR(16) | DDA/account number | HIGH — links transaction to account |
| `BINBANK.Transaction.DDI` | CHAR(17) | Direct Deposit ID | MEDIUM — routing+account or account identifier |
| `BINBANK.nacha_file_entry_detail.dfi_account_number` | VARCHAR(17) | **Bank account number** | **CRITICAL: NACHA entry detail field is the receiving DFI account number — ACH routing target** |
| `BINBANK.nacha_file_entry_detail.individual_name` | VARCHAR(22) | Cardholder name (NACHA format) | MEDIUM: required in NACHA file |
| `BINBANK.nacha_file_entry_detail.receiving_DFI_ID` | VARCHAR(8) | ABA routing number (first 8 digits) | MEDIUM |
| `mantas.AccountHolder.dda_number` | CHAR(16) | DDA number for AML | HIGH |
| `mantas.AccountHolder.address1/City/State/ZipCode` | VARCHAR | PII — Address | HIGH |
| `mantas.AccountHolder.RiskRating` | INT | AML risk score | MEDIUM — law enforcement sensitive |
| `dbo.Escheatment_ny_audit_customer_info_details.*_email` | VARCHAR(50) | Email addresses (3 fields) | HIGH — GDPR/CCPA |
| `dbo.Fincen_process_export.dda_number` | CHAR(16) | DDA number in FinCEN export | **CRITICAL — FinCEN data: regulatory confidentiality obligations** |
| `dbo.Fincen_process_export.Full Name` | NVARCHAR(255) | Full name (FinCEN) | HIGH |

---

## 4. Cross-Database References (Linked Servers)

`app_BI_Transaction_File.sql` (lines 107-134) confirms cf_report uses **linked server queries** to:
- `ECountcore_ss..fdr_dda_account_journal` — eCount journal transactions
- `Ecountcore_ss..core_profile_programs_bank_effective_vw` — program/bank mapping
- `Ecountcore_ss..claimable_payment_transaction` — claimable payment data
- `Ecountcore_ss..fdr_card_account` — card account data
- `Ecountcore_Process_SS..fdr_process_debitach_file` — debit ACH process data
- `Ecountcore_Process_SS..fdr_process_atmach_star_file` — ATM/ACH STAR data
- `ecountcore_ss..citi_process_nacha_status` — Citi NACHA file status (used by AML procedures)

The `_ss` suffix indicates SQL Server linked server connections. These cross-database calls mean cf_report is tightly coupled to ecountcore and ecountcore_process. Any schema change in those databases can break cf_report procedures without any compile-time error detection.

Similarly, `Quickscreen_AML_Corporate_Unusual_Activity.sql` (lines 43-60) queries:
- `ecountcore_ss.dbo.citi_process_nacha_status`
- `ecountcore_process_ss.dbo.citi_process_nacha_file`
- `ecountcore_ss.dbo.fdr_dda_account`

---

## 5. Views Inventory

The dbo schema contains approximately 70 views. Notable views with sensitivity implications:

| View | Sensitivity |
|---|---|
| `dbo.fdr_dda_account_balance` / `fdr_dda_account_balance_view` | HIGH — cardholder balance data |
| `dbo.rpt_view_escheatment` | HIGH — escheatable account PII |
| `dbo.app_process_1099_info` | HIGH — IRS 1099 tax data (payment amounts, recipient identifiers) |
| `mantas.vwAccounts` / `vwAccountsAddress` / `vwAccountsBalance` | HIGH — AML account/address/balance views |
| `mantas.vwAccountsTransactions` / `vwAccountsTransactionParty` | MEDIUM — AML transaction data |
| `dbo.galileo_user_enrollment` / `galileo_user_registration` | MEDIUM — enrollment/registration data |
| `NA_ATLYS.vCustLiabilityT_Details` / `vCustLiabilityT_Details2` | HIGH — customer liability detail |

---

## 6. Functions Inventory

The dbo schema contains approximately 80 scalar and table-valued functions. Key categories:

**Escheatment Functions (dbo schema):**
- `app_func_escheatment_is_account_escheatable`
- `app_func_escheatment_get_expiration_date`
- `app_func_escheatment_get_rule_set`
- `app_func_escheatment_get_status`
- `app_func_escheatment_is_maintenance_fee_allowed`
- `app_func_escheatment_dda_get_address_state`

**Balance and Account Functions:**
- `app_func_dda_get_balance` / `app_func_dda_get_balance_new`
- `app_func_dda_get_open_to_buy` — returns open-to-buy (available balance) for a DDA
- `app_func_dda_get_fee` — returns fee for a DDA/program
- `util_func_get_balance_by_dda` — utility balance lookup

**Card Expiration Functions:**
- `app_func_card_expiration_is_reissue` / `_New` / `_old` — three versions (old/current/new); multiple versions in production repo indicates incomplete cleanup
- `app_func_service_card_expiration_get_status` / `_New` / `_old` — same triplication pattern
- `rpt_func_card_expiration_count` / `rpt_func_card_expiration_get_count` / `_debug` / `_jwu` — multiple debug/personal variants

**NACHA Functions (BINBANK schema):**
- `fn_nacha_get_config_value_by_name`
- `fn_nacha_get_file_name_by_id`
- `fn_NACHA_missing_config_count`

**CB_OFFICE_JWu Function:**
- `CB_OFFICE_JWu.app_func_get_access_level_by_dda2` — analyst personal copy of an access-level function in a production schema

---

## 7. Stored Procedures Inventory

### BINBANK Schema (19 procedures)
- `app_BI_Transaction_File`, `app_BI_Account_Balance_File`, `app_BI_Card_Status_File`, `app_BI_TransactionInternational_File`, `app_BI_Account_File` — Bank Integration file generation
- `Validate` — validates BI file readiness
- `uspAccountTablePopulate`, `uspTransactionTablePopulate`, `uspGetAccount`, `uspGetFileNames`, `uspInsertProcess`, `uspUpdateProcess`, `uspShouldRun` — BI file population helpers
- `usp_nacha_print_section_*` (7 procedures: file_header, batch_header, entry_detail, EFA, batch_trailer, file_trailer, file_trailer_padding) — NACHA section generators
- `usp_nacha_queue_file`, `usp_nacha_queue_file_sources`, `usp_nacha_source_load`, `usp_nacha_source_load_batch`, `usp_nacha_source_load_entry_detail`, `usp_nacha_source_stage_mapping` — NACHA pipeline
- `usp_nacha_source_00001_stage` through `usp_nacha_source_00006_stage` — per-source NACHA staging
- `usp_fiserv_spendtrend_INS`, `usp_sykesreports_summary_load` — specialty data loads

### mantas Schema (10 procedures)
- `sp_AML_Front_Office_Transaction`, `sp_AML_Front_Office_Transaction_Party` — AML transaction feeds
- `uspAccountTablePopulate` (mantas), `uspInitialAccountTablePopulate` — Mantas account population
- `uspGetE2EData`, `uspGetE2EHeaderFooter`, `uspGetFileNames`, `uspGetExchangeRate`, `uspConvertCurrencies` — Mantas E2E file generation
- `uspInsertProcess`, `uspUpdateProcess`, `uspShouldRun` (mantas) — process tracking
- `Validate` (mantas) — Mantas file validation

### ECNT_AB Schema (1 procedure)
- `ab_process_plastic_renewal_prepare` — prepares plastic renewal batch

### dbo Schema (100+ procedures, selected)
- AML: `Quickscreen_AML_Corporate_Unusual_Activity`, `Quickscreen_AML_Corporate_Unusual_Activity_Multiple_Deposits`, `Quickscreen_AML_Corporate_Unusual_Activity_detail`, `Quickscreen_AML_Unusual_Activity_Multiple_Deposits_detail`, `DailyRiskReports`
- Escheatment: `app_escheatment_process_prepare`, `app_escheatment_account_commit`, `app_escheatment_process_commit`, `app_escheatment_account_status_update`, `app_escheatement_process_due_diligence_extract`, `escheatment_naupa_get_property`, `escheatment_naupa_get_summary`, `escheatment_report_by_state`, `escheatment_report_prepare`, `escheatment_report_audit`, `escheatment_get_summary`, `escheatment_get_valid_states`
- NACHA/FDR: `fdr_process_nacha_post`, `fdr_process_nacha_post_old`, `fdr_dda_account_transaction_update`
- ETL: `etl_job_registration_cards`, `etl_job_issue_cards`, `etl_cards`, `dm_ecount_journal_fact_init`, `dm_ecount_journal_fact_refresh`
- Enrollment: `get_enrollment_extract_by_program_id`, `get_enrollment_profile`
- Check/Refund: `check_refund_extract`, `check_refund_extract_canada`, `fdr_check_review_queue_inquiry`
- FinCEN: (implied by `Fincen_process_export` / `Fincen_process_import` tables)

---

## 8. Encryption and PCI CDE Assessment

| Scope Question | Assessment |
|---|---|
| Does cf_report store full PAN? | No direct evidence of PAN columns. `dda_number` CHAR(16) is a DDA/account identifier — classify definitively |
| Does cf_report store cardholder name? | **Yes** — `BINBANK.Account.first_name/last_name`; `mantas.AccountHolder.AccountDisplayName`; `nacha_file_entry_detail.individual_name`; `Escheatment_ny_audit_customer_info_details.*_name` |
| Does cf_report store account/routing numbers? | **Yes** — `nacha_file_entry_detail.dfi_account_number` VARCHAR(17) is the DFI account number in ACH entries |
| Column-level encryption | None observed in any table DDL |
| TDE status | Cannot be confirmed from DDL alone — must verify on production instance |
| Linked-server data access scope | cf_report's stored procedures query CCP (via NAM_ tables in ecountcore) and ecountcore directly — bringing CDE-scoped data into cf_report procedures even if not persisted |

**Conclusion**: cf_report is **in PCI DSS scope for cardholder name (CHD)**. The `dda_number` field must be classified (token vs. PAN) to determine full CDE scope. The `dfi_account_number` in `nacha_file_entry_detail` is a sensitive financial account identifier subject to NACHA security requirements.

---

## 9. Change Management — DeltaSql Scripts

Two active change sets were found:

**STBR-4812 (March 2026, 7 forward + 7 rollback scripts):**
- `1__STBR-4812_new_dim_values.sql` — INSERT new dimension values
- `2__STBR-4812_new_tcode_values.sql` — INSERT new transaction code values
- `3__STBR-4812_create_tcode_lookup_addenda.sql` — CREATE `BINBANK.Tcode_Lookup_Addenda` table
- `4__STBR-4812_inserts_tcode_lookup_addenda.sql` — Populate addenda table
- `5__STBR-4812_rpt_TX_Groups_With_Bin_Bank_Data_Feed.sql` — Modify reporting procedure
- `6__STBR-4812_app_BI_Transaction_File.sql` — Modify transaction file generation procedure
- `7__STBR-4812_usp_sunrise_tcode_lookup_export.sql` — Sunrise tcode lookup export

**STBR-5652 (April 2026, 6 forward + 6 rollback scripts):**
- Further refinements to tcode lookup addenda inserts, removals, and transaction file procedure
- Most recent activity: `DeltaSql/2026-04-12/STBR/STBR-5652/6__STBR-5652_app_BI_Transaction_File.sql`

The rollback scripts exist for every forward script, providing a structured rollback capability. This is a mature change management pattern.
