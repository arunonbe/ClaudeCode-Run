# DS_DB_jobsvc — Solution Architect Report

## 1. Technical Debt Inventory

| Debt Item | Location | Severity | Remediation |
|-----------|----------|----------|-------------|
| `card_number` CHAR(16) plaintext | `instant_issue_card.sql` | **CRITICAL** | Tokenise via Strongbox; truncate to first 6 / last 4 |
| `parent_dda` CHAR(16) plaintext | `instant_issue_card.sql` | **CRITICAL** | Tokenise or mask DDA number |
| Card expiry `exp_month/exp_year` post-auth | `job_action_issue_card.sql` | **HIGH** | Remove post-authorization; do not store SAD |
| Quartz 1.x schema (`IS_VOLATILE`, `IS_STATEFUL`) | `QRTZ_JOB_DETAILS.sql` | **HIGH** | Upgrade to Quartz 2.x or Spring Scheduler |
| `IMAGE` datatype on `QRTZ_JOB_DETAILS.JOB_DATA` | `QRTZ_JOB_DETAILS.sql` | **HIGH** | Replace with VARBINARY(MAX) |
| SQL 2012 compatibility level | `jobsvc.sqlproj` | **HIGH** | Upgrade to SQL 2019+ (compat 150) |
| No CI/CD pipeline committed | Repo root | **HIGH** | Add Jenkins/GitLab pipeline |
| `zzz_` deprecated tables (7 tables) | `dbo/Tables/` | **MEDIUM** | Archive data; DROP tables |
| CDC backup tables (6 tables) | `dbo/Tables/` | **MEDIUM** | Confirm reference-only; DROP |
| `IF NOT EXISTS` ALTER drift | `job_action_register_user.sql` | **MEDIUM** | Normalise to DeltaSql pattern |
| No DeltaSql migration folder | Repo root | **MEDIUM** | Implement migration script structure |
| `job_action_memo_secure.field_secure_ref` vault dependency | `job_action_memo_secure.sql` | **MEDIUM** | Document vault dependency; implement availability monitoring |
| `temp_*` / `migrate_*` tables | `dbo/Tables/` | **LOW** | Review and remove temporary migration artifacts |

## 2. Security Vulnerability Assessment

### 2.1 CRITICAL — PAN Storage in `instant_issue_card.card_number`
**Finding**: `instant_issue_card.card_number` CHAR(16) — column name, length, and context all indicate PANs may be stored in plaintext.  
**Location**: `dbo/Tables/instant_issue_card.sql` line 19  
**PCI DSS Violation**: Requirement 3.3.1 — "SAD must not be stored after authorization, even if encrypted."  
**Remediation Steps**:
1. Query production: `SELECT TOP 10 card_number FROM instant_issue_card WHERE card_number IS NOT NULL`
2. If full PANs confirmed: engage PCI QSA immediately; implement tokenisation via Strongbox before next assessment
3. Replace `card_number` with `card_token` referencing Strongbox vault
4. Truncate existing records to first 6 / last 4 format

### 2.2 CRITICAL — DDA Number Storage in `instant_issue_card.parent_dda`
**Finding**: `parent_dda` CHAR(16) — Demand Deposit Account number stored in instant_issue_card.  
**Location**: `dbo/Tables/instant_issue_card.sql` line 18  
**Impact**: Full bank account numbers must not be stored without tokenisation or encryption.  
**Remediation**: Tokenise via Strongbox; store only masked/tokenised reference.

### 2.3 HIGH — SAD Retention (`exp_month/exp_year`)
**Finding**: `job_action_issue_card.exp_month` (INT) and `exp_year` (INT) store card expiry.  
**Location**: `dbo/Tables/job_action_issue_card.sql` lines 5–6  
**PCI DSS**: Requirement 3.3.2 — Sensitive Authentication Data (SAD) must not be retained after authorization.  
**Remediation**: Determine if expiry data is retained post-authorization. If yes, implement purge process.

### 2.4 HIGH — Java Deserialization Risk in Quartz Job Data
**Finding**: `QRTZ_JOB_DETAILS.JOB_DATA` typed as `IMAGE` stores serialised Java objects.  
**Impact**: Java deserialization of untrusted data is a well-known RCE attack vector (CVE family). If job data can be modified via SQL, it may be exploitable.  
**Remediation**: Restrict write access to `QRTZ_*` tables to the service account only; upgrade Quartz runtime; move to `VARBINARY(MAX)`.

### 2.5 HIGH — OFAC Screening Status Not Enforced at DB Level
**Finding**: `job_action_register_user.recipient_screening_status` VARCHAR(40) stores AML/OFAC screening results but has no check constraint or FK preventing actions from proceeding when `recipient_screening_status` = 'BLOCKED' (or equivalent).  
**Impact**: If application-layer enforcement fails, a blocked recipient could have actions processed.  
**Remediation**: Add a DB-level constraint or trigger that prevents `job_action` completion when `recipient_screening_status` indicates a blocked status.

## 3. All Database Objects with Purpose

### Tables — Full Catalogue

| Table | Purpose | PII/Compliance Flag |
|-------|---------|---------------------|
| `ach_event_status` | ACH status reference codes | No |
| `ach_event_types` | ACH event type reference | No |
| `ach_transfer_detail` | ACH transfer lifecycle | **NACHA/Reg E** |
| `autofile_funds_retry_queue` | Failed fund retry queue | No |
| `autofile_job` | Autofile job records | No |
| `autofile_phase` | Autofile processing phases | No |
| `autofile_status` | Autofile status reference | No |
| `banker_action` | Banker-initiated actions | No |
| `banker_action_log` | Banker action change log | No |
| `banker_approval_notification` | Approval notification tracking | No |
| `banker_available_funds_rule` | Fund availability rules | Financial |
| `banker_default_promo_exception_program` | Promo exception config | No |
| `banker_document_type` | Document type reference | No |
| `banker_email` | Banker email records | No |
| `banker_group_amt_mapping` | Group amount mappings | Financial |
| `banker_job` | Banker job records | No |
| `banker_job_status` | Job status reference | No |
| `banker_payment_method` | Payment method reference | No |
| `banker_payment_type` | Payment type reference | No |
| `banker_preset_funds_config` | Preset fund config | Financial |
| `banker_promotion` | Promotion-level config | Financial |
| `banker_reserved_source` | Reserved fund sources | Financial |
| `banker_reserved_source_log` | Source change log | Financial |
| `banker_temp_unsettled_sources` | Temp unsettled source tracking | Financial |
| `banker_user_group_amt_mapping` | User-group amount mapping | Financial |
| `blackout_actions_log` | Blackout action log | No |
| `blackout_job` | Blackout job records | No |
| `blackout_master` | Blackout period definitions | No |
| `blackout_schedule` | Blackout schedule | No |
| `blackout_weekly_day` | Weekly day blackout rules | No |
| `CDC_captured_columns_bk` | CDC system table backup | No |
| `CDC_change_tables_bk` | CDC system table backup | No |
| `CDC_ddl_history_bk` | CDC DDL history backup | No |
| `CDC_index_columns_bk` | CDC index columns backup | No |
| `CDC_Job_account_map_CT_bk` | CDC change table backup | No |
| `CDC_lsn_time_mapping_bk` | CDC LSN mapping backup | No |
| `CodeArchive` | Archived code reference | No |
| `dav_us_zips` | US ZIP code lookup table | No |
| `ddl_log` | DDL change log | Operational |
| `file_types` | File format reference | No |
| `id_sequences` | Custom sequence generators | No |
| `instant_issue_card` | Card inventory with card_number | **CRITICAL PCI** |
| `instant_issue_core_sync_info` | EcountCore sync state | No |
| `instant_issue_current_inventory_details` | Current card inventory | No |
| `instant_issue_current_inventory_details_log` | Inventory change log | No |
| `instant_issue_inv_card_expiry_notification_log` | Expiry notification log | No |
| `instant_issue_inv_email_log` | Email delivery log | No |
| `instant_issue_inv_email_queue` | Email notification queue | No |
| `instant_issue_inv_email_type` | Email type reference | No |
| `instant_issue_notification` | Notification records | No |
| `instant_issue_order` | Card order records | No |
| `instant_issue_profile_facility` | Facility profile config | No |
| `instant_issue_profile_used_type` | Usage type profile | No |
| `instant_issue_profile_used_type_facility` | Facility-usage profile | No |
| `instant_issue_reserved_type` | Reserved type reference | No |
| `instant_issue_used_card_log` | Card usage audit log | **PCI-adjacent** |
| `inventory_card_action_status` | Card action status reference | No |
| `inventory_order_status` | Order status reference | No |
| `job_account_map` | Job-to-account mappings | No |
| `job_action` | Root action record | No |
| `job_action_add_funds` | Fund loading action (claim_code, echeck_id) | **HIGH — payment token** |
| `job_action_add_funds_cert` | Certified fund load | Financial |
| `job_action_add_funds_cert_memo` | Certified fund memo | Financial |
| `job_action_create_cert` | Certificate creation | No |
| `job_action_create_cert_memo` | Certificate creation memo | No |
| `job_action_create_email_notification` | Email notification setup | No |
| `job_action_create_web_user` | Web user creation | No |
| `job_action_history` | Action execution history | Operational |
| `job_action_history_Archive` | Archived action history | Operational |
| `job_action_issue_card` | Card issuance (exp_month, exp_year) | **PCI SAD** |
| `job_action_memo` | Free-text action memo | Review for PII |
| `job_action_memo_ex` | Extended memo | Review for PII |
| `job_action_memo_ex_group` | Memo group | No |
| `job_action_memo_ex_row` | Memo row | No |
| `job_action_memo_secure` | Secure memo (vault token ref) | **HIGH** |
| `job_action_register_user` | Cardholder PII for registration | **CRITICAL PII** |
| `job_action_register_user_extended_address` | Extended address | **HIGH PII** |
| `job_action_register_user_extended_phone` | Extended phone | **HIGH PII / TCPA** |
| `job_action_send_notification` | Notification dispatch trigger | No |
| `job_action_set_inventory_location_attributes` | Inventory config | No |
| `job_action_set_location_code` | Location code assignment | No |
| `job_action_spin_payment` | SPIN payment action | Financial |
| `job_action_spin_payment_cert` | SPIN with cert | Financial |
| `job_action_spin_payment_cert_memo` | SPIN cert memo | Financial |
| `job_action_status_record_status` | Status reference | No |
| `job_action_stop_payment` | Stop payment instruction | Financial |
| `job_action_update_user` | User update action | **MEDIUM PII** |
| `job_action_update_web_user` | Web user update | No |
| `job_action_withdraw` | Withdrawal action | Financial |
| `job_batch` | Batch processing records | No |
| `job_batch_action_summary` | Batch action summary | No |
| `job_batch_fees` | Batch fee records | Financial |
| `job_batch_reprocess_queue` | Reprocessing queue | No |
| `job_exception_control` | Exception handling config | No |
| `job_fdr_batch_creation_report` | FDR batch report | Reporting |
| `job_file` | Client instruction files | No |
| `job_file_ingest` | File ingestion state | No |
| `job_file_status_history` | File status transitions | No |
| `job_loader_control` | Loader control config | No |
| `job_member_recent_commited_transfers` | Recent transfer cache | Financial |
| `job_order_sync_event` | Order sync events | No |
| `job_payment` | Payment records | Financial |
| `job_process` | Process definitions | No |
| `job_program_email_failed_card_creation_control` | Failed card email control | No |
| `job_record` | Per-record processing state | No |
| `job_record_action` | Record-to-action mapping | No |
| `job_record_change_facility` | Facility change records | No |
| `job_record_journal` | Record processing journal | No |
| `job_record_status` | Status reference | No |
| `job_record_validation_result` | Validation results | No |
| `job_reply_control` | Reply file control | No |
| `job_request` | Job requests | No |
| `partner` | Partner (client) reference | No |
| `partner_affiliate` | Affiliate partner records | No |
| `profile_*` (10 tables) | Configuration profiles | No |
| `program_map` | Program-to-partner mapping | No |
| `program_map_history` | Program map history | No |
| `program_promotion_spin` | SPIN promotion config | Financial |
| `program_promotion_spin_distribution` | SPIN distribution | Financial |
| `QRTZ_*` (12 tables) | Quartz scheduler metadata | No |
| `schedule` | Job schedule definitions | No |
| `schedule_day` | Schedule day rules | No |
| `sch_job_*` | Scheduler job tracking | No |
| `sftp_process_status` | SFTP processing status | No |
| `simplesolve_versionvalidation` | Version validation records | No |
| `spin_control` | SPIN payment control | Financial |
| `work_instance` | Work unit execution state | No |
| `work_instance_context` | Work context data | No |
| `work_instance_log` | Work execution log | No |
| `work_process` | Process state machine | No |
| `work_process_state_machine` | State transitions | No |
| `work_process_step` | Process steps | No |
| `zzz_*` (7 tables) | Deprecated legacy tables | **Remove** |

## 4. Remediation Priority Matrix

| Priority | Item | Owner | Effort |
|----------|------|-------|--------|
| P0 (Emergency) | Assess `instant_issue_card.card_number` for PAN content | Security/DBA | 1 hour |
| P0 (Emergency) | Engage PCI QSA if PANs confirmed | Security/Compliance | Immediate |
| P1 (This sprint) | Tokenise/truncate `card_number` and `parent_dda` | Dev/Security | 2 weeks |
| P1 (This sprint) | Remove `exp_month/exp_year` post-authorization | Dev | 1 week |
| P2 (Q3) | Upgrade Quartz 1.x to Quartz 2.x or Spring Scheduler | Java Dev | 4–6 weeks |
| P2 (Q3) | Upgrade SQL compat level to 150 | DBA | 2 weeks |
| P2 (Q3) | Add DB-level OFAC screening enforcement | Dev/DBA | 1 week |
| P3 (Next cycle) | Drop `zzz_` and `CDC_*_bk` tables | DBA | 1 day |
| P3 (Next cycle) | Implement DeltaSql migration folder | Dev/DevOps | 1 week |
| P3 (Next cycle) | Add CI/CD pipeline | DevOps | 2 weeks |
| P4 (Roadmap) | Replace `IMAGE` with `VARBINARY(MAX)` | Dev | 2 weeks |

## 5. Summary Risk Score

| Category | Score (1–5) |
|----------|------------|
| PCI scope risk | 5 — Potential PAN in card_number |
| Data sensitivity | 5 — PII, payment tokens, ACH refs |
| Security posture | 2 — No TDE, potential PAN plaintext |
| Operational maturity | 3 — Functional but Quartz EOL, no CI/CD |
| Compliance readiness | 2 — PCI, NACHA, TCPA, OFAC all at risk |

**Overall Risk: CRITICAL** — The `instant_issue_card.card_number` field must be assessed and remediated before the next PCI DSS assessment period.
