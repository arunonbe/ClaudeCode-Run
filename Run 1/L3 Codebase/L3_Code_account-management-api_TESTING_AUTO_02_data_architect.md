# account-management-api_TESTING_AUTO — Data Architect View

## Data Stores

This is a test automation repository. It contains no application-level database schema, ORM mappings, or persistence layer. The only "data store" artifacts are:

- **`SoapRequest/` directory**: 18 XML files containing static SOAP request payloads used as test fixtures. These files are the primary data surface of concern.
- **In-memory runtime data**: Rest-Assured response objects are parsed in-memory during test execution (XmlPath, string extraction). No data is persisted by the test framework.
- **No external data source**: There is no database connection configuration, no JDBC/JPA, no properties file with credentials. All test data is hard-coded in the XML fixtures or inline in Java source.

## Schema & Tables

There is no database schema in this repository. However, the SOAP message structures define the implicit data model of the downstream Account Management API. The following data structures are evident from the SOAP request fixtures:

### Account Registration Structure
Fields present across `CreateAccount.xml`, `CreateAccountLink.xml`, `AssignPackage.xml`, `CreatePackage.xml`, `UpdateReg.xml`:
- `partner_user_id` (string) — external client identifier
- `program_id` (string, 8-digit) — product program identifier
- `promotion_id` (string)
- `transaction_id` (string) — idempotency key
- `accountNumber` (16-digit string) — account identifier
- `accessLevel` (integer)
- `accountPersonalized` (boolean string)
- Registration sub-structure (`registation` — note: typo in WSDL/fixtures):
  - `firstName`, `lastName`, `middleName`, `suffixName`
  - `address1`, `address2`, `address3`, `address4`
  - `city`, `state`, `postal`, `country`, `county`
  - `emailAddress`, `homeEmail`, `businessEmail`, `mobileEmail`
  - `homePhone`, `businessPhone`, `mobilePhone`, `phone`
  - `date_of_birth`, `ssn`
  - `addenda`: `reference_1` through `reference_4`

### Card Package Structure
Fields from `CreatePackage.xml`, `AssignPackage.xml`:
- `package_type` (integer, 2 = standard observed)
- `package_id` (16-digit string)
- `cardPackageId` (integer)
- `block` (string: NONE, ALL)
- `express_mail` (boolean)
- `registration_Primary` / `registration_Secondary` (same structure as registration above)

### Load / Fund Structure
From `AddFunds.xml`, `CreateAccount.xml`:
- `amount` (numeric string)
- `comment` (string)
- `claimable` (0/1 flag)
- `notificationIndicator` (0/1 flag)
- `templateId` (integer)

### ACH Withdrawal Structure
From `WithdrawAch.xml`:
- `account_holder_name` (string)
- `account_number` (string, 17-digit example: `99087060252122451`)
- `routing_number` (9-digit string: `096001013`)
- `account_type` (S=savings, C=checking)
- `bank_name` (string)

### Withdrawal Structure
- `withdraw_type` (1=ACH, 2=check)
- `amount` (numeric string)
- `express_flag` (0/1)
- `partner_withdraw_id` (string)
- `comment` (string)

### Activation/PIN Structure
From `ActivateCard.xml`, `ActivationStatusInquiry.xml`, `SetPin.xml`:
- `card_number` (16-digit PAN)
- `cvv` (3-digit)
- `postal_code` (5-digit ZIP)
- `validate_postal` (0/1 flag, payout only)
- `new_pin` (4-digit)
- `accountNumber` (16-digit)

### Account Status Structure
From `UpdateAccStatus.xml`:
- `accountStatus` (string: CLOSED; other values inferred: ACTIVE, SUSPENDED)

## Sensitive Data Handling

### Critical Findings

| Data Element | Location | Value Present | Risk Level |
|---|---|---|---|
| Card PAN (16-digit) | `SoapRequest/ActivateCard.xml` line 5 | `5115531022041490` | CRITICAL |
| Card PAN (16-digit) | `SoapRequest/ActivationStatusInquiry.xml` line 5 | `5115531022041490` | CRITICAL |
| Card PAN (16-digit) | `SoapRequest/ActivationStatusInquiryPayout.xml` line 5 | `5445446554206695` | CRITICAL |
| CVV/CVC | `SoapRequest/ActivateCard.xml` line 6 | `308` | CRITICAL |
| CVV/CVC | `SoapRequest/ActivationStatusInquiry.xml` line 6 | `308` | CRITICAL |
| CVV/CVC | `SoapRequest/ActivationStatusInquiryPayout.xml` line 6 | `319` | CRITICAL |
| PIN | `SoapRequest/SetPin.xml` line 11 | `1234` | HIGH |
| PIN | `SoapRequest/SetPinPayout.xml` line 10 | `1234` | HIGH |
| SSN | `SoapRequest/UpdateReg.xml` line 48 | `741859632` | CRITICAL |
| Date of Birth | `SoapRequest/UpdateReg.xml` line 30 | `01/04/1997` | HIGH |
| Bank Account Number | `SoapRequest/WithdrawAch.xml` line 24 | `99087060252122451` | HIGH |
| Bank Routing Number | `SoapRequest/WithdrawAch.xml` line 25 | `096001013` | MEDIUM |
| Employee Email (PII) | Multiple XML fixtures | `gaurav.sharma@onbe.com` | MEDIUM |
| Employee Email (PII) | `XmltoJson.java` line 75 | `himanshu.goyal@external.wirecard.com` | MEDIUM |
| Account Numbers (16-digit) | Multiple XML fixtures | Various | MEDIUM |
| Program IDs | All XML fixtures | `04012521`, `04016613`, etc. | LOW |

The PANs and CVVs together constitute Sensitive Authentication Data (SAD) under PCI DSS Requirement 3. Once SAD is captured in a git commit, it exists permanently in git history even if the file is later modified.

### Data in Transit

- All SOAP calls use HTTPS (`https://webservice-qa.wirecard.com:4005/` and `:4007/`).
- `Content-Type: text/xml` header — no payload encryption beyond TLS.
- Full request/response logging is enabled in all test methods (`given().log().all()` and `.log().all()`) — complete SOAP envelopes including all sensitive fields are written to console/log output on every test run.

## Encryption & Protection

- **No encryption at rest**: XML fixture files are committed in plaintext to Git. No `.gitignore` entries exclude sensitive fixtures.
- **No masking**: `log().all()` in Rest-Assured will log the complete request body and response body, including PANs, CVVs, PINs, and SSNs, to stdout/stderr on every test execution.
- **No secret management**: No vault, secret manager, or environment-variable injection pattern. All sensitive values are literal strings in source-committed XML files.
- **TLS in transit**: The only protection is HTTPS between the test runner and the QA server. This is necessary but not sufficient.
- **No tokenisation**: Card numbers are used in raw PAN form, not tokenised.

## Data Flow

```
Test Runner (local/CI)
    |
    |-- reads SoapRequest/*.xml (plaintext, contains SAD/PII)
    |
    |-- HTTP POST (HTTPS, text/xml) -->  webservice-qa.wirecard.com:4005
    |                                    /accountmanagementapiws/services/AccountManagementApiWebServices
    |                                    (port 4007 for payout)
    |
    |<-- SOAP XML response (HTTPS)
    |
    |-- XmlPath parse (in-memory)
    |-- Assert PROCESSED_SUCCESSFULLY
    |-- log().all() --> stdout/CI logs (contains full SOAP body with SAD/PII)
```

No data is written back to any store by the tests. However, the QA backend at `webservice-qa.wirecard.com` will process and persist account/card/fund changes against its own database.

## Data Quality & Retention

- **Static fixture quality**: Many fields that should be unique per run (e.g., `transaction_id`, `partner_user_id`) are hardcoded strings (e.g., `testnyuew5566132`, `hggjhjhjjhg`). This will cause duplicate transaction errors on repeated runs.
- **Incomplete fields**: Several fixtures leave required-looking fields empty (e.g., `accountNumber` in `AddFunds.xml` line 9 is blank; `partner_user_id` in `SetPin.xml` line 6 is blank). These may reflect intentional test cases or forgotten setup, but there are no assertions validating these empty-field scenarios.
- **Typo in WSDL field**: The element `registation` (missing the second 'r') appears consistently in all registration-containing fixtures, indicating this is the actual WSDL field name — a typo that has propagated to all consuming tests.
- **No data teardown**: Tests create accounts and submit transactions in the QA environment with no cleanup. The QA environment will accumulate test data over repeated runs.
- **Retention**: No data retention policy is expressed. Test data in QA environments should have a documented retention/purge schedule per GDPR Article 5(1)(e) if any real PII is involved.

## Compliance Gaps

1. **PCI DSS Requirement 3.2.1** — SAD (PAN + CVV + PIN) must not be stored after authorization. These values are committed in git history and exist permanently unless the repository history is rewritten.
2. **PCI DSS Requirement 3.3** — SAD must not be retained. The `log().all()` pattern means SAD appears in CI pipeline logs on every run.
3. **PCI DSS Requirement 3.4** — PANs must be rendered unreadable anywhere stored. The XML fixtures store full PANs in cleartext.
4. **GLBA Safeguards Rule** — SSN and financial account details (bank routing/account numbers) in committed files may constitute inadequate safeguarding of customer financial information.
5. **GDPR/CCPA** — PII (name, address, DOB, email) in test fixtures should use synthetic data, not realistic or real personal data. The `UpdateReg.xml` fixture contains a specific DOB and SSN combination.
6. **NACHA** — Bank routing and account numbers committed in version control represent a potential exposure of financial account details used in ACH processing.
