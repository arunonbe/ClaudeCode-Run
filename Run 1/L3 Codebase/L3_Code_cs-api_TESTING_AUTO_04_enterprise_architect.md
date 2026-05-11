# Enterprise Architect View — cs-api_TESTING_AUTO

## Platform Generation
**Gen-1 Test Tooling** — This repository tests Gen-1 (cs-api-v2_API / csapiws-payout) and Gen-2 (cs-api-v3_API) SOAP services. The test tooling itself is not a platform generation artefact; it is a standalone QA utility written against the SOAP contract surface.

## Domain
- **Domain**: Customer Service / Cardholder Support
- **Sub-domain**: API Quality Assurance
- **Business capability mapped**: Regression validation of CS API SOAP operations (card inquiry, card reissue, payout account management, cardholder registration/authentication)

## Role in Ecosystem
This repository has a purely supportive, non-production role:
- It validates the behaviour of production-bound SOAP APIs before release.
- It has no runtime presence in production.
- It is invoked manually (no CI execution stage found).

## Dependencies
| Upstream Dependency | Type | Notes |
|---|---|---|
| cs-api-v1_API | SOAP endpoint | CardManagement/services/AccountManagement port 4005 |
| cs-api-v3_API | SOAP endpoint | CardManagementV3/services/AccountManagement port 4005 |
| csapiws-payout_API | SOAP endpoint | CardManagementPayoutV3/services/AccountManagement port 4007 |
| webservice-qa.wirecard.com | QA infrastructure | Legacy hostname; DNS resolution must be confirmed |

## Patterns
- **Black-box SOAP testing**: Tests treat the API as a black box; no internal beans, no mocking.
- **Fixture-based testing**: All input data in external XML files; no data generation.
- **Monolithic test suite**: All tests in a flat TestNG suite XML; no test categories or groups.

## Status
- **Active but unmaintained**: No evidence of recent refactoring or modernisation. Test fixtures still reference wirecard.com domains. Java 1.7 target has not been updated.
- **Not integrated into CI pipeline**: Functional quality gate is absent from the CI workflow.

## Migration Blockers (to Gen-3 / modern test strategy)
1. **Sensitive data in fixtures**: Must be replaced with masked/synthetic data before any fixture can be committed to a modernised test suite.
2. **No environment parameterisation**: Test base URLs and application IDs must be externalised to support multi-environment testing (dev, QA, UAT, staging).
3. **No contract-testing alignment**: If cs-api-v3_API moves to Pact consumer-driven contract testing (which the v3 pom.xml hints at via `PACT_PACTICIPANT`), this bespoke REST-Assured suite would be superseded.
4. **Java version gap**: Upgrading to Java 21 (aligned with v1 and v3 production repos) requires updating the pom.xml and verifying TestNG/RestAssured compatibility.
5. **Wirecard hostname**: The QA base URL must be updated to the current Onbe/Northlane QA hostname.
