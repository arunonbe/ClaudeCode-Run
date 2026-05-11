# cbts-client_LIB — Business Analyst View

## Business Purpose

`cbts-client_LIB` is a Java client library (JAR) that provides a typed, HTTP-based façade for the **Cross-Border Transfer Service (CBTS)**, which is itself a client for **Cambridge Global Payments** (a foreign-exchange and international wire provider). The library abstracts all REST calls to CBTS behind a single class, `CBTSClient`, and is intended to be embedded in Onbe/Wirecard legacy prepaid applications — specifically the **OP (Online Portal)** and **batch processing** systems — to enable **global disbursements** (international wire and EFT payouts) from prepaid card programs.

The Javadoc comment in `CBTSClient.java` (line 43–46) confirms:
> "Legacy Prepaid applications currently are using DFAPI for global deposit and will be migrated to CBTSClient for global deposit."

## Business Capabilities

| Capability | Client Method | HTTP Verb | Endpoint |
|---|---|---|---|
| Create / update a remitter (sender) | `createUpdateRemitter` | PUT | `/remitters` |
| Retrieve remitter by ID | `getRemitterbyID` | GET | `/remitters/{id}` |
| Deactivate a remitter | `deactivateRemitter` | POST | `/remitters/{id}/deactivate` |
| Create / update a beneficiary (recipient) | `createUpdateBeneficary` | PUT | `/beneficiaries` |
| Retrieve beneficiary by ID | `getBeneficiarybyID` | GET | `/beneficiaries/{id}` |
| Deactivate a beneficiary | `deactiveBeneficary` | POST | `/beneficiaries/{id}/deactivate` |
| Look up beneficiary rules (per country/currency/method) | `getBeneRules` | GET | `/beneficiaries/beneficiary-rules` |
| Search beneficiary banks | `searchBanks` | GET | `/beneficiaries/search-beneficiary-banks` |
| Validate an IBAN | `validateIban` | POST | `/beneficiaries/ibanvalidation` |
| Request a new FX rate | `getnewRate` | POST | `/rates` |
| Retrieve rate by ID | `getRatebyID` | GET | `/rates/{id}` |
| Book (commit) a rate | `bookRatebyID` | POST | `/rates/{id}/book` |
| Cancel a rate | `cancelRatebyID` | POST | `/rates/{id}/cancel` |
| Update rate status directly | `updateRateStatus` | POST | `/rates/{id}/status` |
| Create an international transfer | `createTransfer` | POST | `/transfers` |
| Retrieve a transfer by ID | `getTransferbyID` | GET | `/transfers/{id}` |
| Look up an existing order | `lookupOrder` | GET | `/orders/{id}?brand={brand}` |
| Check if an order exists (with payments) | `isOrderExists` | GET | `/orders/{id}?brand={brand}` |

## Business Entities

| Entity | Java Class | Key Attributes |
|---|---|---|
| Remitter | `Remitter.java` | `remitterId`, `firstName`, `lastName`, `address`, `accountIdentifier`, `brand`, `enabled`, `firstNameRecurring`, `lastNameRecurring`, `recurringRemitterAddr` |
| Beneficiary | `Beneficiary.java` | `beneficiaryId`, `remitterId`, `firstName`, `lastName`, `address`, `phoneNumber`, `email`, `bankCurrency`, `paymentMethod`, `swiftBicCode`, `bankName`, `bankAddress`, `accountNumber`, `routingCode`, `regulatory` |
| Beneficiary Bank | `BeneficiaryBank.java` | `institutionName`, `swiftBIC`, `nationalBankCode`, `nationalBankCodeType`, `officeType`, `branchName` |
| Beneficiary Rule | `BeneficiaryRule.java` | `id`, `validationRegEx`, `isRequired`, `suggestedErrorMessage`, `suggestedLabel`, `possibleValues` |
| FX Rate | `Rate.java` | `rateId`, `value`, `amount`, `payersCurrency`, `beneficiariesCurrency`, `requestType`, `status`, `brand`, `remitterId`, `indicative`, `paymentAmount`, `bookingId` |
| Transfer | `Transfer.java` | `transferId`, `rateId`, `beneficiaryId` |
| Order | `Order.java` | `orderNumber`, `entryDate`, `buyCurrency`, `buyAmount`, `sellCurrency`, `sellAmount`, `exchange`, `ourAction` |
| Payment | `Payment.java` | `paymentInstructionId`, `feeAmount` |
| Address | `Address.java` | `addressLine1–3`, `city`, `province`, `countryCode`, `postalCode` |

## Business Rules & Validations

All validation is enforced server-side by the CBTS service; the client library propagates errors as `CBTSBusinessException`. The following rules are evidenced in the tests (`CBTSClientTest.java`):

1. **Remitter first name must not be blank** — error 400, `INVALID_REQUEST_DATA`, message contains "firstName must not be blank" (line 196).
2. **Remitter last name must not be blank** — error 400, `INVALID_REQUEST_DATA` (line 207).
3. **Remitter address line 1 must not be blank** — error 400, `INVALID_REQUEST_DATA`, message contains "address.addressLine1 must not be blank" (line 220).
4. **Remitter must exist before a beneficiary can be created** — error 404, `UNKNOWN_DATA_ITEM`, "Could not find Remitter" (line 327).
5. **Rate must be in BOOKED state before a Transfer can be submitted** — implied by the transfer flow in `tranferTest()`.
6. **Rate expiry** — a `NEW` rate that is not booked within approximately 3 minutes transitions to `EXPIRED`; attempting to book it returns error 400, `EXPIRED_RATE` (`CBTSRateExpiredTest.java`, line 114).
7. **Rate cancellation state** — a `NEW` rate cannot be cancelled; only `BOOKED` rates can be cancelled; attempting to cancel twice returns 400, `INVALID_REQUEST_DATA` (lines 487–508).
8. **Duplicate transfer prevention** — re-submitting the same `transferId` returns 400, "Duplicate transfer" (line 580).
9. **Indicative rates are ephemeral** — rates created with `indicative=true` are not persisted; `getRatebyID` returns 404 (lines 451–457).
10. **Recurring remitter name truncation** — names longer than 100 characters are split into `firstNameRecurring` (first 100 chars) and `lastNameRecurring` (remainder); names longer than 200 are truncated to 200 before splitting (`CBTSClient.java`, lines 160–167).
11. **Order existence check** — `isOrderExists` returns false if `orderNumber` is null/empty; returns true only if the order response contains a non-empty `payments` list (`CBTSClient.java`, lines 538–553).
12. **Beneficiary regulatory data** — `Beneficiary` carries a `Map<String, String> regulatory` field to hold country-specific regulatory key-value pairs.

## Business Flows

### International Payout (Full Lifecycle)
```
1. Create/Update Remitter  → obtain remitterID
2. Create/Update Beneficiary (linked to remitterID)  → obtain beneficiaryID
3. Request FX Rate (amount, source currency, target currency, ONE_TIME or RECURRING)  → obtain rateID, status=NEW
4. Book Rate (rateID)  → status=BOOKED
5. Create Transfer (transferID, rateID, beneficiaryID)  → payment instructed at Cambridge
6. (Optional) Get Transfer status / Get Rate status
7. (Optional) Cancel Rate if transfer is not yet executed
```

### Beneficiary Bank Lookup (for IBAN-based payments)
```
1. Search Banks by country + query string  → list of BeneficiaryBank entries
2. Validate IBAN  → IbanValidationResponse (isValid, bankName, swiftBIC, accountNumber, routingNumber)
3. Retrieve BeneficiaryRules by country/currency/paymentMethod  → validation regex and required fields
```

### Order Lookup (idempotency / duplicate check)
```
1. isOrderExists(orderNumber, brand)  → lookupOrder  → check orderDetail + payments list
2. If order exists with payments: skip re-submission; otherwise proceed with payout
```

## Compliance & Regulatory Concerns

- **International wire transfers (SWIFT/SEPA)** are inherently subject to **OFAC sanctions screening**, **AML/CTF** controls, and **Reg E** disclosure requirements. The library passes through `regulatory` metadata (a `Map<String, String>` on `Beneficiary`) to the CBTS service; however, sanctions screening and AML logic are fully delegated to the CBTS/Cambridge layer with no client-side enforcement visible in this library.
- **IBAN validation** (`validateIban`) provides a compliance touch-point for European bank account verification but does not enforce it as a mandatory pre-check.
- **FX rate expiry** (3-minute window observed in tests) creates a business constraint: a rate must be booked promptly to avoid `EXPIRED_RATE` failures and potential re-pricing exposure for the cardholder.
- **Remitter/Beneficiary PII**: first name, last name, physical address, phone number, email, and bank account number are transmitted in plain JSON over TLS to the CBTS service. No field-level encryption or masking is applied by this library.
- The `brand` / `program_id` field links transactions to specific prepaid programs, supporting per-program compliance reporting.
- **GDPR/CCPA**: The library logs beneficiary data (including name and bank details) via SLF4J at `INFO` level (`CBTSClient.java`, line 249), which is a potential PII leakage risk in log aggregation systems.

## Business Risks

1. **Hardcoded credentials in source code** — `CBTSClient.java` lines 94–95 contain a literal `USERNAME` and `PASSWORD` (production-looking strings), duplicated verbatim in `CBTSClientTest.java` lines 62–63. These represent a credential exposure risk if the repository is accessible.
2. **No client-side OFAC/sanctions validation** — the library sends beneficiary data to Cambridge without any pre-screen, relying entirely on the CBTS service to reject sanctioned entities.
3. **FX rate expiry business risk** — if the booking step is delayed (e.g., slow batch processing), the rate expires and the payout fails, requiring a retry cycle.
4. **Indicative rate not persisted** — using `indicative=true` is explicitly not retrievable after creation; callers must track the rate data themselves.
5. **Duplicate transfer handling is partially silent** — `createTransfer` suppresses the "Could not find Transfer" 400 error and returns the original ID without exception (`CBTSClient.java`, lines 419–421), which could mask downstream processing failures.
6. **PII in application logs** — beneficiary full name, bank account, and routing number appear in log output at INFO level.
