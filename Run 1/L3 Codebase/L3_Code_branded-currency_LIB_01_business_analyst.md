# branded-currency_LIB — Business Analyst View

## Business Purpose

`branded-currency_LIB` is a shared Java library (Maven multi-module, version 3.0.3) that encapsulates the core business logic for Onbe's **Branded Currency** (gift certificate / eGift card) product. It is consumed by upstream web application and service tiers rather than deployed as a standalone service. The library enables clients to:

- Issue branded digital gift certificates (echecks / ecards) from a buyer to a recipient.
- Allow recipients to redeem (claim) those certificates against prepaid card (ecard), bank (DDA), or interbank transfer (IEFT) instruments.
- Load funds to an ecard via credit card (add-funds flow).
- Execute bulk/third-party certificate issuances.
- Enforce velocity and dollar-amount constraints per user and per service.
- Schedule and manage email notifications for certificate lifecycle events.

The library operates against the `cbaseapp` SQL Server database (the legacy "CBase" platform) and delegates actual money movement to the internal `ECountCore / MoneyTransferHelper` API (xplatform).

---

## Business Capabilities

| Capability | Key Classes |
|---|---|
| Certificate issuance (single) | `CertificatePurchaseTransactionImpl`, `CreateCertificateSpringImpl` → `dbo.create_certificate` |
| Certificate issuance (bulk/B2B) | `BulkPurchaseTransactionImpl` (extends `CertificatePurchaseTransactionImpl`, uses `EcountActivityCode.THIRD_PARTY_PAYMENT`) |
| Certificate redemption (claim) | `ClaimTransactionImpl`, `ClaimPaymentSpringImpl` → `dbo.claim_payment` |
| Add funds via credit card | `AddFundsTransactionImpl`, uses `addSourceCreditCard()` |
| Certificate lookup | `CertificateImpl.init()` / `GetCertificateDetailSpringImpl` → `dbo.get_op_certificate_detail_new` |
| IVR certificate lookup | `GetCertificateDetailIVRSpringImpl` → separate stored procedure |
| User unclaimed/claimed payment lists | `GetUnclaimedPaymentsSpringImpl` → `dbo.get_op_unclaimed_payments`; `GetClaimedPaymentsSpringImpl` → `dbo.get_op_claimed_payments` |
| Payment history audit trail | `CreatePaymentHistorySpringImpl` → `dbo.create_payment_action_item` |
| Velocity / permission checking | `VelocityImpl`, `CheckServicePermissionSpringImpl` → `dbo.check_service_permissions` |
| Payment constraint checking | `PaymentConstraintImpl`, `CheckPaymentConstraintsSpringImpl` → `dbo.check_claim_payment_constraints` |
| User-to-device binding | `UpdateUserEcountIdSpringImpl` → `dbo.update_user_ecount_id` |
| User group management | `SetUserGroupSpringImpl`, `GetUserGroupsSpringImpl` |
| Email scheduling | `EmailScheduleImpl`, `EmailScheduleSpringImpl` → `dbo.enotify_get_schedule_numbers_by_type` |
| Virtual-card stop-notification on claim | `StopNotificationClaimedCodeImpl`, `GetEventHandlerIdForCertificateId` → `StopNotificationService` |
| Reissued payment tracking | `CreateReissuedPaymentReferenceSpringImpl`, `reissuingPaymentId` in `CertificatePurchaseTransactionVO` |
| Certificate template management | `GetCertificateTemplatesSpringImpl`, `GetTemplateDetailSpringImpl` |

---

## Business Entities

### PaymentVO (`branded-currency-common/.../purchase/payment/PaymentVO.java`)
Root value object for all payment types. Key fields:
- `paymentId`, `amount` (integer, US pennies implied), `echeckId` (echeck GUID), `verificationCode` (claim/redemption code), `buyerId`, `recipientId`, `recipientEmail`, `recipientFirstName`, `recipientLastName`, `activationDate`, `expirationDate`, `createdDate`, `lastAction`, `paymentType`, `claimTransferId`, `apiFlag`.

**Action lifecycle codes** (inner class `PaymentVO.Action`):
- 100 CREATED, 200 NOTIFICATION_EMAIL_SENT, 300 CLAIMED, 400 CANCELED_BY_BUYER, 500 LOCKED_BY_ADMINISTRATOR, 600 DENIED_BY_RECIPIENT, 1000 FROZEN_BY_FRAUD_SYSTEM, 1100 ACCEPTED_BY_FRAUD_DEPT, 1200 REJECTED_BY_FRAUD_DEPT, 1300 HELD_FOR_REVIEW, 1400 IN_REVIEW_BY_CSR, 1500 REISSUED, 50 QUEUED_FOR_RELEASE, 99 RELEASED.

**Payment types** (inner class `PaymentVO.Type`): 0 PERSON_TO_PERSON, 1 APF_BULK, 2 CERTIFICATE, 3 BULK_CERTIFICATE.

### CertificateVO (`...purchase/certificate/CertificateVO.java`)
Extends `PaymentVO`. Adds: `certificateId`, `templateId`, `senderName`, `recipientName`, `cardHtml`, `thumbnailSubjectName`, `subject`, `description`, `isSpinGame`, `affiliateId`.

**CertificateVO.ActionData** constants: `CERTIFICATE_LOCKED`, `CERTIFICATE_UNLOCKED`, `CERTIFICATE_RELEASED`.

### BasketCertificateVO (`...purchase/certificate/BasketCertificateVO.java`)
Extends `CertificateVO`. Adds `basketId` (string) and `fee`.

### CertificateTemplate (`...purchase/certificate/CertificateTemplate.java`)
Extends `PaymentVO`. Holds `certificateTemplateId`, `description`.

### UserTransactionVO (`...transaction/UserTransactionVO.java`)
Represents a pending money movement. Holds `userId`, `memberId`, `ipAddress`, `amount`, `fee`, `serviceType`, `ecountProgramId`, `ecountTransferId`, `ecountActivityCode`, device maps.

**Service types** (inner interface `UserTransactionVO.Type`): 100 ADD_FUNDS, 200 CANCEL_ECHECK, 300 CREATE_ECHECK, 400 WITHDRAWAL_TO_CCARD, 700 CASH_ECHECK, 1100 ADD_FUNDS_WITH_ACH, 1200 PURCHASE_CERTIFICATE, 1300 REGIVE_CERTIFICATE.

**Device types**: ECHECK(1), ECARD(2), CREDIT_CARD(3), DDA(4), PAPER_CHECK(5), ACH(6), IEFT(7).

### CreditCardVO (`...transaction/CreditCardVO.java`)
Stores card number (full), name, month, year, CV code, type. Contains `last4Digits()` helper.

### ConstraintVO (`...transaction/ConstraintVO.java`)
Serializable. Fields: `serviceId`, `serviceDesc`, `minValue`, `maxValue`, `unitOfMeasure`, `unitOfMeasureDesc`, `constraintId`, `hasConstraints`.

### VelocityVO (`...transaction/velocity/VelocityVO.java`)
Unit-of-measure constants: US_PENNIES_PER_CERTIFICATE(500), ..._PER_DAY(2000), ..._PER_MONTH(3000), TRANSACTIONS_PER_DAY(10000), etc.

### UserGroup (`...user/UserGroup.java`)
`groupId`, `groupDescription` — drives velocity group assignments.

### Address (`...common/business/user/Address.java`)
Street1/2, city, state, zipCode, country.

---

## Business Rules & Validations

Evidence sourced directly from code:

1. **Certificate active check** (`PaymentVO.isActive()`, line 182): If `expirationDate` is before today, the certificate is considered expired (returns `false`).
2. **Future-date activation** (`PaymentVO.isFutureDate()`, line 201): If `activationDate` is after today, certificate is deferred; returns 1.
3. **Age check** (`PaymentVO.isGreaterThanMonthOld()`, line 159): Checks if `createdDate` is more than one month old using `GregorianCalendar.roll(MONTH, false)`.
4. **Fraud hold / strategic delay** (`PaymentVO.activateStrategicDelay()`, line 197): Sets `lastAction = 1000 (FROZEN_BY_FRAUD_SYSTEM)`.
5. **Velocity check gate** (`UserTransactionImpl.checkVelocity()`, lines 138–169): Calls `dbo.check_service_permissions`. Return code -1 or 6200 = permission failure; -2 = no velocities found; positive integer = failed velocity constraint; 0 = passed.
6. **Payment constraint pre-claim check** (`PaymentConstraintImpl.getFailedConstraints()`): Calls `dbo.check_claim_payment_constraints`. Return codes 0 = no constraints, 9901 = no such payment.
7. **Claim idempotency / transfer reconciliation** (`ClaimTransactionImpl.execute()`, lines 326–391): If an `ecountTransferId` already exists on the payment, the system performs an inquiry via `TransferManagerImpl.inquiry()` and either commits a pending transfer or cancels and re-initiates based on state/converge flags.
8. **Transfer ID mismatch guard** (`ClaimTransactionImpl.execute()`, line 330–334): If the client's provided `transferId` does not match the stored one, the transaction is rejected with stat code -100.
9. **Reissued payment chain** (`CertificatePurchaseTransactionImpl.postProcess()`): After creating a certificate, calls `dbo.update_create_certificate_info` and `createReissuedPaymentReference` to maintain payment lineage.
10. **Stop notification on claim** (Virtual Card Enhancement, `ClaimTransactionImpl.postProcess()`, line 158–176): On successful claim, retrieves event handler IDs for the certificate and issues `StopNotificationService` calls to cancel pending email notifications.

---

## Business Flows

### Flow 1: Certificate Purchase
1. Caller constructs `CertificatePurchaseTransactionVO` with buyer info, `BasketCertificateVO`, recipient memberId.
2. `CertificatePurchaseTransactionImpl.init()` sets service type = 1200 (PURCHASE_CERTIFICATE), activity code = `online-payment`.
3. `preProcess()` → `dbo.create_user_transaction_history_item` (creates transaction record).
4. `createDestinationEcheck()` → adds echeck device to `MoneyTransferHelper`.
5. `execute()` → `MoneyTransferHelper.transferBegin()` + `transferCommit()` (money movement via ECountCore).
6. `createTransactionDevices()` → records echeck device, then `dbo.create_certificate` (creates payment + certificate rows, returns `payment_id`, `certificate_id`, `claim_code`).
7. `postProcess()` → `dbo.update_transaction_status2` + `dbo.update_create_certificate_info` + `dbo.create_reissued_payment_reference`.

### Flow 2: Certificate Claim
1. Caller constructs `ClaimTransactionVO` with user, verification code, destination device choice.
2. `ClaimTransactionImpl.init()` loads context; `addSourcePayment()` attaches echeck as debit device.
3. Destination set via `setDestinationEcard()` / `setDestinationDDA()` / `setDestinationIEFT()`.
4. `execute(description, transferId)` → `preProcess()` → `dbo.create_user_transaction_history_item`.
5. Optional `checkVelocity()` → `dbo.check_service_permissions`.
6. Transfer ID management (idempotency check if pre-existing transferId).
7. `MoneyTransferHelper.transferBegin()` + `transferCommit()`.
8. `createTransactionDevices()`.
9. `postProcess()` → `claim()` → `dbo.claim_payment`; if new ecard: `dbo.update_user_ecount_id`; stop-notification for virtual card.
10. `dbo.update_transaction_status2`.

### Flow 3: Add Funds (Credit Card Load)
1. `AddFundsTransactionImpl.init()` + `setFundingSource(ExtendedRegistration)` → `addSourceCreditCard()` with full card details.
2. `setDestinationEcard()` → `addDefaultDestinationEcard()`.
3. `execute()` → standard begin/commit cycle.

---

## Compliance & Regulatory Concerns

1. **PCI DSS – Full PAN in memory**: `CreditCardVO` stores `_number` (full card number) and `_cvCode` (CVV/CVC) as unmasked `String` fields. The `getNumber()` method returns the full PAN. No masking, encryption, or tokenization is applied at the VO layer. This is a direct PCI DSS Req. 3 exposure if objects are logged, serialized, or transmitted.
2. **PCI DSS – CVV in object**: `CreditCardVO.getCVCode()` exposes the full CV code. PCI DSS Req. 3.3 prohibits storage of SAD after authorization.
3. **Hardcoded test credentials in committed context file**: `brandedCurrencyTestContext.xml` (line 27–33) contains a live SQL Server URL (`ppamwdcdifsql1.nam.nsroot.net:2232/cbaseapp`) with username `b2ctest` and password `b2ctest` in plaintext. This is also present in commented-out form for `ecsqldev1`. This violates PCI DSS Req. 8 and constitutes a secret-in-code finding.
4. **Reg E / consumer protection**: Payment lifecycle codes (FROZEN_BY_FRAUD_SYSTEM, HELD_FOR_REVIEW, LOCKED_BY_ADMINISTRATOR) suggest fraud-hold workflows; no evidence of consumer dispute resolution logic within this library.
5. **GDPR/CCPA**: Recipient PII (firstName, lastName, email) is stored in `CertificateVO` and passed through to `dbo.get_op_certificate_detail_new` and related stored procedures. No data minimization or anonymization logic is present in this library.
6. **Deprecated Java date API**: `PaymentVO.isGreaterThanMonthOld()` (line 161–162) calls `Date.getDate()`, `Date.getMonth()`, and `Date.getYear()` — all deprecated since Java 1.1. These are unreliable and could cause subtle date-math errors around DST or leap years.

---

## Business Risks

1. **No input validation layer**: The library accepts `verificationCode`, `memberId`, `ipAddress`, and amounts directly from callers without sanitization. SQL injection risk is mitigated by parameterized stored procedure calls but not by the library itself.
2. **Singleton DAO factory with global state** (`BrandedCurrencyDAOFactory.getInstance()`): The singleton holds a single `BrandedCurrencyDAO` reference. In multi-tenant or multi-context deployments, this could result in incorrect datasource binding.
3. **Unchecked raw types throughout**: `Map`, `Dictionary`, `Hashtable` (non-generic) are used pervasively. Type-cast errors at runtime would produce unchecked `ClassCastException`.
4. **No transactional rollback coordination**: The ECountCore `transferBegin/transferCommit` and `cbaseapp` stored procedure calls are not wrapped in a single distributed transaction. A failure between `transferCommit` and `dbo.claim_payment` would leave the money moved but the payment status unclaimed.
5. **Silent exception swallowing in post-process**: `ClaimTransactionImpl.execute()` (lines 401–419) catches all exceptions in the post-process block and logs but does not re-throw, meaning a failed `claim_payment` call may not be surfaced to the caller.
6. **Virtual card stop-notification errors are non-fatal**: `ClaimTransactionImpl.postProcess()` (lines 171–174) catches all exceptions from `stopNotification()` and only logs them, so notification cancellation failures are silent.
