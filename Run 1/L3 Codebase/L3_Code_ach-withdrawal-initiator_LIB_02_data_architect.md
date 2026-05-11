# ach-withdrawal-initiator_LIB — Data Architect View

## Data Stores

Three distinct SQL Server databases are accessed, all via JDBC through the `DirectorConfiguredDBCPdatasourceCreator` bean (which resolves connection credentials dynamically from a "Director" service rather than storing them in properties):

| Spring Bean ID | Property Key | Usage |
|----------------|--------------|-------|
| `JobsvcDataSource` | `${jobsvc.database}` | ACH job queue; primary source of withdrawal batch records |
| `EcountCoreDataSource` | `${ecountcore.database}` | Core transaction/event store; app-event transfers, member data |
| `CbaseappDataSource` | `${cbaseapp_database}` | Application database; affiliate/program data, comments |

Connection pooling is provided by Apache Commons DBCP (`commons-dbcp:1.2.2`) with `commons-pool:1.4`. The DBCP bean definitions are present but commented out in `appContext-ach.xml` (lines 15–47); the live path uses Director-managed connections.

The external properties file is expected at `d:/c-base/config/achwithdrawal/achwithdrawal.properties` (hard-coded Windows path in `appContext-ach.xml`, line 8). This is a platform-specific configuration file not included in the repository.

## Schema & Tables

All data access is through SQL Server stored procedures. No ORM entity classes exist for the core transactional tables; the schema is inferred from stored procedure parameters and `ResultSet` column names in DAO `mapRow()` implementations.

### JobsvcDataSource — Inferred Tables

**ach_transfer_detail** (or equivalent) — queried by `dbo.ach_transfer_initiate_extract`:
- `id` (INT) — primary key / row identifier
- `job_id` (INT) — associated batch job
- `recipient_id` (VARCHAR) — cardholder UUID
- `tx_id` (VARCHAR) — transaction identifier
- `request_attempts` (INT) — retry counter
- `activity` (VARCHAR) — transfer activity code (e.g., "online-direct-withdraw")
- `transfer_ref_id` (VARCHAR) — reference ID for transfer lineage
- `settlement_date` (DATE) — ACH effective date
- `tx_desc` (VARCHAR) — transaction description
- `reverse_tx_id` (VARCHAR) — reversal transaction reference
- `transfer_id` (VARCHAR) — core platform transfer ID
- `device_id` (VARCHAR) — card/device identifier
- `event_type` (INT) — payment type discriminator (1=AUTO_ACH, 2=FUTURE_EFFECTIVE_ACH, 3=STOP_PAYMENT, etc.)
- `status_code` (INT) — processing status (2=PROCESSING, 3=UNPROCESSED)

Written back by `dbo.update_ach_transfer_detail_status` (params: `id`, `result_code`, `status_code`, `request_attempts`, `event_type`, `result_message`, `transfer_id`).

**Unprocessed records**: queried by `dbo.ach_transfer_extract_unprocessed_records` (`UnProcessedAutoACHExtract`) using `event_type` and `rcount` — same column structure.

### EcountCoreDataSource — Inferred Tables/Objects

**app_event_service** (XML or column-mapped) — queried by `dbo.app_event_service_transfer_service`:
- `event_parameters.callback.parameters.id` — event row ID
- `event_parameters.activity` — activity code
- `event_parameters.member` — member UUID
- `event_parameters.source_type` / `event_parameters.dest_type` — device type codes
- `event_parameters.amount` (INT) — transfer amount in cents
- `event_parameters.fee` (INT) — fee in cents
- `event_parameters.tx_desc` — description
- `event_parameters.callback.procedure` — callback stored procedure name
- `status` (INT) — processing status
- `updated` (DATE) — last update timestamp

Written back by `dbo.app_event_service_transfer_update` (params: `id`, `tx_id`, `status`, `status_comment`).

**app_event_service_transfer** (insert via `dbo.app_event_service_transfer_create`):
- `member`, `source_type`, `dest_type`, `amount`, `activity`, `fee`, `cascade_source_type`, `cascade_dest_type`, `reference_id`, `tx_id`, `event_id` (OUT), `process_date`, `tx_desc`

**ach_transfer_api_detail** (or equivalent) — queried by `dbo.ach_transfer_initiate_api_extract` (`AutoClaimApiRequestExtract`). Column structure identical to `ach_transfer_detail`. Written back by `dbo.update_ach_transfer_detail_api_status`.

**AutoACH inquiry**: `dbo.app_user_autoach_inquiry` (params: `member`, `transaction_id`; OUT: `autoach_withdraw_amount` INT).

**Push-to-Debit inquiry**: `dbo.app_user_recurring_push_to_debit_inquiry` (params: `member`, `transaction_id`; OUT: `push_to_debit_withdraw_amount` INT).

### CbaseappDataSource — Affiliate and Comment Tables

Used via Hibernate (`AnnotationSessionFactoryBean`) for the `com.ecount.one.service.affiliate.Affiliate` and `AffiliateDetail` entities (affiliate/program metadata). Also used by the comment service DAO implementations (`CommentHistoryDAOImpl`, `InsertCommentDAOImpl`, etc.) from the `com.ecount.services.comment` library.

## Sensitive Data Handling

Bank account details (routing number, account number, account type, account holder name) are present in the `AccountDefinitionACH` object retrieved from the core platform at runtime via `DeviceManagerImpl.getDefaultACH()`. This data:

- **Is used in memory** to build ACH addenda and beneficiary name fields — `RequestProcessorThread` lines ~237–263, ~595–626, ~773–804.
- **Is NOT written to logs** in any reviewed code path (positive finding).
- **Is NOT stored** in any local table or file by this process.
- **Is NOT encrypted** at the application layer — it is consumed directly from core platform objects.

The `EcheckProcessEmailTemplate` contains commented-out validation code (lines 75–79) that references merge fields for `BANK_ACCOUNT_NUMBER` and `ROUTING_NUMBER`. These fields are currently **disabled**. If uncommented and routed to the email template, they would constitute a serious data exposure risk (PII + financial data in email).

Cardholder PII (first name, last name, email address, mailing address) is retrieved via `MemberManagerImpl.InquiryExtended()` and used for:
- ACH beneficiary name in addenda
- Notification email recipient and merge fields
- Push-to-Debit recipient data submitted to Tabapay API

The Tabapay push-fund API payload (`SharedServiceHelper.sharedServicePushFundCall()`, lines 66–77) includes: cardholder `firstName`, `lastName`, `address`, `postalCode`, `referenceId`, and debit card details (`cardDetails` map). This is transmitted over HTTPS to an external service — the only TLS trust guarantee is the JVM default truststore; no certificate pinning is implemented.

The `msClientSecret` for OAuth 2.0 authentication with the PushPay/Tabapay service is injected as a Spring bean from an external properties file (`${pushpay.ms.client.secret}`) and is available as a plain `String` in the Spring context at runtime.

## Encryption & Protection

- **Transport**: HTTPS is used for Tabapay API calls (`HttpURLConnection` to `${pushpay.url}`). No explicit TLS version enforcement or certificate validation override was found.
- **OAuth 2.0**: MSAL4J (`ClientCredentialFactory.createFromSecret()`) is used for Tabapay service authentication. Token caching via silent token acquisition (`acquireTokenSilently`) is attempted before a full credential flow.
- **At-rest encryption**: Not managed by this component. The process relies on the host database servers and platform infrastructure.
- **Secrets management**: Database credentials are resolved at runtime via the "Director" service (`DirectorConfiguredDBCPdatasourceCreator`) — this avoids embedding credentials in the JAR. The OAuth client secret is read from a filesystem properties file (`achwithdrawal.properties`).
- **No application-layer encryption**: ACH routing/account numbers and cardholder PII are handled as plaintext Java objects in heap memory.

## Data Flow

```
JobsvcDataSource (SQL Server)
    └─[dbo.ach_transfer_initiate_extract]──► IterativeProcess
                                                   │
                                          RequestProcessorThread
                                                   │
                               ┌───────────────────┼──────────────────────┐
                               ▼                   ▼                      ▼
                    EcountCoreDataSource    EcountCore Platform     Tabapay API
                    (member inquiry,        (TransferManagerImpl,   (Push-to-Debit)
                     event service)          DeviceManagerImpl)
                               │
                    [dbo.update_ach_transfer_detail_status]
                               │
                    JobsvcDataSource (status write-back)
```

- The process is **read-heavy on JobsvcDataSource** and **read-write on EcountCoreDataSource**.
- Status write-backs are the only mutations to `JobsvcDataSource`.
- Notification emails are dispatched via the core `NotificationManagerImpl` (no direct SMTP from this process).

## Data Quality & Retention

- **Retry counters**: `request_attempts` is incremented on every status update, providing an audit trail of processing attempts.
- **Failure lookback**: `Process.MaxDaysForProcess.OnFailure.SIMPLE_TRANSFER = 65` — simple transfer failures are retried for up to 65 days. AUTO_ACH uses 2 days.
- **No data archival or purge logic**: This process only updates status codes; record lifecycle (creation, archival, deletion) is managed entirely by upstream and downstream systems.
- **Amount in integer cents**: All monetary amounts are stored and processed as integers (cents), consistent with financial processing best practices.
- **No schema version control**: No Flyway, Liquibase, or equivalent migration framework is present. Schema changes must be coordinated externally.

## Compliance Gaps

1. **Audit trail gap**: There is no structured audit log produced by this process (beyond log4j TRACE/INFO/ERROR messages to a rolling file). Changes to payment status are written to DB via stored procedures, but no separate audit event table is written by this component.
2. **Commented-out bank account/routing number in email template**: The merge fields `BANK_ACCOUNT_NUMBER` and `ROUTING_NUMBER` exist in the disabled validation block of `EcheckProcessEmailTemplate`. Reactivating them without masking would violate GLBA and NACHA data handling rules.
3. **No data masking in logs**: `logger.info("Pushpay: -  Post Data: " + jsonBody.toString()` in `SharedServiceHelper` (lines 104, 186) logs the full JSON request body including card details and recipient PII. This log output goes to `ach_processor.log` (rolling file, 50 × 10 MB) and to `stdout`. This is a PCI DSS and GDPR concern.
4. **Client secret in properties file**: The OAuth2 `msClientSecret` value comes from a filesystem properties file; if this file is not protected by OS-level ACLs, it constitutes a credential exposure risk.
5. **Hard-coded config path**: `file:///d:/c-base/config/achwithdrawal/achwithdrawal.properties` in `appContext-ach.xml` ties deployment to a specific Windows drive letter and directory structure.
