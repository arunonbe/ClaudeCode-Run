# client-api-v4_TESTING_AUTO — Enterprise Architect View

## Platform Generation (Gen-1/Gen-2/Gen-3)

**Generation: Gen-1 / Legacy**

Evidence supporting this classification:

- The SOAP service under test (`ClientApiWebServices/v4`) uses SOAP/XML messaging — a Gen-1 integration pattern that predates REST/JSON API conventions used in Onbe's newer platform generations.
- XML namespace roots reference `one.ecount.com` (the ecount brand, an Onbe predecessor brand), confirming the service's provenance in the legacy ecount platform.
- The prior QA hostname comments (`q-na-app01.nam.wirecard.sys`, `ppnaut.nam.wirecard.sys`) reference the Wirecard North America infrastructure, which was the operational platform prior to the Onbe rebrand.
- Maven compile target of Java 1.7 is consistent with software originally authored circa 2011–2015.
- TestNG 6.10 (2016) and REST Assured 4.4.0 targeting a SOAP service are consistent with a legacy-era test automation approach.

## Business Domain

**Prepaid Card Account Lifecycle Management — Client-Facing Operations**

The Client API v4 provides the B2B integration surface through which Onbe clients (corporate program sponsors) perform card operations on behalf of their cardholders:

- Fund loading (disbursements, incentives, refunds)
- Account status management (open, close, suspend)
- Cardholder registration data updates (name, address, contact details, identity fields)
- Transaction status inquiry

This maps to Onbe's core business domain of B2C disbursements and prepaid card management, delivered via a client-operated B2B API layer.

## Role in Platform

This repository plays a **quality assurance / test validation** role — it is not a production service. Its place in the platform architecture is:

```
[Onbe Client (Program Sponsor)]
         |
         | B2B SOAP/XML API call
         v
[Client API v4 Service] <-- this automation suite tests this service
  (webservice-qa.wirecard.com / production equivalent)
         |
         v
[Core Prepaid Platform (card account management, ledger, cardholder data)]
```

The automation suite validates the contract between the Client API v4 service and its callers, ensuring the four tested operations behave as expected in the QA environment before production deployment.

## Dependencies

### Upstream (services this suite depends on)

| Service | Hostname | Protocol | Notes |
|---|---|---|---|
| Client API v4 Web Service (QA) | webservice-qa.wirecard.com:4005 | SOAP over HTTPS | Primary SUT (system under test) |
| Onbe Internal Nexus (Maven artifacts) | d-na-stk01.nam.wirecard.sys:8081 | HTTPS | Internal Maven proxy; Wirecard-era hostname |
| GitHub Packages | maven.pkg.github.com/onbe/onbe_maven_releases | HTTPS | Onbe Maven package registry |

### Downstream (nothing; this is a test client)

No downstream services depend on this repository.

### Build-time Dependencies

- Apache Maven 3.9.1
- Java JDK (1.7 compile target; any modern JDK acceptable at build time)
- TestNG 6.10, REST Assured 4.4.0, Apache Commons IO 2.11.0, org.json 20211205

## Integration Patterns

- **Protocol**: SOAP 1.1 over HTTP/HTTPS (not REST)
- **Message format**: XML with SOAP envelope
- **Namespaces**:
  - Service namespace: `http://ws.clientapi.one.ecount.com/v4`
  - Request namespace: `http://request.clientapi.one.ecount.com/v4`
  - Common namespace: `http://common.clientapi.one.ecount.com/v4`
  - Domain type namespace: `http://v4.common.clientapi.one.ecount.com`
- **Transport security**: HTTPS (TLS) to the QA endpoint
- **Authentication**: No WS-Security headers observed in any fixture file. The SOAP headers are empty (`<soapenv:Header/>`). Authentication may be IP-based, network-level (VPN), or omitted in QA.
- **SOAPAction header**: All four tests send `SOAPAction: add` regardless of the actual operation — this is likely a residual copy-paste artifact and may or may not be significant depending on the server's routing logic.
- **Idempotency**: Transaction IDs are used as client-assigned idempotency keys, but are hardcoded in fixtures.

## Strategic Status

**Status: Legacy / Maintenance Mode (inferred)**

- The service under test (`ClientApiWebServices/v4`) references `ecount.com` namespaces — a brand that has been superseded by Onbe. This suggests the service is a legacy interface maintained for backward compatibility with existing clients.
- No active development is evident in this test automation repository. It appears to have been created during the Wirecard/Northlane/ecount-to-Onbe transition period.
- The commented-out internal hostnames (`q-na-app01.nam.wirecard.sys`, `ppnaut.nam.wirecard.sys`) confirm the original implementation predates the current Onbe infrastructure.
- The README is entirely boilerplate GitLab template content — no project-specific documentation has been added, suggesting the repository was not maintained as a long-term asset.
- GitLab origin URL (`gitlab.com/northlane/testing/automation/api/client-v4-api`) confirms origin from the Northlane era.

## Migration Blockers

Should Client API v4 be targeted for Gen-3 migration or decommission, the following blockers apply to this test automation suite:

| Blocker | Description | Remediation |
|---|---|---|
| SOAP-only test fixtures | All tests are SOAP/XML-based; no REST/JSON equivalents exist | Rewrite tests in REST Assured or equivalent targeting a REST API surface |
| Hardcoded QA endpoint | No environment abstraction; cannot point to a new environment without code changes | Externalise endpoint to a configuration property or environment variable |
| Hardcoded transaction IDs | Repeat runs produce duplicate-ID failures; not suitable for repeatable CI | Replace with dynamically generated unique IDs |
| SSN in committed fixture | Must be purged from Git history before migration or sharing | Git history rewrite + rotate any real data |
| Plaintext credentials in settings.xml | Must be moved to secrets management before any new platform onboarding | Migrate to CI/CD secret variables or vault integration |
| Java 1.7 target | Incompatible with Java 11/17 modern platform requirements without source changes | Upgrade compiler target and verify compatibility |
| TestNG 6.10 | End-of-active-support; may not be compatible with newer Java runtimes | Upgrade to TestNG 7.x or migrate to JUnit 5 |
| No CI test execution | Tests are never run automatically in the current pipelines | Add `mvn test` job to GitLab CI and/or GitHub Actions workflow |
| ecount.com SOAP namespaces | If the Gen-3 service uses different namespaces, all test fixtures must be regenerated | Align to new service WSDL upon migration |
