# Business Analyst View — manage-payment-rest-api

## Executive Summary

`manage-payment-rest-api` (version 1.3.4, artifact `com.onbe.external.api:manage-payment-rest-api`) is a production-grade Spring Boot REST API that serves as Onbe's Generation-3 (Gen-3) external-facing payment management interface. It provides a unified, OAuth/JWT-secured RESTful API surface for enterprise clients to manage prepaid cardholder accounts, fund loads, withdrawals, and debit operations. This service is the primary modernisation of the legacy `clientapi_API` and `js-import_SVC` approaches, offering real-time JSON-over-HTTPS interactions in place of file-based batch processing.

## Business Capabilities

The API is segmented into two functional groups, each with a dedicated REST controller:

### Account Management (`/v1/accounts`) — `AccountManagementRestController`

| Endpoint | Method | Business Operation |
|---|---|---|
| `POST /v1/accounts` | Create Account | Enrol a new payee (cardholder); optionally issue card, add funds |
| `POST /v1/accounts/add-funds` | Add Funds | Load disbursement funds onto an existing account |
| `PUT /v1/accounts/registration` | Update Registration | Update cardholder demographic profile; assign InstantPay cards |
| `POST /v1/accounts/withdraw` | Withdraw | Issue ACH transfer or physical check from account; void an existing check |
| `GET /v1/accounts/card` | Card Inquiry | Retrieve card number and expiration date |
| `GET /v1/accounts/cvv` | CVV Inquiry | Retrieve card CVV value |
| `GET /v1/accounts/transaction-status` | Transaction Status | Query status of a specific transaction by ID |
| `POST /v1/accounts/bulk-order` | Create Bulk Order | Create an InstantPay card bulk order |
| `POST /v1/accounts/link-card` | Link Card | Link a plastic card to a DDA payee account |
| `GET /v1/accounts/balance` | Get Balance | Retrieve the program/promotion funding balance |

### Debit Operations (`/v1/accounts/debit`) — `DebitRestController`

| Endpoint | Method | Business Operation |
|---|---|---|
| `POST /v1/accounts/debit/begin` | Begin Debit | Initiate a debit transaction; hold the transaction amount |
| `PUT /v1/accounts/debit/commit` | Commit Debit | Finalise a pending debit; apply the held amount |
| `DELETE /v1/accounts/debit/cancel` | Cancel Debit | Release a held debit; reverse the hold |

The debit API implements a **two-phase commit** pattern for debit operations: `begin` → `commit` (or `cancel`). This is appropriate for payment operations where authorisation must be separated from settlement.

## Client Identity and Access Model

The API uses JWT-based authentication (`AuthenticationFilter.java`) where requests carry an `External-Auth-Response` header (a JSON object containing JWT validation results from an upstream security gateway). The `JwtSecurityValidator` then authorises the request against domain-method-program combinations, e.g.:
```
{METHOD=createAccount, API=AccountManagement, PROGRAM=04016113}
{FEATURE=Return-Card-Number, METHOD=createAccount, API=AccountManagement, PROGRAM=04016113}
```

This provides **fine-grained, feature-level access control** — a client can be granted the ability to call `createAccount` but denied the ability to receive the card number in the response. This is a significant PCI DSS-aligned security control.

## Business Data Elements

### CreateAccountRequest
- `programId` (8-digit client program ID)
- `partnerUserId` (client's own payee reference, 1–40 alphanumeric)
- `registration` (required): name, address, email, phone — full cardholder PII
- `card` (optional): `cardAccessLevel`
- `link` (optional): for linking a plastic card
- `load` (optional): for initial fund load at creation
- `accessLevel`: sub-program

### WithdrawRequest
- ACH: `AchWithdraw` (routing number, account number, account type, name)
- Check: `CheckWithdraw` (payee name, address)
- Void: `VoidCheckWithdraw` (check number)

### CardInquiry / CVV Inquiry
- Returns card number, expiry, CVV — Sensitive Authentication Data (SAD) under PCI DSS

## Compliance Significance

This API is squarely **within PCI DSS scope**:
- `cardInquiry` and `cvvInquiry` endpoints return full card data (PAN, CVV)
- `createAccount` initiates card issuance
- `addFunds` constitutes an electronic funds transfer under Reg E
- `withdraw` initiates ACH / check disbursement under NACHA / Reg E

The `logbook` (Zalando HTTP logging library) configuration in `application.yml` (lines 120–122) provides HTTP-level field masking:
```yaml
logbook:
  obfuscate:
    json-body-fields: [ssn,cardNumber,cvv]
```
This masks `ssn`, `cardNumber`, and `cvv` fields in HTTP request/response logs — a strong PCI DSS Req 3.3 control at the API layer.

## Multi-Database Architecture

The API connects to four separate SQL Server databases (from `application.yml`):
- `cbaseapp` — core cardholder data
- `jobsvc` — job/action queue
- `ordersvc` — order management
- `ecountcore` — eCount core platform

Plus a Redis cache for international program flags and country rules.

## Deployment Status

The service has a CI/CD pipeline (`deployment.yml`) publishing to APIM (`PUBLISH_TO_APIM: true`, `EXTERNAL_APIM: true`) — indicating this is an externally published API available to enterprise clients through Azure API Management. The latest release tag is `20260430.203650`.
