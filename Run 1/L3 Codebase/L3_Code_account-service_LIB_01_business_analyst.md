# account-service_LIB — Business Analyst View

## Business Purpose

`account-service_LIB` is a shared Java library (Maven multi-module, artifact `accountservice` v4.0.33-SNAPSHOT under groupId `com.ecount.service`) that encapsulates the core account lifecycle operations for Onbe's prepaid card platform. It is consumed by other services (not deployed standalone) and provides the authoritative business logic for provisioning, funding, notification, and disbursement of prepaid accounts. The `_LIB` suffix indicates it is a library dependency, not a deployable service.

The library sits within the Gen-2 "ecount/prepaid" platform heritage, evidenced by package roots `com.ecount` and `com.citi.prepaid`, and by dependencies on the internal `xplatform`, `ecount-core-client`, `director-client`, `xsecurity`, and `debitapi` artifacts.

---

## Business Capabilities

The service exposes eleven operations defined in `IAccountService` (`account-common/src/main/java/com/ecount/account/service/IAccountService.java`):

| Operation | Method Signature | Business Meaning |
|---|---|---|
| Register User | `registerUser(RegisterUserInput, agent, affiliate)` | Create a new cardholder member and issue a DDA-type prepaid account. |
| Extended Register User | `extendedRegisterUser(ExtendedRegisterUserInput, …)` | Register with enriched profile fields (used for international/expanded demographics). |
| Update User | `updateUser(UpdateUserInput, …)` | Modify cardholder profile and associated account metadata. |
| Extended Update User | `extendedUpdateUser(ExtendedUpdateUserInput, …)` | Update with international or extended registration fields. |
| Issue Card | `issueCard(IssueCardInput, …)` | Issue a physical or virtual card (plastic or DDA device) to an existing member. |
| Add Funds | `addFunds(AddFundsInput, …)` | Load value onto a prepaid account via QuickLoad (direct), create a redeemable e-check certificate (indirect), or generate a claimable claim code (claimable-choice program). |
| Stop Payment | `stopPayment(StopPaymentInput, …)` | Reverse or cancel a previously issued disbursement; supports `STOP_REVERSED` (code 1) and `STOP_CANCELED` (code 2) modes (`StopPaymentModes.java`). |
| Send Notification | `sendNotification(SendNotificationInput, …)` | Trigger SMS or email notification for a cardholder event. |
| Set Location Code | `setLocationCode(SetLocationCodeInput, …)` | Assign a physical inventory/distribution location to an account or batch. |
| Set Inventory Location Attributes | `setInventoryLocationAttributes(…)` | Update attributes of a card inventory location node. |
| Withdraw | `withdraw(WithdrawInput, …)` | Debit/withdraw value from a prepaid account, including direct debit (withdraw type 3). |

---

## Business Entities

| Entity | Source Class(es) | Key Fields |
|---|---|---|
| Cardholder / Member | `RegisterUserInput`, `UpdateUserInput`, `ExtendedRegistration` | `partner_user_id` (PUID), `emember_id`, first/last name, address, email, phone |
| Prepaid Account / DDA | `IssueCardInput`, `AddFundsInput`, `WithdrawInput` | `dda_number`, `emember_id`, `access_level`, `plastic_only` |
| Transaction / Transfer | `AddFundsInput`, `WithdrawInput`, `ACHTransferDetail` | `tx_id` (UUID), `amount` (integer cents), `activity`, `description`, `settlement_date` |
| Program / Promotion | `AddFundsInput.program_id`, `RegisterUserInput.promotion_id`, `NotificationProgramPromotion` | 8-digit `program_id`, integer `promotion_id` |
| Stop Payment Record | `StopPaymentInput`, `ACHTransferDetail` | `reversal_tx_id`, `orig_transfer`, `stop_payment_code`, `settlement_date` |
| ACH Transfer Detail | `ACHTransferDetail` | `jobID`, `txID`, `recipientID`, `reverseTxID`, `stopPaymentCode`, `settlementDate`, `deviceID` |
| Claimable Payment | `CreateClaimablePayment`, `ClaimCodeIssuanceInfo`, `ClaimablePaymentAddenda` | `claim_code`, `amount`, `dda`, `expiration_date`, `claimable_payment_id` |
| SMS Queue Message | `SmsQueueMessage`, `SmsQueueDao` | `puid`, `program_id`, `mobile_phone`, `short_code`, `message_text`, `status` (PENDING), `scheduled_send_time` |
| Notification Config | `NotificationProgramPromotion`, `ProgramShortCodeMapping` | `program_id`, `promotion`, `enable`, `notification_validation`, `short_code` |
| Inventory Location | `SetLocationCodeInput`, `SetInventoryLocationAttributesInput` | `site_id`, `address1`, `city`, `state`, `postal`, `delivery_code` |
| Job Account Map | `JobAccountMapDetails` (via `JobAccountMapGet`) | `partner_id`, `affiliate_id`, `partner_user_id`, `emember_id` |

---

## Business Rules & Validations

Rules are enforced in `validate()` methods on input value objects and in `ValidationLibrary` / `EmailValidator`:

1. **PUID Scientific Notation Guard** (`ValidationLibrary.validatePartnerUserID`): Rejects any `partner_user_id` that appears to have been converted to scientific notation by Excel (e.g., `1.23E+15`). Returns `INVALID_PARTNER_USER_ID` (code 11).

2. **Transaction Amount** (`AddFundsInput.validate()`): `amount` must be positive (integer cents). Settlement date defaults to `now()` if null or in the past.

3. **Settlement Date** (`AddFundsInput`, `StopPaymentInput`): Settlement date is prevented from being in the past; always set to at least the current timestamp.

4. **Email Format** (`EmailValidator.isValid()`): Enforces RFC-like pattern `^(([a-zA-Z0-9_])…)@…`. Rejects the sentinel address `none@ecount.com` and the configured `commonReceiverEmailId`.

5. **Restricted Email Domain** (`ValidationLibrary.emailDomainValidation`, `AccountServiceContext.restrictedEmailSuffix`): Rejects registration if any email address ends with a domain in the configured blocklist (property `Restricted.email.domain`). Returns `INVALID_PARAMETER_FAILURE` (code 1) with message referencing `AccountServiceConstants.RESTRICTED_EMAIL_DOMAIN_ERR_MSG`.

6. **Address Required Fields** (`ValidationLibrary.validateExtendedRegistration`): Address1, City, State, Postal Code are required; validated against first/last name presence.

7. **DHL Delivery Code Block** (`ValidationLibrary.checkForDHLDeliveryCodes`): Blocks legacy DHL codes (007, 410, 411, 430, 450, 470, 902, 910, 911) from being submitted as delivery codes — DHL is decommissioned.

8. **Password Policy** (`ValidationLibrary.corePasswordValidation`): Minimum 8 characters, must contain both letters and digits.

9. **Direct/Claimable Routing** (`AddFundsInput.isDirect()`, `AddFunds.execute()`): If `direct_claim_flag` equals `DCF_CLAIM` (1), the payment service issues a redeemable certificate. If the program is a "claimable-choice" program (detected via `ProgramPaymentSelectionLibrary`), a claim code is generated via `CreateClaimablePayment` stored procedure.

10. **Enrollment Gate** (`AddFunds.execute()`): If a program has enrollment enabled and the member is un-enrolled, fund loading is blocked with code 1 and message "Transactions are not permitted against un-enrolled account."

11. **Card Block Codes**: `CardBlockCodes` maps codes to states; code `"1"` = active, `"3"` = frozen. (Legacy codes 2–10 are commented out in source.)

12. **Duplicate/Retry Handling** (`AddFunds.execute()`, syscode=3): When `syscode==3`, the service attempts to clean up a prior failed transaction by inquiring on, then committing or cancelling, the existing `tx_id`.

13. **SMS Opt-Out Check** (`SmsNotificationConfigDao.isSmsOptedOut()`): Before sending SMS, the system checks `NotificationSvc.dbo.sms_opt_out` for the short code + mobile phone combination.

14. **PUID Not-Specified Sanitisation** (`CrcpNotificationService.sanitizeRecipientId()`): Strips "NOT SPECIFIED " prefix from PUIDs stored in the DB for plastic-only recipients before forwarding to the CRCP notification orchestrator.

---

## Business Flows

### 1. Register & Fund Cardholder (Standard Path)
```
Caller → AccountServiceImpl.registerUser()
  → RegisterUserInput.validate()     (defaults country=US, phone=610-941-4600 if missing)
  → ValidationLibrary.validatePartnerUserID()
  → ValidationLibrary.emailDomainValidation()
  → MemberDelegate.addExtendedMember()   (creates ecount member record)
  → DeviceDelegate.create()              (issues DDA/ECard account)
  → DeviceDelegate.ecardInquiry()        (retrieves DDA number & IBAN)
  → AccountEventServiceLibrary.registerUserCompleteEvent()
  → returns RegisterUserOutput (ememberID, ecountID, ibanNumber, vExpressURL)
```

### 2. Add Funds — Direct (QuickLoad)
```
Caller → AccountServiceImpl.addFunds()
  → AddFundsInput.validate()
  → AddFunds.execute()
    → EnrollLibrary.isProgramEnrollmentEnabled() / isMemberUnEnrolled()
    → AGMLConfigLoader.loadTransactionStrategy()   (AGML/CBM limit config)
    → TransferDelegate.quickLoad(agent, tx [, transactionStrategy])
    → if blocked/over-limit → return code 14012/14155/14156
    → AccountEventServiceLibrary.addFundsCompleteEvent()
  → returns AddFundsOutput (txID, vExpressURL, completedEventID)
```

### 3. Add Funds — Claimable Choice
```
AddFunds.execute()
  → ProgramPaymentSelectionLibrary.checkClaimableChoiceProgram()
  → GetCliamablePaymentExpiryDate.execute()   (retrieves expiry config)
  → CreateClaimablePayment.execute()           (stored proc, EcountCoreDataSource)
  → ClaimCodeIssuanceInfoDao.insert()          (audit record)
  → ClaimablePaymentAddendaDao.insertAll()     (addenda linkage)
  → returns claim_code in AddFundsOutput
```

### 4. Stop Payment
```
Caller → AccountServiceImpl.stopPayment()
  → StopPaymentInput.validate()   (sets reversal_tx_id, settlement_date = payment_settlement_dt)
  → StopPayment.execute()         (invokes transfer/payment reversal via core)
```

### 5. Send Notification (SMS path)
```
Caller → AccountServiceImpl.sendNotification()
  → SendNotification.execute()
    → SmsProgramConfigurationHelper / SmsNotificationConfigDao → look up program enable, template, short code
    → isSmsOptedOut() check
    → if CRCP enabled (isCrcpNotificationEnabled): CrcpNotificationService.sendSmsNotification()
    → else: SmsQueueService.queueSmsMessage() → SmsQueueDao.insertQueueMessage() (status=PENDING)
    → else legacy: SmsNotificationService.sendSmsService()
```

---

## Compliance & Regulatory Concerns

1. **PCI DSS — Sensitive Authentication Data**: The codebase does not store, log, or transmit PANs, CVVs, or track data. `ACHTransferDetail` and payment objects carry only `dda_number` (a routing-style identifier, not a full PAN) and UUIDs. No PAN fields are observed in any value object.

2. **NACHA / Reg E — ACH Transfers**: `ACHTransferDetail` (`account-common`) carries `jobID`, `txID`, `recipientID`, `reverseTxID`, `stopPaymentCode`, `settlementDate`, `transferRefID` — these are the fields submitted to the ACH rail. The `StopPayment` operation with modes `STOP_REVERSED` and `STOP_CANCELED` implements NACHA return-code semantics.

3. **TCPA / CTIA — SMS Consent**: `SmsQueueService` appends a configurable `smsConsentSuffix` ("By giving this number, you consent to automated service messages. Msg and data rates may apply. Type HELP to get help or STOP to opt out.") to every SMS message text. An opt-out table (`sms_opt_out`) is checked prior to sending. This reflects TCPA compliance intent.

4. **GDPR / CCPA — PII in Logs**: `CrcpNotificationService` includes `sanitizeLog()` (strips CR/LF and ANSI sequences) and `maskSecretForLog()` (masks OAuth client secrets) before writing to logs. However, PUID and email addresses do appear in some debug-level log statements (`SmsNotificationService`, `AccountServiceDAOJDBCImpl`) without masking — a partial gap.

5. **OFAC / AML**: No OFAC screening logic is visible in this library. The library trusts that callers have already screened recipients; no sanctions list lookups are performed.

6. **Reg E — Error Codes**: Stop payment codes, reversal transaction IDs, and settlement dates are captured in `ACHTransferDetail` to support Reg E dispute and error resolution traceability.

7. **Tax Reporting**: `AddFundsInput.taxable` field and addenda code `STR_PPD_TAXABLE` ("101") propagate tax-reportability into the transaction addenda, enabling downstream 1099 reporting.

---

## Business Risks

1. **Hardcoded Fallback Phone Number**: `RegisterUserInput.validate()` line 89 sets phone to `"610-941-4600"` when no phone is provided. This may cause incorrect contact data on cardholder records and is a data quality risk.

2. **Silent Notification Failures**: `AccountServiceImpl` catches all exceptions around event dispatch (`accountContext.getAccountEventServiceLibrary()`) and logs but does not fail the transaction. A notification that silently fails will not retry without external monitoring.

3. **SMS Queue PENDING Without Worker**: `SmsQueueService.queueSmsMessage()` writes rows to `NotificationSvc.dbo.sms_notification_queue` with status PENDING. If no separate worker processes this queue, SMS messages are never delivered and pile up. No worker is visible in this library.

4. **PUID Scientific Notation Slip**: The scientific-notation check is a warning-only validation (returns `false` but the business logic in `AccountServiceImpl.registerUser` does not gate on it — it gates only on `INVALID_PARTNER_USER_ID` code 11). However the validation method only returns false for sci-notation — callers that do not handle this may accept invalid PUIDs.

5. **Claimable Choice Partial Failure**: If `ClaimCodeIssuanceInfoDao.insert()` fails after `CreateClaimablePayment` succeeds, a claim code is issued but the audit record is missing. The code catches this exception and logs a warning but returns success to the caller.

6. **No Idempotency for RegisterUser / IssueCard**: These operations do not perform duplicate detection before calling the member/device delegates. Repeated calls with the same PUID may create duplicate members in the core system.
