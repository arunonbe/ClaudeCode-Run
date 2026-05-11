# DS_DB_jobsvc — Business Analyst Report

## 1. Repository Identity

| Attribute | Value |
|-----------|-------|
| Repo name | DS_DB_jobsvc |
| Internal alias | Job Service Database |
| Project file | `jobsvc.sqlproj` (GUID `73ef9390-5a34-414d-9eeb-c9b79f088f5e`) |
| Solution file | `jobsvc.sln` |
| SQL Server version target | SQL Server 2012 (DSP `Sql110DatabaseSchemaProvider`) |
| Target framework | .NET 4.6.1 |
| Total files | 669 |

## 2. Business Purpose

`DS_DB_jobsvc` is the **central job processing and batch orchestration database** for Onbe's prepaid card disbursement platform. It stores the operational state for all batch jobs that process client-submitted instruction files containing cardholder registration, card issuance, fund loading, and payment actions. This database is the persistence layer for the `jobservice_SVC` / `batch_LIB` components and coordinates:

1. **File ingestion and parsing** — receiving client partner instruction files (CSV, XML, or proprietary formats) and tracking their parsing status.
2. **Job action decomposition** — breaking down each file record into discrete executable actions (register user, issue card, add funds, send notification).
3. **Work orchestration** — scheduling and executing job actions in order via the `work_instance` / `work_process` state machine.
4. **ACH transfer tracking** — recording ACH/eCheck disbursements initiated on behalf of cardholders.
5. **Instant Issue inventory management** — tracking pre-activated card inventory for instant card issuance at point-of-sale or mailing.
6. **Banker / sweep management** — tracking reserved fund sources, preset fund configurations, and banker-driven payment distribution.
7. **Quartz scheduler** — hosting `QRTZ_*` tables for the Java Quartz scheduler used by the job service.
8. **Blackout window management** — preventing job execution during defined maintenance or market-hours blackout periods.
9. **SFTP and autofile processing** — tracking file-based integration workflows via `sftp_process_status` and `autofile_*` tables.

## 3. Core Business Processes Supported

### 3.1 Batch File Processing (Client Partner Files)
Clients submit instruction files to Onbe containing rows of disbursement actions. The jobsvc database tracks the full lifecycle:
- **File receipt**: `job_file` table records file arrival, partner ID, file name, timestamps.
- **Parsing status**: `job_file_status_history` and `job_file_ingest` track parse progress.
- **Record decomposition**: `job_record` and `job_record_action` map file rows to action sets.
- **Action queuing**: `job_action` and action-type-specific tables (`job_action_register_user`, `job_action_issue_card`, `job_action_add_funds`, etc.) hold the action payload.
- **Completion tracking**: `job_action_history` and `job_action_history_Archive` record action results.

### 3.2 Cardholder Registration (PII-Intensive)
The `job_action_register_user` table holds **cardholder PII submitted by clients** for card issuance:
- First name, last name, middle name, suffix
- Home email address (`home_email`)
- Phone numbers: home, business, mobile (`home_phone`, `business_phone`, `mobile_phone`)
- Mailing address: address1, address2, city, state, postal, country
- `ecount_id` — the cardholder's Onbe platform identifier

Extended phone data is in `job_action_register_user_extended_phone`.
Extended address data is in `job_action_register_user_extended_address`.

### 3.3 Card Issuance
`job_action_issue_card` records card issuance actions with card expiry data (`exp_month`, `exp_year`), card type, and access level. Linked to the corresponding register user action.

### 3.4 Fund Loading / Payments
`job_action_add_funds` records fund-loading actions:
- `amount` (integer cents)
- `claim_code` — Claimable payment token (PII — links to NexPay claimable)
- `echeck_id` — ACH/eCheck payment reference
- `direct_claim_flag` — Whether the payment is directly claimable

### 3.5 ACH / eCheck Transfer Tracking (NACHA)
`ach_transfer_detail` tracks ACH transfers at the transaction level:
- `tx_id`, `recipient_id` — Transaction and recipient identifiers
- `settlement_date` — ACH settlement date
- `event_type`, `status_code`, `result_code` — ACH processing outcomes

**Regulatory**: ACH data is governed by NACHA Operating Rules and Regulation E (12 CFR Part 1005). Error resolution timelines, reversal tracking, and return codes must be maintained per Reg E requirements.

### 3.6 Instant Issue Card Inventory
`instant_issue_card` and related tables (`instant_issue_order`, `instant_issue_current_inventory_details`) track pre-activated card inventory:
- `card_number` CHAR(16) — **CRITICAL PCI FLAG** — 16-digit card number stored in plain text
- `tracking_number` — Physical card shipping tracking
- `partner_user_id` — Cardholder identifier
- `parent_dda` CHAR(16) — DDA (Demand Deposit Account) number — **CRITICAL PCI FLAG**

### 3.7 Quartz Scheduler
`QRTZ_JOB_DETAILS`, `QRTZ_TRIGGERS`, `QRTZ_CRON_TRIGGERS`, `QRTZ_FIRED_TRIGGERS`, `QRTZ_SCHEDULER_STATE`, `QRTZ_LOCKS`, and related tables are the **Quartz 1.x job scheduling metadata tables**. These store job definitions, trigger schedules (cron expressions), and execution history for all batch jobs across the platform.

### 3.8 Banker / Fund Management
`banker_job`, `banker_promotion`, `banker_preset_funds_config`, `banker_reserved_source` tables manage fund reservations and distribution configurations for bulk disbursement programs.

### 3.9 Blackout Window Management
`blackout_master`, `blackout_schedule`, `blackout_weekly_day`, `blackout_job` tables define time windows during which batch job execution is suppressed (e.g., bank cutoff times, exchange close periods).

## 4. Data Stored and Data Classification

| Data Category | Table | PII/Sensitive Flag |
|---------------|-------|--------------------|
| Cardholder name | `job_action_register_user` | **HIGH PII** |
| Email address | `job_action_register_user.home_email` | **HIGH PII / TCPA** |
| Phone numbers | `job_action_register_user.home_phone/business_phone/mobile_phone` | **HIGH PII / TCPA** |
| Mailing address | `job_action_register_user.address1/city/state/postal` | **MEDIUM PII** |
| Card number (16-digit) | `instant_issue_card.card_number` | **CRITICAL — PCI PAN** |
| DDA number | `instant_issue_card.parent_dda` | **CRITICAL — Account number** |
| Claim code token | `job_action_add_funds.claim_code` | **HIGH — Payment token** |
| ACH transfer refs | `ach_transfer_detail.tx_id`, `transfer_ref_id` | **HIGH — NACHA** |
| Secure field references | `job_action_memo_secure.field_secure_ref` | References to Strongbox vault |
| Fund amounts | `job_action_add_funds.amount` | Financial |
| Card expiry | `job_action_issue_card.exp_month/exp_year` | **PCI SAD** |

## 5. Regulatory Relevance

### PCI DSS — CRITICAL
**The `instant_issue_card.card_number` CHAR(16) column is a strong indicator that PANs may be stored in this table.** This places `instant_issue_card` — and potentially the entire `jobsvc` database — **in PCI DSS CDE scope or directly adjacent**. PCI DSS Requirement 3 prohibits storage of the full PAN unless it is masked, truncated, or encrypted using approved cryptographic methods. Storing a 16-character card number in plaintext is a critical PCI finding.

Additionally, `parent_dda` (DDA account number) in `instant_issue_card` may represent a bank account number — another sensitive financial identifier.

`job_action_issue_card.exp_month` and `exp_year` constitute Sensitive Authentication Data (SAD) elements if stored post-authorization — a direct PCI DSS Requirement 3.3.1 violation.

### NACHA / Regulation E
`ach_transfer_detail` stores ACH transaction records. NACHA Operating Rules require:
- Accurate record of ACH entries (Reg E 12 CFR 1005.9)
- Error resolution records (Reg E 1005.11)
- Return code tracking

### TCPA (Telephone Consumer Protection Act)
`job_action_register_user` stores phone numbers used for notification delivery. If the platform sends SMS or automated calls using these numbers, TCPA consent records must be maintained. The `notification_code` field in this table may reference consent status.

### GLBA / Consumer Privacy
Cardholder name, email, address, and phone are GLBA-protected consumer financial information. The `jobsvc` database is a primary store of this data and must be included in Onbe's GLBA safeguards program.

## 6. Data Flows

```
Client Partner Files (SFTP)
        ↓
autofile_job / job_file (file receipt & tracking)
        ↓
job_record → job_record_action (file parsing)
        ↓
job_action_* tables (action decomposition)
        ↓
work_instance / work_process (execution orchestration)
        ↓
EcountCore (cardholder registration → card issuance → fund loading)
        ↓
ach_transfer_detail (ACH settlement tracking)
        ↓
job_action_history / job_action_history_Archive (completion audit)
```

Quartz scheduler (`QRTZ_*`) drives the timing of batch execution across all steps.

## 7. Integration Points

| System | Integration | Purpose |
|--------|------------|---------|
| `jobservice_SVC` | Primary writer | Java Spring Batch / Quartz service |
| `ecountcore` database | Downstream | Card operations execution |
| `DS_DB_ordersvc` | Related | Order lifecycle events trigger job actions |
| `DS_DB_notificationsvc` | Downstream | `job_action_send_notification` triggers notifications |
| `DS_DB_nexpay_claimable` | Related | `claim_code` links claimable payment tokens |
| Strongbox vault | Downstream | `job_action_memo_secure.field_secure_ref` references vault tokens |
| SFTP partner feeds | Upstream | Client file delivery |
