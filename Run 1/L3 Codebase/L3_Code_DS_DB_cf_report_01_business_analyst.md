# DS_DB_cf_report — Business Analyst View

## 1. Business Purpose

`cf_report` (Client-Facing Report) is Onbe's central operational reporting database. It serves as the reporting and data-orchestration hub that bridges the Gen-1 cardholder transactional data (ecountcore, cbaseapp) and the Gen-2 BIN-level operational data (CCP) to produce client-facing reports, regulatory extracts, compliance outputs, and operational file deliveries.

The database contains stored procedures, functions, and tables spanning multiple schemas: `dbo` (primary), `BINBANK` (Bank Integration file generation), `ECNT_AB` (eCount AB processing), `ISA`, `mantas`, `CB_OFFICE_*` (individual analyst workspaces), and others. The repository has an active **DeltaSql change management pattern** with Jira-ticket-numbered delta scripts dated through April 2026 (STBR-4812, STBR-5652) — the most recently active database in this analysis batch.

---

## 2. Business Processes Supported

### 2.1 Bank Integration (BINBANK schema)
The `BINBANK` schema generates Bank Integration files for financial institution partners:
- **`app_BI_Transaction_File`** — produces a daily transaction file extract for the bank/FI, drawing from CCP transaction data and ecountcore transaction journal. Last modified March 2026 (STBR-4812) and April 2026 (STBR-5652).
- **`app_BI_Account_Balance_File`** — generates account balance file for FI reconciliation.
- **`app_BI_Card_Status_File`** — generates card status file extract.
- **`app_BI_TransactionInternational_File`** — generates international transaction file.
- The `BINBANK.Account` and `BINBANK.Transaction` tables serve as intermediary data stores during file generation.

### 2.2 NACHA File Generation
The `BINBANK` schema contains a complete NACHA ACH file generation subsystem:
- `nacha_file_batch`, `nacha_file_entry_detail`, `nacha_file_source`, `nacha_file_status` — NACHA file structure tables
- `nacha_source_data_staging`, `nacha_source_data_staging_mapped` — staging for NACHA data
- `nacha_config_value`, `nacha_config_labels`, `nacha_bank_source`, `nacha_source`, `nacha_status`, `nacha_transaction_mapping`, `nacha_transaction_mapping_history` — NACHA configuration
- `usp_nacha_print_section_*` procedures — generate each section of a NACHA ACH file (file header, batch header, entry detail, EFA, file trailer, padding)
- `usp_nacha_queue_file`, `usp_nacha_source_*_stage` — queue and stage NACHA source data
- This subsystem generates compliant NACHA ACH files for fund loading or disbursement to prepaid cardholders.

### 2.3 Escheatment Processing
Extensive escheatment (unclaimed property) processing:
- `app_escheatment_process_prepare`, `app_escheatment_account_commit`, `app_escheatment_process_commit`, `app_escheatment_account_status_update` — multi-step escheatment workflow
- `app_escheatement_process_due_diligence_extract` — due diligence letter generation
- `escheatment_report_by_state`, `escheatment_naupa_get_property`, `escheatment_naupa_get_summary` — state-by-state escheatment reporting in NAUPA format
- Functions: `app_func_escheatment_*` — determine escheatability, maintenance fee eligibility, expiration dates, state-of-last-address rules
- This subsystem handles compliance with all 50 US states' unclaimed property laws.

### 2.4 AML / Fraud Monitoring (Quickscreen)
- `Quickscreen_AML_Corporate_Unusual_Activity` — identifies corporate accounts with unusual transaction patterns
- `Quickscreen_AML_Corporate_Unusual_Activity_Multiple_Deposits` — multiple-deposit velocity screening
- `Quickscreen_AML_Unusual_Activity_Multiple_Deposits_detail` — detailed output for Suspicious Activity Report (SAR) investigation
- `DailyRiskReports` — daily risk report generation
- `mantas` schema — Mantas/Oracle FCRM anti-money-laundering (AML) system integration data

### 2.5 Card Expiration and Reissue Management
- `app_func_card_expiration_is_reissue` — determines whether an expiring card is eligible for reissue
- `app_func_service_card_expiration_get_status` — returns expiration status for a card
- `rpt_func_card_expiration_count`, `rpt_func_card_expiration_get_count` — count cards pending expiration for planning

### 2.6 Enrollment and Registration Extracts
- `get_enrollment_extract_by_program_id` — enrollment data extract per program
- `get_enrollment_profile` — enrollment profile data
- `etl_job_registration_cards`, `etl_job_issue_cards` — ETL jobs for registration and card issuance data
- `ECNT_AB` schema — eCount AB process management (plastic card renewal, etc.)

### 2.7 Datamart and Analytics
- `dm_ecount_journal_fact_init`, `dm_ecount_journal_fact_refresh` — eCount journal fact table for datamart
- `datamart_report_accounts`, `datamart_report_jobsvc_issuance` — datamart-sourced reports
- `ecountcore_tx_profile` — transaction profile analysis

### 2.8 Check and Refund Processing
- `check_refund_extract`, `check_refund_extract_canada` — extract refund check data
- `fdr_check_review_queue_inquiry` — check review queue for fraud/operations
- `fdr_process_nacha_post` — posts NACHA ACH file for fund delivery
- `fdr_dda_account_transaction_update` — updates DDA account transaction records

### 2.9 Individual Analyst Workspaces
The `CB_OFFICE_*` schemas (`CB_OFFICE_BLogano`, `CB_OFFICE_HNaylor`, `CB_OFFICE_JWu`, `CB_OFFICE_SQuarshie`) contain individual analyst tables and functions:
- Personal working tables (e.g., `_hwnivRsData` in CB_OFFICE_HNaylor)
- Analyst-specific functions (`app_func_get_access_level_by_dda2` in CB_OFFICE_JWu)
- These represent a significant governance concern — personal workspaces in a production reporting database.

---

## 3. Business Rules Encoded

| Procedure/Function | Business Rule |
|---|---|
| `app_func_escheatment_is_account_escheatable` | Determines if an account meets dormancy and balance thresholds for state filing |
| `app_func_escheatment_get_expiration_date` | Computes regulatory expiration date per state law |
| `app_func_escheatment_get_rule_set` | Returns applicable rule set for a given state/program combination |
| `app_func_card_expiration_is_reissue` | Business logic for reissue eligibility (fee structure, program rules) |
| `app_func_dda_get_balance` | Returns current balance for a DDA account |
| `app_func_in_same_fdr_cycle` | Determines if two transactions are in the same FDR settlement cycle |
| `Validate` (BINBANK) | Validates Bank Integration file requirements before generation |
| `usp_nacha_queue_file` | Queues a NACHA file for transmission; enforces file-sequencing rules |

---

## 4. Regulatory Relevance

### NACHA
cf_report generates ACH files via the `usp_nacha_*` procedures. These files must comply with NACHA Operating Rules: correct batch headers, entry detail format, addenda records, control totals, file padding to 10-record blocking factor. The `nacha_config_value` and `nacha_transaction_mapping` tables encode the configuration values required for NACHA compliance.

### Escheatment / NAUPA
Unclaimed property laws require annual reporting in NAUPA (National Association of Unclaimed Property Administrators) standard format. The `escheatment_naupa_*` procedures produce this output.

### BSA / AML
Quickscreen AML procedures produce outputs used to identify accounts for SAR filings. The `mantas` schema integrates with Oracle Financial Services FCRM (Mantas), the AML transaction monitoring system.

### Reg E
Card transaction data used in cf_report supports Reg E periodic statement obligations.

---

## 5. Active Development Evidence

The `DeltaSql/` directory contains recently merged change scripts:
- `DeltaSql/2026-03-01/STBR-4812/` — March 2026 changes for Bank Integration transaction file (7 forward scripts, 7 rollback scripts)
- `DeltaSql/2026-04-12/STBR/STBR-5652/` — April 2026 changes for same area (6 forward scripts, 6 rollback scripts)

This confirms cf_report is under active development as of April 2026, with a structured delta-SQL change management process.
