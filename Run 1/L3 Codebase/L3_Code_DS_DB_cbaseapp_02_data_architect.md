# DS_DB_cbaseapp — Data Architect View

## 1. Schema Overview

The `cbaseapp` database is a SQL Server 2012-targeted database project with two schemas: `dbo` (primary) and `b2c` (B2C spend-portal objects). The project file (`Cbaseapp.sqlproj`) lists 509 table DDL files, 781 stored-procedure files, 28 view files, 4 function files, and multiple user-defined types.

---

## 2. Complete Database Object Inventory

### 2.1 Tables — Core Cardholder Identity

| Table | Key Columns | Sensitivity |
|---|---|---|
| `cbase_user` | `user_id` IDENTITY, `application_id`, `affiliate_id`, `user_status`, `created` | Low — no CHD; PK for all cardholder data |
| `user_personal_info` | `user_id`, `first_name`, `last_name`, `middle_initial`, `phone_number`, **`birth_date`**, `gender`, `mobile_number` | **HIGH — DOB is PII (GDPR/CCPA); full name + phone** |
| `user_personal_info_history` | Same columns, history snapshot | **HIGH** |
| `user_validation_information` | `user_id`, `username`, **`password`** VARCHAR(100), `password_type`, `secret_question`, `secret_answer`, `application_id` | **CRITICAL — password stored; type=0 suggests possible plaintext or weak hash** |
| `user_ecount` | `user_id`, `ecount_id` (GUID), `ecount_member_id` (GUID), `dda_id` (GUID), `status_code` | Medium — eCount GUIDs are internal identifiers |
| `user_address` | `user_id`, `address_id`, `address_type` | Medium |
| `address` | `address_id`, `street1`, `street2`, `city`, `state`, `country`, `zip` | **HIGH — full residential address (PII)** |
| `user_address_history` | History of address | **HIGH** |
| `user_email` | `user_id`, `email_id`, `email_address_type` | Medium |
| `email_address` | `email_id`, `address` VARCHAR | **HIGH — email address (PII)** |
| `user_email_history` | History of email | HIGH |
| `user_admin_tpin` | `user_id`, **`tpin`** VARBINARY(256), `created_date` | **HIGH — encrypted PIN; column-level encryption via VARBINARY — verify key management** |

### 2.2 Tables — Payment and Transaction

| Table | Key Columns | Sensitivity |
|---|---|---|
| `payment` | `payment_id`, `amount`, `echeck_id` GUID, **`verification_code`**, `buyer_id`, `recipient_id`, `recipient_email`, `recipient_first_name`, `recipient_last_name`, `activation_date`, `ivr_claim_code` (computed) | **HIGH — recipient PII, IVR claim code** |
| `payment_history` | History of payment actions | HIGH |
| `payment_request` | `payment_id`, `payment_request_action_code`, amounts | Medium |
| `batch_payment` | `batch_id`, `affiliate_batch_payment_id`, `sender_name`, `sender_email` | Medium |
| `batch_payment_detail` | Per-payment detail rows | HIGH |
| `batch_payment_detail_history` | History of detail rows | HIGH |
| `user_transaction_history` | `transaction_id`, `timestamp`, `user_id`, `service_type`, `ecount_transaction_id`, `user_confirmation_number`, **`ip_address`**, `transaction_result_code`, `amount`, `fee`, `ecount_member_id` | **HIGH — IP address, amounts, confirmation numbers** |
| `user_transaction_history_old` | Legacy copy | HIGH |
| `transfer_ticket` | `id`, `created`, `transfer_id` GUID, `claim_code` VARCHAR(32) | Medium |
| `strongbox_ticket` | `id`, `created`, `strongbox_reference`, `code` | Medium — internal security reference |

### 2.3 Tables — Registration and KYC

| Table | Key Columns | Sensitivity |
|---|---|---|
| `pdm_registration` | `registration_id`, `channel_id`, `iaffiliate_id`, **`dda_number`** CHAR(16), **`dfi_number`** CHAR(17), `member_id`, `dda_device_id`, `ip_address` | **CRITICAL — dda_number CHAR(16) may be a PAN; dfi_number is a routing/transit number** |
| `pdm_registration_customer` | `registration_id`, `first_name`, `last_name`, `address1`–`city`–`state`–`zip`, `email_address`, phone fields, **`birthdate`** DATETIME | **CRITICAL — full PII set including DOB** |
| `pdm_registration_bank` | `registration_id`, `add_funds_amount`, **`aba_number_hash_key`** VARCHAR(100), `ach_device_id` | **HIGH — routing number hash; ACH device ID** |
| `pdm_registration_profile` | Profile fields | HIGH |
| `pdm_registration_employer` | Employer fields | HIGH |
| `pdm_registration_partner_fields` | Partner-specific KYC fields | HIGH |
| `pdm_registration_v2` | Extended registration v2 | HIGH |
| `pdm_payroll_detail` | Payroll data | HIGH |

### 2.4 Tables — ECAP (Card Issuance)

| Table | Key Columns | Sensitivity |
|---|---|---|
| `ecap_purchaser_info` | `confirmation_number`, `member_id`, `first_name`, `last_name`, `address1`–`zip`, `email_id`, `state_code`, `country_code` | **HIGH — PII of card purchaser** |
| `ecap_recipient_card_info` | `recipient_id`, `member_id`, `first_name`, `last_name`, `address1`–`zip`, `email_id`, `card_value`, `card_type`, `shipping_method` | **HIGH — recipient PII and card value** |
| `ecap_bin_number_info` | `bin_number` BIGINT, `card_name`, `type` | **MEDIUM — BIN register; BIN itself is not PAN but is CHD-adjacent** |
| `ecap_transaction_info` | `id`, `member_id`, **`credit_card_number`** CHAR(50) | **CRITICAL — credit card number in plaintext; PCI DSS Req 3.4 violation** |
| `ecap_velocity_info` | Velocity counters per member | Medium |
| `ecap_financial_info` | Load ceilings per affiliate | Medium |
| `ecap_audit_trail` | Audit events | High |
| `ecap_batchprocess_monitor` | Batch job tracking | Low |

### 2.5 Tables — Fraud and Risk

| Table | Key Columns | Sensitivity |
|---|---|---|
| `fraud_score` | `iuser_id`, `ifraudscr_score`, transaction counts, ACH load counts, free-email flag | HIGH |
| `FraudAddressChanges` | Suspicious address-change events | HIGH |
| `FraudCCVelocity` | Credit-card load velocity | HIGH |
| `FraudHighDollar` | Large transaction flags | HIGH |
| `FraudMultiPay` | Multiple payment detection | HIGH |
| `FraudRefunds` | Suspicious refunds | HIGH |
| `risk_score` | Supplementary risk data | HIGH |

### 2.6 Tables — Security and Audit

| Table | Key Columns | Sensitivity |
|---|---|---|
| `AuditTrail` | `Action`, `Table_Name`, `Primary_Key`, `Pre_Snap` NVARCHAR(2000), `Post_Snap` NVARCHAR(2000), `User_Name`, `Change_Date` | **HIGH — contains before/after snapshots of data changes; may capture CHD snapshots** |
| `security_audit_log` | Application-level audit log | HIGH |
| `security_audit_event` | Event types | Low |
| `security_audit_user_data` | User data at audit time | HIGH |
| `app_audit_event` | Portal audit events | HIGH |
| `app_audit_session` | Portal session audit | HIGH |
| `login_history` | Login attempts with `username`, `ip_address`, result code | HIGH |
| `ddl_log` | DDL change log | Medium |
| `access_entity_certificate` | Certificate-based access entities | HIGH |

### 2.7 Tables — Notifications

| Table | Key Columns | Sensitivity |
|---|---|---|
| `email_queue` | Email body, recipient, sender, status | HIGH |
| `mail_queue` | Physical mail queue | HIGH |
| `enotify_request`, `enotify_task_queue` | Notification jobs | Medium |
| `sms_cardnotification_profile` | Phone number, program, notification preferences | **HIGH — mobile number** |

### 2.8 Tables — Affiliate, Program, and Config (Low/Medium Sensitivity)

`affiliate`, `affiliate_detail`, `affiliate_locale`, `affiliate_enrollment`, `affiliate_batch`, `affiliate_batch_type`, `affiliate_field_lookup`, `affiliate_fieldname`, `affiliate_fieldtype`, `affiliate_glamour_name`, `affiliate_locale_affiliate`, `affiliate_locale_copy`, `affiliate_locale_copy_tag`, `affiliate_locale_copy_type`, `affiliate_locale_skin` — all configuration/reference data.

`bridge_programs`, `bridge_program_status`, `bridge_program_screen_status`, `bridge_featurecontrol_config`, `bridge_czsetup_configuration`, `bridge_czsetup_load_restriction`, `bridge_precheckcontrol_config`, `bridge_accesslevel_configuration`, `bridge_promotionlevel_configuration` — Bridge admin-portal configuration.

`opsetup_features_master`, `opsetup_features_transaction`, `opsetup_fee_affiliate`, `opsetup_fee_velocity`, `opsetup_graphics`, `opsetup_header_master` — operational setup.

`fee_definition`, `fee_presentation`, `fee_presentation_details`, `fee_set`, `fee_source` — fee schedule configuration.

### 2.9 Views

| View | Purpose |
|---|---|
| `dbo.Account_info_View` | Joins cbase_user + personal_info + address + email + payment + transaction_history; returns demographic and payment data — **contains PII** |
| `dbo.v_general_users_demographic` | General demographic summary |
| `dbo.v_buyer_info_exists` | Payment buyer lookup |
| `dbo.v_recipient_info_exists` | Payment recipient lookup |
| `dbo.v_batch_payment` | Batch payment summary |
| `dbo.view_user_email` | User email listing |
| `dbo.v_user_demographics` | User demographics |
| `dbo.v_total_ecount_hist` | eCount transaction history (linked-server view) |
| `dbo.v_pdm_registration` | PDM registration summary |
| `dbo.pdm_affiliate_meta_data` | Affiliate metadata |
| `dbo.pdm_workflow_status_*` (8 views) | PDM workflow state per section |
| `dbo.init_verification_status` | Enrollment verification |
| `dbo.access_entity_*_view` (5 views) | Access entity lookups |
| `dbo.affiliate_locale_copy_view` | Locale copy content |
| `b2c.session_login_info` | B2C login session union (dynamically managed by `ddl_create_session_login`) |

### 2.10 Stored Procedures — Selected Catalogue

781 procedures. Key groups:

- **User lifecycle**: `b2c_create_user`, `backup_create_cbase_user`, `rs_create_user`, `bmc_update_user`, `update_user_profile`, `update_personal_info`, `update_user_personal_info`
- **Authentication**: `b2c_login_user`, `bc_login_user`, `update_user_password`, `update_password2`, `set_password_status`, `update_security_questions`, `username_exists`
- **Payment**: `cancel_payment`, `cancel_payment_request`, `settle_payment_request`, `resend_payment_request`, `proc_batch_payment_initialize_ins`, `proc_batch_payment_detail_ins`, `proc_release_batch_payment_upd`
- **Fraud**: `proc_fraud_score_calc`, `proc_fraud_score_ecount_calc`, `proc_fraud_score_new_user_ins`, `proc_fraud_score_batch_upd`, `proc_busFraudPayment_Sel`
- **CSA search**: `csa_forward_search`, `csa_pdm_customer_search`, `csa_user_info_by_member_id`, `csa_lock_info`, `csa_status_info`, `csa_GetEcountHist`
- **Card issuance**: `card_balance_debit_update_job`, `card_balance_debit_populate_recent_orders`
- **Enrollment**: `proc_enroll_confirm_upd`, `proc_enroll_get_confirm_sel`
- **Dynamic SQL** (security risk): `csa_forward_search` (EXEC(@strSQL)), `csa_GetEcountHist` (EXEC(@strSql)), `set_login_info`, `ddl_create_session_login` (sp_executesql)
- **DBA utilities**: `utl_dba_db_stats_history`
- **Inquiry**: `cbaseapp_user_inquiry`, `OAccount_Details_inquiry`, `proc_pb_csa_get_user_information`, `banker_get_cbase_user_info`

### 2.11 Functions

| Function | Purpose |
|---|---|
| `dbo.bounce_func_get_member_id` | Retrieves member ID for bounce processing |
| `dbo.SplitString` | String split utility |
| `dbo.func_get_binary_IPv4` | Converts dotted-decimal IPv4 to binary |
| `dbo.func_get_string_IPv4` | Converts binary IPv4 to dotted-decimal |

### 2.12 User-Defined Types

`type_id`, `type_first_name`, `type_last_name`, `type_street`, `type_city`, `type_state`, `type_country`, `type_zipcode`, `type_timestamp`, `type_code`, `type_boolean`, `type_login_name`, `type_ip_address`, `type_salutation`, `type_gender`, `type_verification_code`, `type_denomination`, `type_brief_description`, `ecount_guid`, `ecount_avs_message`, `ecount_transaction_amount`

---

## 3. Sensitive Data Field Inventory

| Table.Column | Data Type | Classification | PCI DSS / Regulatory Flag |
|---|---|---|---|
| `ecap_transaction_info.credit_card_number` | CHAR(50) | **CHD — PAN** | **PCI DSS Req 3.4 — CRITICAL: plaintext PAN; must be masked, tokenised, or encrypted** |
| `pdm_registration.dda_number` | CHAR(16) | **Potential PAN / Account Number** | PCI DSS Req 3 scope assessment required; 16-digit field on a BIN-linked account |
| `pdm_registration.dfi_number` | CHAR(17) | **ABA Routing + Account** | NACHA-scope; bank account identifier |
| `pdm_registration_bank.aba_number_hash_key` | VARCHAR(100) | Hashed routing number | Hashing approach unknown; verify algorithm strength |
| `user_personal_info.birth_date` | type_timestamp (DATETIME) | **DOB — PII** | GDPR/CCPA; PCI DSS CHD-adjacent for KYC |
| `pdm_registration_customer.birthdate` | DATETIME | **DOB — PII** | GDPR/CCPA |
| `user_personal_info.first_name`, `last_name` | Custom types | **PII — Cardholder Name** | PCI DSS Req 3 (cardholder name is CHD) |
| `user_validation_information.password` | VARCHAR(100) | **Credential** | Must be hashed with bcrypt/Argon2; `password_type=0` may indicate plaintext or MD5 |
| `user_validation_information.secret_answer` | type_brief_description | **Security secret** | Should be hashed |
| `user_admin_tpin.tpin` | VARBINARY(256) | Encrypted PIN | Column-level encryption; verify key management |
| `address.street1`–`zip` | Custom types | **PII — Full Address** | GDPR/CCPA |
| `email_address.address` | VARCHAR | **PII — Email** | GDPR/CCPA |
| `user_transaction_history.ip_address` | type_ip_address | **PII — IP Address** | GDPR (personal data); CCPA |
| `ecap_purchaser_info.*` (name, address) | VARCHAR fields | **PII** | GDPR/CCPA |
| `ecap_recipient_card_info.*` (name, address) | VARCHAR fields | **PII** | GDPR/CCPA |
| `AuditTrail.Pre_Snap`, `Post_Snap` | NVARCHAR(2000) | **Potential CHD/PII snapshot** | If audit captures CHD fields, this is a CDE-scoped table |
| `ecap_bin_number_info.bin_number` | BIGINT | BIN register | PCI DSS context — not a full PAN |

---

## 4. Encryption at Rest Assessment

### Transparent Data Encryption (TDE)
- No TDE configuration files exist in this repository. TDE is a SQL Server instance-level configuration; its presence cannot be confirmed from DDL alone. **Verification required against production SQL Server configuration.**
- Given PCI DSS Req 3.5 (protect stored cardholder data), TDE should be confirmed active on the cbaseapp database.

### Column-Level Encryption
- `user_admin_tpin.tpin` VARBINARY(256) — explicit column-level storage; encryption key management unknown.
- `pdm_registration_bank.aba_number_hash_key` VARCHAR(100) — described as a hash; algorithm not confirmed.
- `user_validation_information.password` VARCHAR(100) — `password_type` column exists but no documentation of hash algorithm. The `b2c_create_user` procedure accepts plaintext password parameter and inserts directly, suggesting the hashing occurs at the application layer (or does not occur at all).
- All other sensitive columns (PAN, DOB, name, address) have **no column-level encryption** in DDL.

---

## 5. PCI DSS CDE Scope Assessment

**CDE CONFIRMED IN SCOPE:**

1. `ecap_transaction_info.credit_card_number` — stores credit card number used to fund prepaid cards. This is a PAN and is in explicit CDE scope under PCI DSS Req 3.
2. `pdm_registration.dda_number` CHAR(16) — 16-digit account identifier on a prepaid DDA; if this is the embossed card number, it is a PAN and CDE-scoped.
3. `ecap_recipient_card_info` — contains cardholder name, address, and card metadata submitted to the embosser.
4. `ecap_purchaser_info` — contains cardholder name and address for the card purchaser.
5. `user_personal_info` — cardholder name (PCI DSS Req 3 defines cardholder name as CHD).
6. `AuditTrail` — `Pre_Snap`/`Post_Snap` may capture snapshots of CDE tables; must be classified as CDE-scope.

**PROBABLE CDE:**
- `ecap_bin_number_info` — BIN registry
- `payment` — payment records with verification codes and amounts
- `user_transaction_history` — transaction log

---

## 6. Data Retention

No `purge_date`, `retention_date`, or data-subject-request columns were found in any table DDL. The presence of tables like `email_queue_archive_test`, `email_queue_archive_work`, and history tables (`*_history`) suggest ad-hoc archival rather than a systematic retention framework. **This is a gap against PCI DSS Req 3.1 (data retention policy) and GDPR Art. 5(1)(e) (storage limitation).**

---

## 7. Index Strategy Notes

- High-volume tables use `FILLFACTOR = 70` (payment, user_transaction_history) reflecting heavy write activity.
- Tables supporting lookups use `FILLFACTOR = 90`.
- `user_transaction_history` has a non-clustered PK and a clustered index on `user_id` — appropriate for per-user transaction scans.
- `ecap_transaction_info` — primary key only; no additional indexes. Given it stores PANs this warrants access restriction rather than indexing optimisation.
