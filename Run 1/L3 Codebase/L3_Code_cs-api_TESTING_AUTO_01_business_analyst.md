# Business Analyst View — cs-api_TESTING_AUTO

## Business Purpose
This repository is an automated regression and smoke-test suite for the CS API (Customer Service API) family of web services. It exercises the SOAP endpoints of both the prepaid card management API (V1 and V3) and the payout card management API (V3 Payout). Its role is QA validation — not production business logic. The test suite validates that the downstream SOAP endpoints return expected response codes when provided with specific account identifiers and operation payloads.

## Capabilities Tested
| Test Class | SOAP Operation | Target Endpoint |
|---|---|---|
| AccountInquiryV1 | accountInquiry (V1) | CardManagement/services/AccountManagement |
| AccountInquiryV3 | accountInquiry (V3) | CardManagementV3/services/AccountManagement |
| ReissueCard | reissueCard | CardManagementV3/services/AccountManagement |
| AuthenticationReq | authenticationRequest | CardManagementPayoutV3/services/AccountManagement |
| ForgotUserNameReq | forgotUserName | CardManagementPayoutV3/services/AccountManagement |
| PayoutAccountInquiry | payoutAccountInquiry | CardManagementPayoutV3/services/AccountManagement |
| RegistrationReq | registrationRequest | CardManagementPayoutV3/services/AccountManagement |
| UpdatePasswordReq | updatePassword | CardManagementPayoutV3/services/AccountManagement |
| UpdateRegReq | updateRegistrationRequest | CardManagementPayoutV3/services/AccountManagement |

## Entities (from SOAP request fixtures)
- **Card**: card_number field present in AccountInquiryV3.xml and RegistrationReq.xml fixtures (sensitive — see Compliance Concerns below)
- **PUID (Partner User ID)**: numeric user reference, used in V1 and payout searches
- **DDA Number**: account number for payout search (PayoutAccountInquiry.xml contains a DDA number value)
- **AccountProfile / Registration**: first/last name, address, phone, email, ZIP used in UpdateRegReq.xml
- **Application ID**: API key identifying the calling affiliate application

## Business Rules (inferred from test fixtures and success criteria)
1. A valid `application_id` is required for all operations.
2. Either `card_number`, `puid`, `ppd`, or `mobile_phone` must be supplied for account search.
3. Successful account inquiry returns `completion_message = OK`.
4. Successful authentication returns `message = PROCESSED_SUCCESSFULLY`.
5. Successful registration returns `message = PROCESSED_SUCCESSFULLY`.
6. Card reissue requires `puid` and `block_code` (e.g., "lost").

## Business Flows Tested
1. **Prepaid Card Inquiry V1**: Submit card search by PUID → validate OK response.
2. **Prepaid Card Inquiry V3**: Submit card search by card number → validate OK response.
3. **Card Reissue**: Submit reissue by PUID with block code → validate OK.
4. **Payout Authentication**: Submit username/password → validate PROCESSED_SUCCESSFULLY.
5. **Payout Registration**: Submit card + CVV + email + phone → validate PROCESSED_SUCCESSFULLY.
6. **Payout Account Inquiry**: Submit DDA number search → validate OK.
7. **Payout Update Registration**: Submit address/contact update → validate OK.

## Compliance Concerns
**CRITICAL — PCI DSS Violation Risk:**
- `SoapRequest/AccountInquiryV3.xml` contains a full 16-digit card number value in the `card_number` field. This constitutes a PAN committed to source control, which is a direct violation of PCI DSS Requirement 3.3 (do not store sensitive authentication data after authorization) and Requirement 3.4 (render PAN unreadable). The exact file location is `E:\OnbeEast363\repos\cs-api_TESTING_AUTO\SoapRequest\AccountInquiryV3.xml`.
- `SoapRequest/RegistrationReq.xml` contains a full 16-digit card number and a 3-digit CVV/CVC value in plaintext. This is a PCI DSS violation at the test fixture level. File location: `E:\OnbeEast363\repos\cs-api_TESTING_AUTO\SoapRequest\RegistrationReq.xml`.
- `SoapRequest/RegistrationReq.xml` also contains a plaintext password value and an email address referencing an internal domain. These constitute credential and PII exposure in source control.
- `SoapRequest/AuthenticationReq.xml` contains a plaintext username and password. File: `E:\OnbeEast363\repos\cs-api_TESTING_AUTO\SoapRequest\AuthenticationReq.xml`.
- `SoapRequest/UpdateRegReq.xml` contains PII: first name, last name, address, phone numbers, email address referencing a former domain (wirecard.com). File: `E:\OnbeEast363\repos\cs-api_TESTING_AUTO\SoapRequest\UpdateRegReq.xml`.
- `SoapRequest/PayoutAccountInquiry.xml` contains a DDA number value in plaintext. File: `E:\OnbeEast363\repos\cs-api_TESTING_AUTO\SoapRequest\PayoutAccountInquiry.xml`.

**Immediate Remediation Required**: All XML fixture files must be rotated to use only masked/test values. Any real credentials or card data must be revoked immediately if they represent live accounts.

## Risks
1. **No parameterisation of test data**: All sensitive values are hard-coded in XML fixture files committed to the repository.
2. **Hardcoded QA base URL**: All tests point to a hardcoded HTTPS host and port. If the QA environment moves, every test file must be manually updated. No environment variable or config injection is implemented.
3. **Single-assertion testing**: Each test class has a single test method with a regex match on one field. There is no negative-path testing, no boundary testing, and no structured assertion framework.
4. **No test isolation or mocking**: Tests call live QA SOAP endpoints. They cannot run in CI without network access to the QA host.
5. **Java 1.7 compiler target**: pom.xml specifies `maven.compiler.source/target = 1.7`, well below current supported Java versions. The Spring Boot and Java 21 used in the production repos creates a version gap.
6. **Thread count set to 5 for V1 test only**: The `testng.xml` sets `thread-count="5"` for AccountInquiryV1 but all others are sequential. This is inconsistent.
7. **No GitLab CI deployment stage**: The `.gitlab-ci.yml` only includes SAST scanning, not test execution. Tests are not automatically run on commit.
