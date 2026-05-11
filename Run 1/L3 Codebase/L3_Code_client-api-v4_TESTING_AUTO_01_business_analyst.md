# client-api-v4_TESTING_AUTO — Business Analyst View

## Business Purpose

This repository is a **test automation suite** for the Onbe (formerly ecount/Wirecard NA) **Client API v4** — a SOAP/XML web-services interface used by clients to manage prepaid card accounts and funds. The suite validates four core operations of the Client API through automated HTTP-level assertions. It does not implement production business logic; its role is quality assurance for the Client API v4 service layer.

## Business Capabilities

The automation suite covers the following Client API v4 operations:

| Test Class | API Operation | Business Capability |
|---|---|---|
| AddFundsV4 | `addFundsRequest` | Load monetary value onto a prepaid card package |
| GetRequestStatusV4 | `getRequestStatusRequest` | Query the processing status of a prior transaction |
| UpdateAccStatusV4 | `updateAccountStatusRequest` | Change a card account status (e.g., set to CLOSED) |
| UpdateRegV4 | `updateRegistrationRequest` | Update cardholder registration/demographic data |

A fifth utility class (`XmltoJson`) demonstrates XML-to-JSON conversion of a `createAccountRequest` SOAP envelope — this appears to be a developer utility/prototype, not an active test.

## Business Entities

- **Package** (`package_id`): A prepaid card package identifier (e.g., `0401500700051334`). Represents a specific card instance.
- **Program** (`program_id`): The prepaid program under which the card operates (e.g., `04015007`).
- **Promotion** (`promotion_id`): A promotional configuration linked to the program.
- **Transaction** (`transaction_id`): A unique client-assigned identifier for each API request, used for idempotency and status tracking.
- **Region** (`region_id`): Geographic processing region (e.g., `NA` for North America).
- **Cardholder Registration**: Demographic data including name, address, phone numbers, date of birth, SSN, and email.
- **Account Status**: Lifecycle state of a card account (tested value: `CLOSED`).
- **Fund Load**: A monetary load instruction including amount, comment, and references.

## Business Rules & Validations

- All four test methods assert HTTP 200 status code from the SOAP endpoint.
- The sole business-outcome assertion is a regex match for the string `PROCESSED_SUCCESSFULLY` in the `ns2:description` field of the XML response.
- `transaction_id` is supplied by the caller and must be unique per operation to avoid idempotency conflicts. The test fixtures use hardcoded transaction IDs (e.g., `Testv4proghgssd5may10`, `rytrysstrfg`, `Test1212`), which will cause failures on repeat execution if the API enforces uniqueness.
- The `addFundsRequest` carries a hardcoded load amount of `100` (currency not specified in the request; assumed to be the program's configured currency).
- Account closure is tested via status `CLOSED` in `updateAccountStatusRequest`.
- All four operations share identical endpoint path: `clientapiws/services/ClientApiWebServices/v4`.

## Business Flows

```
Test Execution (TestNG suite)
  |
  +-- AddFundsV4
  |     Load SOAP XML fixture --> POST to Client API v4 QA endpoint --> Assert 200 + PROCESSED_SUCCESSFULLY
  |
  +-- GetRequestStatusV4
  |     Load SOAP XML fixture --> POST to Client API v4 QA endpoint --> Assert 200 + PROCESSED_SUCCESSFULLY
  |
  +-- UpdateAccStatusV4
  |     Load SOAP XML fixture --> POST to Client API v4 QA endpoint --> Assert 200 + PROCESSED_SUCCESSFULLY
  |
  +-- UpdateRegV4
        Load SOAP XML fixture --> POST to Client API v4 QA endpoint --> Assert 200 + PROCESSED_SUCCESSFULLY
```

No setup/teardown hooks are implemented. Tests are independent and can run in any order as defined by the TestNG suite XML.

## Compliance & Regulatory Concerns

- **SSN in committed test fixture**: The file `SoapRequest/UpdateRegV4.xml` contains a 9-digit value in the `<v41:ssn>` field committed to source control. SSNs are personally identifiable information (PII) regulated under GLBA, CCPA, and various state privacy laws. This is a **high-severity compliance finding** — see Data Architect view for details.
- **Real email address in test fixture**: A named Onbe employee email address appears in `SoapRequest/UpdateRegV4.xml` within the `<v41:e_mail>` field. Under GDPR and CCPA, storing identifiable personal data in source control is a risk.
- **Real email address in source code**: The `XmltoJson.java` utility contains a named Wirecard employee email address (`himanshu.goyal@external.wirecard.com`) embedded as a string literal.
- **Committed credentials**: The Maven `settings.xml` file contains plaintext server passwords for multiple Nexus/Maven repository servers. These are credential secrets in source control — a PCI DSS and security policy violation.
- The suite targets a **QA environment** (`webservice-qa.wirecard.com`), which reduces — but does not eliminate — risk of inadvertent production data exposure.
- No data masking, anonymization, or synthetic PII generation is used in the test fixtures.

## Business Risks

1. **Hardcoded transaction IDs**: Tests will produce duplicate-transaction errors on re-execution unless the API is idempotent or test data is reset, undermining reliability of the automation suite.
2. **No negative/boundary testing**: Only the happy path (`PROCESSED_SUCCESSFULLY`) is validated. No tests exist for error codes, rejected loads, invalid inputs, or account-not-found scenarios.
3. **Single assertion point**: The only correctness check is a string match on `ns2:description`. No amounts, status codes, or returned entity values are verified.
4. **QA environment dependency**: Tests are tightly coupled to `webservice-qa.wirecard.com:4005`. If this environment is unavailable, the entire suite fails.
5. **No test data lifecycle management**: There is no mechanism to create, reset, or clean up test card accounts, making sustained CI execution fragile.
6. **Legacy tooling**: TestNG 6.10 (2016) and Maven compiler target Java 1.7 are significantly outdated and may carry unpatched vulnerabilities.
