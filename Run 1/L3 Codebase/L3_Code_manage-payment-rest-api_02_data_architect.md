# Data Architect View — manage-payment-rest-api

## Overview

`manage-payment-rest-api` is a data-intensive payment API that reads from and writes to four SQL Server databases and one Redis cache, while also orchestrating calls to multiple internal legacy services (director service, banker SOAP service, order service, job service). Understanding the data models, flows, and masking configurations is essential for PCI DSS, GLBA, and GDPR compliance assessments.

## Request / Response Data Models

### Domain Objects (under `model/domain/`)

| Class | Key Fields | Sensitivity |
|---|---|---|
| `Registration` | name, address, email, phone, SSN (inferred) | PII (GLBA, CCPA, GDPR) |
| `Card` | `cardAccessLevel` | Low — access level only (no PAN) |
| `AchWithdraw` | routing number, account number, account type | Financial PII (NACHA) |
| `CheckWithdraw` | payee name, address | PII |
| `Address` | street, city, state, postal, country | PII |
| `Link` | (linking a physical card) | Card-related |
| `Load` | amount, currency | Financial |
| `Addenda` / `AddendaKeyValue` | custom key-value pairs | Varies |

### Response Objects

| Class | Key Fields | Sensitivity |
|---|---|---|
| `CardInquiryResponse` | Card number, expiration date | **SAD — PCI DSS Req 3.3** |
| `CvvInquiryResponse` | CVV value | **SAD — PCI DSS Req 3.3** |
| `CreateAccountResponse` | Account number, card details | PCI DSS |
| `GetBalanceResponse` | Program balance | Financial |
| `WithdrawResponse` | Transaction ID, status | Low-moderate |
| `DebitResponse` | Transaction ID, status, amount | Financial |

## HTTP-Level Data Masking (Logbook)

The `application.yml` configuration (lines 119–122) implements Zalando Logbook for HTTP request/response body logging:
```yaml
logbook:
  obfuscate:
    json-body-fields: [ssn,cardNumber,cvv]
```
This masks the `ssn`, `cardNumber`, and `cvv` JSON fields in logged HTTP bodies. However:
- **Masking is field-name-based**: only fields literally named `ssn`, `cardNumber`, and `cvv` are masked. Variations like `card_number`, `cardNo`, `pan`, or fields containing card numbers under other names are NOT masked.
- **No PAN regex masking**: If a card number appears in a field not named `cardNumber` (e.g., in a custom addenda value, an error message, or a legacy field name), it will be logged in plaintext.
- **Exception bodies**: Logbook logs request bodies; exception stack traces in responses are not subject to this obfuscation.

## Multi-Database Data Architecture

### Database Connection Map

| DataSource Bean | Database | Tables/Schema | Purpose |
|---|---|---|---|
| `cbaseapp` | cbaseapp (SQL Server) | Core cardholder tables | Account, cardholder profile data |
| `jobsvc` | jobsvc (SQL Server) | job_file, job_batch, job_action | Job/action queue for async processing |
| `ordersvc` | ordersvc (SQL Server) | Order tables | Bulk card order management |
| `ecountcore` | EcountCore (SQL Server) | Core eCount tables | Legacy platform core data |

The `DatabaseConfiguration.java` bean wires separate HikariCP connection pools for each database. Each pool has:
- `timeout: 5000` (5 seconds connection timeout)
- `fail-fast: true` (application fails to start if DB unreachable)

All JDBC URLs use `sslProtocol=TLSv1.2;trustServerCertificate=true`. The `trustServerCertificate=true` disables certificate validation — a security risk discussed in the Solution Architect view.

### Redis Cache

Azure Redis Cache (`radis-az1-cluster-qa-ss.redis.cache.windows.net:6380`) is used for:
- `recipientweb:programSetup:{affiliateId}` — international flag per program
- `intlCountry:map` — country rules for international validation

Connection uses TLS over port 6380 (`ssl.enabled: true`) — correct for Azure Redis Cache. Password injected via `${RECIPIENTWEB_REDIS_PASSWORD}`.

## Data Flow Architecture

### Create Account Flow
```
POST /v1/accounts
  → CreateAccountRequest (JSON)
  → AccountManagementRestController.createAccount()
  → AccountManagementRestHandlerImpl
    → AccountManagementApi (com.citi.prepaid.accountmanagementapi)
      → director-service (SOAP/HTTP: https://uat.nam.wirecard.sys:8080/service/dispatch.asp)
      → cbaseapp DB (stored procedures)
      → jobsvc DB (job actions)
  ← CreateAccountResponse (JSON)
```

### Debit Flow (Two-Phase)
```
POST /v1/accounts/debit/begin
  → BeginDebitRequest
  → DebitServiceRestHandlerImpl
    → DebitTransactionService
      → DebitApi (com.citi.prepaid.webservices.debitapi)
        → Redis (check/set debit transaction state)
        → banker SOAP service (wsdl: https://qa.nam.wirecard.sys:9009/banker-service/...)
  ← DebitResponse (transactionId, status)

PUT /v1/accounts/debit/commit
  → CommitDebitRequest (transactionId from begin)
  → [same path] → banker commit

DELETE /v1/accounts/debit/cancel
  → CancelDebitRequest (transactionId)
  → [same path] → banker cancel/reverse
```

## Validation Framework

The API implements a rich custom validation framework (`validation/` package):
- `StringParameterConstraintValidator` — regex-based string validation
- `EmailParameterConstraintValidator` — email format validation
- `PhoneParameterConstraintValidator` — phone number validation
- `DateParameterConstraintValidator` — date format validation
- `ChoiceParameterConstraintValidator` — enumerated value validation
- `ConditionalValidator` — context-dependent field requirement validation
- `DynamicConstraintValidator` — dynamic constraint evaluation
- `InternationalContext` — conditional validation rules for international programs (uses Redis cache)

This is a sophisticated, extensible validation architecture that is well-suited to a payments API with complex field dependency rules.

## Dapr Secret Store

`dapr-components/dapr-secrets.json` contains development secrets. This file is committed to the repository:

```json
{
  "managepaymentapi-ordersvcdb-password": "[REDACTED — rotate immediately]",
  "managepaymentapi-securityservice-visakey": "VVG8CPATV43C511XKDN013ALopepi6j4SvofpaIUlrV-kuQBQ",
  "managepaymentapi-securityservice-visasharedsecret": "u@wiGsudTR8-R5PfKQnkTNVhJSDBto$MmT43krYq"
}
```

**Critical finding**: A Visa security service key and shared secret are committed to source control. These credentials enable access to Visa security services and must be rotated immediately. The file should be deleted from the repository and added to `.gitignore`.

## PCI DSS Data Scope

| Operation | Card Data Involved | PCI Scope |
|---|---|---|
| createAccount | Card issuance (no PAN in request) | In scope |
| cardInquiry | Returns full PAN and expiry | **In scope — SAD in response** |
| cvvInquiry | Returns CVV | **In scope — SAD in response** |
| addFunds | Amount only | In scope |
| withdraw (ACH) | Bank routing/account | In scope (NACHA) |
| debit begin/commit/cancel | Amount, transaction ID | In scope |
| updateRegistration | Cardholder PII | In scope |
