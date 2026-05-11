# consumerload_API — Business Analyst View

## Business Purpose

consumerload_API is a SOAP/JAX-RPC web service that provides prepaid cardholders (consumers) with the ability to load funds onto their prepaid eCards using a credit card (CC) or ACH/direct deposit, and to manage the identity-verification (KYC) information required to enable those loads. The service is owned by the Citi Prepaid division (package namespace `com.citi.prepaid.consumerload`) and sits between a partner-facing channel and the underlying card-management platform (eCore/cbase). At Onbe/Ecount this service enables the "consumer self-load" rail for prepaid programs where cardholders top up their own balance using a source-of-funds instrument.

## Business Capabilities

| Operation | Entry Point | Description |
|---|---|---|
| Load funds via credit card | `loadFundsUsingCC` | Initiates a real-money transfer from a credit card to the cardholder's eCard. Applies velocity/limit/fee rules. |
| Get CC load fee | `getCCLoadFee` | Returns the transaction fee for a hypothetical CC load of a given amount for a given program. |
| Get ACH direct-deposit info | `getACHInfo` | Returns the virtual bank account number and routing number for ACH/direct-deposit loads, plus min/max limits. |
| Update KYC information | `updateKYCInfo` | Updates the cardholder's PII (name, address, phone, DOB, SSN) in the member profile and optionally triggers a KYC check. |
| Check KYC status | `checkKYCStatus` | Returns the current KYC status (Pass / Pending / Fail / KYC_HAS_NOT_BEEN_RUN) for a cardholder. |
| Get default credit card | `getDefaultCreditCard` | Returns the masked card number (last 4 digits unmasked), card type, and expiry for the cardholder's stored default credit card. |

## Business Entities

- **Partner / Program**: Callers identify themselves via `partner_user_id` (alphanumeric, 1–40 chars, regex `[A-Za-z0-9-]{1,40}`) and `program_id` (8-digit numeric string). These are required on every call.
- **Cardholder / Member**: Resolved internally from `partner_user_id` + `program_id` via `AccountHelper.getMemberId()` → `GetPuid` DB lookup. Represented as `com.cbase.business.core.value.Member`.
- **eCard**: The prepaid card device (virtual card identifier) to which funds are credited, retrieved via `DeviceManagerImpl.getDefaultEcard()`.
- **Credit Card**: Source-of-funds instrument. Domain class `CreditCard` (cardNumber, cardType, expMonth, expYear) + `CCBillingInfo` (billing address).
- **KYC Information**: Split into `BasicKYCInfo` (name, address, phone) and `SecureKYCInfo` (DOB, SSN). Stored in `ExtendedUniversalRegistration` and `SecureUserProfile` respectively.
- **Bank Account**: ACH virtual account returned as `BankAccount` (accountNumber, routingNumber) from `DeviceManager.getDirectDepositBankAccount()`.
- **Fee**: Calculated via `Fee.getTxFeeAmount()` using fee type `"cc-load"` (constant in `CLConstants.CC_LOAD_FeeType`).
- **Transaction Strategy**: Velocity and max-balance rules read from `AppProfileProgramStrategy` — max daily amount, max monthly amount, max balance.

## Business Rules & Validations

### Common (all operations)
- `partner_user_id`: required, must match `[A-Za-z0-9-]{1,40}` (`partnerUserIdValidator` in `validator.xml`).
- `program_id`: required, must match `[0-9]{8}` — exactly 8 digits (`programIdValidator`).
- Member must exist; if not found, `ServiceFailureException(MEMBER_NOT_FOUND)` is thrown.
- Member's default eCard must be in block-code state `"active"`; otherwise `ACCOUNT_NOT_ACTIVE`.

### loadFundsUsingCC-specific
- `amount`: required, minimum value 0 (`amountValidator`), unit is cents (long).
- `cvv`: required, must match `[0-9][0-9][0-9]` — exactly 3 digits (`cvvValidator`).
- If a new credit card is supplied: cardNumber `[0-9]{1,16}`, cardType `[a-zA-Z][a-zA-Z '.-]{0,10}`, expMonth `[0-1][0-9]`, expYear `[2][0][1-9][1-9]` (validator.xml lines 108–113 — note year range hard-coded to 2011–2199).
- If billing info is supplied: firstName/lastName `[a-zA-Z][a-zA-Z '.-]{0,50}`, address1/2 `[a-z A-Z0-9'.-//#]{0,50}`, city, state (2 letters), postal (5–6 alphanumeric), country (2 letters).
- Credit card Luhn validity checked by `CreditCardValidator` (`ValidationHelper.validateCreditCard()`).
- Card expiry validated: expYear >= current year; if equal, expMonth >= current month.
- If KYC is enabled for the program (`ProfileHelper.isKYCEnabled()`), the KYC status must be `"Pass"` (`handleKYC()` in `ConsumerLoadService`).
- Amount must be between `AppProfileProgramMembership.recurring_limit_min_cc` and `recurring_limit_max_cc`; violation throws `FAILED_TO_LOAD_FUNDS_THRESHOLD`.
- If no default credit card exists and none is supplied in the request, `MISSING_CREDIT_CARD_INFORMATION`.
- Transaction strategies (daily/monthly velocity, max balance) enforced by the core transfer engine (`TransferManagerImpl.addFundsCreditCardToECard()`).
- Optional `transactionId` passed as `partner-payment-id` addendum on the transfer.

### updateKYCInfo-specific
- `KYCInfo`, `BasicKYCInfo`, and `SecureKYCInfo` are all required (null check in `ValidationHelper`, line 107–111).
- DOB format: 8-char string `MMDDYYYY`, validated by `BirthDateValidator`.
- SSN format: 9-digit numeric string (`ssnValidator`), but SSN Luhn validation (`validateSSN`) is commented out in `ValidationHelper` line 159.
- Flag `checkKYC` (boolean, from `UpdateKYCInfoRequest.isCheckKYC()`) controls whether a KYC check is triggered after profile update.
- KYC result must not be null or `"Unknown"` after the check; otherwise `FAILED_TO_CHECK_KYC`.

### getACHInfo / checkKYCStatus
- Both check KYC status if KYC is enabled for the program (same `handleKYC()` guard as loadFundsUsingCC).

## Business Flows

### CC Load Flow
1. Validate request fields (partner_user_id, program_id, cvv, amount, card fields).
2. Validate credit card Luhn + expiry.
3. Resolve internal memberId via PUID database lookup.
4. Check account is active.
5. If KYC-enabled program: verify KYC status is "Pass".
6. Check load amount against program min/max CC limits.
7. Retrieve or create the stored credit card record.
8. Get default eCard ID.
9. Retrieve transaction strategies (velocity, max balance).
10. Calculate CC load fee.
11. Execute `transferManager.addFundsCreditCardToECard()`.
12. Write auto-comment to audit trail (`CommentHelper.autoComment()`).
13. Return success/failure response.

### KYC Update Flow
1. Validate common fields + KYC block presence.
2. Resolve member.
3. Check account is active.
4. Update `ExtendedUniversalRegistration` (name, address, phone) via `MemberManager.UpdateUniversalRegistration()`.
5. Update `SecureUserProfile` (DOB, SSN) via `MemberManager.UpdateSecureProfile()`.
6. If `checkKYC == true`: invoke `AccountHelper.doKYCCheck()` → `MemberManager.doKYCCheck()`.
7. Return success/failure.

## Compliance & Regulatory Concerns

- **KYC / Identity Verification**: The service collects and stores SSN and DOB through `SecureKYCInfo` and `SecureUserProfile`. This directly implicates the Bank Secrecy Act (BSA), FinCEN CIP rules, and GLBA safeguards. The `doKYCCheck()` call triggers the downstream ID-verification engine.
- **PCI DSS**: Full credit card numbers (PAN) and CVV are accepted in SOAP request payloads. The `LoadFundsUsingCCRequest.cvv` and `CreditCard.cardNumber` fields carry SAD/PAN in-flight. There is no evidence in the code of transport-layer TLS enforcement at the application layer; security depends entirely on the network/server configuration. The `GetDefaultCreditCardService.maskThefirst12NumbersCC()` method masks all but the last 4 digits when returning the card number — this is correct behavior for display.
- **Reg E**: The fund-load transaction is a consumer-initiated electronic fund transfer; error resolution and reversal capabilities are expected but not visible in this service.
- **OFAC / Sanctions**: No OFAC screening evidence in any service class; this obligation must be satisfied by a downstream system or the KYC engine.
- **NACHA**: The `getACHInfo` operation returns real account and routing numbers for ACH-pull capability. These numbers in transit or in logs would be a sensitive data exposure risk.
- **GLBA / CCPA**: SSN, DOB, full name, and address are collected and transmitted. Data minimization and access control obligations apply.

## Business Risks

1. **SSN validation commented out** (`ValidationHelper` line 159): `validateSSN()` is defined but never called. Invalid SSNs can be submitted to the KYC engine, potentially generating false KYC passes or compliance errors.
2. **Year validator hard-coded to 2011–2199** (`expYearValidator` regex `[2][0][1-9][1-9]`): Will incorrectly reject cards expiring in 2020–2029 (only years 2011–2019 and 2021–2099 etc. pass, depending on interpretation). This is a known functional defect.
3. **Credit card numbers in logs**: `ConsumerLoadWebServiceImpl.print()` uses XStream to serialize the full request object including PAN and CVV to the log at DEBUG level (lines 30, 59, 87, 120, 167). In a debug-enabled environment this exposes SAD.
4. **No authentication or authorization**: There is no evidence of any caller authentication (username/password, certificates, OAuth tokens) on the SOAP service layer. Any client that can reach the endpoint can invoke any operation.
5. **KYC bypass possible for non-KYC-enabled programs**: If `isKYCEnabled()` returns false (including on exception — the catch block returns false silently), the KYC gate is skipped entirely, allowing loads for members who may never have been identity-verified.
