# customer-service-rest-api — Business Analyst View

## Business Purpose
`customer-service-rest-api` is Onbe's **external-facing Customer Service REST API** (v1.2.3-SNAPSHOT, production-bound). It exposes cardholder account management operations to client/partner systems over HTTPS. The API is published to Onbe's external APIM under the path suffix `managepayments/customerservice` and is documented at `sandbox-api.onbe.com/customerservice`.

## Capabilities
| Operation | HTTP Method / Path | Description |
|---|---|---|
| Update Account Status | `PUT /v1/account-status` | Activate, lock, mark lost/stolen, close a card |
| Account Inquiry | `GET /v1/account-inquiry` | Retrieve balance, registration profile, transaction history, card detail, comment history |
| Reissue Card | `POST /v1/reissue-card` | Issue a replacement card for lost/stolen/revoked |
| Set PIN | `PUT /v1/set-pin` | Set 4-digit PIN for all cards on a payee account |

## Key Entities
| Entity | Fields of Note |
|---|---|
| Payee / Cardholder | `partnerUserId` (1–40 chars), `accountNumber` (16 digits), registration profile (name, address, phones, email) |
| Card | `cardNumber` (masked in responses), `programId` (8 digits), `promotionId` (1–4 digits), `expiration`, `accountStatus` |
| Balance | `balanceAvailable`, `balanceLedger`, `balancePending`, `balanceDate` (amounts in hundredths of currency unit) |
| Transaction | `transactionDate`, `transactionDetails` (masked), `transactionType`, `transactionAmount`, `transactionFee`, `paymentDetails` |
| Comment / Inquiry | `inquiryIdNumber`, `problemDescription`, `inquiryTypeDesc`, `employeeId`, `status` |
| SetPinRequest | `programId`, `promotionId`, `transactionId`, `newPin` (4-digit numeric), `accountNumber` or `partnerUserId` |

## Business Rules
- Either `accountNumber` OR `partnerUserId` must be provided (not both) for account-status and set-pin operations (`CustomerService.java` line 166, errors 34001/34002).
- `programId` must be exactly 8 digits (`[0-9]{8}`); `promotionId` 1–4 digits; `transactionId` 1–40 alphanumeric.
- `newPin` must match `[0-9]{4}` (OpenAPI schema; validated at controller layer).
- `accountStatus` enum: `ACTIVATE | ACTIVE | CLOSED | LOCK | LOST | STOLEN`.
- `blockCode` for reissue enum: `LOST | STOLEN | REVOKED`.
- Response codes: 34001/34002 → ValidationException (400); 34003–34007 / 34050 → processing failed (200 with subCode); 36010 → Forbidden (401); 34099 / 36099 → system failure (500).
- `journalDetail` query param: 0 = no transactions, 1 = transactions, 2 = transactions with PPID.

## Flows
1. **Request arrives** → `AuthenticationFilter` checks `External-Auth-Response` header → JWT validated → `CandidateStore` populated.
2. **Controller** (`CustomerServiceController`) delegates to **`CustomerService`** (implements `CustomerServiceApiDelegate`).
3. **Service** calls legacy backend: `UpdateAccountStatusService`, `SearchAccount`, `ReissueCard`, or `SetPinService`.
4. **Mapper** (`AccountStatusMapper`, `AccountInquiryMapper`, etc.) transforms backend objects to API model.
5. **Response** returned as reactive `Mono<T>`.

## Compliance Notes
- API endpoint for Set PIN handles SAD (PIN) in transit; TLS assumed via APIM/gateway.
- Card numbers masked to first-6/last-4 not implemented in responses; the `cardNumber` in `AccountInquiry` response example shows `5115XXXXXXXX8649` — middle digits masked by upstream backend.
- `fiservDRPrograms` list configures Fiserv disaster-recovery program codes, relevant to payment-rail continuity.
- Transaction details masked as `XXXXX` by default unless explicitly permitted (`journalDetail=2` with PPID access).

## Risks
- `allow-circular-references: true` and `allow-bean-definition-overriding: true` in `application.yml` (lines 75–77) — indicates Spring dependency design issues.
- `CSConfig.java` line 139: `commentService.setApplicationId(12)` is hard-coded with a comment "not sure why it's hardcoded" — undocumented magic number.
- Version is `1.2.3-SNAPSHOT`; SNAPSHOT artifacts should not be deployed to production per Maven enforcer policy (enforcer configured in `pom.xml` but `com.onbe*` excluded from SNAPSHOT check).
