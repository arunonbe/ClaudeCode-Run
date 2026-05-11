# account-service_LIB — Data Architect View

## Data Stores

The library interacts with multiple distinct SQL Server databases, accessed via Spring-configured `DataSource` beans. Each data source is named and referenced in `AccountServiceDAO.xml` and `appCtx-AccountService.xml`.

| DataSource Bean | Logical Database | Purpose |
|---|---|---|
| `jobsvcDS` / `JobSvcDataSource` | Job Service DB | ACH transfer detail creation; job-account mapping (`dbo.job_account_map_get`, `dbo.job_account_map_update`) |
| `EcountCoreDataSource` | Ecount Core DB | Claimable payment creation (`CreateClaimablePayment` SP), expiry date retrieval (`GetCliamablePaymentExpiryDate` SP), claimable-payment addenda, claim-code issuance audit |
| `notificationSvcDS` (via Director) | NotificationSvc DB | SMS/email notification configuration, program enable status, template resolution, short code mapping, SMS opt-out, SMS queue |
| `CbaseappDataSource` | Cbaseapp DB | Affiliate presentation metadata, virtual express install/extract SPs, debit API audit, partner user ID mapping |

DataSource beans for `jobsvcDS` / `notificationSvcDS` are created at runtime via `DirectorConfiguredDBCPdatasourceCreator`, consuming Director-supplied connection parameters (`${director.address}`, `${agent.notificationsvc}`, `${data.environment.notificationsvc}`).

---

## Schema & Tables

All table references are extracted from the SQL constants in `SmsNotificationConfigDao.java` and `SmsQueueDao.java`, supplemented by stored procedure class names.

### NotificationSvc Database (schema `NotificationSvc.dbo`)

| Table | Operation | Key Columns |
|---|---|---|
| `notification_config_sms_program_enable` | SELECT | `program_id`, `promotion`, `enable`, `notification_validation` |
| `notification_sms_event_subscriber` | SELECT | `event_id`, `subscriber_id`, `enable` |
| `notification_event_subscriber` | SELECT (email path) | `event_id`, `subscriber_id`, `enable` |
| `notification_config_program_locale` | SELECT | `program_id`, `promotion`, `locale_id`, `status_id` |
| `notification_config_program_channel` | SELECT | `program_id`, `promotion`, `channel_id`, `status_id` |
| `notification_config_sms_program_template_map` | SELECT | `program_id`, `promotion`, `subscriber_id`, `locale_id`, `channel_id` (=3 SMS), `template_id`, `status_id` |
| `notification_config_program_template_map` | SELECT | Same columns, `channel_id` = 1 (EMAIL) |
| `program_short_code_mapping` | SELECT | `id`, `program_code`, `short_code`, `active_flag`, `created_at`, `updated_at` |
| `sms_opt_out` | SELECT (COUNT) | `short_code`, `recipient_phone_number` |
| `notification_sms_event_name` | SELECT | `event_name`, `event_id` |
| `notification_event_name` | SELECT (email path) | `event_name`, `event_id` |
| `notification_sms_event_template` | SELECT | `event_id`, `product`, `template_id` |
| `notification_event_template` | SELECT (email path) | `event_id`, `product`, `template_id` |
| `notification_sms_template` | SELECT | `template_id`, `template_value` |
| `notification_service_type_config` | SELECT (COUNT) | `program_id`, `service_type` (=1 for CRCP) |
| `sms_notification_queue` | INSERT | `puid`, `program_id`, `program_name`, `mobile_phone`, `short_code`, `message_text`, `url`, `amount_in_dollars`, `status`, `retry_count`, `created_at`, `updated_at`, `scheduled_send_time` |

Stored procedure `notification_get_programenablestatus_config` is executed via `StoredProcGetProgramEnableStatus` against `notificationSvcDS`.

### EcountCore Database

| Object | Type | Operation | Class |
|---|---|---|---|
| `claim_code_issuance_info` | Table | INSERT | `ClaimCodeIssuanceInfoDao` |
| (unnamed SP for claimable payment) | Stored Procedure | EXEC | `CreateClaimablePayment` |
| (unnamed SP for expiry date) | Stored Procedure | EXEC | `GetCliamablePaymentExpiryDate` |
| (claimable_payment_addenda) | Table | INSERT (batch) | `ClaimablePaymentAddendaDao` |

`claim_code_issuance_info` columns (from `ClaimCodeIssuanceInfoDao.insert()`):
`claim_code`, `amount`, `dda`, `currency`, `issued_date`, `program_id`, `puid`, `home_email`, `first_name`, `last_name`, `address1`, `city`, `state`, `zip`, `country`

### Job Service Database

| Object | Type | Operation |
|---|---|---|
| `dbo.job_account_map_get` | Stored Procedure / Function | SELECT (list) by partner_id+affiliate_id+PUID+emember_id |
| `dbo.job_account_map_get2` | Stored Procedure / Function | SELECT (list) by program_id+PUID+emember_id |
| `dbo.job_account_map_update` | Stored Procedure / Function | UPDATE PUID mapping (partner_id+affiliate_id) |
| `dbo.job_account_map_update2` | Stored Procedure / Function | UPDATE PUID mapping (program_id) |
| `ach_transfer_detail_create` | Stored Procedure | INSERT — via `AchTransferDetailCreate` |

ACH transfer detail includes: `job_id`, `tx_id`, `recipient_id`, `reverse_tx_id`, `stop_payment_code`, `activity`, `transfer_ref_id`, `settlement_date`, `tx_desc`, `event_type`, `device_id` (`ACHTransferDetail.java`).

---

## Sensitive Data Handling

| Data Element | Where It Appears | Handling |
|---|---|---|
| Mobile Phone Number | `SmsQueueDao` (stored in `sms_notification_queue.mobile_phone`), `SmsNotificationService`, `CrcpNotificationService.sendSmsNotification()` | Stored in plaintext in the SMS queue table. No masking or tokenisation is applied in-library. |
| Email Address | `claim_code_issuance_info.home_email`, `RegisterUserInput`, CRCP request body | Stored in plaintext. Passed to CRCP service over HTTPS (OAuth2). |
| First / Last Name | `claim_code_issuance_info`, CRCP `RecipientInfo` | Stored in plaintext in audit and notification tables. |
| Address (Address1, City, State, ZIP, Country) | `claim_code_issuance_info`, `SetLocationCodeInput`, `ValidationLibrary` | Stored in plaintext. |
| PUID (partner_user_id) | `SmsQueueDao.puid`, CRCP `recipientId`, `job_account_map` | Stored/transmitted as plaintext. `CrcpNotificationService.sanitizeRecipientId()` strips "NOT SPECIFIED " prefix but does not mask. |
| DDA Number | `AddFundsInput.dda_number`, `ClaimCodeIssuanceInfo.dda`, `WithdrawInput.dda_number` | This is an internal account identifier (not a full PAN), transmitted to stored procedures. No explicit encryption observed. |
| OAuth Client Secret (SMS, CRCP) | Injected via Spring properties `${sms.client.secret}`, `${crcp.client.secret}` | Stored as String fields in `SmsNotificationService` and `CrcpNotificationService`. Masked in logs by `maskSecretForLog()` in the CRCP service only. The SMS service does not apply log masking. |
| Secure User Profile | `RegisterUserInput.secure_profile` (`SecureUserProfile`) contains federal_id, date_of_birth, driver_license_number | Passed to `MemberDelegate.addExtendedMember()` — the handling of these fields within the core delegate is outside this library's scope, but the fields are present in the API. |

---

## Encryption & Protection

- **Transport**: External calls to CRCP service (`CrcpServiceConnector`) and SMS shared service (`SmsServiceClient`) are HTTPS-based, authenticated via MS OAuth2 (client credentials flow) using `clientId`, `clientSecret`, `authority`, `scope` injected via Spring properties.
- **At Rest**: No field-level encryption is applied within this library. The `xsecurity-client/common/impl` artifacts (version 4.0.3) are on the classpath; they may provide encryption services consumed by `StrongBoxXMLRPCClient` (injected into `AccountServiceContext`), but no calls to StrongBox are observed in the business flows.
- **Cache**: EhCache 3 (`jakarta` classifier) is used for notification program enable status. The cache is in-heap only (no disk persistence in production config `ehCache3-mapping-naProd.xml`). Cache entries for `notificationMappingNaProd` and `notificationProgramEnableNaProd` have `<ehcache:none/>` expiry (eternal). No cache encryption.

---

## Data Flow

```
External Caller
    │
    ▼
AccountServiceImpl (IAccountService)
    │
    ├─► MemberXMLRPCClient → EcountCore member DB (register/update/inquire)
    ├─► DeviceXMLRPCClient → EcountCore device DB (issue card)
    ├─► TransferDelegate (XML-RPC) → EcountCore transfer engine (add funds / withdraw)
    ├─► PaymentServiceDelegate → payment-service (create certificate)
    │
    ├─► AccountServiceDAOJDBCImpl
    │       ├─► JobSvcDataSource → dbo.job_account_map_*, ach_transfer_detail_create
    │       ├─► EcountCoreDataSource → claimable payment SPs, claim_code_issuance_info
    │       └─► notificationSvcDS → notification config tables (read-only lookups)
    │
    ├─► NotificationServiceDelegateImpl
    │       ├─► SmsProgramConfigurationHelper → SmsNotificationConfigDao (NotificationSvc)
    │       ├─► SmsQueueService → SmsQueueDao → sms_notification_queue (INSERT)
    │       └─► CrcpNotificationService → CrcpServiceConnector → CRCP HTTP API (HTTPS/OAuth2)
    │
    └─► SmsNotificationService → SmsServiceClient → SMS HTTP API (HTTPS/OAuth2)
```

---

## Data Quality & Retention

- **Settlement Date**: `AddFundsInput.validate()` enforces `settlement_date >= now()`. `StopPaymentInput.validate()` always sets `settlement_date = payment_settlement_dt`.
- **UUID Generation**: `tx_id` and `reversal_tx_id` default to `UUID.randomUUID()` when not provided by caller, ensuring uniqueness.
- **SMS Queue Retention**: Rows inserted into `sms_notification_queue` with status `PENDING`. No TTL or purge logic is present in this library; retention policy depends on an external worker/DBA process.
- **Claim Code Audit**: `claim_code_issuance_info` is written once at issuance with `issued_date = LocalDate.now().atStartOfDay()`. No update or expiry mechanism exists in this library.
- **EhCache TTL**: In non-production environments (`ehCache3-mapping-nasit.xml`, `ehCache3-mapping-naqa.xml`), default TTL of 86400 seconds applies to notification caches. Production uses eternal entries.
- **Comment Truncation**: `WithdrawInput.validate()` enforces `comment.length() <= 64` for direct debit (withdraw type 3), silently truncating at 64 characters.

---

## Compliance Gaps

1. **PII in SMS Queue (plaintext mobile phone + PUID)**: `sms_notification_queue` stores `mobile_phone` and `puid` in plaintext SQL Server columns. For GDPR/CCPA compliance, these should be masked or tokenised at rest, and subject to a documented retention/deletion schedule.

2. **Email Address in Audit Table**: `claim_code_issuance_info.home_email` stores the cardholder email in plaintext. This table lacks an observed purge/anonymise mechanism, which is a GDPR right-to-erasure risk.

3. **OAuth Secrets in Application Memory**: SMS (`smsClientSecret`) and CRCP (`crcpClientSecret`) OAuth client secrets are injected as plain Strings into Spring beans. No evidence of SecureString handling or in-memory secret protection (e.g., StrongBox for in-process secrets).

4. **No Observed Data Masking in Debug Logs**: `AccountServiceDAOJDBCImpl` and `AddFunds` log PUID, emember IDs, and program IDs at DEBUG level without masking. In environments with DEBUG logging enabled, these could appear in log aggregators.

5. **DDA Number Traceability**: `dda_number` is present in `WithdrawInput`, `AddFundsInput`, and `ClaimCodeIssuanceInfo` but there is no explicit check that this is an internal routing number (not a full PAN). If callers pass an actual card PAN, it would be stored in the audit table. This represents a potential PCI DSS cardholder data risk.

6. **No Observed Row-Level Encryption on Claim Code Table**: The `claim_code` in `claim_code_issuance_info` is stored as plaintext; if claim codes provide value redemption capability, they should be treated as sensitive payment credentials.
