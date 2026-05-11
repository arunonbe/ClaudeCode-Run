# Business Analyst View — qa-mocking-service

## Business Purpose

`qa-mocking-service` is a test-infrastructure repository that provides controllable HTTP stub responses for downstream third-party payment processor APIs during QA and integration testing. It is not a production service and carries no revenue or cardholder-facing function. Its sole business purpose is to enable QA engineers and developers to test Onbe platform services against realistic Fiserv API responses without requiring live connectivity to Fiserv's production or certification environments.

## Capabilities

The service is a WireMock server delivered as a Docker container. It serves pre-authored JSON stub mappings that simulate Fiserv's card-management API endpoints. The mapping library covers a broad range of Fiserv operations:

- Card lifecycle: card activation, embossing (standard and rush), EMV chip add, plastic count update, type-of-plastic-issued, presentation instrument update, reissue
- Account management: new account creation, account transfer, activation code update, customer inquiry, customer update, address update, unusual-address update
- Balance operations: cardholder balance/status, debit balance retrieval and update, DDA balance update, DDA maintenance add
- Authorization: authorization flag update, authorization adjustment, external status/reason code management
- PIN management: set PIN ID, reset PIN attempts, update PIN, generate PIN change reference ID, mail generated PIN
- Strategy and portfolio: current strategy update, personal embossing feature, user flag update, mail code update, business phone update

Each operation provides both a success (HTTP 200) and a processor-error (HTTP 453) response stub, enabling testers to exercise both the happy path and error-handling branches of consuming services.

## Client and Cardholder Impact

This service has no direct client or cardholder impact. It is strictly internal test infrastructure. However, its correctness and completeness directly influences the quality of integration tests run against Gen-1 Fiserv-connected services, which do affect live cardholders. Gaps in mock fidelity can result in bugs escaping to production.

## Business Rules in Code

Business rules are encoded as WireMock request-matching conditions in the JSON mapping files:
- Requests are matched by HTTP method, URL path, and JSON body field values (e.g., `accountId` must equal a specific test value for the 200-response stub to activate).
- A companion 453 stub exists for each endpoint to simulate Fiserv processor decline conditions.
- Global response templating is enabled (`--global-response-templating`), meaning stubs may reference request data in responses.

## Regulatory Obligations

As a test-only service, the primary regulatory concern is data hygiene. The mock responses contain placeholder (`"string"`) values throughout. However, the cardholder balance status response includes fields such as `primaryCustomerSocialSecurityNumber`, `secondaryCustomerSocialSecurityNumber`, `primaryCustomerBirthDate`, and `secondaryCardholderBirthDate`. Even as synthetic stubs, care must be taken to ensure no real PAN, SSN, or personal data is committed into these JSON mapping files. Under PCI DSS Req 12.3 and Req 3.3, test environments must not use real production cardholder data. Current mappings use placeholder strings, which is compliant, but this must be governed through policy as new mappings are added.

## Key Business Risks

1. **Real data contamination**: Future contributors may inadvertently add WireMock mappings containing real account numbers, PANs, or SSNs sourced from production systems. There is no automated scanning in the current pipeline to prevent this.
2. **Mapping drift**: As Fiserv API contracts evolve (field additions, schema changes, new error codes), the WireMock stubs can silently diverge, causing tests to pass in QA against an outdated contract while failures occur in production.
3. **Scope creep into shared environments**: If this service is ever exposed on a shared or externally reachable network rather than isolated Docker-only internal environments, it could be mistaken for a real Fiserv endpoint or expose internal API schema details.
4. **No version pinning on WireMock image**: The docker-compose.yml uses `wiremock/wiremock:latest`, creating a risk that a future WireMock major-version release could break stub behavior or matching semantics without explicit upgrade management.
