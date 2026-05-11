# DS_DP_db02 — Solution Architect Report

## Critical Security Vulnerabilities

### VULN-01: `cv_code` Column in `fdr_card_account_detail`
- **Severity:** CRITICAL
- **PCI DSS Requirement:** 3.2.1 — Sensitive Authentication Data must not be stored after authorization
- **Evidence:** `20200311_NATS-6935_insert_card_account_and_journal.sql`, line 16: `cv_code` is a defined column in `fdr_card_account_detail`. Insert statements set it to `null` but the schema column exists.
- **Risk:** If this column contains non-null values in any row in production, it constitutes a PCI DSS Requirement 3.2.1 violation — one of the most serious possible PCI violations.
- **Remediation:** (1) Immediately run `SELECT COUNT(*) FROM EcountCore.dbo.fdr_card_account_detail WHERE cv_code IS NOT NULL`. (2) If any rows found, treat as P0 security incident. (3) Regardless of result, DROP the column from the schema. (4) Review application code to ensure cv_code is never populated.
- **Priority:** P0 — BLOCKING

### VULN-02: `dda_number` as Unmasked Account Key
- **Severity:** HIGH
- **PCI DSS Requirement:** 3.3 — PAN must be masked when displayed
- **Evidence:** `dda_number` (char 16) appears in `fdr_card_account`, `fdr_dda_account_journal`, `kyc_tracker`, `core_profile_dda_payment_nacha_status` — unmasked in scripts. The journal description field (`20200311_NATS-6935`, line 47) contains merchant names but also includes the `dda_number` in plain text as a table value.
- **Risk:** `dda_number` functions as a primary account identifier. Its presence in multiple tables without masking increases blast radius of any data breach.
- **Remediation:** Implement column-level encryption or data masking on `dda_number` in non-processing contexts; audit all application queries that SELECT `dda_number` without purpose.
- **Priority:** P1

### VULN-03: Cardholder PII in `fdr_card_account_registration` Without Visible Encryption
- **Severity:** HIGH  
- **PCI DSS Requirement:** 3.5 — PAN (and associated data) must be protected
- **GLBA / CCPA:** Full name, address, email, phone constitute Non-Public Personal Information (NPPI)
- **Evidence:** Full PII fields confirmed in insert script `20200311_NATS-6935_insert_card_account_and_journal.sql`, lines 31–43
- **Risk:** No evidence of encryption-at-rest or column-level encryption for this table
- **Remediation:** Implement Transparent Data Encryption (TDE) at minimum; consider column-level encryption for name/address fields; ensure TDE keys are managed via HSM
- **Priority:** P1

### VULN-04: `EXEC(@SQL)` Dynamic SQL in Partition Migration
- **Severity:** MEDIUM
- **Evidence:** `20191018_NAMDATASVC-1388_02-Partition_security_audit_device_user_data.sql`, line 42 (shared pattern from DB04 to DB02): `EXEC (@SQL)` to drop a PK constraint using a dynamically constructed string
- **Risk:** Dynamic SQL creates SQL injection risk if any parameter is not fully sanitized. In this context the index name is read from `sys.indexes` (safe), but the pattern sets a precedent.
- **Remediation:** Replace dynamic SQL with parameterized execution where possible; document all uses of EXEC(@sql) for security review
- **Priority:** P2

---

## Technical Debt Inventory

### TD-01: `cv_code` Column Existence
See VULN-01 above. P0.

### TD-02: No Application-Level Column Encryption
- `fdr_card_account_registration` contains full cardholder PII with no evidence of encryption
- `kyc_portal_token_id` is a GUID stored in plain text — if this is a sensitive KYC token, it may need encryption
- Priority: P1

### TD-03: Linked Server Dependencies Without Documented Fallback
- `REPORTINGDBSERVER` and `DATAWAREHOUSEDBSERVER` are used in production DML scripts (SQ-3539, SQ-3087)
- No fallback or retry logic in the linked server calls
- Linked server failures would silently leave dimension tables out of sync
- Priority: P2

### TD-04: Transaction Code Updates Span Multiple Databases
- Single transaction code insert scripts update: `EcountCore`, `EcountIds`, `Prepaid_Warehouse`, and `cf_report`
- These updates run within a single script but across multiple servers (linked server calls)
- No distributed transaction coordinator (DTC) is used — partial failures leave data inconsistent across nodes
- Priority: P1

### TD-05: `Repositorysvc_rollback` / Archive on Same Instance
- Inherited pattern from DB01
- Priority: P2

### TD-06: KYC Stored Procedure Using Non-Parameterized GOTO Pattern
- `kyc_status_insert_update` SP (SQ-5175) uses `GOTO` labels for flow control
- GOTO is deprecated practice in modern T-SQL; creates maintenance complexity
- Priority: P3

### TD-07: `@@ERROR` Instead of TRY/CATCH in KYC SP
- `kyc_status_insert_update` SP uses `IF @@ERROR <> 0 GOTO` pattern (lines 95, 113) rather than TRY/CATCH blocks
- Modern T-SQL should use TRY/CATCH for consistency and correctness
- Priority: P3

---

## Complete Object Inventory

### `EcountCore` Database
| Object | Type | Purpose |
|---|---|---|
| `dbo.fdr_card_account` | Table | Core card account (card_id, dda_number, sys_prin_agent) |
| `dbo.fdr_card_account_detail` | Table | Card detail — expiration, block codes, cv_code (FLAGGED) |
| `dbo.fdr_card_account_registration` | Table | Cardholder PII (name, address, email, phone) |
| `dbo.fdr_dda_account_registration` | Table | DDA-keyed cardholder PII |
| `dbo.fdr_dda_account_journal` | Table | Transaction journal (amount, merchant, dda_number) |
| `dbo.fdr_card_number_bins` | Table | BIN/sys/prin registry |
| `dbo.fdr_profile_transaction_source` | Table | Transaction source dimension (source_id, name, inline_fee, fee_source) |
| `dbo.fdr_profile_transaction_facility` | Table | Transaction facility dimension |
| `dbo.app_profile_escheatment_rules` | Table | State dormancy configuration |
| `dbo.app_profile_dda_exclusions` | Table | DDA exclusion list for ACH processing |
| `dbo.app_profile_promotion` | Table | Program promotion configuration |
| `dbo.fdr_profile_program_schema` | Table | Program schema configuration (root_key referenced in SQ-1259) |
| `dbo.kyc_tracker` | Table | KYC workflow state tracker |
| `dbo.kyc_tracker_status` | Table | KYC status reference data |
| `dbo.kyc_status_insert_update` | Stored Procedure | KYC portal workflow orchestration |
| `dbo.core_profile_dda_payment_nacha_status` | Table | NACHA ACH payment status per DDA |

### `EcountCore_Process` Database
| Object | Type | Purpose |
|---|---|---|
| `dbo.fdr_process_dcaf_auth_data_switch` | Partitioned Table | Debit auth data switch — CDE CORE |
| `dbo.fdr_process_dcaf_chd_data_switch` | Partitioned Table | Cardholder data switch — CDE CORE |
| `dbo.fdr_process_dcaf_ticket_data_switch` | Partitioned Table | Ticket data switch |
| `dbo.fdr_process_debitach_file_switch` | Partitioned Table | ACH file staging |
| `dbo.fdvs_process_ivr_capture_file_data_switch` | Partitioned Table | IVR capture data |
| `dbo.ivr_card_activation_stage` | Table | IVR activation staging (dda_number, card_last4) |
| `dbo.ivr_card_activation_stage_backfill` | Table (temporary) | Backfill staging (created/dropped for SQ-3087) |
| `dbo.ivr_card_activation_update` | Stored Procedure | Process activation stage records |
| `dbo.ivr_card_activation_processed` | Table (inferred) | Processed activation records |

---

## Schema Consistency Notes vs. Other DS_DP Nodes

DB02 shares the following with DB04 (schema similarity):
- Both reference `EcountCore` and `EcountCore_Process` database patterns
- Transaction source/facility table structure is identical between DB02 and DB06 (same INSERT template)
- `fdr_profile_transaction_source` schema extended with `inline_fee` and `fee_source` columns in later scripts (NAMDATASVC-2302) — this extension must be confirmed present on DB04 as well

**Schema drift risk:** If DB02's `fdr_profile_transaction_source` has `inline_fee`/`fee_source` columns added but DB04 or other nodes do not, cross-node queries or reporting procedures that JOIN these tables will fail. The SQ-3539 scripts confirm this update was applied to both DB02 and DB06 — DB04 status unknown.

---

## Remediation Priority Matrix

| Priority | Item | Effort | Impact |
|---|---|---|---|
| P0 | Audit and drop `cv_code` column | LOW effort, CRITICAL impact | PCI Req 3.2.1 compliance |
| P1 | Column encryption / TDE for registration table | HIGH | GLBA/CCPA compliance |
| P1 | Distributed transaction safety for multi-DB scripts | HIGH | Data consistency |
| P1 | Audit `dda_number` exposure | MEDIUM | PCI scope reduction |
| P2 | Refactor linked server dependencies | HIGH | Resilience |
| P3 | Modernize KYC SP (GOTO → TRY/CATCH) | LOW | Maintainability |
