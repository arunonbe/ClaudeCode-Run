# contact-center-agent-api — Business Analyst View

## Business Purpose

`contact-center-agent-api` is a Spring Boot REST service that acts as the backend for a contact-center / AI chat-bot ("Decagon") integration. It allows contact-center agents (and the AI Decagon chat widget) to perform cardholder servicing operations on behalf of customers — without giving those agents direct access to the core prepaid processing systems (ECount Core / cbaseapp). The service is Onbe's controlled intermediary between an external AI-agent platform and internal payment processing infrastructure.

The servers listed in `openapi.yml` (`https://decagonapi.onbe.com`) confirm the live caller is the Decagon conversational AI platform.

---

## Business Capabilities

| Capability | OpenAPI operationId | HTTP Method / Path |
|---|---|---|
| Account Inquiry (balance, card, transactions, program) | `getAccountDetails` | GET `/v1/account-inquiry` |
| Submit cardholder comment / escalation | `postCommentEscalation` | POST `/v1/comments` |
| Retrieve comment history | `getComments` | GET `/v1/comments` |
| User Lookup (pre-authentication) | `lookupUser` | POST `/user-auth/lookup` |
| Send OTP to cardholder | `sendOtp` | POST `/user-auth/send-otp` |
| Verify OTP and issue JWT | `verifyOtp` | POST `/user-auth/verify-otp` |
| Reissue card (lost/stolen/revoked) | `reIssueCard` | POST `/v1/account/reissue` |
| Update cardholder registration | `registerAccount` | PUT `/v1/account/registration` |
| Withdraw funds / issue paper check | `checkWithdraw` | POST `/v1/account/withdraw` |
| Reset PIN attempt counter | `pinReset` | POST `/v1/account/pin-reset` |

---

## Business Entities

| Entity | Source | Key Attributes |
|---|---|---|
| **Account / DDA** | ECount Core REST + ECount DB | `ddaNumber` (16-digit), `deviceId`, `ownerId` (GUID memberId) |
| **Card** | ECount Core REST | masked `cardNumber` (format `5115XXXXXXXX5304`), `blockCode`, `expiration`, `activationStatus` |
| **Member / Cardholder** | ECount Core REST | `memberId`, `firstName`, `lastName`, `emailAddress`, `mobilePhone`, `address` |
| **Transaction** | ECount Core REST (`InquiryDetail.journal`) | `transactionDate`, `transactionType`, `amount` (cents), `fee` (cents), `addenda` |
| **Affiliate / Program** | cbaseapp DB (`b2c_csa_detailscreen_general`, `partnerdetail`) | `affiliateId` (8-digit prefix of DDA), `programDescription`, `programCurrency`, `programReissuance` |
| **Service Record / Comment** | cbaseapp DB (`service_records`) | `inquiryIdNumber`, `problemDescription`, `inquiryType`, `responseType`, `closed`, `ddaNumber` |
| **API Request Audit Log** | cbaseapp DB (`api_request_audit_log`) | `requestUrl`, `requestHeaders`, `requestBody`, `clientIp`, `responseStatus` |
| **OTP Session** | OTP shared-service (external) | `sessionId` (UUID), `deliveryChannel` (EMAIL/SMS) |
| **JWT Token** | Generated in-service | `memberId`, `ddaNumber` claims, HS256 signed, 20-minute default expiry |

---

## Business Rules & Validations

### Authentication Priority (AuthenticationFilter.java, lines 56-87)
1. **JWT token** (header `token`) — validated and decoded for `memberId` + `ddaNumber`.
2. **Encrypted DDA** (header `encryptedDDA` + header `channel=CHAT`) — AES/GCM decrypted to obtain account number.
3. **Plain account number** (header `accountNumber`) — must match regex `[0-9]{16}`.

Failure to authenticate returns HTTP 403 (not 401 — a notable deviation from the OpenAPI spec which declares 401).

### User Lookup Parameter Combinations (UserLookupParameterValidator.java)
Valid search combinations (any one suffices):
- `firstName` + `lastName`
- `address` + `city` + `state` + `postalCode`
- `address` + `postalCode` + `firstName` + `lastName`
- `email` (standalone)
- `userName` (standalone)
- `phone` (standalone)

Ambiguous multi-match resolution: if `cardLastFour` is provided, results are narrowed by that value before raising `TooManyUsersException`.

### Account Number Structure
- 16-digit DDA: first 8 digits = affiliate/program ID (e.g., `04016113`).
- Affiliate ID parsing: `product = (id/1000000)%100`, `brand = (id/10000)%100`, `affiliate = id%10000` (`DataConversionUtils.parseProgramId`).

### Reissue Block Codes (openapi.yml, BlockCode schema)
Valid values: `lost`, `stole`, `revoked`.

### Withdraw / Check Issuance Business Rule (WithdrawFundsService.java, line 58)
- Before executing, checks the affiliate's `paper_check_flag` = `"Y"` in the `cbaseapp` partner detail table.
- If not enabled, throws `ProgramConfigurationException("Program does not allow Check Issuance")` → 400.
- Uses a two-phase begin/commit transfer against ECount Core operator device `E45B78C8-D73E-46F4-A24B-0014E7A9E9D7`.

### PIN Reset Rule (PinResetService.java, lines 75-98)
- Configured `maxAttempts = 3` (prod/qa `appsettings.json`).
- If `pin_tries >= maxAttempts`: calls `pin-tries-reset` control method, inserts a comment (inquiryType=112, responseType=21, closed=1), returns `PIN_RESET`.
- If `pin_tries < maxAttempts`: skips reset, returns `PIN_RESET_SKIP` with current attempt count.

### Comment Service Defaults (application.yml, prod appsettings.json)
- `employeeId = "CSA-AI-Agent"`, `applicationId = 12`, `inquiryTypeId = 175` (prod), `daysToFetchComments = 14`.

### OTP Disable List
- Configurable per-email and per-phone-number allow-list in `application.yml` under `api.settings.user-authentication.otp-disabled`. Test value: `none@ecount.com` and phone `6109414600`.

### Email Validation on Registration (RegistrationRequestValidator.java)
- Max 50 characters per email field.
- Restricted country-code TLDs (configurable via `api.apiValidation.restrictedEmailSuffix`; default: `.cu,.ir,.kp,.sy,.ua`).

### Transaction Max Limit (AccountInquiryService.java, lines 54-60)
- Default: 50 (prod), configurable via `api.settings.account-inquiry.default-max-transactions`.
- Hard cap: 100 (prod), configurable via `api.settings.account-inquiry.max-transactions`.

---

## Business Flows

### Authentication Flow (Decagon → Cardholder)
1. Decagon calls `POST /user-auth/lookup` with cardholder PII (name, address, email, etc.).
2. API validates parameter combination, searches ECount Core member inquiry, deduplicates results.
3. Returns masked email (`j***e@domain.com`) and masked phone (`*****4567`) plus `userId` (memberId UUID).
4. Decagon calls `POST /user-auth/send-otp` with `userId` + `otpChoice` (EMAIL or MOBILE).
5. API fetches member contact details from ECount Core, validates OTP-disable rules, calls OTP shared service.
6. Returns `sessionId`.
7. Decagon calls `POST /user-auth/verify-otp` with `sessionId` + `otp` + `userId`.
8. API validates OTP, retrieves default DDA from ECount Core, generates and returns a signed JWT (`token`).
9. Subsequent calls use JWT in the `token` header.

### Account Inquiry Flow
1. Request arrives with `token` (JWT) or `encryptedDDA`+`channel=CHAT` or raw `accountNumber`.
2. Filter decodes to `accountNumber`.
3. `AccountInquiryService` calls ECount Core `/device/dda/{dda}` → gets `deviceId` + `ownerId`.
4. Calls `/device/inquiry/{deviceId}` for balance, journal (transactions), card definition.
5. Queries ECount DB (`CoreCardAccountEmbossHistory`) for ship date.
6. Queries cbaseapp (`b2c_csa_detailscreen_general`, `partnerdetail`) for program metadata.
7. Queries ECount DB (`app_profile_promotion_label`) for program currency.
8. Calls ECount Core `/member/basic/{memberId}` for cardholder name/email.
9. Assembles and returns `AccountInquiryResponse`.

### Card Reissue Flow
1. Authenticated request → DDA resolved.
2. `ReissueCardService` calls ECount Core to get `ownerId`, then `catalogInquiry` for default eCard.
3. Calls ECount Core `DeviceService.control` with method `"transfer"`, options `{emboss_flag: true, block_code: <value>}`.
4. Re-fetches device to confirm new card details.
5. Returns masked card detail.

### Fund Withdrawal / Check Issuance Flow
1. Validates affiliate `paper_check_flag` in cbaseapp.
2. Builds two `TransactionDefinition`s: operator device (positive amount) and DDA device (negative amount).
3. Calls ECount Core `beginTransfer` then `commitTransfer`.

---

## Compliance & Regulatory Concerns

- **PCI DSS**: Card numbers are masked (`maskCardNumber` in `DataConversionUtils.java`) before returning to caller. Full PANs are never stored or logged. AES/GCM encryption applied to DDA in the `CHAT` channel flow. DDA numbers are masked in log output (`maskDda` in `AuthenticationService.java`).
- **Reg E / NACHA**: Fund withdrawal via check issuance requires explicit program-level configuration approval (`paper_check_flag`). Transaction history includes EFT addenda.
- **OFAC / AML**: No explicit OFAC screening implemented in this service. The service relies on downstream ECount Core for any such controls.
- **GDPR / CCPA**: PII (name, email, phone) is only fetched on demand and returned to caller; audit log captures request headers/body (configurable, enabled in prod). Email and phone masked in responses from user-lookup endpoint.
- **GLBA**: API enforces JWT-based session authentication (20-minute expiry) and tri-mode access control (token/encryptedDDA/accountNumber). No cardholder credential storage within this service.
- **Request Audit Logging**: `api_request_audit_log` table in cbaseapp captures URL, filtered headers (`encryptedDDA`, `channel`), parameters, body, IP, and response status. Enabled in prod via `api.settings.auditing.enabled = true`.

---

## Business Risks

1. **Authentication bypass via plain `accountNumber` header**: Any caller knowing a 16-digit DDA can authenticate without OTP or encryption. This may be intentional for internal/trusted callers, but represents a risk if the API is reachable from untrusted networks. OpenAPI marks all auth headers as `required: false`.
2. **Restricted TLD list is application-config driven**: The sanctioned-country email suffix list (`.cu,.ir,.kp,.sy,.ua`) could be bypassed with slight domain variation (subdomains, etc.) and is not enforced downstream.
3. **OTP disable list is in application config**: Hardcoded test bypass (`none@ecount.com`, phone `6109414600`) in default `application.yml` could unintentionally persist to non-local environments if app-config overrides are missed.
4. **No OFAC check**: The withdrawal endpoint performs no OFAC sanction screening on payee names (`primaryPayeeName`, `secondaryPayeeName`), relying entirely on downstream ECount Core.
5. **Paper check flag gate**: If the `paper_check_flag` check fails silently (exception path in `AffiliateService.isAffiliateFlagEnabled` returns `false` on any error), check issuance would be blocked even for eligible programs.
6. **PIN reset uses threshold logic only**: No explicit fraud signal or cardholder consent step is required before resetting a PIN counter. Any authenticated call with the correct DDA resets PIN tries if the threshold is met.
