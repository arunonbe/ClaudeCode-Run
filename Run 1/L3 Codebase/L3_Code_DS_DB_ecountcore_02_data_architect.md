# DS_DB_ecountcore — Data Architect View

## Database Overview

- **Database Name**: `Ecountcore`
- **SQL Server Version**: SQL Server 2016 (`Sql130DatabaseSchemaProvider`)
- **Project Type**: SSDT SQL Server Database Project
- **Schema**: `dbo` (single schema)
- **Active Branch**: `development`
- **Object Counts**: 130+ functions, 300+ stored procedures (Procs1 folder alone contains 200+), tables estimated 100+, plus data seed scripts

---

## Schema Prefixes and Domain Mapping

The stored procedures, functions, and tables use a consistent naming prefix convention that reveals the domain model:

| Prefix | Domain |
|---|---|
| `ach_` | ACH (Automated Clearing House) processing |
| `app_` | Application-level business logic |
| `app_func_` | Application scalar/table functions |
| `app_process_` | Batch processing procedures |
| `app_profile_` | Configuration/profile management |
| `achdirect_` | Direct ACH settlement |
| `check_` | Paper check processing (Harland) |
| `core_` | Core platform objects (cards, members, transactions, devices) |
| `core_func_` | Core utility functions |
| `fdr_` | First Data Resources (FDR) card processing |
| `fdr_card_` | FDR card account operations |
| `fdr_dda_` | FDR DDA (demand deposit account) operations |
| `fdr_process_` | FDR file/batch processing |
| `fdr_profile_` | FDR configuration profiles |
| `ieft_` | International EFT / WorldLink |
| `monitor_` | Operational monitoring queries |
| `notification_` | Notification processing |
| `psc_` | PSC (payment statement/report) |
| `rpt_` | Reporting procedures |
| `util_` | Utility/operational procedures |
| `smots_` | SMOTS programme (specific card product) |
| `qa_` | QA/testing procedures |
| `wcfdr_` | Write/log procedures |
| `bin_bank_` | BIN-to-bank mapping |

---

## Functions — Complete Inventory (130+ objects)

### ACH Functions
- `app_func_ach_effective_date` — Calculates ACH effective date
- `app_func_ach_get_effective_date` — Gets effective date
- `app_func_ach_get_vendor` — Gets ACH vendor for a DDA
- `app_func_ach_velocity_check` — Returns 0/1 velocity check pass/fail
- `app_func_build_achFundSql` — Builds dynamic ACH funding SQL (dynamic SQL — **injection risk review needed**)
- `app_func_build_ccFundSql` — Builds dynamic credit card funding SQL (dynamic SQL — **injection risk review needed**)
- `app_func_get_ach_batch_desc` — ACH batch description
- `app_func_get_ach_batch_desc_bank` — ACH batch description by bank
- `app_func_get_ach_device_status` — ACH device status
- `app_func_get_ach_nacha_force_accept_begin_date` — NACHA force-accept date
- `app_func_get_ach_updated_date` — Last ACH update date
- `app_func_get_ach_verification_code_by_member` — ACH verification code
- `app_func_get_kyc_velocity_check` — KYC velocity limit check
- `app_func_get_last_ach_status` — Most recent ACH status
- `app_func_get_last_ach_tx_date` — Last ACH transaction date
- `app_func_is_ach_tx_distribution_required` — Checks if distribution step needed
- `app_func_get_next_ach_load_date` — Next scheduled ACH load date

### Card Functions
- `app_func_card_expiration_allow_renew` — Can a card be renewed?
- `app_func_card_expiration_dda_get_last_activity` — Last activity for expiry
- `app_func_card_expiration_dda_get_last_payment` — Last payment for expiry
- `app_func_card_expiration_is_reissue` — Is this a reissue?
- `app_func_get_activation_status` — Card activation status
- `app_func_get_block_code_by_card_id` — Card block code
- `app_func_get_card_activation_status` — Detailed activation status
- `app_func_get_card_creation_date` — Card creation date
- `app_func_get_card_expiration_date_by_program` — Program-based expiry date
- `app_func_get_card_id_by_number` — Card ID from card number
- `app_func_get_card_last4digits_by_notification_process_queue_id` — Last 4 digits
- `app_func_get_card_number_by_card_encrypted_tableres` — Decrypt PAN from encrypted value (table-valued)
- `app_func_get_card_number_by_card_hash_tableres` — Get PAN from hash (table-valued)
- `app_func_get_card_number_by_card_id_tableres` — Decrypt PAN from card_id (table-valued) — **full PAN retrieval**
- `app_func_get_card_number_by_card_id_tableres_masked` — Masked PAN (first 6 + XXXXXX + last 4)
- `app_func_get_card_number_by_id` — **FULL PAN DECRYPTION** via `DecryptByKeyAutoCert(cert_id('card_number_cert'), null, card_encrypted)` — returns CHAR(16)
- `app_func_get_card_number_by_id_masked` — Masked PAN
- `app_func_get_cc_expiration_date` — Credit card expiry
- `app_func_get_cc_last_tx_status` — Last CC transaction status
- `app_func_get_cc_updated_date` — CC last update
- `app_func_service_card_expiration_get_status` — Card expiry service status
- `app_func_service_card_expiration_queue_get_status` — Queue status

### Member / DDA Functions
- `app_func_companion_get_role_by_member` — Companion card role
- `app_func_dda_get_activated_card_count` — Activated card count on DDA
- `app_func_dda_get_balance` — **Current DDA balance** — financial
- `app_func_dda_get_balance_by_date` — Balance at a date
- `app_func_dda_get_default_access_level` — Default access level
- `app_func_dda_get_emboss_code` — Emboss code
- `app_func_dda_get_fee` — Fee on DDA
- `app_func_dda_get_open_to_buy` — Open-to-buy (available credit)
- `app_func_dda_transaction_velocity_check` — Transaction velocity
- `app_func_get_access_level_by_dda` — Access level by DDA
- `app_func_get_access_level_by_member` — Access level by member
- `app_func_get_dda_by_card_id` — DDA from card ID
- `app_func_get_dda_by_member` — DDA from member ID
- `app_func_get_member_by_card` — Member from card number
- `app_func_get_member_by_card_id` — Member from card ID
- `app_func_get_member_by_dda` — Member from DDA number
- `app_func_get_member_correlator` — Member correlation ID

### Escheatment Functions
- `app_func_escheatment_dda_get_address_state` — State for escheatment rules
- `app_func_escheatment_get_account_min_created` — Earliest account date
- `app_func_escheatment_get_expected_date` — Expected escheatment date
- `app_func_escheatment_get_max_fee_amount` — Max fee during dormancy
- `app_func_escheatment_get_rule_id` — Rule ID for state
- `app_func_escheatment_get_rule_set` — Rule set for state
- `app_func_escheatment_is_account_escheatable` — Is account escheatable?
- `app_func_escheatment_is_maintenance_fee_allowed` — Fee during dormancy?
- `app_func_validate_dormancy_period` — Validates dormancy period

### Notification Functions
- `app_func_notification_batch_is_active` — Is notification batch active?
- `app_func_notification_get_delivery_date` — Delivery date calculation
- `app_func_notification_get_email_address` — **Cardholder email — PII**
- `app_func_notification_get_merge_data` — Merge data for templates
- `app_func_notification_get_message_id` — Message ID
- `app_func_notification_get_sms_email_address` — **SMS gateway email — PII**
- `app_func_notitification_balance_premium_active` — Premium alert active?

### Utility / Crypto Functions
- `app_func_get_secure_token` — Returns secure token from `core_secure_profile` (joins on `owner_id`)
- `app_func_get_IBAN_Number` — Computes IBAN from account data
- `app_func_get_check_account_number_by_serial_number` — Check account number
- `ConvertFromBase` — Base conversion utility
- `enotify_url_encode` — URL encoding for notifications
- `fn_IsHoliday` — Holiday calendar check (for ACH effective date calculation)
- `fn_null` — Null helper
- `fn_puid_encode` — PUID encoding
- `GetLastWorkingDate` — Last banking day
- `maxdatetime`, `mindatetime`, `maxint`, `minint` — Type boundary utilities
- `SplitString`, `app_func_split_string` — String splitting
- `udf_Tbl_GUIDColumnsTAB` — GUID column utility

---

## Sensitive Data Fields — Complete Flag

### PCI DSS — CRITICAL

| Field | Location | Classification | Finding |
|---|---|---|---|
| `card_encrypted` | `core_card_master` (via `app_func_get_card_number_by_id`) | **PAN** | Encrypted with `card_number_cert` SQL Server certificate. GOOD — encrypted at column level. RISK — any principal with `CONTROL DATABASE` can access the cert key. |
| `card_hash` | `core_card_master` | PAN hash (SHA-1) | SHA-1 is considered weak for PCI DSS purposes — SHA-256 minimum recommended |
| `cv_code` | `fdr_card_account_detail` (via `fdr_card_account_create` which accepts `@cv_code` parameter) | **CVV/CVC2** | If stored post-authorisation = **PCI DSS violation (Req 3.3.1)**. Verify column definition and whether value is purged after use. |
| `dda_number` CHAR(16) | Multiple tables | Account number | PCI DSS scope — 16-character account identifier |
| `exp_date` | `fdr_card_account_detail` | Card expiry | Combined with PAN = full card data |

### PII — High

| Field | Location | Classification |
|---|---|---|
| `first_name`, `last_name` | `fdr_card_account_registration`, `core_member_basic` | PII |
| `email_address` | `fdr_card_account_registration`, `core_member_basic`, notification functions | PII |
| `address1`, `address2`, `city`, `state`, `postal`, `country` | `fdr_card_account_registration` | PII |
| `phone` | `fdr_card_account_registration` | PII |
| Date of birth | Not directly visible in reviewed functions but implied by KYC/1099 context | PII |
| SSN (implied) | Not directly visible in code reviewed but KYC requirements and 1099 reporting imply SSN storage | **PII — highly sensitive** |
| `ach_account` VARCHAR(64) | `ach_transaction_journal` | **Bank routing/account number** — PII/financial |
| `secure_token` | `core_secure_profile` | Authentication token — sensitive |

---

## Encryption Architecture

### Column-Level Encryption (SQL Server Certificate)
- **Certificate**: `card_number_cert`
- **Key type**: Symmetric key (implied by `DecryptByKeyAutoCert`)
- **Usage**: `card_encrypted` column in `core_card_master`
- **Decrypt functions**: `app_func_get_card_number_by_id`, `app_func_get_card_number_by_card_id_tableres`, `app_func_get_card_number_by_card_encrypted_tableres`
- **Masking function**: `app_func_get_card_number_by_id_masked` — returns first 6 + `XXXXXX` + last 4 (BIN + last4)

### CVV Encryption
The `util_update_cvcode` stored procedure in the rollback repo is declared `WITH ENCRYPTION` (SQL Server T-SQL encryption — obfuscates the procedure body in sys.syscomments). This suggests CVV update logic was intentionally obfuscated, but does not confirm the stored value is encrypted.

---

## PCI DSS CDE Scope Assessment

**This database IS the CDE.** Every system connecting to `Ecountcore` is in PCI DSS scope:
- All service accounts (`NAM\PPA_PRD_ECORESVC`, `NAM\PPA_PRD_APISVC`, etc.)
- The batch server running SSIS packages
- The `EcountCore Service` application tier
- Any reporting tool querying this database

PCI DSS Requirements directly applicable:
- **3.3.1**: SAD must not be stored — CVV presence in `fdr_card_account_detail.cv_code` must be confirmed/remediated
- **3.4.1**: PAN must be rendered unreadable — satisfied by column-level encryption with `card_number_cert`
- **3.5.1**: Key management — `card_number_cert` management procedures must be documented and key rotation scheduled
- **8.2**: Unique IDs for all access — confirmed by service account naming (`NAM\PPA_PRD_*SVC`)

---

## Data Retention

The database contains archival procedures (`archival_fdaja_dda`, `archival_journal_account_base`, `Archive_ecountcore_account_base_steps`) suggesting a formal archival process moves closed accounts out of the main tables. The archive destination appears to be a separate archive database. Retention policies are configured per-program and per-jurisdiction (escheatment rules are state-specific).
