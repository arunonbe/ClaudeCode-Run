# batch_LIB — Business Analyst View

## Business Purpose

batch_LIB is a shared Spring Batch library (`com.ecount.service.core:batch:2.0.29-SNAPSHOT`) that provides all scheduled batch processing capabilities for the Onbe (formerly Northlane/Citi Prepaid) platform. It is packaged as a fat JAR (`batch-1.0.0.jar`) and executed via `CommandLineJobRunner`. It supports the full lifecycle of prepaid card, ACH, push-to-debit, PayPal, and Venmo payment operations — from initial card issuance through funds loading, transaction settlement, fee posting, and disbursement expiry/reversal.

## Business Capabilities

| Capability | Batch Job ID | Class / Package |
|---|---|---|
| Auto-claim (Disney Global Deposit) | `autoClaimBatchJob` | `AutoClaimProcessor`, `AutoClaimProcessHelper` |
| Claim code expiration & reversal | `ClaimExpirationBatchJob` | `ClaimExpirationProcessor`, `ClaimExpirationReverseHelper` |
| Claimable-choice code expiration | `ClaimableChoiceCodeExpirationBatchJob` | `ClaimableChoiceExpirationProcessor`, `ClaimableChoiceAPIClient` |
| PayPal recurring choice payout | `paypalChoiceJob` | `PayPalChoiceRecurringDetailsProcessor` |
| Venmo recurring choice payout | `venmoChoiceJob` | `VenmoChoiceRecurringDetailsProcessor` |
| Payment Hub auto card issuance | `phAutoCardProcessBatchjob` | `CardCreateService`, `PaymentHubAutoCardLoadProcessor` |
| Payment Hub check issuance | `phCheckIssuanceBatchjob` | `PaymentHubCheckIssuanceProcessor` |
| Card selection notification | `phCardSelectionNotificationBatchjob` | `PaymentHubCardSelectionNotificationWriter` |
| Check selection notification | `phCheckSelectionNotificationBatchjob` | `PaymentHubCheckSelectionNotificationWriter` |
| Reminder notification | `phReminderNotificationBatchJob` | `PaymentHubReminderNotificationMemberDetailsItemWriter` |
| Payment selection reminder | `psReminderNotificationBatchJob` | `PaymentSelectionReminderNotificationMemberDetailsItemWriter` |
| Balance sync (DDA refresh) | `BalanceSyncBatchjob` | `BalanceSyncProcessor` |
| Account status sync (FP queue) | `AccountStatusSyncBatchjob` | `AccountStatusMessageProcessor`, `AccountStatusRetrieverProcessor` |
| ECS daily auth posting | `ECSDailyAuthBatchjob` | `ECSDailyAuthPostingDAO` |
| ECS released auth posting | `ECSReleasedAuthBatchjob` | `ECSReleasedAuthPostingDAO` |
| ECS settlement posting (ATPT/ATGT) | `ECSSettlementPost` | `ECSSettlementPostingDAO` |
| Alto BACS direct load (PACS/ARUCS) | `altoBacsProcessLoadPaymentBatchjob` | `AltoBacsLoadPaymentsProcessor`, `AltoBacsEcountCoreServiceHelperImpl` |
| GPP Alto report (daily/weekly) | `GPPAltoReportDailyBatchjob`, `GPPAltoReportWeekBatchjob` | `GPPAltoReportProcessor` |
| IVR EP memo details load | `IVREPMemoDetailsLoadBatchjob` | `IVREPMemoDetailsProcessor`, `IVREPMemoDetailsLoadHelperImpl` |
| Encashment Paypoint settlement | `EncashmentPaypointSettlementBatchjob` | `EncashmentSettlementWriter`, `FileMovingTasklet` |
| Push-to-debit transaction import | `PushtodebitTransactionImportBatchjob` | `PushtodebitTransactionItemProcessor` |
| Push-to-debit transaction extract | `pushtodebittdExtractBatchJob`, `pushtodebittdFtbExtractBatchJob` | `PushToDebitTransactionExtractDaoImpl` |
| PayPal settlement file parsing | `PaypalSettlementFileBatchJob` | `PaypalSettlementReportProcessor`, `PaypalSettlementFileMultiResourceItemReader` |
| PayPal transaction detail extract | `paypaltdExtractBatchJob`, `paypalDrawdownTdExtractBatchJob` | `PaypalTransactionDetailsExtractDetailsRowMapper` |
| PayPal drawdown report | `paypalDrawdownReportDetailsBatchJob` | `PaypalDrawdownDetailsFileCreator` |
| Rewards posting | `RewardsPostingBatch` | `RewardsPostingHelper`, `CitiFundedRewardsPostingDAO` |
| Returned email processing | `ReturnedEmailBatch` | `MSExchangeEmailReaderDelegateImpl`, `EmailReaderCountProcessor` |
| Account data extract | `AccountDataBatchjob` | `AccountDataItemProcessor`, `RangePartitioner` |
| R05 embosser data | `R05EmbosserDataBatchjob` | `R05EmbosserDataProcessingDAO` |
| CBTS pending confirmation status | `cbtsPendingConfirmationStatusJob` | `CbtsPendingConfirmationStatusWriter` |
| Allowed domain list notification | `AllowedDomainListBatchJob` | `AllowedDomainDetailsSender` |

## Business Entities

- **Member**: Cardholder identity; referenced by `memberId` across all batch jobs. Maps to `com.cbase.business.core.value.Member`.
- **DDA (Demand Deposit Account)**: Prepaid account linked to a member (`AccountDefinitionDDA`). Used in balance sync, PayPal payout, and auto-claim.
- **ECard**: Physical/virtual card (`AccountDefinitionECard`). Created or loaded by Payment Hub auto card jobs.
- **AutoClaimTransactions** (`dto/autoclaimprocess/AutoClaimTransactions.java`): Disney Global Deposit record with `id`, `ddaNumber`, `amount`, `memberId`, `statusCode`, `resultMessage`.
- **ExpiredClaimVO** (`dto/claimexpirationprocess/ExpiredClaimVO.java`): Expired payment claim subject to reversal.
- **ExpiredClaimablePaymentVO** (`dto/claimablechoicecodeexpiration/ExpiredClaimablePaymentVO.java`): Claimable-choice payment expired via REST API call.
- **PayPalChoiceRecurringDetails** (`dto/paypalchoicedetails/PayPalChoiceRecurringDetails.java`): Members opted for recurring PayPal sweep.
- **VenmoChoiceRecurringDetails** (`dto/venmochoicedetails/VenmoChoiceRecurringDetails.java`): Members opted for recurring Venmo sweep.
- **PaymentHubAutoCardMember** (`domain/paymenthubautocard/common/PaymentHubAutoCardMember.java`): Member pending physical card issuance.
- **PushtodebitTransactionVo** (`dto/pushtodebittransactionimport/PushtodebitTransactionVo.java`): Push-to-debit (TabaPay) settlement record with 60+ fields including `last4`, `bin`, `PAR`, `MAC`, `OFAC` dates/codes.
- **AltoBacsPayment** (`dto/altobacsdirectload/AltoBacsPayment.java`): UK BACS payment record from PACS/ARUCS files.
- **BalanceSyncVO** (`dto/balancesyncprocess/BalanceSyncVO.java`): Device/member pair for balance refresh.
- **RewardsPaymentRecord** (`dto/rewardsposting/RewardsPaymentRecord.java`): Rewards disbursement to be loaded via ecount request file.
- **EmailMessageVO** (`dto/returnedemailprocess/EmailMessageVO.java`): Bounced email message with `notificationId`, `messageSubscriberId`, from/to addresses.
- **SettlementDetailRecord / SettlementHeaderRecord / SettlementFooterRecord**: Encashment paypoint settlement file components.

## Business Rules & Validations

- **Auto Claim (Disney)**: Requires `memberId`, `ddaNumber` (first 8 chars = programId), and `buyer_ecount_device` from affiliate table before calling PaymentServiceLibrary `createCertificate`. Missing any field throws and marks record FAILED (`AutoClaimProcessHelper`, lines 160–165).
- **PayPal Choice Payout**: Balance must be > 0 and transfer total < 2,000,000 cents ($20,000 USD) (`PayPalChoiceRecurringDetailsProcessor`, line 142). Zero-balance issuance flag `preventZeroBalanceIssuance` controls whether members with no balance are skipped (`CardCreateService`, line 124). Refund is automatically attempted if shared-service call returns `FAILED` batch status (line 208–228).
- **Claim Expiration Reversal**: Canadian programs (prefix `0601`) use `CA` locale; others use `US` (`ClaimExpirationReverseHelper.getCurrencyLocale`, line 110–119). Facility set to `order` (26) for API-flagged claims, `ecount-transfer` (0) for standard.
- **Push-to-Debit Import**: Validates date formats (`M/d/yy HH:mm` and `M/d/yy`), monetary fields within ±9,999,999.99999, all string fields ≤ 256 chars, and deduplication by `importFileId + referenceId` (`PushtodebitTransactionItemProcessor`).
- **Claimable Choice Expiration**: Calls external REST endpoint `POST /redeemDefaultExpiredClaimCode`. HTTP 200 = success; any other status throws, blocking the batch step (`ClaimableChoiceAPIClient`, line 78–87).
- **Balance Sync**: Parent/child group membership is checked via `GroupMemberInquiry`; parent DDA used if member is parent (`BalanceSyncProcessor`).
- **Infinite Loop Protection**: All partitioned jobs maintain previous/current execution counts in the Spring Batch `ExecutionContext` and abort if counts do not decrease between passes (see `PaymentHubAutoCardConstants.INFINITE_LOOP_EXIT_CODE = 13`, `BatchConstants.INFINITELOOP_EXIT_CODE = 2`).

## Business Flows

### PayPal Choice Recurring Sweep
1. SP `dbo.payout_transfer_details_fetch` reads members with PayPal option.
2. `PayPalChoiceRecurringDetailsProcessor.process()`: get DDA → get account balance → get PayPal payor details → calculate fee → debit ecount core via `transferManager.transferToPaypal()` → call external PayPal Shared Service → on failure, refund → send notification.

### Auto Claim (Disney Global Deposit)
1. SP `auto_claim_process_count_extract` counts pending records.
2. Partitioner distributes work; SP `auto_claim_process_extract_transaction` per partition.
3. `AutoClaimProcessHelper.processTransaction()` calls `PaymentServiceLibraryImpl.createCertificate()`.
4. `AutoClaimAchTransferDaoImpl.execute()` records the ACH transfer; SP `core_profile_global_deposit_file_update` updates status.

### Payment Hub Auto Card Issuance
1. Load step reads members pending card issuance.
2. `CardCreateService.issueCard()` checks for existing ecard; if absent, calls `DeviceManager.createECard()` and `deviceManager.issuePlastic()`.
3. `CardCreateService.enrollCardHolder()` creates user profile option `card/system_selection`.

### Claim Expiration Reversal
1. Count step finds expired claims; partitioned processing step calls `ClaimExpirationReverseHelper` to build `TransferDefinition` credit/debit transactions.
2. Status codes: 1700 = expired-reversed, 1800 = failed reversal, 1900 = failed claim.

## Compliance & Regulatory Concerns

- **NACHA / ACH**: Auto-claim creates ACH transfers via `AutoClaimAchTransferDaoImpl`. ACH routing is via `jobsvcDataSource`.
- **OFAC Screening**: `PushtodebitTransactionVo` carries `ofacDate`, `ofacCode`, `corrOfacDate`, `corrOfacCode` fields imported from TabaPay settlement files.
- **Reg E / Dispute**: Claim reversal activity `online-payment-deposit-cancel` and returned-email processing support dispute / error-resolution workflows.
- **PCI DSS**: `PushtodebitTransactionVo` stores card `last4`, `bin`, `PAR` (Payment Account Reference), `MAC`; CVV2 field is present in the VO. Settlement files are moved post-processing by `FileMovingTasklet`.
- **Canada locale**: Programs prefixed `0601` use CAD locale in `ClaimExpirationReverseHelper.getCurrencyLocale()`.
- **GDPR / CCPA**: `EmailMessageVO` captures cardholder email addresses, from/to, body content, and custom notification IDs — this PII is persisted to the notification service database.

## Business Risks

- **Disney Auto Claim hard-coded description**: `createCertificateInput.setDescription("Disney Global Deposit")` is hard-coded at `AutoClaimProcessHelper` line 202 — any non-Disney client using this batch would receive an incorrect description.
- **Thread.sleep(5000) in PayPal refund path**: `PayPalChoiceRecurringDetailsProcessor.handleRefundAmountFromPaypal()` (line 707) contains `Thread.sleep(5000)`, a blocking call inside an item processor thread. This can cause job hangs and degrades throughput under load.
- **Silent exception swallowing in AutoClaimProcessor**: The catch block at line 43 logs but returns the original `autoClaimTransactions` object without setting a failure status — the writer will process a record that failed processing as if it succeeded.
- **No dead-letter / retry for PayPal sweep**: If the PayPal shared service call fails and the refund also fails, the money is debited from the member's account with no automated recovery mechanism.
- **Email credentials in properties file**: `MSExchangeEmailReaderDelegateImpl` accepts `emailAccountPassword` as a Spring-injected string property — credentials are stored in plaintext properties files on disk at `D:\c-base\config\`.
