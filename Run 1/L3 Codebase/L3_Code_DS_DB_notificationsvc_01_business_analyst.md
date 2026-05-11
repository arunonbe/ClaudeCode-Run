# DS_DB_notificationsvc — Business Analyst Report

## 1. Repository Identity

| Attribute | Value |
|-----------|-------|
| Repo name | DS_DB_notificationsvc |
| Internal alias | Notification Service Database |
| Project file | `NotificationSvc.sqlproj` |
| Solution file | `NotificationSvc.sln` |
| Database name | `NotificationSvc` |
| Has DeltaSql migrations | YES — `DeltaSql/2026-04-26/BZGD-0000/` |
| Stored procedures | 41 |
| Tables | ~75 |
| Views | 1 |

## 2. Business Purpose

`DS_DB_notificationsvc` is the **persistence layer for Onbe's multi-channel notification service**. It stores all configuration, templating, queuing, delivery tracking, opt-in/opt-out records, and scheduling data for both **email** (via Mailgun) and **SMS** (via an SMS gateway with short code management) notifications sent to Onbe cardholders.

The notification service is critical to Onbe's business because it:
1. **Delivers cardholder communications**: Card activation confirmations, balance alerts, transaction notifications, promotional messages, and security alerts.
2. **Supports TCPA compliance**: Stores SMS opt-out records and consent state for all recipients.
3. **Enables client configuration**: Clients configure notification templates, event mappings, and channel enablement per program/promotion.
4. **Provides operational visibility**: Tracks delivery failures via Mailgun webhook events, enabling bounce/complaint management.
5. **Manages Quartz scheduling**: Contains `QRTZ_*` tables used by the notification scheduler.

## 3. Core Business Processes Supported

### 3.1 Notification Event Processing
The central workflow:
1. An upstream service (ordersvc, jobsvc, ecountcore) triggers a `notification_event`.
2. The event is matched to a `notification_template` via `notification_config_program_template_map`.
3. A `notification_message_subscriber` record is created (linking event to subscriber/recipient).
4. The message is queued in `notification_queue` for delivery.
5. The notification engine dispatches the message (email via Mailgun, SMS via provider).
6. Delivery status is tracked in `notification_queue.status_id` and `notification_event_subscriber_log`.

### 3.2 Email Notification Management
- `notification_queue`: Core outbound queue with `to_address`, `from_address` email fields.
- `notification_template`: Email template bodies and subjects (`template_value` NVARCHAR(MAX)).
- `mailgun_events_queue`: Tracks Mailgun webhook delivery events (opens, bounces, failures).
- `mailgun_jobrun_tracker`: Tracks Mailgun event polling jobs.
- `email_details`: Stores email content for failed/bounced messages.
- `email_reader_job_status`: Status tracking for email reader jobs.

### 3.3 SMS Notification Management
- `notification_sms_template`: SMS message templates.
- `notification_sms_template_field`: Template merge field definitions.
- `notification_sms_subscriber`: SMS subscriber registry.
- `notification_sms_event_name`, `notification_sms_event_subscriber`, `notification_sms_event_template`: SMS event-to-template mapping.
- `program_short_code_mapping`: Maps programs to SMS short codes.

### 3.4 Opt-In / Opt-Out Management (TCPA)
- `sms_opt_out` (DeltaSql 2026-04-26): Stores SMS opt-out events — **short_code + recipient_phone_number + occurred_at + provider_message**.
- `ch_consent` (DeltaSql 2026-04-26): New unified consent table — **channel + identifier + sender + is_active + timestamps**.
- `ch_consent_history` (DeltaSql 2026-04-26): Full audit trail of consent state changes.
- `revert_sms_opt_out.sql` / `Sms_opt_out_creation.sql`: Migration and revert scripts for opt-out tables.

The April 2026 DeltaSql migration (`BZGD-0000`) introduced a significant **consent management overhaul**:
- New `ch_consent` table consolidating multi-channel consent state
- Migration from legacy `sms_opt_out` to `ch_consent` via MERGE statement
- New `ch_quiet_hours` table for TCPA quiet hour enforcement (20:00–10:00 EST default system setting)
- New `ch_recipient` table for recipient-level consent management

### 3.5 Quiet Hours Enforcement (TCPA)
`ch_quiet_hours` (DeltaSql 2026-04-26):
- Stores time windows during which SMS/notification delivery is suppressed
- System-level default: `start_time=20:00`, `end_time=10:00`, `timezone=America/New_York` (TCPA FCC quiet hours standard)
- Program-level and recipient-level overrides supported via `program_id` and `recipient_id` columns
- Prioritised by `priority` integer column

### 3.6 Batch Notification Processing
- `notification_batch`, `notification_batch_status`: Track batch notification jobs.
- `notification_select_batch_notification_queue` SP: Selects pending batch notifications.
- `notification_update_batch_notification_queue` SP: Updates batch processing status.

### 3.7 Template and Configuration Management
- `notification_template`: Email template bodies/subjects (HTML/text).
- `notification_template_field`: Merge field definitions for templates.
- `notification_config_program_channel`: Per-program channel configuration.
- `notification_config_program_enable`: Per-program notification enable/disable.
- `notification_config_program_locale`: Locale (language) configuration per program.
- `notification_config_program_subscriber`: Subscriber assignment per program.
- `notification_config_program_subscriber_schedule`: Schedule configuration per subscriber.
- `notification_config_program_template_map`: Event-to-template mapping per program.

### 3.8 Quartz Scheduler (Notification Service Instance)
`QRTZ_*` tables (same Quartz schema as jobsvc) — manages scheduling of notification batch jobs, Mailgun event polling, and scheduled notification delivery. This is a **separate Quartz instance** from the one in jobsvc, dedicated to the notification scheduler.

## 4. Data Stored and Data Classification

| Data Category | Table/Column | PII/Sensitive Flag |
|---------------|-------------|--------------------|
| Email address (to/from) | `notification_queue.to_address`, `from_address` | **HIGH PII / TCPA** |
| Phone number (SMS recipient) | `sms_opt_out.recipient_phone_number` | **HIGH PII / TCPA** |
| Phone/email identifier | `ch_consent.identifier` | **HIGH PII / TCPA** |
| Email template content | `notification_template.template_value` | May contain PII in merge fields |
| Notification event data | `notification_event_data` | May contain PII |
| Email details (failed) | `email_details` (bounceback content) | **HIGH PII** |
| Consent state | `ch_consent.is_active` | **HIGH — TCPA compliance** |
| Consent history | `ch_consent_history` | **HIGH — TCPA audit** |
| Quiet hours config | `ch_quiet_hours` | Operational |
| Program short code mapping | `program_short_code_mapping.short_code` | Operational |
| Mailgun message IDs | `mailgun_events_queue.message_id` | Operational |

## 5. Regulatory Relevance

### TCPA (Telephone Consumer Protection Act)
**Critical regulatory scope**: The TCPA restricts automated calls and SMS to mobile phones. Onbe's SMS notification infrastructure must:
1. **Maintain opt-out records**: `sms_opt_out` and `ch_consent` tables with `is_active=0` for opted-out numbers.
2. **Enforce quiet hours**: `ch_quiet_hours` system default (20:00–10:00 EST) implements FCC TCPA quiet hour requirements.
3. **Honour opt-out within one business day**: New consent system must process opt-out events immediately.
4. **Maintain opt-out audit trail**: `ch_consent_history` provides the full consent change log for compliance evidence.
5. **Short code compliance**: `program_short_code_mapping` must ensure each program uses a properly registered short code.

The April 2026 DeltaSql migration (`BZGD-0000/notificationssvc_consent_tables.sql`) demonstrates active investment in TCPA compliance infrastructure.

### CAN-SPAM (Email)
Email notifications from `notification_queue` must comply with CAN-SPAM:
- Accurate `from_address` — `notification_queue.from_address`
- Opt-out mechanism — not directly stored here; likely managed in `notification_config_user_enable`
- No deceptive subject lines — template subjects in `notification_template.template_subject`

### GDPR / CCPA
Email addresses in `notification_queue.to_address` are personal data. Deletion requests require:
1. Nulling/deleting `to_address` from historical `notification_queue` records
2. Removing consent records from `ch_consent` / `ch_consent_history`
3. Coordinating with EcountCore for source data deletion

## 6. Data Flows

```
Upstream Events (ordersvc, jobsvc, ecountcore)
        ↓ trigger
notification_event (event created)
        ↓ matched via
notification_config_program_template_map
        ↓ generates
notification_message_subscriber + notification_queue
        ↓ dispatched to
Email → Mailgun → delivery event → mailgun_events_queue (webhook)
SMS   → SMS Provider → opt-out events → sms_opt_out / ch_consent
        ↓ reporting via
notification_message_debug_vw (view)
```

## 7. Integration Points

| System | Integration | Purpose |
|--------|------------|---------|
| `notification-framework_SVC` | Primary writer | Notification event creation |
| `notification-service-client_SVC` | API client | Service-to-service notification requests |
| `notification-requests-generator_LIB` | Library | Notification request generation |
| Mailgun API | External | Email delivery and event webhooks |
| SMS provider (via short codes) | External | SMS delivery and opt-out webhook |
| `jobsvc` | Upstream | `job_action_send_notification` triggers |
| `ordersvc` | Upstream | Order status notification triggers |
| `ecountcore` | Upstream | Card lifecycle notification triggers |
