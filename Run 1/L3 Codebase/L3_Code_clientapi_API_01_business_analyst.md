# clientapi_API — Business Analyst View

## Business Purpose

clientapi_API is a B2B SOAP web service that allows corporate clients (program sponsors, financial institutions) to perform real-time card account management operations against the Onbe (formerly Wirecard/eCount) prepaid card platform. It serves as the external-facing integration gateway for clients who need to fund prepaid cards, update cardholder registration data, close accounts, and query request status. The service underpins Onbe's instant-issue prepaid disbursement capabilities (healthcare, insurance, rebates, gig payouts, etc.).

The production `memberId` in `app-config/prod/appsettings.json` is `53FECB63-3CBC-485A-8DA6-221DBEC04C28`, confirming this is a live payment gateway service.

## Business Capabilities

1. **Add Funds (Load)** — Credits monetary value (in cents, USD) to an existing prepaid card account. Validates against minimum/maximum load limits and load-count limits. (`AddFundsService`, `clientapi-impl/.../service/AddFundsService.java`)

2. **Update Registration** — Updates cardholder PII (name, address, SSN, date of birth, email, phone numbers) associated with a card account. Supports both domestic (NA) and international cardholders; international routing is determined at runtime by querying a Redis-backed program-setup flag. (`UpdateRegistrationService`)

3. **Update Account Status** — Closes a prepaid card account. The only accepted status value is `CLOSED` (enforced in `ClientApiWebServiceHandlerImpl` at line 158 and `v4` handler at line 166). (`UpdateAccountStatusService`)

4. **Get Request Status** — Queries the processing status of a previously submitted request by transaction ID, returning PROCESSED_SUCCESSFULLY (0), PROCESSING (2), or PROCESSING_FAILED (1). Also returns ACH/DFI routing data on success for NA region. (`GetRequestStatusService`)

5. **Get Request Status and DFI** — Identical to Get Request Status but also always returns DFI account number, routing number, and account type for ACH disbursement. (`GetRequestStatusAndDFIService`)

6. **Service Availability Check** — Lightweight ping/health endpoint (`/hc`) to confirm service is running.

## Business Entities

| Entity | Key Fields | Source |
|---|---|---|
| **Prepaid Card Account** | `package_id` (card identifier, alphanumeric 1-16), `program_id` (8-digit numeric), `promotion_id` (1-4 digit) | `ServiceInput.java`, `validationNA.xml` |
| **Cardholder Registration** | first_name, last_name, middle_name, address (1-4 lines), city, state_province, postal, country, home/business/mobile phone, email, SSN (9-digit), date_of_birth (YYYYMMDD format) | `UpdateRegistrationInput.java` |
| **Transaction** | `transaction_id` (1-40 alphanumeric), amount (cents, long integer), comment, reference_1 through reference_4 (addenda/memo fields) | `AddFundsInput.java`, `ServiceInput.java` |
| **ACH/DFI Details** | dfi_account_number (DFI prefix + ecountId suffix), routing_number (`011001234` NA), account_type (`C` checking) | `clientapi.yml` (dfiNA=553, routingNA=011001234, typeNA=C) |
| **Security Entity** | API name (`InstantIssue`), method names, program_id; used for per-program access control | `APISecurityValidatorConfiguration.java`, `clientapi.yml` |
| **International Country** | 2-digit country code, validated against Redis `intlCountries/{code}` endpoint | `InternationalFlagService.java` |

## Business Rules & Validations

**Input Validation (enforced by `Validator` / `validationNA.xml`, `validationEMEA.xml`):**
- `package_id`: required, alphanumeric, 1-16 chars
- `program_id`: required, exactly 8 digits
- `transaction_id`: required, 1-40 alphanumeric (NA); extended Unicode character set for EMEA
- `amount`: required, >= 0 (NA); 0–2,147,483,647 (EMEA)
- SSN: optional, exactly 9 digits (formatted as XXX-XX-XXXX for processing via `formatSsn()` in `ClientApiServiceImpl.java`)
- Date of birth: optional, exactly 8 digits (YYYYMMDD), parsed in `getDateOfBirth()` method
- Home phone: required (3 parts); business/mobile phones: optional
- Address 3 and Address 4 fields are explicitly prohibited for NA region (throws `ADDRESS_3_NOT_SUPPORTED` / `ADDRESS_4_NOT_SUPPORTED` in handler)
- Email max length: 50 characters (NA validator `emailValidatorNA`)

**Business Logic Rules:**
- `CLOSED` is the only valid status value for `updateAccountStatus` (hardcoded check in handlers)
- Duplicate requests: if `isRequestAlreadyFound()` is true from OrderService, a `DUPLICATE_REQUEST` exception is thrown; `PACKAGE_ID_AND_TRANSACTION_ID_MISMATCH` is remapped to `DUPLICATE_REQUEST` in the handler
- Remote JMS timeout (detected by message prefix `REMOTE-JMS-TIMEOUT` or `SocketTimeoutException`): returns PROCESSING status (not failure), to prevent false negatives
- International routing: V4 handler checks Redis-backed `intlProgram` flag for the program before applying domestic vs international validators
- Per-program security: `ClientApiServiceImpl.validateAPISecurity()` calls `SecurityValidator.authorize()` against a cached entity model; access denied throws `ACCESS_DENIED` business exception

**Response Codes:**
- 0 = PROCESSED_SUCCESSFULLY
- 1 = PROCESSING_FAILED
- 2 = PROCESSING (includes timeout scenarios)

## Business Flows

**Add Funds Flow:**
1. Client sends SOAP `addFunds` request with package_id, program_id, transaction_id, amount
2. Handler validates all fields via regional `Validator`
3. `AddFundsService.execute()` calls `validateAPISecurity()` to check program authorization
4. Submits `ProcessInstantIssueRequest` (with `AddFundsAction`) to `SynchronousOrderProcessor` via HTTP invoker
5. Response maps OrderManager result to PROCESSED_SUCCESSFULLY / PROCESSING / PROCESSING_FAILED
6. Duplicate detection via `isRequestAlreadyFound()` flag in response

**Update Registration Flow:**
1. Client sends SOAP request with full cardholder PII
2. Handler validates fields; rejects address_3/address_4 for NA
3. `UpdateRegistrationService.execute()` checks `InternationalFlagService` (Redis call) to determine routing
4. Builds `UpdateUserRegistrationAction` + optional `ActionSecureMemo` (for SSN/DOB) + `UpdateInventoryAction`
5. Submits to OrderService; on success, returns ACH/DFI numbers (NA only)

**Close Account Flow:**
1. Client sends `updateAccountStatus` with status=CLOSED
2. Handler enforces `CLOSED` as the only valid value
3. `UpdateAccountStatusService` submits `UpdateAccountStatusAction` + addenda memo to OrderService

**Get Status Flow:**
1. Client sends `getRequestStatus` / `getRequestStatusAndDFI` with transaction reference
2. Service calls `SynchronousOrderProcessor.getInstantIssueStatus()`
3. Returns PROCESSED/PROCESSING/FAILED; on success for NA, returns DFI account number (DFI prefix 553 + ecountId suffix)

## Compliance & Regulatory Concerns

- **SSN handling**: SSN is transmitted in clear text in the SOAP request body (`UpdateRegistrationInput.ssn`). It is formatted and stored inside a `SecureUserProfile.toXML()` blob via `ActionSecureMemo`. There is no evidence of SSN masking or encryption at the API layer. This is a PCI/GLBA concern for PII in transit.
- **Date of Birth**: Transmitted and processed in plain text (YYYYMMDD string format) through the SOAP request. PII field without explicit encryption.
- **SOAP over HTTPS**: The production `app-config/prod/appsettings.json` uses HTTPS endpoints (`https://prod.nam.wirecard.sys:8080`), indicating transport-level encryption, but the SOAP payload itself carries raw PII.
- **IP/Certificate-based access control**: `APISecurityValidatorConfiguration` configures IP address, IP range, and certificate-based entity identification (`JdbcAccessEntityIPAddressDao`, `JdbcAccessEntityIPRangeDao`, `JdbcAccessEntityCertificateDao`). This controls which clients can call which API methods per program.
- **Reg E relevance**: `updateAccountStatus` with CLOSED status terminates a payment instrument; duplicate-request detection provides idempotency for financial operations.
- **NACHA/ACH**: The service returns ACH routing and DFI account numbers (routing `011001234`, account type `C`) for NA region after successful registration, establishing the ACH disbursement instrument.
- **No PAN in scope**: The service uses `package_id` (card package identifier) not a full PAN, reducing PCI CDE scope for this service.

## Business Risks

1. **SSN and DOB in SOAP payload**: PII fields traverse the service in clear text within the XML envelope. If transport security fails or logs capture request/response bodies, sensitive personal data would be exposed.
2. **Hardcoded ACH routing numbers**: NA routing number (`011001234`) and DFI prefix (`553`) are in source config (`clientapi.yml`). These must be environment-specific and any misconfiguration would produce invalid ACH data returned to clients.
3. **TEST MODE capability**: `TestAPI` bean (`ClientApiImplConfiguration.java`, `ClientApiServiceImpl.java`) allows deliberate delays, simulated failures, and simulated timeouts. If this mode is accidentally enabled in production, real payment operations would be disrupted.
4. **Duplicate request remapping**: `PACKAGE_ID_AND_TRANSACTION_ID_MISMATCH` is silently reclassified as `DUPLICATE_REQUEST` in the handlers (lines 90-93 in `ClientApiWebServiceHandlerImpl`), potentially hiding data integrity issues from clients.
5. **EMEA validator lacks SSN check**: The `validatorEMEA` configuration (`validationEMEA.xml`) does not include an SSN field validator, meaning SSN validation is NA-only.
6. **Address 3/4 silently accepted but blocked late**: V1-V3 handlers accept address_3/address_4 through XML parsing but then throw `InputValidationException` after parsing; V4 only blocks these for NA region, allowing them for EMEA.
