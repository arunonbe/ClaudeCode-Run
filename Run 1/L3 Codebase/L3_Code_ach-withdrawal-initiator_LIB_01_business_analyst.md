# ach-withdrawal-initiator_LIB — Business Analyst View

## Business Purpose

This library is a standalone Java batch process that initiates and manages ACH (Automated Clearing House) withdrawals and related payment-rail transfers on behalf of Onbe cardholders. It runs as a command-line JVM process (entry point: `ACHWithdrawalProcessMain.main()`), polls one or more SQL Server databases for pending transfer requests, executes transfers through the ecount/cbase platform core, and writes back status results. It also supports Push-to-Debit (card push) via an external "PushPay" (Tabapay) service.

## Business Capabilities

The process supports the following discrete payment-type request categories (defined in `RequestType.java`):

| Code | RequestType | Description |
|------|-------------|-------------|
| 1 | AUTO_ACH | Recurring automatic ACH withdrawal from cardholder bank account |
| 2 | FUTURE_EFFECTIVE_ACH | ACH withdrawal with a future settlement/effective date |
| 3 | STOP_PAYMENT | Cancel/stop a pending ACH transaction |
| 4 | SIMPLE_TRANSFER | Ad-hoc direct ACH/DDA fund movement triggered by an app-event |
| 5 | AUTO_CLAIM | Automatic claim/disbursement via ACH |
| 6 | PUSH_TO_DEBIT | Recurring push-to-debit card disbursement (legacy, non-API path) |
| 9 | AUTO_CLAIM_FAILURE | Retry previously failed AUTO_CLAIM records |
| 10 | AUTO_CLAIM_API | Auto-claim via external API path |
| 11 | PUSH_TO_DEBIT_API | Push-to-debit via external API path |
| 12 | AUTO_ACH_API | Auto ACH via external API path (WARR-6544) |
| 6F | AUTO_ACH_FAILURE | Retry previously failed AUTO_ACH records |
| 7F | FUTURE_EFFECTIVE_ACH_FAILURE | Retry failed future-effective ACH records |
| 8F | STOP_PAYMENT_FAILURE | Retry failed stop payment records |

The process is triggered in two modes via a command-line argument:
- Default (no arg): Processes ACH/claim rails.
- `PTC` arg: Processes Push-to-Card rails (PUSH_TO_DEBIT and PUSH_TO_DEBIT_API only).

## Business Entities

- **Cardholder/Member**: Identified by `recipient_id` / `memberId` (UUID string). Referenced throughout `AutoACHExtractData`, `AppEventServiceData`, and all DAO calls.
- **Transfer**: A funds movement between source and destination device types (ACH, DDA, eCard). Represented by `AppEventServiceTransfer` and core `TransferDefinition`.
- **ACH Extract Record**: A queued withdrawal job row pulled from `JobsvcDataSource` via stored procedure `dbo.ach_transfer_initiate_extract`. Fields: `id`, `job_id`, `recipient_id`, `tx_id`, `request_attempts`, `activity`, `transfer_ref_id`, `settlement_date`, `event_type`, `status_code`.
- **App Event**: A platform-level async event record in `EcountCoreDataSource`, pulled via `dbo.app_event_service_transfer_service`. Fields: `event_parameters.member`, `event_parameters.amount`, `event_parameters.source_type`, `event_parameters.dest_type`, `event_parameters.activity`.
- **Allotment**: An autoclaim split allocation (`com.citi.prepaid.core.autoclaim.domain.Allotment`), representing how funds are distributed across devices.
- **Affiliate/Program**: A program configuration entity used for notification templates and payment-selection feature flags.
- **Push-to-Debit Card**: Cardholder debit card details fetched via `PushToDebitCardDetailsRetrieveSP` from `EcountCoreDataSource`.

## Business Rules & Validations

- **Retry logic**: Each request type has a configurable maximum retry count (`Process.MaxTries.*`) and failure-day lookback window (`Process.MaxDaysForProcess.OnFailure.*`). For example, `AUTO_ACH` retries up to 3 times and looks back 2 days for failures.
- **CPS exception bypass codes**: Certain Core Processing System exception codes (14012, 14011, 14003, 4001, 4005, 4010, configured in `configuration.properties`) halt retries immediately for `SIMPLE_TRANSFER`. If the exception code is in this list, no further attempts are made.
- **ACH amount guard**: ACH transfers only proceed when `autoACHAmount > 0` (checked in `processAutoACH()` and `processFutureEffectiveACH()`). Zero-amount requests are silently marked successful.
- **Stop payment deduplication**: Before cancelling, the code checks whether a transfer record already exists (`AppEventServiceTransferInquiry` → `dbo.app_event_service_transfer_inquiry`) to avoid double-cancellations.
- **Simple transfer idempotency**: When an `AppEventServiceData.updated` date is set, the process treats it as a retry of an existing transfer and uses the previously assigned `tx_id`.
- **Cardholder name truncation**: Beneficiary name in ACH addenda is truncated to 40 characters (`StringUtils.substring`, `RequestProcessorThread` lines ~242, ~601, ~779).
- **Push-to-Debit affiliate ID validation**: `getPushToDebitSoftDescriptorName()` and `getPushToDebitMID()` enforce exactly 9-digit affiliate IDs, throwing `IllegalArgumentException` for invalid inputs (`RequestProcessorThreadTest` confirms this rule).
- **Balance sync feature flag**: A per-affiliate feature flag `balance_sync_recurring_ach` controls whether FDR balance synchronization runs before AUTO_ACH transfer initiation (WARR-8756). Defaults to off if flag lookup fails.
- **IDD program detection**: Programs with both `selection_opt_fx_transfer` and `selection_opt_cardless_fx` flags active are treated as IDD (International Direct Disbursement) programs, altering the notification email template.

## Business Flows

### Auto ACH Flow (PRIMARY)
1. `IterativeProcess.loadAutoACHRequests()` → calls SP `dbo.ach_transfer_initiate_extract` with event_type=1 on `JobsvcDataSource`.
2. Records distributed to `RequestProcessorThread` worker threads (up to 3 concurrent, 5 records per iteration).
3. `processAutoACH()`:
   a. Look up member's default ACH definition (routing/account type).
   b. Query withdrawal amount via `dbo.app_user_autoach_inquiry`.
   c. Optionally sync FDR balance (feature flag).
   d. Calculate fee via `simpleFeeInquiry()`.
   e. Call `TransferManagerImpl` to initiate and commit the ACH withdrawal.
   f. If successful, send email notification via `EcheckProcessNotification`.
4. Update status via `dbo.update_ach_transfer_detail_status`.

### Future Effective ACH Flow
Similar to Auto ACH but creates an `AppEventServiceTransfer` record (via `dbo.app_event_service_transfer_create`) with a settlement date, rather than directly initiating the transfer through core.

### Stop Payment Flow
1. Check if an app-event transfer record exists (`dbo.app_event_service_transfer_inquiry`).
2. Cancel via `dbo.app_event_service_transfer_cancel`.
3. Update status.

### Simple Transfer Flow
1. Pulls from `dbo.app_event_service_transfer_service` on `EcountCoreDataSource`.
2. Looks up member's default ACH definition.
3. Calls `TransferManagerImpl.transferFunds()` directly.
4. Handles retry with configurable sleep between attempts.
5. Updates status via `dbo.app_event_service_transfer_update`.

### Push-to-Debit Flow
1. Pulls push-to-debit records, retrieves card details from `PushToDebitCardDetailsRetrieveSP`.
2. Authenticates with Microsoft Entra ID (OAuth 2.0 client credentials) via `SharedServiceHelper.performOAuth2()`.
3. POSTs JSON payload to PushPay/Tabapay API URL.
4. Parses `processorStatus` from JSON response; maps COMPLETED/UNKNOWN/ERROR to internal `TabapayStatus` enum.
5. Inserts transaction status via `InsertPushToDebitTransactionStatusSP`.

## Compliance & Regulatory Concerns (especially NACHA, ACH rules, Reg E)

- **NACHA addenda fields**: The code populates ACH addenda explicitly — EFT type (`eft-type` = "ACH"), account type (Checking/Savings), terminal location ("Online"), and beneficiary name. These map to NACHA PPD/CCD entry detail records. Any misconfiguration of these values could result in NACHA return codes.
- **Reg E error handling**: Retry limits and CPS exception codes act as business-level stop controls. However, there is no explicit Reg E error-code mapping or customer dispute flagging in this code — those are presumed handled downstream.
- **Settlement date**: `FUTURE_EFFECTIVE_ACH` uses `settlement_date` from the database record as the ACH effective entry date. Late or incorrect dates could result in NACHA late-return or reversal issues.
- **Beneficiary name**: Truncated to 40 characters in addenda. NACHA limits individual name fields; truncation is compliant but must not corrupt the name.
- **Stop payment**: The `STOP_PAYMENT` flow cancels transfers at the platform layer. There is no evidence in the code of a NACHA stop-payment notification file being generated — this may be handled by downstream ACH file generation services.
- **No encryption of bank credentials in-flight**: The `AccountDefinitionACH` object (containing routing/account details) is retrieved from the core platform and used in memory. No logging of account numbers was found in the reviewed code, which is positive. However, the `EcheckProcessEmailTemplate` comment block (lines 75–79) references merge fields for `BANK_ACCOUNT_NUMBER` and `ROUTING_NUMBER` that are currently disabled/commented out — if re-enabled, these would violate PCI DSS and banking privacy standards.
- **OFAC/AML**: No OFAC screening or AML checks are visible in this process. Responsibility is assumed to lie with upstream systems that queue the transfer records.

## Business Risks

1. **Silent failure on AutoClaim in Load.java**: `loadAutoClaimRequests()` in `Load.java` (lines 151–168) contains dead code returning `null` after a `System.out.println("Testing Auto Claim")`. If `DefaultProcess` is used (not `IterativeProcess`), AUTO_CLAIM requests will be silently dropped. This is a critical data-loss risk if `DefaultProcess` mode is ever activated.
2. **No idempotency guarantee for Push-to-Debit**: The PushPay API call in `SharedServiceHelper` does not check whether the Tabapay call was already submitted before re-trying on HTTP error codes, risking duplicate disbursements.
3. **Thread-pool exhaustion under load**: All request types share a fixed thread pool sized by `Process.MainThreads = 2`. Under high volume, earlier request types block later ones.
4. **Hard-coded bank name**: `SharedServiceHelper.sharedServicePushFundCall()` has a TODO comment on line 51: `//TODO: Get Bank Name Dynamically` with `bankName` hard-coded to `ACHConstants.SUNRISE_BANK`. Multi-bank programs will silently receive incorrect routing.
5. **Tests skipped in CI**: `.gitlab-ci.yml` sets `MAVEN_TEST_OPTS: "-Dmaven.test.skip=true"` — tests are never executed during GitLab CI/CD, meaning test regressions go undetected.
