# account-management-api_TESTING_AUTO — Enterprise Architect View

## Platform Generation (Gen-1/Gen-2/Gen-3)

**Classification: Gen-1**

Indicators:
- Targets a SOAP/XML web service interface (`AccountManagementApiWebServices`) — classic enterprise SOA/WS-* architecture, characteristic of Gen-1 platform services.
- WSDL XML namespace roots: `http://ws.accountmanagementapi.prepaid.citi.com`, `http://request.accountmanagementapi.prepaid.citi.com`, `http://domain.accountmanagementapi.prepaid.citi.com`, `http://common.accountmanagementapi.prepaid.citi.com` — the `citi.com` namespace root indicates this service was originally developed during or for the Citi prepaid partnership era, which predates Onbe's rebranding and platform modernisation.
- Java 1.7 compiler target (EOL 2015).
- Non-standard Maven project structure; Eclipse `.classpath`-driven development.
- TestNG 6.10 (released ~2016).
- REST-Assured 4.4.0 used to call SOAP endpoints — a workaround indicative of no modern SOAP client (JAX-WS) adoption.
- No containerisation, no cloud-native configuration, no feature flags, no API gateway integration.

## Business Domain

**Prepaid Card Account Lifecycle Management**

This test suite exercises core lifecycle operations for Onbe's prepaid card products. It spans two product lines:

1. **Standard Prepaid** (`AccMgmtAPI` package): Account creation, funding, card package management, registration, PIN, ACH/check withdrawal, account status.
2. **Payout Prepaid** (`AccMgmtAPI_Payout` package): Card activation, activation status, PIN set — a distinct product with its own service endpoint (port 4007, path `accountmanagementpayoutapiws`).

The domain covers:
- **Cardholder onboarding** (CreateAccount, AssignPackage, CreatePackage, CreateAccountLink)
- **Fund management** (AddFunds, WithdrawAch, WithdrawCheck)
- **Card operations** (LinkCard, ActivateCard, SetPin, ActivationStatusInquiry)
- **Account maintenance** (UpdateReg, UpdateAccStatus, GetRequest, CreateBulkOrder)

## Role in Platform

This repository is a **QA test automation client** — it has no runtime role in the Onbe production platform. Its role is:

- **Regression testing** of the Account Management API web service contract
- **Smoke testing** of QA environment connectivity after deployments
- **Test evidence** generation for release sign-off processes

The system under test (`accountmanagementapiws`) is a backend platform service that is the canonical source of truth for account state, card provisioning, and cardholder registration within the prepaid card platform.

The existence of a separate `_Payout` package and a distinct service port (4007) indicates the platform has at least two separate deployment units for prepaid vs. payout product lines at the service layer.

## Dependencies

### Runtime Dependencies (pom.xml)
| Dependency | Version | Purpose |
|---|---|---|
| `io.rest-assured:rest-assured` | 4.4.0 | HTTP client for SOAP calls |
| `com.fasterxml.jackson.dataformat:jackson-dataformat-xml` | 2.9.0 | XML-to-JSON conversion (utility class only) |
| `org.testng:testng` | 6.10 | Test framework and runner |
| `org.json:json` | 20211205 | JSON/XML utility (`XmltoJson.java`) |
| `commons-io:commons-io` | 2.11.0 | File reading (`IOUtils.toString`) |
| `org.eclipse.birt.runtime.3_7_1:org.w3c.dom.smil` | 1.0.0 | SMIL DOM API (unused in practice — dead dependency) |

### External Service Dependencies
| Service | Host | Port | Protocol |
|---|---|---|---|
| Account Management API (prepaid) | `webservice-qa.wirecard.com` | 4005 | HTTPS/SOAP |
| Account Management API (payout) | `webservice-qa.wirecard.com` | 4007 | HTTPS/SOAP |

The `wirecard.com` domain dependency is the single largest operational risk. Wirecard AG was declared insolvent in June 2020. If this QA environment has been migrated to Onbe-owned infrastructure and re-hosted under a different domain, the codebase has not been updated to reflect it (all `baseURI` assignments still reference `wirecard.com`).

### Development/Infrastructure Dependencies
- GitLab repository (origin: `gitlab.com/northlane/testing/automation/api/account-management-api`)
- GitHub repository (Onbe GitHub org — CodeQL workflow references `Onbe/om-ci-setup`)
- Self-hosted GitHub Actions runners (`self-hosted`, `X64`, `Linux`, `ubuntu-docker`)

Note: The GitLab remote references `northlane` — this is the trading name under which Wirecard's Australian/APAC operations were conducted, suggesting this codebase may have originated in or been maintained by the Northlane entity.

## Integration Patterns

- **SOAP over HTTP (SOA/WS-*)**: All integration uses SOAP 1.1 envelopes (`http://schemas.xmlsoap.org/soap/envelope/`) with a generic `SOAPAction: add` header. This is a legacy SOA integration pattern.
- **Synchronous request/response**: All test calls are synchronous HTTP POST with immediate response parsing. No async patterns, message queuing, or event-driven integration.
- **Static XML fixture files**: Request payloads are loaded from filesystem-resident XML files, not generated programmatically. This is a fragile integration pattern — any field addition or structural change to the SOAP contract requires manual fixture file updates.
- **Partial XML-to-JSON exploration**: `JsonFiles/CreateAccountJson.java` and `JsonFiles/XmltoJson.java` contain experimental code for converting SOAP XML to JSON. This appears to be exploratory/utility code, not part of the test suite (neither class is referenced in `testng.xml`). It may indicate early-stage investigation into a REST/JSON migration of the API interface.
- **No authentication mechanism visible**: No WS-Security headers, no API keys, no OAuth tokens are present in any fixture or test class. Either the QA endpoint is open (unauthenticated) or authentication is handled at the network layer (VPN/IP whitelisting).

## Strategic Status

**Status: Legacy / Maintenance Mode — Low Active Investment**

Evidence:
- Java 1.7 compiler target has not been updated (EOL since 2015).
- TestNG 6.10 has not been updated (current is 7.x).
- No functional test coverage evolution beyond the initial test set.
- Commented-out alternative base URIs suggest development occurred across multiple environments but the suite was never productionised for multi-environment support.
- The `JsonFiles` package contains experimental, non-integrated code suggesting the author was exploring REST/JSON patterns but did not complete the migration.
- GitLab CI does not actually run the tests — no automated execution pipeline.
- The WSDL namespace roots still reference `citi.com`, indicating the underlying service has not been rebranded/rehosted since original development.
- README is the default GitLab-generated template — no project-specific documentation was ever written.

This suite likely represents initial automation work done to satisfy a testing requirement but was never matured into a production-quality, continuously-running regression suite.

## Migration Blockers

For any Gen-2/Gen-3 migration of the Account Management API test automation:

1. **SOAP-first contract**: The system under test exposes only SOAP/XML interfaces. A Gen-3 migration would require the underlying service to expose REST/JSON or GraphQL APIs. The `JsonFiles` experiment suggests this was being explored.
2. **Wirecard namespace coupling**: All WSDL namespace URIs are `*.citi.com` / `*.wirecard.com`. Replacing the backend would require namespace updates across all 18 fixture files and potentially the WSDL contract itself.
3. **Hardcoded test data**: Account numbers, program IDs, and transaction IDs are hardcoded. A proper Gen-3 test suite would require a test data management system (TDM) or data factory approach.
4. **Java 7 baseline**: Modern test frameworks (JUnit 5, TestNG 7.x, RestAssured 5.x) require Java 8 minimum. The codebase must be upgraded before modern tooling can be adopted.
5. **PII/SAD remediation prerequisite**: Before any migration or re-platforming effort proceeds, the sensitive data in the fixture files (PANs, CVVs, SSN, bank account details) must be replaced with synthetic test data and the git history must be scrubbed. This is a mandatory compliance prerequisite, not a nice-to-have.
6. **No environment abstraction**: Adding non-QA environment support (e.g., staging, production smoke) requires architectural refactoring — externalising base URIs, credentials, and test data to configuration.
7. **Dead dependency**: `org.eclipse.birt.runtime.3_7_1:org.w3c.dom.smil` appears to be an unused, legacy dependency that may introduce transitive vulnerabilities.
