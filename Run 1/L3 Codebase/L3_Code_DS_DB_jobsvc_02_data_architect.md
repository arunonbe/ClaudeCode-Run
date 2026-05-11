# DS_DB_jobsvc — Data Architect Report

## 1. Database Object Inventory

| Object Type | Count | Location |
|-------------|-------|----------|
| Tables | ~155 | `dbo/Tables/` |
| Views | 48 | `dbo/Views/` |
| Stored Procedures | 287 | `dbo/Stored Procedures/` |
| Scalar/Table Functions | 30 | `dbo/Functions/` |
| Defaults | 11 | `dbo/Defaults/` |
| Security principals | Present | `Security/` |
| Storage filegroups | Present | `Storage/` |

## 2. Table Catalogue with Sensitivity Flags

### 2.1 File Processing Tables

| Table | Purpose | Sensitive |
|-------|---------|-----------|
| `job_file` | Tracks client instruction files received | No |
| `job_file_status_history` | File processing state transitions | No |
| `job_file_ingest` | Raw file ingestion records | No |
| `file_types` | Reference: file format types | No |
| `Job_File_Content_Validation_Errors` | File validation error log | No |

### 2.2 Job Record Tables

| Table | Purpose | Sensitive |
|-------|---------|-----------|
| `job_record` | Root record for each file row | No |
| `job_record_action` | Maps records to action sets | No |
| `job_record_status` | Reference: record status codes | No |
| `job_record_journal` | Record processing journal | No |
| `job_record_validation_result` | Validation outcome per record | No |
| `job_record_change_facility` | Facility change log | No |
| `Job_Request_Content_Validation_Errors` | Request validation errors | No |
| `Job_Batch_Content_Validation_Errors` | Batch validation errors | No |
| `Job_Action_Content_Validation_Errors` | Action validation errors | No |

### 2.3 Action Tables (PII-Intensive)

| Table | Columns of Note | PII Flag |
|-------|----------------|----------|
| `job_action` | `action_id`, `action_code`, `job_id`, `status_id` | No |
| `job_action_register_user` | `first_name`, `last_name`, `home_email`, `home_phone`, `business_phone`, `mobile_phone`, `address1`, `city`, `state`, `postal` | **CRITICAL PII** |
| `job_action_register_user_extended_phone` | `phone_country_code`, `phone_area_code`, `phone_number`, `phone_type` | **HIGH PII / TCPA** |
| `job_action_register_user_extended_address` | Address fields | **MEDIUM PII** |
| `job_action_issue_card` | `exp_month`, `exp_year`, `card_type`, `device_id` | **PCI SAD (expiry)** |
| `job_action_add_funds` | `amount`, `claim_code`, `echeck_id`, `direct_claim_flag` | **HIGH — payment token** |
| `job_action_add_funds_cert` | Add funds with certificate | Financial |
| `job_action_create_cert` | Certificate creation action | Financial |
| `job_action_stop_payment` | Stop payment instructions | Financial |
| `job_action_withdraw` | Withdrawal actions | Financial |
| `job_action_spin_payment` | SPIN payment actions | Financial |
| `job_action_spin_payment_cert` | SPIN with certificate | Financial |
| `job_action_send_notification` | Notification triggers | No |
| `job_action_create_email_notification` | Email notification setup | No |
| `job_action_create_web_user` | Web portal user creation | No |
| `job_action_update_user` | User profile updates | **MEDIUM PII** |
| `job_action_update_web_user` | Web user updates | No |
| `job_action_memo` | Free-text action memo | **Review needed** |
| `job_action_memo_ex` | Extended memo | **Review needed** |
| `job_action_memo_secure` | Secure memo with vault reference (`field_secure_ref`) | **HIGH — vault token** |
| `job_action_memo_ex_group` | Memo group | No |
| `job_action_memo_ex_row` | Memo row | No |
| `job_action_set_location_code` | Inventory location assignment | No |
| `job_action_set_inventory_location_attributes` | Inventory attribute setting | No |
| `job_action_status_record_status` | Status cross-reference | No |
| `job_action_history` | **Action execution history** | Operational |
| `job_action_history_Archive` | Archived action history | Operational |

### 2.4 CRITICAL PII Table — `job_action_register_user`
```sql
-- File: dbo/Tables/job_action_register_user.sql
CREATE TABLE [dbo].[job_action_register_user] (
    [action_id]                    INT              NOT NULL,
    [first_name]                   VARCHAR (25)     NULL,   -- PII
    [middle_name]                  VARCHAR (25)     NULL,   -- PII
    [last_name]                    VARCHAR (25)     NULL,   -- PII
    [home_email]                   VARCHAR (50)     NULL,   -- PII / TCPA
    [address1]                     VARCHAR (50)     NULL,   -- PII
    [city]                         VARCHAR (25)     NULL,   -- PII
    [state]                        VARCHAR (2)      NULL,   -- PII
    [postal]                       VARCHAR (10)     NULL,   -- PII
    [country]                      VARCHAR (2)      NULL,   -- PII
    [home_phone]                   VARCHAR (16)     NULL,   -- PII / TCPA
    [business_phone]               VARCHAR (16)     NULL,   -- PII / TCPA
    [mobile_phone]                 VARCHAR (16)     NULL,   -- PII / TCPA
    [ecount_id]                    CHAR (16)        NULL,   -- Internal ID
    [online_registration_required] BIT              NOT NULL,
    [plastic_only]                 BIT              NOT NULL,
    [recipient_screening_status]   VARCHAR (40)     NULL    -- AML screening result
)
```

### 2.5 CRITICAL PCI TABLE — `instant_issue_card`
```sql
-- File: dbo/Tables/instant_issue_card.sql
CREATE TABLE [dbo].[instant_issue_card] (
    [instant_issue_card_id]    INT           IDENTITY NOT NULL,
    [order_id]                 INT           NOT NULL,
    [partner_user_id]          VARCHAR (50)  NOT NULL,
    [card_number]              CHAR (16)     NULL,   -- CRITICAL: Potential PAN
    [parent_dda]               CHAR (16)     NULL,   -- CRITICAL: Potential DDA
    [tracking_number]          VARCHAR (32)  NULL,   -- Physical card shipping
    [used]                     BIT           NOT NULL,
    [status]                   INT           NULL,
    ...
)
```

**PCI DSS Assessment**: `card_number` CHAR(16) almost certainly contains full PANs (Primary Account Numbers). If confirmed, this is a **PCI DSS Requirement 3 violation** — full PAN must not be stored without strong cryptography (tokenisation, truncation, or encryption). This table must be reviewed in the context of a PCI DSS assessment.

`parent_dda` CHAR(16) may contain a full bank account (DDA) number. If so, this is a NACHA/Reg E compliance concern for the financial data protection.

### 2.6 ACH/Payment Tables

| Table | Purpose | Regulatory |
|-------|---------|-----------|
| `ach_transfer_detail` | ACH transfer lifecycle tracking | **NACHA / Reg E** |
| `ach_event_status` | ACH event status reference | No |
| `ach_event_types` | ACH event type reference | No |
| `job_action_add_funds.echeck_id` | eCheck/ACH payment reference | **NACHA** |

### 2.7 Quartz Scheduler Tables (QRTZ_*)

| Table | Purpose |
|-------|---------|
| `QRTZ_JOB_DETAILS` | Job class names, descriptions, data blobs |
| `QRTZ_TRIGGERS` | Trigger definitions |
| `QRTZ_CRON_TRIGGERS` | Cron expression triggers |
| `QRTZ_SIMPLE_TRIGGERS` | Simple interval triggers |
| `QRTZ_FIRED_TRIGGERS` | Currently-firing and recently-fired triggers |
| `QRTZ_SCHEDULER_STATE` | Cluster node state |
| `QRTZ_LOCKS` | Optimistic locking for cluster coordination |
| `QRTZ_PAUSED_TRIGGER_GRPS` | Paused trigger group tracking |
| `QRTZ_CALENDARS` | Calendar exclusions |
| `QRTZ_JOB_LISTENERS` | Job listener registrations |
| `QRTZ_TRIGGER_LISTENERS` | Trigger listener registrations |
| `QRTZ_BLOB_TRIGGERS` | Binary blob trigger data |

**Note**: `QRTZ_JOB_DETAILS.JOB_DATA` is typed as `IMAGE` — a deprecated SQL Server type. This stores serialised Java objects (Quartz job context). If job data inadvertently contains PII or credentials, this column is opaque to standard SQL queries.

### 2.8 Instant Issue Inventory Tables

| Table | Purpose | Sensitive |
|-------|---------|-----------|
| `instant_issue_card` | Card inventory with card_number | **CRITICAL PCI** |
| `instant_issue_order` | Card order records | Operational |
| `instant_issue_current_inventory_details` | Current inventory levels | Operational |
| `instant_issue_core_sync_info` | Sync state with EcountCore | Operational |
| `instant_issue_profile_facility` | Facility configuration | No |
| `instant_issue_notification` | Notification triggers for inventory | No |
| `instant_issue_inv_email_queue` | Email notification queue | No |
| `instant_issue_inv_email_log` | Email delivery log | No |
| `instant_issue_used_card_log` | Card usage log | **Operational / PCI-adjacent** |
| `instant_issue_inv_card_expiry_notification_log` | Expiry notification log | No |

### 2.9 Banker / Fund Management Tables

| Table | Purpose | Sensitive |
|-------|---------|-----------|
| `banker_job` | Banker-initiated job records | No |
| `banker_promotion` | Promotion-level fund configurations | Financial |
| `banker_preset_funds_config` | Preset fund loading configurations | Financial |
| `banker_reserved_source` | Reserved fund sources | Financial |
| `banker_reserved_source_log` | Change log for reserved sources | Financial |
| `banker_payment_method` | Payment method reference | No |
| `banker_email` | Banker email notifications | No |

### 2.10 Work Orchestration Tables

| Table | Purpose |
|-------|---------|
| `work_instance` | Individual work unit execution records |
| `work_instance_context` | Context data for work execution |
| `work_instance_log` | Execution log per work unit |
| `work_process` | Process definition (state machine root) |
| `work_process_state_machine` | State transition rules |
| `work_process_step` | Steps within each process |

## 3. Stored Procedure Catalogue (287 total — key SPs)

| Prefix | Count (approx) | Purpose |
|--------|---------------|---------|
| `ach_transfer_*` | 3 | ACH transfer create/extract/initiate |
| `autofile_*` | 10 | Autofile job management |
| `banker_*` | 20 | Banker fund operations |
| `blackout_*` | 10 | Blackout period management |
| `instant_issue_*` | ~30 | Card inventory management |
| `job_*` | ~150 | Core job processing (file, record, action) |
| `schedule_*` | ~15 | Job scheduling |
| `spin_*` | ~10 | SPIN payment processing |
| `work_*` | ~20 | Work orchestration |

## 4. Functions (30 total)

| Function | Purpose |
|----------|---------|
| `convert_any_base_to_int` | Base conversion utility |
| `convert_int_to_any_base` | Base conversion utility |
| `convert_to_program_id` | Program ID format conversion |
| Others | Utility functions for job processing |

## 5. Default Constraints (11)

| Default | Purpose |
|---------|---------|
| `DF_BLANK` | Empty string default |
| `DF_init_action_status` | Initial action status code |
| `DF_init_job_status` | Initial job status code |
| `DF_init_process_status` | Initial process status code |
| `DF_init_request_status` | Initial request status code |
| `DF_init_stat_action` | Initial static action code |
| `DF_init_syscode` | Initial system code |
| `DF_NEWID` | NEWID() GUID default |
| `DF_new_emember_id` | New eMember GUID default |
| `DF_now` | GETDATE() timestamp default |
| `DF_spid` | Server process ID default |
| `DF_ZERO` | Integer 0 default |

## 6. PCI DSS CDE Scope Assessment

**Assessment: POTENTIALLY IN CDE SCOPE**

**Critical Finding**: `instant_issue_card.card_number` CHAR(16) may contain Primary Account Numbers (PANs). If confirmed:
- This table is **in PCI DSS CDE scope**
- The entire `jobsvc` database becomes CDE-adjacent, requiring network segmentation, access controls, and monitoring per PCI DSS requirements
- PCI DSS Requirement 3.3.1: Full PAN must not be stored unless protected with strong cryptography
- PCI DSS Requirement 3.5.1: PAN must be rendered unreadable via approved methods

**Immediate Action Required**: Query `instant_issue_card.card_number` on the production database and determine whether values are:
1. Full 16-digit PANs (PCI violation — must tokenise/truncate immediately)
2. Masked/truncated values (compliant)
3. Tokenised values from a vault (compliant if vault is properly scoped)

`job_action_issue_card.exp_month/exp_year`: Card expiry months/years. If these are retained post-authorization, they constitute SAD — **PCI DSS Requirement 3.3.2 prohibits SAD storage after authorization is complete**.

## 7. Indexes of Note

- `IX_reporting_register_user_ecount_id` on `job_action_register_user` — supports reporting queries on cardholder registration by ecount_id
- `RS_job_action_add_funds_direct_claim_Flag` — filtered covering index for direct claim lookup
- `NC_job_file_status` — filtered partial index on `job_status < 250` for active file monitoring
- `RS_job_file_received_dt` — date-range reporting index on `job_file`
