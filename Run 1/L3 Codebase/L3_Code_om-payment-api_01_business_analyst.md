# om-payment-api — Business Analyst View

## Executive Summary

`om-payment-api` is the Onboarding Manager Payment API — a Spring Boot 3.4.4 REST API that implements the `manage-payment-rest-api` contract within the Onboarding Manager (OM) workflow. It provides the complete set of payment operations required to onboard a new payee: account creation, card issuance (virtual and physical), fund loading, disbursements (check, ACH, debit), and card management (reissue, void, inquiry). The service is the operational payment backbone for Onbe's B2C disbursement platform in the East region.

## Business Capabilities

### Account Management Domain (`/v1/accounts`)
The `AccountManagementRestController` (`src/main/java/.../controller/AccountManagementRestController.java`) exposes the following operations directly relevant to client business processes:

| Endpoint | HTTP Method | Business Operation |
|---|---|---|
| `POST /v1/accounts` | POST | Create new payee account (with optional virtual or physical card issuance and fund loading) |
| `POST /v1/accounts/add-funds` | POST | Load funds to an existing payee account |
| `PUT /v1/accounts/registration` | PUT | Update payee demographic profile; also used to assign InstantPay cards |
| `POST /v1/accounts/withdraw` | POST | General-purpose withdraw: issue check, ACH, or void check |
| `POST /v1/accounts/issue-check` | POST | Dedicated check issuance |
| `POST /v1/accounts/issue-check-escheatment` | POST | Issue check for escheatment processing |
| `POST /v1/accounts/void-check` | POST | Cancel/void a previously issued check |
| `POST /v1/accounts/reissue-check` | POST | Reissue a check |
| `POST /v1/accounts/reissue-card` | POST | Reissue a physical card (marks old as lost/suspended, requests new plastic) |
| `POST /v1/accounts/reissue-account` | POST | Reissue the account without requesting plastic |
| `POST /v1/accounts/request-plastic` | POST | Request physical card for existing account |
| `GET /v1/accounts/card` | GET | Retrieve card number and expiration date |
| `GET /v1/accounts/cvv` | GET | Retrieve card CVV (SAD — protected by access controls) |
| `POST /v1/accounts/bulk-order` | POST | Create InstantPay bulk card order |
| `POST /v1/accounts/link-card` | POST | Associate a physical card to a payee account |

### Debit Transaction Domain (`/v1/debit`)
The `DebitRestController` provides the two-phase commit debit transaction model:
- `beginDebit` — initiates a hold/authorization
- `commitDebit` — finalizes the transaction
- `cancelDebit` — releases the hold

This three-phase debit pattern supports atomic financial operations with explicit rollback capability, which is critical for payment integrity in a PCI DSS environment.

## Business Flows and Stakeholders

### Payee Onboarding Flow
The primary business flow served by this API:
1. Client system calls `POST /v1/accounts` with payee demographics, program ID, and card issuance preference.
2. API creates the account in eCount Core via `com.citi.prepaid.accountmanagementapi`.
3. API optionally issues a virtual or physical card.
4. API optionally loads initial funds.
5. Payee receives card (physical via embossing order, or virtual immediately).

### Disbursement Flows
Clients trigger disbursements through:
- **Check**: `POST /v1/accounts/issue-check` → triggers check print/mail via `WithdrawService`.
- **ACH**: `POST /v1/accounts/withdraw` with `withdrawType=ACH` → initiates ACH transfer.
- **Debit/Transfer**: Begin/Commit/Cancel cycle through the Debit API.

### Escheatment Flow
`POST /v1/accounts/issue-check-escheatment` handles the legal requirement to transfer unclaimed funds to the state. This is a compliance-driven process that must be auditable.

## Integration Dependencies

The API integrates with several critical downstream systems:

| System | Artifact | Purpose |
|---|---|---|
| eCount Core | `com.ecount:xplatform:6.3.2` | Core prepaid account management platform (member, device, transfer management) |
| Account Management API | `com.citi.prepaid.accountmanagementapi:accountmanagementapi-impl:3.0.3-SNAPSHOT` | Citi prepaid account management services (create account, add funds, withdraw, card inquiry) |
| Debit API | `com.citi.prepaid.webservices.debitapi:debitapi-impl:3.1.2` | Debit transaction services (begin/commit/cancel) |
| eCount Director | `https://uat.nam.wirecard.sys:8080/service/dispatch.asp` | System dispatch service (application.yml lines 82-85) |
| Order Service | `https://uat.nam.wirecard.sys:9003/order/OrderService` | Order processing |
| SQL Server (cbaseapp) | `u-lis-db01.nam.wirecard.sys:2231` | Application data store |
| SQL Server (ecountcore) | `u-lis-db02.nam.wirecard.sys:2231` | eCount core data store |

The presence of `accountmanagementapi:3.0.3-SNAPSHOT` in the pom.xml (line 31) is a risk indicator — SNAPSHOT dependencies are mutable and may introduce breaking changes without version increments. This should be stabilized to a release version before production deployment.

## Sensitive Data Handling

The API handles Sensitive Authentication Data (SAD) directly:

- **CVV retrieval** (`GET /v1/accounts/cvv`): The `CvvInquiryResponse` is returned via the REST API. CVV is SAD under PCI DSS and its transmission must occur only over TLS, from systems within the CDE, to authorized caller entities.
- **Card number retrieval** (`GET /v1/accounts/card`): Returns full card number (`accountNumber` parameter example `0401114500019542` — 16 digits) and expiration. This is PAN + expiration, qualifying as CHD.
- **SSN in request bodies**: `application.yml` line 107 configures Logbook to obfuscate `ssn`, `cardNumber`, and `cvv` in JSON body logs — confirming these fields appear in API request/response payloads.

## Compliance Observations

1. **Logbook obfuscation configured** (`application.yml` lines 106-107): `json-body-fields: [ssn, cardNumber, cvv]` — these fields are masked in HTTP request/response logs. This is a key PCI DSS and GLBA control.

2. **JWT security validator is disabled** (`JwtSecurityValidator.java` lines 31-57): The entire authorization logic is commented out and replaced with `return true;` (line 57). This means **all callers are unconditionally authorized**. This is a critical security gap for a production payment API.

3. **TLS on database connections**: All four `application.yml` datasource URLs specify `sslProtocol=TLSv1.2` — TLS in transit to SQL Server is enforced.

4. **trustServerCertificate=true**: All datasource URLs also set `trustServerCertificate=true`, meaning TLS certificate validation is disabled. This eliminates protection against man-in-the-middle attacks on database connections and violates PCI DSS network security requirements.

5. **SNAPSHOT dependency in production path**: `accountmanagementapi:3.0.3-SNAPSHOT` should be replaced with a release version before any production deployment.
