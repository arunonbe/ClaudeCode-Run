# core2-common_LIB — Business Analyst View

## Business Purpose

`core2-common_LIB` is a shared Java library (Maven artifact `com.ecount.service.Core2:common:2.0.0`) that defines the **contract layer** for Ecount's Core2 prepaid card and payment platform. It provides the canonical domain model, service interfaces, DTO (Data Transfer Object) definitions, and error codes used by all Core2 service implementations. It is not a deployable application; it is consumed by other Core2 services as a compile-time dependency. The "ecount" brand in package names (`com.ecount.Core2`) reflects the pre-Onbe company origin of the Gen-2 platform.

---

## Business Capabilities

The library defines contracts (Java interfaces) for four discrete business service domains:

| Service Interface | File | Business Domain |
|---|---|---|
| `IMemberService` | `service/IMemberService.java` | Member/cardholder lifecycle management |
| `IDeviceService` | `service/IDeviceService.java` | Payment device (card/account) lifecycle management |
| `IManageService` | `service/IManageService.java` | Check and PreCheck instrument management |
| `ITransfer` | `service/ITransfer.java` | Money movement / fund transfers |

### Member Management (`IMemberService`)
- Enroll new cardholders with basic (name + email) or extended (name + address + phone + email) registration.
- Universal registration that handles multi-address / multi-phone formats via `ExtendedUniversalRegistration`.
- Attach and update addenda (flexible key-value metadata, keyed to `fdr_profile_transaction_field_type` DB table).
- Attach/update a secure profile (SSN / `federal_id`, date of birth, driver's license, passport, military number, alien ID) stored separately ("strong box" / "director").
- Retrieve member profile at basic, extended, or secure-profile depth.
- Group member management (add/remove/search members within a named group with roles).
- Feature-set evaluation per member.
- Partner-user-ID (PUID) lookup for cross-system reconciliation.

### Device Management (`IDeviceService`)
- Create, inquire, update, and control (block/unblock) monetary devices: eCard, eCheck, CreditCard, ACH, DDA, Operator.
- Device catalog inquiry (list available device types for a member or group).
- DDA inquiry (demand deposit account).
- Extended addenda inquiry per device.
- Default device retrieval per device type.
- Secure profile update from within the device layer.

### Check / PreCheck Management (`IManageService`)
- Physical check ordering (`CheckOrderRequest` / `CheckOrderInquiry`).
- Stop payment request and inquiry.
- DDA available authorization inquiry.
- Program account inquiry.
- PreCheck full lifecycle: order, book inquiry, stop payment, addenda set, assign, authorize, merchant verify, definition inquiry, catalog inquiry, activity journal inquiry, activity definition inquiry, member inventory inquiry, and fee inquiry.
- Transaction review queue inquiry and update (`TxReviewQueueInquiry` / `TxReviewQueueUpdate` in eManage DTO package).

### Fund Transfers (`ITransfer`)
- Begin, Commit, Cancel a multi-leg fund transfer (with `TransferDefinition` + `TransactionDefinition[]`).
- Fee inquiry (`SimpleFeeInquiry`).
- Transfer status inquiry (`Inquiry`).

---

## Business Entities

| Entity | Class | Key Fields |
|---|---|---|
| Member | `value/Member.java` | `UUID id` |
| Account | `value/Account.java` | `UUID id`; base for all monetary devices |
| BasicRegistration | `value/BasicRegistration.java` | first/middle/last/suffix name; home/business/mobile email |
| ExtendedRegistration | `value/ExtendedRegistration.java` | + address, city, state, postal, country, phone (home/business/mobile) |
| SecureUserProfile | `value/SecureUserProfile.java` | `federal_id` (SSN), `date_of_birth`, driver's license, passport, military, alien ID |
| UserEnrollment | `value/UserEnrollment.java` | program, affiliate, agent, promotion, enrollment date |
| StoredValueCard | `value/StoredValueCard.java` | card number, expiry, activation_code, block_code, PIN selection code |
| StoredValueAccount | `value/StoredValueAccount.java` | DDA account number, block_code |
| BankAccount | `value/BankAccount.java` | routing_number, account_number, account_type |
| CreditCard | `value/CreditCard.java` | number, type, exp_month/year, cv_code |
| AccountDefinition | `value/AccountDefinition.java` | device_type, block_code, addenda, is_default, is_protected |
| AccountDefinitionECard | `value/AccountDefinitionECard.java` | card (StoredValueCard), dda (StoredValueAccount), bank/check (BankAccount) |
| AccountDefinitionDDA | `value/AccountDefinitionDDA.java` | dda, bank, check |
| AccountDefinitionACH | `value/AccountDefinitionACH.java` | bank, verification_code, verification_amount |
| AccountDefinitionCreditCard | `value/AccountDefinitionCreditCard.java` | card (CreditCard), billing (ExtendedRegistration), session |
| FDRCardAccountDetail | `value/FDRCardAccountDetail.java` | extends AccountDefinitionECard + billing |
| PreCheck | `value/PreCheck.java` | `UUID id` |
| PreCheckDefinition | `value/PreCheckDefinition.java` | check_account_number, serial_number, status, authorized_amount, authorization_code, fees, merchant_verified_code, addenda |
| Transfer | `value/Transfer.java` | `UUID id` |
| TransferDefinition | `value/TransferDefinition.java` | name, state, converged, activity, risk |
| Transaction | `value/Transaction.java` | `UUID id` |
| TransactionDefinition | `value/TransactionDefinition.java` | account, amount (Funds), fee (Funds), addenda, taxable, promotion |
| Funds | `value/Funds.java` | amount (int, cents), currency |
| CoreTransactionJournal | `value/CoreTransactionJournal.java` | id, created, transaction_state, ordinal, amount, fee, adjusted_amount, device_id, device_type |
| TxReviewQueueDetail | `value/TxReviewQueueDetail.java` | member, dda_number, transaction, amount, disposition, status, check_type, check_account_number |
| GroupMember | `value/GroupMember.java` | (group member aggregate) |
| MemberAddenda | `value/MemberAddenda.java` | HashMap<String,Object> keyed by addenda type codes |

---

## Business Rules & Validations

Evidence from source code:

1. **Credit Card Validation** (`CreditCard.java`, `validate()` method, lines 91–263):
   - Card must not be expired (validated against Calendar.getInstance()).
   - Card number length must be 13–16 digits depending on card type.
   - Card prefix must match declared type (Visa=4, MC=51–55, Amex=34/37, Discover=6011, DinersClub=36/38/300–305, etc.).
   - Internal Ecount BINs: Visa=448156, MasterCard=553772 (`enums/InternalCards.java`).
   - Luhn mod-10 checksum must pass (`CreditCard.java` lines 239–262).
   - CVC is permitted to be null/empty.

2. **SSN / federal_id Normalization** (`SecureUserProfile.java`, `validate()`, lines 46–67):
   - Non-digit characters stripped.
   - Truncated to last 10 digits if longer than 10.
   - Set to null if blank after stripping.

3. **Registration Defaults** (`BasicRegistration.validate()`, `ExtendedRegistration.validate()`):
   - Null fields for optional items (middle_name, suffix_name, email variants) coerced to empty string then back to null.
   - Country defaults to `CountryCodes.UnitedStates.code()` ("US") when absent.
   - State is set to empty string for non-US, non-CA countries (Canada validation present).

4. **Account Validation** (`Account.validate()`, line 47): `id` cannot be null — throws `BusinessObjectNotValidException`.

5. **AccountDefinition Validation** (`AccountDefinition.validate()`): Null addenda map normalized to empty HashMap, then to null if empty. Empty block_code set to null.

6. **Device Block Codes** (`enums/BlockCodes.java`): `active`, `closed`, `suspended`, `batch-initialized`, `batch-queued`.

7. **Activation Codes** (`enums/ActivationCodes.java`): `disabled-by-program`, `required-by-program`, `disabled-by-admin`, `required-by-admin`, `activated-by-customer`.

8. **Device Types** (`enums/DeviceTypes.java`): `eCard`, `eCheck`, `CreditCard`, `Operator`, `DDA`, `ACH`.

9. **Error Codes** (`enums/Exceptions.java`): 40+ typed error constants including `InsufficientFundsFailure` (11), `AccountAccessBlocked` (12), `OverDepositLimit` (16), `OverWithdrawLimit` (17), `AccountAlreadyExists` (137), `InvalidRegistrationSSN` (112), `InvalidRegistrationDateOfBirth` (113), class ID = 14.

10. **ECS Debit Service Errors** (`exceptions/ECSDebitServiceExceptions.java`): JMS communication error (34001), JMS receive error (34002), invalid ECS MLI request (34011), ECS MLI response error (34012) — indicates JMS messaging integration with an external ECS debit processor.

---

## Business Flows

### Cardholder Enrollment (Basic)
1. Caller populates `AddBasicXMLRPCInput` with agent, affiliate, `BasicRegistration`.
2. `IMemberService.AddBasic(agent, affiliate, registration, addenda)` is invoked.
3. Output is `AddBasicOutput` (extends `OutputBase`) containing `Member` (UUID) and `Result` (code + message).

### Cardholder Enrollment with PII (Extended)
1. Caller populates `ExtendedRegistration` (address, phone, etc.) and optionally a `SecureUserProfile` (SSN, DOB, etc.).
2. `IMemberService.AddExtended(agent, affiliate, registration, addenda, secure_profile)` invoked.
3. Secure profile is written to a separate "strong box" service; member is returned via `AddExtendedOutput`.

### Card Creation
1. `IDeviceService.Create(agent, member, accountDefinition, options, batch_process)` called.
2. `AccountDefinitionECard` carries `StoredValueCard` (number, block_code, activation_code) and `StoredValueAccount` (DDA number).
3. Returns `CreateOutput` containing created account reference.

### Fund Transfer (Begin/Commit)
1. `ITransfer.Begin(agent, BeginInput{member, TransferDefinition, TransactionDefinition[]})` — initiates multi-leg transfer.
2. Each `TransactionDefinition` carries source/destination `AccountDefinition`, `Funds` amount, addenda.
3. On success, `BeginOutput` returns a `Transfer` UUID.
4. `ITransfer.Commit(agent, CommitInput)` — finalizes the transfer.
5. `ITransfer.Cancel(agent, CancelInput)` — aborts if needed.

### PreCheck Authorization Flow
1. `PreCheckOrderRequest` — orders a PreCheck instrument for a member.
2. `PreCheckAssign` — assigns check serial to a member account.
3. `PreCheckAuthorize` — authorizes a presented check amount.
4. `PreCheckMerchantVerify` — merchant verification step.
5. `CheckStopPaymentRequest` — stop payment if required.

---

## Compliance & Regulatory Concerns

- **PCI DSS**: `CreditCard` class stores `cv_code` (CVV/CVC) and full PAN (`number`) in plain Java fields. There is no evidence of truncation, masking, or tokenization within the library itself. The library is a DTO/interface definition; actual masking must be enforced by the consuming service at persistence or logging boundaries. The `InternalCards` class hardcodes two internal BIN prefixes (448156 for Visa, 553772 for MasterCard).
- **GLBA / Privacy**: `SecureUserProfile` holds SSN (`federal_id`), date of birth, driver's license, passport, military and alien identification numbers as plain Strings. The Javadoc comment on `IMemberService.AddExtended` references storage in "strong box" (a separate secure vault) for the secure profile, but this is a convention that is not enforced at the library level.
- **Reg E**: The `ITransfer` interface supports Begin/Commit/Cancel semantics and transaction reversals consistent with Reg E error-resolution requirements. The `IManageService.CheckStopPaymentRequest` supports stop-payment rights.
- **NACHA**: The `ACH` device type is present (`DeviceTypes.ACH`), and `AccountDefinitionACH` includes `verification_code` and `verification_amount` fields consistent with micro-deposit verification under NACHA rules.
- **OFAC / AML**: No OFAC screening or AML logic is present in this library. Screening must be implemented upstream.
- **Addenda / Audit**: A recurring `addenda: Map<String,Object>` pattern on member, account, and transaction objects provides a generic extensibility mechanism for compliance metadata, but no schema enforcement is present in the library.

---

## Business Risks

1. **PII in plain Java objects**: `SecureUserProfile` fields (SSN, DOB, passport, driver's license) are public Strings with getters/setters. If logging frameworks (e.g., toString(), JSON serialization) serialize these objects, PII will be exposed in logs. No `@JsonIgnore` or masking annotations are observed.
2. **No input length constraints**: Registration fields (name, address, phone, email) have no maximum-length annotations or validation beyond null-coercion. Upstream services must enforce length limits to prevent database truncation errors.
3. **Addenda schema is un-typed**: All addenda fields are `Map<String,Object>`. Business rules for which addenda codes are valid are externalised to a DB table (`fdr_profile_transaction_field_type`) not visible in this library. Changes to valid codes require no recompile but are invisible to the library consumer.
4. **Monetary amounts as `int`**: `Funds.amount`, `CoreTransactionJournal.amount`, `AccountBalance.ledger/pending/available` are all Java `int` (32-bit signed). Values are likely in cents. Max representable value is ~$21.4M. If multi-currency or large-value disbursements approach this threshold, silent overflow is a risk.
5. **Check instrument flows**: The PreCheck lifecycle (`PreCheckDefinition`) carries authorization codes, stop fees, misuse fees, and return fees. Unauthorized changes to `admin_override_code` or `authorization_code` could enable fraud.
