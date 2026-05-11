# cambridge-service_LIB — Business Analyst View

## Business Purpose

`cambridge-service_LIB` is a Java client library that integrates Onbe/Citi prepaid systems with the Cambridge FX (now Corpay Cross-Border) API platform. Its sole purpose is to enable cross-border foreign exchange (FX) wire payments on behalf of a prepaid program — covering authentication, beneficiary management, FX rate retrieval, deal booking, and payment instruction. The library is packaged as a JAR and is intended to be consumed by other internal services rather than deployed as a standalone application.

The package namespace `com.citi.prepaid` indicates this library was originally authored under Citi's prepaid program and subsequently adopted by Onbe.

---

## Business Capabilities

| Capability | Class | Description |
|---|---|---|
| SSO / Authentication | `SSOServiceImpl` | Generates a time-stamped, HMAC-signed security token required for all subsequent Cambridge API calls. |
| FX Rate Retrieval | `TradeServiceImpl.getRate()` | Requests a spot FX quote for a given currency pair and amount, returning a `quoteId`. |
| Forward Quote | `TradeServiceAPIStub` (op `getForwardQuote`) | Retrieves a forward FX rate (settlement on a future date). |
| Deal Booking | `TradeServiceImpl.bookDeal()` | Converts a quote into a booked FX deal, returning an order number. |
| Deal Cancellation | `TradeServiceImpl.cancelDeal()`, `getCancelRate()` | Unwinds a previously booked deal; a cancel-rate quote is obtained first. |
| Payment Instruction | `TradeServiceImpl.instructPayment()`, `instructPaymentSettlement()` | Associates a beneficiary and payment amount with a booked deal to initiate the wire. |
| Settlement Instruction | `TradeServiceAPIStub` (op `instructSettlement`) | Stub operation for settlement-only instructions. |
| Order Search | `TradeServiceAPIStub` (op `searchOrders`) | Queries historical orders. |
| Beneficiary Create/Update | `BeneficiaryServiceImpl.createOrUpdateBeneficiary()` | Creates or modifies a payment recipient including bank details, compliance classification, and address. |
| Beneficiary Lookup | `BeneficiaryServiceImpl.getBeneficiaryDetails()` | Retrieves full beneficiary record by ID. |
| Dynamic Validation Rules | `BeneficiaryServiceImpl.getDynamicValidationRules()` | Retrieves country/currency-specific field validation rules for beneficiary forms. |
| Bank Search | `BankServiceImpl.searchBanks()` | Searches Cambridge's bank directory by name and country. |
| Bank Detail Lookup | `BankServiceAPIStub` (op `getBankDetails`) | Retrieves detailed information for a specific bank. |
| Reg E Disclosure | `RegEDisclosureServiceAPIStub` (op `getRegEDisclosure`) | Retrieves Regulation E disclosure text (US-specific consumer funds transfer disclosure). |

---

## Business Entities

| Entity | Source Class/Package | Key Fields |
|---|---|---|
| Security Token | `SecurityToken` (`cambridge_service_integration_api`) | `token` (string session credential) |
| Beneficiary (core) | `BeneficiaryCore` (beneservice) | `beneficiaryId`, `beneficiaryName`, `currency`, `paymentMethods` |
| Beneficiary (complete) | `BeneficiaryComplete` extends `BeneficiaryCore` | Adds `bankDetails`, `compliance`, `contact`, `address`, `alerts`, `mailing`, `regulatoryFields` |
| Bank Account | `BankAccountInformation` extends `BankInformation` | `accountNumber`, `routingNumber`, `SWIFTBIC`, `institutionName`, `address` |
| Compliance | `BeneficiaryCompliance` | `classification` (`BeneficiaryClassification` enum: Individual/Corporate), `payPurpose` |
| Payment Methods | `PaymentMethods` (beneservice) | `acceptsEFTPayment`, `acceptsWirePayment` |
| Bank | `Bank` (`cambridge_service_integration_api_bankservice`) | `bankDetails.institutionName`, `bankDetails.address`, `branchName` |
| FX Rate Amount | `GetRateAmount` (tradeservice) | `amount` (BigDecimal), `lockSide` (`LockSide` enum), `paymentCurrency`, `settlementCurrency` |
| Quote | referenced via `quoteId` string | Returned by `getRate`; consumed by `bookDeal` |
| Order/Deal | referenced via `orderNumber`/`dealNumber` strings | Returned by `bookDeal`; consumed by `instructPayment` |
| Approval Status | `ApprovalStatus` enum (cambridge_logic_query_beneficiary) | Enum values for beneficiary approval state |
| Validation Rule | `ValidationRuleSpec` | `fieldName`, `validationRegex`, `valueRange`, `suggestedValues` |

---

## Business Rules & Validations

1. **Authentication signature**: `CambridgeServiceHelper.getDigitalSignature()` computes an HMAC-style hash over `sharedSecretKey | returnurl | <url> | username | <user> | timestamp | <ms>`. The `algorithm` is configurable (SHA-256 expected but not enforced in code). The timestamp is `System.currentTimeMillis()`.

2. **Token-first pattern**: Every service operation (`bookDeal`, `instructPayment`, `createOrUpdateBeneficiary`, etc.) wraps its arguments in a `SecurityToken` object using the token string obtained from `SSOServiceImpl.generateSecurityToken()`. No request proceeds without a valid token.

3. **Payment method enforced as WIRE**: In `TradeServiceImpl.instructPayment()` (line 226) and `instructPaymentSettlement()` (line 252), `request.setPaymentMethod(PaymentMethod.WIRE)` is hard-coded. EFT is not exercised via this code path.

4. **Dynamic validation rules**: `BeneficiaryServiceImpl.getDynamicValidationRules()` accepts `countryISO2` and `currency`, returning per-field regex, value ranges, and suggested values — indicating the library defers validation rule management to Cambridge rather than embedding them locally.

5. **Quote-then-book workflow**: `bookDeal` requires a `quoteId` obtained from `getRate`; it is not possible to skip the quote step.

6. **Correlation ID support**: `bookDeal` and `cancelDeal` accept an optional `correlationId` parameter (overloaded methods), which is forwarded to Cambridge for transaction tracing.

7. **Beneficiary classification**: The `BeneficiaryCompliance.classification` field uses the `BeneficiaryClassification` enum (values: `Individual`). The test code in `App.java` uses `Individual` (line 77) with `payPurpose = "Payroll"`.

---

## Business Flows

### Flow 1: FX Wire Payment (primary flow exercised in App.java)
1. `SSOServiceImpl.generateSecurityToken()` — authenticate, get token.
2. `BeneficiaryServiceImpl.getBeneficiaryDetails(token, beneficiaryId)` — verify recipient exists.
3. `TradeServiceImpl.getRate(token, amount, lockSide, payCurrency, settleCurrency)` — obtain FX quote ID.
4. `TradeServiceImpl.bookDeal(token, quoteId)` — lock the rate and get order/deal number.
5. `TradeServiceImpl.instructPayment(token, beneficiaryId, dealNumber, amount, paymentMethod)` — send payment instruction.

### Flow 2: Beneficiary Onboarding
1. Authenticate (SSO).
2. `getDynamicValidationRules(token, countryISO2, currency)` — get field constraints.
3. Populate `BeneficiaryComplete` with address, bank details (`BankAccountInformation`), compliance info, payment methods.
4. `createOrUpdateBeneficiary(token, beneficiary)` — upsert record.

### Flow 3: Deal Cancellation
1. Authenticate.
2. `getCancelRate(token, dealNumber)` — obtain cancellation quote.
3. `cancelDeal(token, cancelQuoteId)` — cancel the booked deal.

### Flow 4: Bank Search
1. Authenticate.
2. `searchBanks(token, searchStr, matchCriteria, countryISO2)` — find bank by name/address.
3. Inspect returned `Bank[]` for institution name, branch, and address.

---

## Compliance & Regulatory Concerns

- **Regulation E (Reg E)**: The presence of `RegEDisclosureServiceAPIStub` with operation `getRegEDisclosure` confirms this library touches US consumer funds transfer disclosures. Reg E requires written disclosures for international remittance transfers. The stub exists but no corresponding `RegEDisclosureServiceImpl` implementation class is present — the capability is stubbed but not fully wired up.

- **AML / KYC / Sanctions (OFAC)**: `BeneficiaryCompliance` holds classification and `payPurpose` fields. The library relies on Cambridge to perform AML/KYC checks on the beneficiary; there is no local sanctions screening logic in this library. Any OFAC exposure is delegated to the Cambridge platform.

- **NACHA / Wire**: Payment method is hard-coded to `WIRE` in `instructPayment`. Cross-border wire payments are subject to SWIFT/correspondent bank rules. The library does not handle NACHA ACH.

- **PCI DSS**: The library does not process card PANs. However, bank account numbers (`BankAccountInformation.accountNumber`) and routing numbers (`BankAccountInformation.routingNumber`) are transmitted in plain text in SOAP XML over TLS. These are sensitive financial credentials requiring access control and audit logging under PCI DSS scope for service providers.

- **GLBA / CCPA / GDPR**: Beneficiary data (name, address, bank account, routing number) is consumer financial information. Onbe, as a service provider, must apply GLBA and applicable privacy regulation safeguards. No data minimization or masking is implemented in this library.

---

## Business Risks

1. **Beta endpoint hardcoded in source code**: All stub default constructors point to `https://isbeta.cambridgefxonline.com/...` (e.g., `SSOServiceStub.java` line 135, `TradeServiceAPIStub.java` line 342). If a consuming service instantiates stubs without providing a production endpoint override, all calls will go to Cambridge's beta/sandbox environment. There is no environment-switching mechanism in the library itself.

2. **No Reg E implementation**: `RegEDisclosureServiceAPIStub` is the only Reg E artifact; there is no service implementation class. If Reg E disclosure is required before a payment is instructed, the obligation is not fulfilled by this library.

3. **Hardcoded beneficiary ID in test/demo code**: `App.java` and `BeneficiaryServiceImpl.createOrUpdateBeneficiary()` contain literal beneficiary IDs (`873f8ed7339e4178a3c0983f656cd38d`). This is demo/test code in the main source tree, posing risk of accidental use.

4. **Single payment method**: Wire is hard-coded. Business demand for EFT or other rails cannot be served without code change.

5. **No retry or error-handling framework**: All remote calls throw `java.rmi.RemoteException` which is caught and logged with `e.printStackTrace()` in `App.java`. There is no retry logic, circuit breaker, or alerting.

6. **Dependency on external vendor availability**: The entire cross-border payment capability depends on Cambridge FX uptime. No fallback rail exists in this library.
