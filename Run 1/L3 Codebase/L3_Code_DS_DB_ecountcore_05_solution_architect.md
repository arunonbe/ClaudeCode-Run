# DS_DB_ecountcore — Solution Architect View

## Technical Debt Summary

EcountCore carries the highest technical debt of all six repositories. It is a 20-year-old monolithic database that has grown organically to support a wide range of payment products. Key debt dimensions: business logic embedded in T-SQL, SHA-1 card hashing, potential CVV storage, dynamic SQL construction, absence of CI/CD, and a deeply complex stored procedure API surface that resists refactoring.

---

## Key Objects — Selected Inventory

### Functions (130+ total — selected high-impact ones)

| Object | File | Purpose |
|---|---|---|
| `app_func_get_card_number_by_id` | `dbo/Functions/app_func_get_card_number_by_id.sql` | Decrypts full PAN using `card_number_cert`. Returns CHAR(16). Any SQL trace capturing this call exposes PAN. |
| `app_func_get_card_number_by_id_masked` | `dbo/Functions/app_func_get_card_number_by_id_masked.sql` | Returns first6+XXXXXX+last4 masked PAN |
| `app_func_get_card_number_by_card_id_tableres` | `dbo/Functions/` | Table-valued function returning decrypted PAN — **highest risk for bulk PAN exposure** |
| `app_func_get_card_number_by_card_id_tableres_masked` | `dbo/Functions/` | Masked table-valued version |
| `app_func_ach_velocity_check` | `dbo/Functions/app_func_ach_velocity_check.sql` | Weekly ACH credit velocity check — uses `$500/week` hardcoded limit; should be configuration-driven |
| `app_func_build_achFundSql` | `dbo/Functions/app_func_build_achFundSql.sql` | Builds dynamic ACH funding SQL — **SQL injection risk if any input is untrusted** |
| `app_func_build_ccFundSql` | `dbo/Functions/app_func_build_ccFundSql.sql` | Builds dynamic CC funding SQL — **SQL injection risk** |
| `app_func_get_secure_token` | `dbo/Functions/app_func_get_secure_token.sql` | Returns authentication token from `core_secure_profile` |
| `app_func_notification_get_email_address` | `dbo/Functions/` | Returns cardholder email — PII exposure control needed |
| `app_func_escheatment_get_rule_id` | `dbo/Functions/` | State-specific escheatment rule lookup |

### Stored Procedures — Domain Groups (300+ total)

#### ACH Domain
| Object | Purpose |
|---|---|
| `achdirect_process_settlement_post` | Posts ACH direct settlement transactions |
| `ach_account_verify` | Verifies ACH account (micro-deposit or bank verification) |
| `ach_bank_inquiry`, `ach_bank_validate` | Bank routing number lookup and validation |
| `ach_cancel_transaction` | Cancels ACH transaction |
| `ach_event_create`, `ach_event_service`, `ach_event_jobend_service` | ACH event lifecycle |
| `ach_event_service_batch`, `ach_event_service_batch_count` | Batch ACH event processing |
| `ach_is_first_time_withdraw` | Checks if first ACH withdrawal |
| `ach_process_batch_request` | Processes ACH batch |
| `ach_profile_ach_delay_configure/extract/install` | ACH delay configuration (NACHA effective date rules) |
| `ach_profile_ach_same_day_configure/extract/install` | Same-Day ACH configuration |
| `ach_transaction_create` | Creates ACH transaction record |
| `ach_transaction_inquiry` | Queries ACH transaction |
| `ach_unprocessed_transaction_extract` | Extracts unprocessed transactions for NACHA file |
| `ach_void` | Voids ACH transaction |

#### Application / Business Logic Domain
| Object | Purpose |
|---|---|
| `app_event_service_transfer_*` | Transfer event processing |
| `app_process_1099_extract`, `app_process_1099_extract_update` | 1099 tax reporting extraction |
| `app_process_ach_funding` | ACH funding batch process |
| `app_process_activation_extract` | Card activation export |
| `app_process_assess_fee` | Fee assessment |
| `app_process_escheatment_commit`, `_enqueue`, `_due_diligence`, `_get_summary`, `_get_valid_states`, `_verify_queue` | Full escheatment lifecycle |
| `app_process_extended_dormancy`, `_ecount`, `_fee_post`, `_webcert` | Extended dormancy processing |
| `app_process_fee_funding` | Fee funding |
| `app_process_flucare_*` | FluCare health programme (FSA/HRA) processing |
| `app_process_teen_service_fee` | Teen account service fee |
| `app_process_user_overdue_fee` | Overdue fee processing |
| `app_profile_cardholder_rewards_*` | Cardholder rewards configuration |
| `app_profile_escheatment_rules_*` | Escheatment rules management |
| `app_profile_event_*` | Event configuration |
| `app_profile_feature_ach_*`, `_ach_recurrence_*`, `_ach_same_day_*` | ACH feature configuration |
| `app_profile_feature_auto_claim_*` | Auto-claim feature |
| `app_profile_feature_tax_reporting_*` | Tax reporting feature |
| `app_profile_fee_*`, `_fee_grace_period_*` | Fee profile management |
| `app_profile_global_label_*`, `_product_*`, `_symbol_*` | Global configuration |
| `app_profile_program_alert_*` | Programme alert configuration |
| `app_profile_program_auto_check_order_*` | Auto check ordering |
| `app_profile_program_check_fraud_control_*` | Check fraud controls |
| `app_profile_program_currency_*` | Currency configuration |
| `app_profile_program_debit_strategy_*` | Debit strategy |
| `app_profile_program_enrollment_*` | Enrollment configuration |
| `app_profile_program_feature_*` | Programme features |
| `app_profile_program_fulfillment_*` | Card fulfilment configuration |
| `app_profile_program_funding_cycle_*` | Funding cycle permissions |
| `app_profile_program_instant_issue_*` | Instant issue configuration |
| `app_profile_program_membership_*` | Membership configuration |
| `app_profile_program_mfa_settings_*` | MFA configuration |
| `app_profile_program_papercheck_*` | Paper check configuration |
| `app_profile_program_payment_selection_*` | Payment selection |
| `app_profile_program_precheck_*` | Pre-check fraud controls |
| `app_profile_program_refill_*` | Refill configuration |
| `app_profile_program_refund_file_threshold_*` | Refund thresholds |
| `app_profile_program_shared_secret_*` | Shared secret (TOTP/auth) |
| `app_profile_program_sort_code_*` | Sort code (UK/Canadian) |

#### Data Seed Scripts
| Object | File | Purpose |
|---|---|---|
| `bin_bank_friendly_config_map_insert_FriendlyConfigId` | `dbo/Data/` | BIN-to-bank friendly config mapping. Uses MERGE with transaction. |
| `fdr_profile_block_code_insert_BLOCKED_SANCTION` | `dbo/Data/` | Inserts OFAC sanction block codes. Uses idempotent pattern with HOLDLOCK/UPDLOCK. |

---

## Security Vulnerabilities — Detailed

### CRITICAL: CVV Presence in `fdr_card_account_detail`

**Evidence**: `fdr_card_account_create` stored procedure (in rollback repo, line 46): `insert fdr_card_account_detail ( card_number, access_level, exp_date, cv_code ) values ( @card_number, @access_level, @exp_date, @cv_code )`

The `cv_code` field is persisted to `fdr_card_account_detail`. If this column retains the CVV after card creation, this is a **PCI DSS Requirement 3.3.1 violation** — SAD must not be stored post-authorisation.

**Also**: The `util_update_cvcode` procedure (rollback repo) is `WITH ENCRYPTION` — suggesting deliberate obfuscation of CVV update logic. This raises additional concern.

**Remediation**: Verify whether `cv_code` is nullified after card activation. If not, implement a purge mechanism. Engage QSA to assess scope of violation.

---

### CRITICAL: Plaintext PAN as Stored Procedure Parameter

**Evidence**: `fdr_card_account_create` accepts `@card_number char(16)` as input. Any SQL Server query trace, Query Store capture, or extended events session that records stored procedure calls will capture the full plaintext PAN.

**Remediation**: Refactor to accept pre-encrypted or pre-hashed values at the API boundary. Disable query store capture of procedure parameters for procedures handling PANs. Ensure SQL Server `sp_configure 'in-doubt xact resolution'` and auditing are appropriately configured.

---

### HIGH: Dynamic SQL Functions

**Evidence**: `app_func_build_achFundSql` and `app_func_build_ccFundSql` build SQL strings dynamically.

**Risk**: If any input to these functions originates from user-supplied data (e.g., program codes, DDA numbers) without proper sanitisation, SQL injection is possible. These functions return SQL strings that are presumably executed via `EXEC` or `sp_executesql` by calling procedures.

**Remediation**: Review calling procedures. Confirm all inputs are validated/escaped before being passed to these functions. Prefer `sp_executesql` with parameterised queries over concatenated `EXEC` strings.

---

### HIGH: SHA-1 Card Hash

**Evidence**: `app_func_get_card_number_by_id` comments reference `card_hash` in `core_card_master`. The `fdr_process_dd031_import` procedure (process repo) uses `hashbytes('sha1', ds.card_number)` for cross-database matching.

**Risk**: SHA-1 is considered cryptographically weak. With known card number ranges (BINs are public), SHA-1 hashes of PANs can be pre-computed (rainbow table attack). PCI DSS recommends SHA-256 with random salt.

**Remediation**: Upgrade card hashing to SHA-256 with per-card random salt. This requires cross-database migration of `card_hash` values.

---

### HIGH: `development` Branch as Production Source

The active branch is `development`. Deploying from a development branch directly to production without a merge-to-main gate means unreviewed or incomplete changes could reach production.

---

### MEDIUM: Hardcoded Velocity Limit in `app_func_ach_velocity_check`

**Evidence**: Line 76: `select @maxamount = 50000` (i.e., $500 hardcoded in cents). The comment says "get setting" but immediately hardcodes the value without querying a configuration table.

**Risk**: Velocity limit changes require code deployment rather than configuration update. A DBA or developer could bypass the control by directly modifying the function.

**Remediation**: Move to a configuration table (`app_profile_program_feature` pattern already exists in the codebase).

---

## Remediation Priority Matrix

| Priority | Finding | Action |
|---|---|---|
| P0 — Immediate | CVV in `fdr_card_account_detail.cv_code` | Verify storage; implement purge if stored post-authorisation; engage QSA |
| P0 — Immediate | Plaintext PAN as SP parameter in `fdr_card_account_create` | Disable query/trace captures on PAN-handling procedures; plan API refactor |
| P1 — Within 30 days | SHA-1 card hashing | Migrate to SHA-256 with salt; coordinate cross-database update |
| P1 — Within 30 days | Dynamic SQL in `build_achFundSql`, `build_ccFundSql` | Audit callers; implement parameterised queries |
| P1 — Within 30 days | Certificate (`card_number_cert`) backup and rotation documentation | Document key management procedure; schedule annual rotation |
| P2 — Within 90 days | No CI/CD pipeline for production CDE database | Implement GitLab CI with schema validation, migration scripts, DBA approval gate |
| P2 — Within 90 days | Hardcoded velocity limit | Move to configuration table |
| P2 — Within 90 days | Data masking for non-production environments | Implement dynamic data masking or synthetic data generation |
| P3 — Within 180 days | Business logic in database stored procedures | Begin migration to service layer as part of microservices roadmap |
| P3 — Within 180 days | HSM-based tokenisation to replace column encryption | Plan tokenisation vault implementation |
