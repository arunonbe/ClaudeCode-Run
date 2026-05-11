# cbts-client_LIB — Solution Architect View

## Technical Architecture

`cbts-client_LIB` is a single-class synchronous REST client library packaged as a Maven JAR. The architecture is intentionally minimal:

```
Package: com.wirecard.crossbordertransferservice.xclient
│
├── CBTSClient.java              ← Single entry point; all HTTP logic
│
├── domain/                      ← Plain Java DTOs (request/response models)
│   ├── Address.java
│   ├── Beneficiary.java
│   ├── BeneficiaryBank.java
│   ├── BeneficiaryBanks.java
│   ├── BeneficiaryRule.java
│   ├── BeneficiaryRules.java
│   ├── IbanValidationResponse.java
│   ├── IsoCurrencyCode.java     ← ~150-entry enum
│   ├── LookupOrderResponse.java
│   ├── Order.java
│   ├── Payment.java
│   ├── PaymentMethod.java       ← WIRE, EFT
│   ├── Rate.java
│   ├── RateStatus.java          ← NEW, BOOKED, EXPIRED, PAYMENT_REQUESTED, CANCELLED, PENDING_CONFIRMATION
│   ├── Remitter.java
│   ├── RequestType.java         ← ONE_TIME, RECURRING
│   ├── Transfer.java
│   ├── TransferStatus.java      ← PROCESSED, FAILED
│   └── UpdateRateStatusRequest.java
│
└── exception/
    ├── CBTSBusinessException.java   ← Checked exception wrapping HTTP 4xx/5xx responses
    ├── ErrorResponse.java           ← Structured error DTO (errorcode, errorkey, errorField, errormessage)
    └── ErrorType.java               ← Enum: INVALID_REQUEST_DATA, UNKNOWN_DATA_ITEM, DATA_ALREADY_EXISTS,
                                         UNEXPECTED_ERROR, UPSTREAM_SERVICE_ERROR, EXPIRED_RATE,
                                         UNAUTHORIZED_REQUEST, FORBIDDEN_REQUEST
```

**Key design decisions:**
- All 18 API operations are methods on the single `CBTSClient` class, annotated `@Data` (Lombok generates getters/setters for all fields including credentials).
- Gson is used for both serialisation and deserialisation; no Jackson, no ObjectMapper configuration.
- `javalite-common`'s `Http` class is used directly — it wraps `HttpURLConnection` with no connection pooling, no retry, and no async capability.
- Domain objects use a mix of Lombok `@Data` (on `Rate`, `Address`, `CBTSClient`) and hand-written getters/setters (on `Beneficiary`, `Remitter`, `Transfer`, etc.), creating an inconsistent style.

## API Surface

The public API exposed by `CBTSClient` consists of 18 methods:

| Method Signature | Returns | Throws |
|---|---|---|
| `createUpdateRemitter(remitterID, firstName, lastName, address, accountNumber, programId, recurringName, recurringAddr)` | `String` (remitterID) | `CBTSBusinessException` |
| `getRemitterbyID(remitterID)` | `Remitter` | `CBTSBusinessException` |
| `deactivateRemitter(remitterID)` | `boolean` (enabled state) | `CBTSBusinessException` |
| `createUpdateBeneficary(beneficiaryID, remitterID, firstName, lastName, address, currency, paymentMethod, phone, email, swiftBic, bankName, bankAddress, bankAccount, routingNum, regulatory)` | `String` (beneficiaryID) | `CBTSBusinessException` |
| `getBeneficiarybyID(beneficiaryID)` | `Beneficiary` | `CBTSBusinessException` |
| `deactiveBeneficary(beneficiaryID)` | `boolean` (enabled state) | `CBTSBusinessException` |
| `getBeneRules(country, currency, paymentMethod)` | `BeneficiaryRules` | `CBTSBusinessException` |
| `searchBanks(country, query, skip, take)` | `BeneficiaryBanks` | `CBTSBusinessException` |
| `validateIban(iban)` | `IbanValidationResponse` | `CBTSBusinessException` |
| `getnewRate(rateID, amount, payerCurrency, beneCurrency, requestType, programId, remitterID, indicative)` | `Rate` | `CBTSBusinessException` |
| `getRatebyID(rateID)` | `Rate` | `CBTSBusinessException` |
| `bookRatebyID(rateID)` | `RateStatus` | `CBTSBusinessException` |
| `cancelRatebyID(rateID)` | `RateStatus` | `CBTSBusinessException` |
| `updateRateStatus(rateId, status)` | `RateStatus` | `CBTSBusinessException` |
| `createTransfer(transferId, rateId, beneficiaryId)` | `String` (transferID) | `CBTSBusinessException` |
| `getTransferbyID(transferId)` | `Transfer` | `CBTSBusinessException` |
| `lookupOrder(orderNumber, brand)` | `LookupOrderResponse` | `CBTSBusinessException` |
| `isOrderExists(orderNumber, brand)` | `boolean` | `CBTSBusinessException` |

**Public static utility:**
- `CBTSClient.requiresCorrelationId()` — reads `audit.global.request.id` from SLF4J MDC or generates a UUID.

**URL patterns** (all relative to `uriBase`):
```
PUT    /remitters
GET    /remitters/{id}
POST   /remitters/{id}/deactivate
PUT    /beneficiaries
GET    /beneficiaries/{id}
POST   /beneficiaries/{id}/deactivate
GET    /beneficiaries/beneficiary-rules?country={c}&currency={cur}&paymentMethod={m}
GET    /beneficiaries/search-beneficiary-banks?country={c}&query={q}&skip={s}&take={t}
POST   /beneficiaries/ibanvalidation
POST   /rates
GET    /rates/{id}
POST   /rates/{id}/book
POST   /rates/{id}/cancel
POST   /rates/{id}/status
POST   /transfers
GET    /transfers/{id}
GET    /orders/{id}?brand={b}
```

**Content-Type**: `application/vnd.cross_border_transfer_service.v1+json` (vendor-specific, v1 only)

## Security Posture

### Critical Vulnerabilities

**1. Disabled TLS Certificate Validation (CRITICAL — PCI DSS Req 4.2.1)**
- **Location**: `CBTSClient.java`, `initSSLContext()`, lines 126–151.
- **Evidence**: `checkClientTrusted()` and `checkServerTrusted()` are empty no-ops; `getAcceptedIssuers()` returns an empty array. `SSLContext.setDefault()` and `HttpsURLConnection.setDefaultSSLSocketFactory()` apply this JVM-globally.
- **Impact**: Any HTTPS request made by the embedding JVM is subject to Man-in-the-Middle attacks. An attacker on the network path could intercept CBTS traffic including beneficiary bank credentials, IBAN values, and FX rate data.

**2. Hardcoded Credentials in Source Code (CRITICAL — PCI DSS Req 8.3)**
- **Location**: `CBTSClient.java`, lines 94–95; duplicated in `CBTSClientTest.java`, lines 62–63.
- **Evidence**: `private String USERNAME = "[REDACTED — rotate immediately]"` and `private String PASSWORD = "[REDACTED — rotate immediately]"` are literal strings.
- **Impact**: Anyone with repository access has the CBTS service credentials. Lombok `@Data` on the class generates public getters for these fields, making them accessible via `cbtsClient.getUSERNAME()` and `cbtsClient.getPASSWORD()`.

**3. PII and Sensitive Data Logged at INFO Level (HIGH — GDPR Art 5, PCI DSS Req 3.3)**
- **Location**: `CBTSClient.java` line 249: `log.info("Create/Update a beneficiary: " + bene.toString())`.
- `Beneficiary.toString()` includes `accountNumber` and `routingCode`.
- **Location**: `CBTSClient.java` line 491: `log.info("IBAN value for validateIban " + iban)`.
- **Impact**: Bank account numbers, routing codes, full IBAN values, and PII (name, address, phone, email) are written to application logs.

**4. Insecure Default Constructor Exposes Hardcoded Credentials**
- **Location**: `CBTSClient.java`, lines 113–124. The 5-argument constructor calls `this.setUSERNAME(USERNAME)` using the class-level default.
- **Impact**: If a caller omits credentials (uses the 5-arg constructor), hardcoded production credentials are silently used.

**5. Plain HTTP in Test / Possible Production Config**
- `CBTSClientTest.java` line 47: `http://q-na-app08.nam.wirecard.sys:9443/...` — uses plain HTTP scheme.
- `CBTSRateExpiredTest.java` line 47: `http://localhost:9000/...`.
- These configs indicate that callers may use HTTP without TLS depending on environment.

### Access Control
- Authentication uses HTTP Basic Auth per request — no OAuth 2.0, no mutual TLS, no token rotation.
- The `@Data` Lombok annotation on `CBTSClient` generates public setters for `USERNAME` and `PASSWORD`, allowing any caller to change credentials at runtime after construction.

### Error Handling Security
- `getErrorResponse()` logs the raw HTTP error body at INFO level (line 448), which may contain server-side stack traces or internal error details.
- The hyphen-stripping in `getErrorResponse()` (`structuredError.replaceAll("-", "")`) is applied globally to all error response text, which could corrupt data and was likely introduced to work around a specific CBTS API quirk.

## Technical Debt

| Item | Location | Severity | Description |
|---|---|---|---|
| Hardcoded credentials | `CBTSClient.java:94–95` | Critical | Must be externalised to vault before any environment promotion |
| TLS cert validation bypass | `CBTSClient.java:126–151` | Critical | JVM-wide; makes all HTTPS untrustworthy |
| Lombok `@Data` on `CBTSClient` | `CBTSClient.java:69` | High | Exposes getters/setters for USERNAME, PASSWORD, uriBase to all callers |
| PII in logs | `CBTSClient.java:249, 491` | High | Violates GDPR/PCI log data policy |
| Typos in method names | `CBTSClient.java` | Low | `createUpdateBeneficary` (missing 'i'), `deactiveBeneficary` (missing 'te') — part of the public API, cannot be renamed without breaking callers |
| Mixed Lombok/manual getters | Domain classes | Low | Some classes use `@Data`, others manually define getters/setters |
| Windows-1252 encoding | `pom.xml:20` | Medium | Causes character corruption in `IsoCurrencyCode.java` (visible as `?` characters) |
| Brittle Location header parsing | `CBTSClient.java:191–197` | Medium | `split("/")[5]` assumes URL path depth of exactly 5 segments |
| Hyphen-stripping in error parser | `CBTSClient.java:450` | Medium | `replaceAll("-", "")` on entire error body is a code smell; may corrupt legitimate values |
| No connection pooling | `javalite-common` Http | Medium | A new `HttpURLConnection` is established per request with no pooling |
| No retry logic | All methods | Medium | Single-attempt HTTP calls; transient failures propagate immediately as exceptions |
| SNAPSHOT version in production use | `pom.xml:15` | Medium | SNAPSHOT artifacts are mutable; consuming applications may get different behaviour on rebuild |
| Test credentials in test source | `CBTSClientTest.java:62–63` | High | Same hardcoded production credentials duplicated in test class |
| `Beneficiary.toString()` exposes bank details | `Beneficiary.java:181–199` | High | `toString()` includes `accountNumber` and `routingCode` |
| Unused `IsoCurrencyCode` enum | `IsoCurrencyCode.java` | Low | The enum exists but is not used in `CBTSClient` request construction; currency is passed as raw String |

## Gen-3 Migration Requirements

To migrate this library to a modern Gen-3 architecture, the following changes are required:

### Security (Must Fix Before Promotion)
1. **Remove hardcoded credentials** — replace with injection from Azure Key Vault or environment-managed secrets; remove public Lombok setters for credentials.
2. **Fix TLS** — remove `initSSLContext()` trust-all pattern; configure a proper trust store; do not modify the global JVM SSL context.
3. **Redact sensitive fields from logs** — implement a `BeneficiaryMasked` toString or use a structured logging approach with explicit masking of `accountNumber`, `routingCode`, `iban`, and PII.

### Architecture
4. **Replace `javalite-common` HTTP client** with a production-grade client: Spring `RestTemplate`/`WebClient`, Apache HttpClient 5, or OkHttp with connection pooling, retry, and circuit-breaker support.
5. **Generate a typed client from an OpenAPI specification** for the CBTS service — either obtain the CBTS OpenAPI spec or produce a contract-first client stub.
6. **Rename package namespace** from `com.wirecard.crossbordertransferservice` to `com.onbe.*` to align with current corporate identity.
7. **Fix source encoding** — change `pom.xml` to `UTF-8`; fix corrupted characters in `IsoCurrencyCode.java`.

### Testability
8. **Add WireMock or MockServer** stubs for CBTS API endpoints to enable integration tests to run in CI without a live CBTS service.
9. **Enable unit tests in CI** — remove `-Dmaven.test.skip` from the publish workflow; add a dedicated test job.

### Observability
10. **Replace SLF4J MDC correlation with OpenTelemetry trace propagation** — propagate `traceparent`/`tracestate` headers in addition to or instead of the legacy `CORRELATION-ID` header.
11. **Add Micrometer metrics** — instrument HTTP call duration, success/failure rates, and rate booking latency.

### Maintainability
12. **Fix method naming typos** (`createUpdateBeneficary`, `deactiveBeneficary`) with a deprecation bridge if backwards compatibility is required.
13. **Align domain model serialisation** — standardise on Lombok `@Data` or manual getters/setters; avoid mixing both.
14. **Remove `@Data` from `CBTSClient`** — use a builder pattern or explicit constructor injection; credentials should not have public setters.

## Code-Level Risks

| Risk | File | Line(s) | Detail |
|---|---|---|---|
| JVM-global SSL bypass | `CBTSClient.java` | 126–151 | `SSLContext.setDefault()` affects all HTTPS in the JVM process, not just CBTS connections |
| Credential exposure via Lombok getter | `CBTSClient.java` | 69, 94–95 | `@Data` generates `getUSERNAME()` and `getPASSWORD()` — credentials readable by any code with a reference to the client |
| Silent error suppression in `createTransfer` | `CBTSClient.java` | 419–421 | HTTP 400 with "Could not find Transfer with transferId" is silently swallowed and the original ID returned as success — could mask real processing failures |
| `bookRatebyID` fallback to GET | `CBTSClient.java` | 379–382 | If the book POST returns non-200, the code falls back to `getRatebyID`, which returns a stale status — this may incorrectly report a rate as booked when the booking failed |
| `cancelRatebyID` same pattern | `CBTSClient.java` | 397–400 | Same GET fallback issue as `bookRatebyID` |
| Hyphen strip corrupts error JSON | `CBTSClient.java` | 450 | `replaceAll("-", "")` on the error body could corrupt error codes like `"INVALID-DATA"` → `"INVALIDDATA"`, preventing `ErrorType.fromValue()` from matching |
| `split("/")[5]` index out of bounds | `CBTSClient.java` | 192 | Array index access without bounds check; if Location header URL has fewer than 6 path segments, this throws `ArrayIndexOutOfBoundsException` |
| Null pointer on missing Location header | `CBTSClient.java` | 261 | `createUpdateBeneficary` accesses `put.headers().get("Location").toString()` without null check (unlike the remitter equivalent which added a null guard after the Azure migration) |
| `@SerializedName("required")` on `isRequired` | `BeneficiaryRule.java` | 17 | Gson `@SerializedName` annotation needed because Lombok/manual getter generates `isRequired()` which Gson would otherwise map to field name `isRequired`; this is fragile if the CBTS API field name changes |
| No timeout on `validateIban` URL construction | `CBTSClient.java` | 492–493 | `MessageFormat.format(uriBase.concat(uriValidateIbanPost), iban)` — the IBAN value is interpolated into the URL using `MessageFormat.format`, but `uriValidateIbanPost = "/beneficiaries/ibanvalidation"` has no `{0}` placeholder, so the IBAN is silently ignored in the URL; the actual IBAN is sent in the POST body correctly, but the URL formation is misleading |
