# DS_DB_cbaseapp — Business Analyst View

## 1. Business Purpose

`cbaseapp` is the primary cardholder application database for the Onbe prepaid card platform. It serves as the authoritative record of prepaid card members, their identities, account credentials, payment events, email queues, fee structures, fraud scoring, and all customer-service operations. It is the functional core of what was originally the eCount/CitiPrepaid cardholder management platform and continues to underpin multi-program prepaid card issuance across all Onbe client verticals (healthcare, auto, insurance, incentives, gig/creator, consumer rebates).

The project file (`Cbaseapp.sqlproj`) targets SQL Server 2012 DSP (`Microsoft.Data.Tools.Schema.Sql.Sql110DatabaseSchemaProvider`) with .NET 4.6.1 tooling. The solution (`Cbaseapp.sln`) is a Visual Studio SQL Database Project managed in source control with GitHub Actions CodeQL scanning (`.github/workflow/CodeQL.yaml`).

---

## 2. Business Processes Supported

### 2.1 Card Member Registration and Enrollment
- **User creation**: The stored procedure `b2c_create_user` creates a record in `cbase_user`, writes credentials to `user_validation_information` (username + password), and links the eCount member GUID in `user_ecount`. The `pdm_registration`, `pdm_registration_customer`, `pdm_registration_bank`, and `pdm_registration_employer` tables record the full application workflow for prepaid DDA (direct deposit account) products.
- **Enrollment tracking**: `enrollment_events`, `enrollment_event_details`, `enrollment_status`, `enrollment_options`, and `enrollment_login_verifications` capture every step of the cardholder onboarding funnel.
- **Address verification**: `address_verification`, `address_verification_history`, and `address_verfication_action` implement address validation business rules at enrollment and address-change events.
- **Email verification**: `email_verification`, `email_verification_history`, and `email_verification_action` implement email confirmation workflows.
- **MFA / OTP**: `mfa_validation_information` and `user_otp_registration_status` support multi-factor authentication for portal login.

### 2.2 Card Issuance and Embossing
- **Instant-issue**: `instant_issue_preregistration` (and its historical variants dated 070711 and rollback tables) manages pre-registered instant-issue cards before physical personalisation.
- **ECAP**: `ecap_purchaser_info`, `ecap_recipient_card_info`, `ecap_emboss_messages`, `ecap_emboss_messages_master`, `ecap_bin_number_info`, `ecap_financial_info`, `ecap_velocity_info`, `ecap_batchprocess_monitor`, and `ecap_audit_trail` collectively drive the eCount Card Activation and Provisioning subsystem. `ecap_recipient_card_info` holds the recipient's name, address, card type, shipping method, and BIN-level metadata needed for personalisation files sent to card manufacturers (Fiserv/First Data, etc.).
- **BIN management**: `ecap_bin_number_info` maps `bin_number` (BIGINT) to card name and product type, serving as the BIN register.
- **Instant-issue display settings**: `InstIssueDisplaySettings`, `InstIssueDisplayDefaultData`, `InstIssueDisplayReferenceFields`, `InstIssuePmtOrRevReasons`, and `InstIssueDispValidationMetaData` configure the UI that bank-branch or CSA staff use for point-of-sale instant issuance.

### 2.3 Card Loading and Fund Management
- **Payment**: The `payment` table is the central payment record, linking a buyer (`buyer_id`) to a recipient (`recipient_id`) with amount, verification code, IVR claim code (computed column), and activation date. Card loading is recorded here and in `user_transaction_history`.
- **Batch payments**: `batch_payment`, `batch_payment_detail`, `batch_payment_detail_history`, and `batch_payment_status` manage bulk disbursements (e.g., healthcare reimbursements, auto finance settlements). `proc_batch_payment_initialize_ins`, `proc_batch_payment_detail_ins`, and `proc_release_batch_payment_upd` implement the multi-step batch load lifecycle.
- **PDM registration bank**: `pdm_registration_bank` records ABA routing number hash (`aba_number_hash_key`), ACH device ID, and fund-availability date for DDA-linked direct deposit programs.
- **Balances**: Card balances are managed by the downstream `ecountcore` system; cbaseapp records the association between `user_id` and `ecount_member_id` / `dda_id` via `user_ecount`.

### 2.4 Transaction History
- `user_transaction_history` records every platform-level transaction event: service type, eCount transaction GUID, IP address, amount (integer cents), fee, result code, and cardholder confirmation number.
- `ecap_transaction_info` captures a credit card number (`credit_card_number CHAR(50)`) associated with purchaser/member, used for funding a prepaid card via credit card — a **PCI DSS CDE-scoped field** (see Section 5).
- `debit_audit_info`, `card_balance_debit_details`, and `card_balance_debit_promotion` track promotional debit events and card-balance debiting processes.

### 2.5 Member Profile and Address Management
- `user_personal_info` holds first name, last name, middle initial, phone number, **date of birth** (`birth_date`), and gender for each cardholder.
- `user_address` and `address` hold mailing/residential address (street, city, state, zip, country).
- `user_email` and `email_address` hold one or more email addresses per user.
- Profile history tables (`user_personal_info_history`, `user_address_history`, `user_email_history`) preserve prior-state records for auditing.

### 2.6 Fraud Detection and Risk
- `fraud_score` tracks a real-time fraud score per user, counting completed transactions, prior ACH/credit-card load attempts, free-email-domain flags, and supervisor-verified status.
- `FraudAddressChanges`, `FraudCCVelocity`, `FraudHighDollar`, `FraudMultiPay`, and `FraudRefunds` are dedicated fraud surveillance tables populated by batch processes detecting suspicious patterns.
- `risk_score` is a supplementary risk scoring table.
- `proc_fraud_score_calc`, `proc_fraud_score_ecount_calc`, and `proc_fraud_score_batch_upd` implement the scoring algorithms.

### 2.7 Customer Service (CSA Portal)
- CSA (Customer Service Application) stored procedures — `csa_forward_search`, `csa_lock_info`, `csa_status_info`, `csa_user_info_by_member_id`, `csa_pdm_customer_search`, `csa_GetEcountHist`, `proc_csa_get_transaction_hist` — enable agents to search for cardholders, view balances, and process service requests.
- `Service_Records`, `service_records_escalation`, `service_records_assignee`, `service_records_rapid_file`, and `service_records_status` manage customer service tickets.
- `csa_monetary_adjustments`, `csa_fee_reversals`, and `csa_fee_reversal_group` support agent-initiated financial adjustments and fee waivers.

### 2.8 Affiliate and Program Management
- `affiliate`, `affiliate_detail`, `affiliate_locale`, `affiliate_enrollment`, and `affiliate_batch` configure each client program (affiliate) including locale copy, branding, and batch settings.
- `bridge_programs`, `bridge_program_status`, `bridge_program_screen_status`, `bridge_featurecontrol_config`, `bridge_czsetup_configuration`, and `bridge_accesslevel_configuration` manage the Bridge admin portal's per-program feature flags and access rules.
- `opsetup_features_master`, `opsetup_features_transaction`, and `opsetup_fee_affiliate` configure per-program operational features and fee schedules.

### 2.9 Notification and Email
- `email_queue`, `enotify_request`, `enotify_task_queue`, `enotify_instant_task_queue`, and `enotify_schedule` drive the email notification engine.
- `sms_cardnotification_profile` and `sms_cardnotification_log` handle SMS card-activity alerts.
- `Template`, `email_templates`, and merge-field tables (`template_type_merge_field`, `template_static_merge_reference`) define email/SMS personalisation.

### 2.10 Security and Access Control
- `security_role`, `security_group`, `security_permission`, `security_method`, `security_url`, `security_acl_permission`, and `security_acl_object_identity` implement a fine-grained RBAC model.
- `security_audit_log`, `security_audit_event`, `security_audit_user_data`, and `app_audit_event` / `app_audit_session` provide application-level audit trails for portal actions.
- `user_admin_tpin` stores an encrypted (VARBINARY 256) TPIN for administrative telephone-PIN operations.
- `strongbox_ticket` holds short-lived Strongbox references used for secure secret retrieval.

### 2.11 Rewards Programs
- The `rewards_gmict_*` table family (25 tables) manages GM/ICT dealer incentive reward payments.
- The `rewards_subaru_*` table family (20 tables) manages Subaru sales incentive programs, including territory ascent schedules, cycles, and reward addenda.
- Both programs result in batch disbursements back through the `payment` and `batch_payment` flows.

---

## 3. Business Rules Encoded in Stored Procedures

| Procedure | Business Rule |
|---|---|
| `b2c_create_user` | Enforces username uniqueness across application IDs 3 and 6; prevents duplicate eCount member IDs |
| `b2c_login_user` | Locks account after 5 failed logins within 60 minutes (lockout window) |
| `proc_fraud_score_calc` | Scores transactions against velocity, address-change frequency, and free-email-domain flags |
| `proc_busFraudPayment_Sel` | Selects payments matching fraud hold criteria for manual review |
| `proc_busAcceptWithdrawal_Upd` / `proc_busRejectWithdrawal_Upd` | Two-stage payment release/reject workflow |
| `cbaseapp_process_partition_maintain` | Manages time-based partitioning on high-volume tables |
| `cancel_payment` | Cancels in-flight payment and records reversal |
| `card_balance_debit_update_job` | Batch job that processes promotional card balance debits |
| `csa_monetary_adjustments` | Governs which CSA roles may perform monetary adjustments and fee reversals |
| `ddl_create_session_login` | Dynamically creates monthly partitioned session-login tables using `sp_executesql` |

---

## 4. Regulatory Relevance

### PCI DSS Requirements 3 and 6
- `ecap_transaction_info.credit_card_number` (CHAR 50) stores a credit card number in plaintext — this is a CDE-scope finding requiring immediate assessment. See `02_data_architect.md`.
- `pdm_registration.dda_number` (CHAR 16) stores a 16-digit DDA/card number. Whether this is a PAN or a DDA number determines PCI scope.
- The absence of column-level encryption on any PII/CHD fields (PAN, DOB, SSN) is a gap against PCI DSS Req 3.4.

### NACHA / Reg E
- `pdm_registration_bank.aba_number_hash_key` stores a hashed bank routing number, and `pdm_registration.dfi_number` (CHAR 17) and `dda_number` (CHAR 16) store ACH identifiers. NACHA-regulated ACH debit/credit flows originate from cbaseapp payment initiations.
- `csa_monetary_adjustments_addenda` tracks error-correction and return addenda relevant to Reg E dispute rights.

### OFAC / AML
- `arcsight_country_program_filter_list` and `sanction_field_state` tables implement sanctions screening configuration.
- `security_audit_cz_allowed_users_temp` and `security_audit_approved_country_list_temp` are used in OFAC country-allowlist reviews.

### GDPR / CCPA
- `user_personal_info` (name, DOB, phone), `address`, `email_address`, and `user_validation_information` contain personal data subject to GDPR/CCPA deletion and portability rights. No retention-policy columns (e.g., `purge_date`, `data_subject_request_id`) are visible in schema files.

---

## 5. Data Flows

```
Client Application / Web Portal
        |
        v
cbaseapp stored procedures (b2c_create_user, b2c_login_user, etc.)
        |
        +---> user_ecount (links user_id <-> ecount_member_id / dda_id)
        |           |
        |           v
        |     ecountcore database (DDA balances, transaction journal)
        |
        +---> payment / batch_payment (payment records)
        |
        +---> user_transaction_history (platform audit log)
        |
        +---> email_queue / enotify (outbound notifications)
        |
        +---> fraud_score (real-time fraud scoring)
        |
        +---> CSA portal (csa_* procs for agent access)
        |
        +---> cf_report database (reporting extracts via linked server)
```

---

## 6. Summary Statistics

| Object Type | Count |
|---|---|
| Tables (dbo schema) | 509 |
| Stored Procedures | 781 |
| Views (dbo + b2c) | 28 |
| Functions | 4 |
| User-Defined Types | Multiple (type_id, type_first_name, ecount_guid, etc.) |
| Schemas | dbo, b2c |
