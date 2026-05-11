# DS_DB_notificationsvc — Data Architect Report

## 1. Data Store Overview

| Attribute | Value |
|-----------|-------|
| Platform | Microsoft SQL Server (SQL Server 2012 DSP — `Sql110DatabaseSchemaProvider`) |
| Database name | `NotificationSvc` |
| Project type | SSDT SQL Database Project (`NotificationSvc.sqlproj`) |
| Schema | `dbo` (single schema) |
| Table count | ~75 tables (including DeltaSql additions) |
| Stored procedure count | 41 |
| Views | 1 (`notification_message_debug_vw`) |
| Functions | 2 (`getTemplateName`, `Split`) |
| Migration method | DeltaSql (folder-based: `DeltaSql/<date>/<ticket>/`) |

---

## 2. Schema and Table Inventory

### 2.1 Core Notification Event Tables

| Table | Key Columns | Purpose |
|-------|-------------|---------|
| `notification_event` | `message_id BIGINT IDENTITY`, `event_name VARCHAR(125)`, `agent_name VARCHAR(32)`, `program_id VARCHAR(16)`, `promo_id INT`, `caller_member UNIQUEIDENTIFIER`, `priority INT`, `status_id INT`, `date DATETIME` | Central event record; correlates upstream trigger to notification lifecycle |
| `notification_event_name` | `event_name VARCHAR(125)` | Lookup: valid event type codes |
| `notification_event_status` | `status_id INT` | Lookup: event processing status |
| `notification_event_data` | (FK to event) | Payload/merge data for event |
| `notification_event_archive` | mirror of `notification_event` | Archival of processed events |
| `notification_exception` | (FK to event) | Stores exceptions/failures during processing |

### 2.2 Queue and Delivery Tables

| Table | Key Columns | Sensitivity |
|-------|-------------|-------------|
| `notification_queue` | `notification_id BIGINT IDENTITY`, `message_subscriber_id BIGINT`, `template_id INT`, `to_address VARCHAR(100)`, `from_address VARCHAR(100)`, `friendly_to_address VARCHAR(100)`, `status_id INT`, `channel_id INT`, `jms_queue_msg_id NVARCHAR(256)` | **HIGH PII** — `to_address` and `friendly_to_address` contain recipient email |
| `notification_queue_cc` | CC recipient addresses | **HIGH PII** |
| `notification_message_subscriber` | links events to subscribers | Internal |
| `notification_msg_sub_schedule` | scheduled delivery records | Operational |
| `notification_msg_sub_status` | delivery status per subscriber | Operational |
| `notification_msg_sub_schedule_status` | schedule status tracking | Operational |

### 2.3 Template and Configuration Tables

| Table | Key Columns | Notes |
|-------|-------------|-------|
| `notification_template` | `template_id INT IDENTITY`, `template_name VARCHAR(125)`, `template_value NVARCHAR(MAX)`, `template_subject NVARCHAR(256)`, `template_alt_value NVARCHAR(MAX)`, `locale_id INT`, `application_id INT`, `url_encoded BIT` | Email template HTML/text bodies; `template_value` may contain PII via merge tags |
| `notification_template_field` | merge field definitions | Defines tokens like `{{firstName}}` |
| `notification_config_program_channel` | per-program channel config | Operational |
| `notification_config_program_enable` | per-program enable/disable | Operational |
| `notification_config_program_locale` | per-program locale (language) | Operational |
| `notification_config_program_subscriber` | subscriber assignment per program | Operational |
| `notification_config_program_subscriber_schedule` | delivery schedule per subscriber | Operational |
| `notification_config_program_template_map` | event-to-template mapping | Core routing config |
| `notification_config_user_channel` | per-user channel config | Operational |
| `notification_config_user_enable` | per-user enable/disable (opt-out linkage) | PII-adjacent |
| `notification_config_user_locale` | per-user locale | PII-adjacent |
| `notification_config_user_subscriber` | per-user subscriber | PII-adjacent |
| `notification_status` | delivery status lookup | Lookup table |
| `notification_channel` | channel lookup (EMAIL, SMS, etc.) | Lookup table |
| `notification_config_status` | config status lookup | Lookup table |

### 2.4 SMS Tables

| Table | Key Columns | Notes |
|-------|-------------|-------|
| `notification_sms_template` | SMS message templates | |
| `notification_sms_template_field` | SMS merge field definitions | |
| `notification_sms_subscriber` | SMS subscriber registry | |
| `notification_sms_event_name` | SMS event type lookup | |
| `notification_sms_event_subscriber` | event-subscriber mapping | |
| `notification_sms_event_template` | event-template mapping | |
| `notification_sms_schedule` | SMS delivery schedule | |
| `notification_sms_config_program_template_map` | per-program SMS template mapping | |
| `notification_config_sms_program_enable` | per-program SMS enable | |
| `notification_config_sms_program_subscriber` | SMS subscriber per program | |
| `notification_config_sms_program_subscriber_schedule` | SMS schedule per subscriber | |
| `notification_config_sms_program_template_map` | SMS template mapping | |
| `program_short_code_mapping` | `short_code`, `program_id` | Maps SMS short codes to programs |

### 2.5 Mailgun (Email Delivery Tracking) Tables

| Table | Key Columns | Sensitivity |
|-------|-------------|-------------|
| `mailgun_events_queue` | `id BIGINT IDENTITY`, `notification_id BIGINT`, `message_subscriber_id BIGINT`, `program_id NVARCHAR(8)`, `message_id NVARCHAR(200)`, `mailgun_event_type NVARCHAR(30)`, `mailgun_event_reason NVARCHAR(30)`, `mailgun_message_response NVARCHAR(500)`, `email_subject NVARCHAR(200)`, `email_sent DATETIME` | Moderate — event metadata, no email body stored here |
| `mailgun_event_types` | `event_type NVARCHAR(30)` | Lookup (delivered, opened, bounced, failed, etc.) |
| `mailgun_jobrun_tracker` | job run timestamps | Operational |
| `email_details` | `from_address`, `to_address`, `bounceback_to_address`, `subject`, `body_content`, `login_email_address` | **HIGH PII** — stores full email address and body content for failed/bounced messages |
| `email_reader_job_status` | job processing status | Operational |

### 2.6 Consent and TCPA Tables (DeltaSql 2026-04-26)

| Table | Key Columns | Sensitivity |
|-------|-------------|-------------|
| `ch_consent` | `id BIGINT IDENTITY`, `channel VARCHAR(20)`, `identifier VARCHAR(255)`, `sender VARCHAR(50)`, `source VARCHAR(100)`, `is_active TINYINT`, `created_at DATETIME2(3)`, `updated_at DATETIME2(3)`, `last_consent_requested_at DATETIME2(3)` | **HIGH** — `identifier` is phone/email; `is_active` is consent state |
| `ch_consent_history` | `consent_id BIGINT FK`, `channel`, `identifier`, `sender`, `event_type`, `is_active BIT`, `provider`, `provider_message_id`, `provider_message NVARCHAR(MAX)` | **HIGH** — full consent audit trail; `identifier` is PII |
| `ch_quiet_hours` | `recipient_id INT`, `program_id VARCHAR(50)`, `start_time TIME`, `end_time TIME`, `timezone VARCHAR(100)`, `priority INT` | Operational (TCPA enforcement) |
| `ch_recipient` | referenced by `ch_quiet_hours` FK | PII — recipient identity |
| `sms_opt_out` | `short_code`, `recipient_phone_number`, `occurred_at`, `provider_message` | **HIGH** — phone number PII; TCPA record |

### 2.7 Batch Tables

| Table | Purpose |
|-------|---------|
| `notification_batch` | Batch notification job records |
| `notification_batch_status` | Status lookup for batch jobs |
| `notification_fixed_message` | Pre-composed fixed message bodies |
| `notification_merge_data` | Merge data payloads |
| `notification_schedule` | Notification schedule definitions |

### 2.8 Quartz Scheduler Tables

| Table | Purpose |
|-------|---------|
| `QRTZ_JOB_DETAILS` | Quartz job definitions |
| `QRTZ_TRIGGERS` | Trigger records |
| `QRTZ_CRON_TRIGGERS` | Cron schedule triggers |
| `QRTZ_SIMPLE_TRIGGERS` | Simple schedule triggers |
| `QRTZ_FIRED_TRIGGERS` | Active/executing trigger records |
| `QRTZ_SCHEDULER_STATE` | Cluster node states |
| `QRTZ_LOCKS` | Distributed locks |
| `QRTZ_PAUSED_TRIGGER_GRPS` | Paused trigger groups |
| `QRTZ_BLOB_TRIGGERS` | Blob-serialised triggers |
| `QRTZ_CALENDARS` | Calendar exclusions |
| `QRTZ_JOB_LISTENERS` | Job event listeners (legacy) |
| `QRTZ_TRIGGER_LISTENERS` | Trigger event listeners (legacy) |

### 2.9 Cross-Database Reference Tables

| Table | Source | Purpose |
|-------|--------|---------|
| `CbaseApp_bridge_promotionlevel_configuration` | CbaseApp | Promotion-level config bridged from core payments DB |
| `CbaseApp_email_templates` | CbaseApp | Email template copies from CbaseApp |
| `EcountCore_app_profile_event` | EcountCore | Profile event definitions from EcountCore |
| `EcountCore_app_profile_event_code` | EcountCore | Profile event code lookup |
| `EcountCore_fdr_profile_scope` | EcountCore | FDR (First Data Resources) profile scope |
| `JobSvc_profile_symbols` | JobSvc | Job service symbol definitions |

### 2.10 Temporary/Migration Tables

| Table | Notes |
|-------|-------|
| `temp_notification_config_program_template_map` | Temporary — migration staging |
| `temp_notification_config_program_template_map1` | Temporary — additional migration variant |

---

## 3. Sensitive Data Classification

| Data Element | Column/Table | Classification | Regulation |
|---|---|---|---|
| Recipient email address | `notification_queue.to_address`, `email_details.to_address` | **PII — HIGH** | GDPR, CCPA, CAN-SPAM |
| Friendly name of recipient | `notification_queue.friendly_to_address` | **PII — MEDIUM** | GDPR, CCPA |
| Sender/from address | `notification_queue.from_address`, `email_details.from_address` | PII — LOW (service account) | CAN-SPAM |
| SMS phone number | `sms_opt_out.recipient_phone_number`, `ch_consent.identifier` (when channel=SMS) | **PII — HIGH** | TCPA, GDPR, CCPA |
| Email in consent | `ch_consent.identifier` (when channel=EMAIL) | **PII — HIGH** | GDPR, CCPA |
| Consent history raw | `ch_consent_history.provider_message NVARCHAR(MAX)` | **PII — HIGH** | TCPA audit |
| Email body content | `email_details.body_content` | **PII — HIGH** (may contain cardholder data) | GDPR, PCI DSS |
| Notification merge data | `notification_event_data`, `notification_merge_data` | **PII — VARIABLE** (merge tokens may resolve to PAN, name, balance) | PCI DSS, GDPR |
| Template content | `notification_template.template_value NVARCHAR(MAX)` | PII — VARIABLE (HTML with merge fields) | GDPR |
| Mailgun message ID | `mailgun_events_queue.message_id` | Operational | None |

---

## 4. Encryption and Data-at-Rest Security

- No column-level encryption (`ENCRYPTBYKEY`, `COLUMN_MASTER_KEY`, Always Encrypted) is defined in any table DDL in this repository.
- `to_address` (email) and `recipient_phone_number` (SMS) are stored as plaintext `VARCHAR`/`NVARCHAR`.
- `notification_template.template_value NVARCHAR(MAX)` stores full HTML email templates in plaintext.
- `ch_consent_history.provider_message NVARCHAR(MAX)` stores raw SMS provider messages in plaintext.
- Data-at-rest protection relies entirely on SQL Server Transparent Data Encryption (TDE) at the OS/storage layer (not visible in schema artefacts; must be confirmed in SQL Server instance configuration).
- **PCI DSS Req 3.5 gap**: No SQL-level encryption of PII columns. TDE alone does not satisfy column-level protection recommendations.

---

## 5. Data Flow

```
Upstream (ordersvc / jobsvc / ecountcore)
    |
    v
notification_event  [program_id, event_name, promo_id]
    |
    +-- notification_config_program_template_map  [routing]
    |
    v
notification_message_subscriber
    |
    v
notification_queue  [to_address, from_address, template_id, channel_id]
    |
    +-- EMAIL channel --> Mailgun API
    |       |
    |       v
    |   mailgun_events_queue  [webhook callbacks: delivered/bounced/failed]
    |       |
    |       v
    |   email_details  [failed messages only — body_content stored]
    |
    +-- SMS channel --> SMS Provider
            |
            v
        sms_opt_out / ch_consent  [opt-out events]
        ch_consent_history  [audit trail]
        ch_quiet_hours  [delivery suppression]
```

---

## 6. Data Quality and Retention

- **No explicit retention policy** found in schema DDL. `notification_event_archive` exists as an archival table but no automated purge jobs or retention triggers are defined in this repository.
- `email_details` stores full email content for bounced/failed messages with no apparent TTL — this is a PII retention risk.
- `notification_event_archive` (`insert_notification_event_archive.sql`) is a migration/insertion script, not a triggered purge.
- `mailgun_events_queue` accumulates all webhook events without a defined purge window.
- **Data quality risk**: `notification_queue.to_address` and `from_address` are `VARCHAR(100)` without a `NOT NULL` constraint — null delivery addresses are possible.
- Duplicate-prevention index `UX_ch_consent_unique` on `(channel, identifier, sender)` provides consent uniqueness guarantee.

---

## 7. Access Control (Database Security Layer)

From `Security/RoleMemberships.sql`:

| Principal | Role | Access Level |
|-----------|------|-------------|
| `notificationsvc` (service account) | `db_datareader` | Read all tables |
| `notificationsvc_Execute` grant | Execute SPs | Writes occur via stored procedures |
| `notificationsvc_Delete/Update/Select/Insert` grants | Granular DML | Fine-grained per-operation |
| `b2c` | `db_datareader` | Read access (B2C application) |
| `report`, `report_full` | `db_datareader` | Reporting access |
| `NAM\PROD`, `NAM\UAT` | `db_datareader` | Windows AD groups |
| `emer_*` users | `db_datareader` + `db_datawriter` | Emergency access logins |
| `NAM\ISA_SQL_SECADMIN`, `ifs_infosec`, `ifs_gidadb` | `db_accessadmin` + `db_securityadmin` + `db_denydatawriter` | Security administration with write denial |
| `FortiDBRptRole`, `gers_role` | Custom roles | Monitoring/reporting |

**Finding**: Emergency access accounts (`emer_sk14163`, `emer_rb27292`, `emer_sp10000`, `emer_sr14161`) have both `db_datareader` AND `db_datawriter` roles — they can read and write all data. These accounts are associated with individual personnel. Under PCI DSS Req 8.2.2, shared/emergency accounts require compensating controls and must not be used for routine access.

**Finding**: Login `notificationsvc` has a hardcoded password stored in `Security/notificationsvc.sql` committed to the git repository. This is a PCI DSS Req 8.3.1 violation — passwords/credentials must not be stored in clear text in source code or scripts.

---

## 8. Compliance Gaps

| Gap | Regulation | Severity |
|-----|-----------|----------|
| Plaintext PII storage (`to_address`, `identifier`, phone numbers) | PCI DSS Req 3.5, GDPR Art 32 | HIGH |
| Hardcoded login password in `Security/notificationsvc.sql` | PCI DSS Req 8.3.1, GLBA | CRITICAL |
| No defined data retention/purge policy for `email_details`, `mailgun_events_queue` | GDPR Art 5(e) (storage limitation) | HIGH |
| Emergency accounts with `db_datawriter` (personnel-linked) | PCI DSS Req 8.2.2, 8.6 | HIGH |
| No column-level encryption on phone/email fields | PCI DSS Req 3.5, GDPR Art 32 | MEDIUM |
| `temp_notification_config_*` tables committed as permanent schema objects | Data governance | LOW |
| `QRTZ_JOB_LISTENERS` / `QRTZ_TRIGGER_LISTENERS` — deprecated Quartz 1.x tables | Technical debt | LOW |
