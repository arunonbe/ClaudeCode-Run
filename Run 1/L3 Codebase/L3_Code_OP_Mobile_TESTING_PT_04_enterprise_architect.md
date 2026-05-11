# Enterprise Architect Report — OP_Mobile_TESTING_PT

## Source Availability Note

No source files are present in this repository clone. This analysis is based on the repository name, naming conventions observed across the Onbe 363-repo estate, and contextual knowledge of the OnePlatform mobile and testing architecture.

## Platform Generation

**Indeterminate — testing tooling for Gen-3 (OnePlatform) target.** The `OP` prefix indicates this is associated with OnePlatform, which is Gen-3. However, the testing tooling itself may not be Java/Kotlin/Spring Boot — it could be JMeter (Java-based), k6 (Go/JavaScript), Postman/Newman (JavaScript), Python, or other testing frameworks that exist outside the generational classification of the application under test.

The target system being tested (OnePlatform Mobile) is Gen-3.

## Role in Platform Architecture

A testing repository for the OnePlatform mobile surface serves a quality assurance and security validation role in the Gen-3 SDLC. Its position in the platform:

```
[SDLC / Release Pipeline]
    --> [OP_Mobile_TESTING_PT] (testing tooling)
        --> [OnePlatform Mobile APIs (test/QA environment)]
            --> [Gen-3 Backend Services]

[Security Governance]
    --> [OP_Mobile_TESTING_PT] (pen test artifacts)
        --> [PCI DSS Req 11.4 Compliance Evidence]
```

This repository is an enabling function — it does not deliver business value directly but enables the validation and security assurance of systems that do.

## Integration Patterns (Inferred)

- **HTTP/REST integration:** Test scripts target OnePlatform mobile API endpoints via HTTP/HTTPS
- **Authentication integration:** Tests authenticate using test credentials via OAuth 2.0 / API key patterns consistent with OnePlatform's authentication model
- **Result integration:** Test results feed into CI/CD release gates and/or vulnerability management systems (Jira, DefectDojo)

## External Dependencies (Inferred)

| Dependency | Purpose |
|---|---|
| Testing framework (JMeter/k6/Gatling/Postman) | Test execution |
| CI/CD platform (GitHub Actions) | Automated test execution |
| OnePlatform test/QA environment | Target under test |
| Azure infrastructure (QA) | Hosts target services |
| Vulnerability management tool (Jira/DefectDojo) | Tracks pen test findings |

## OnePlatform Mobile Architecture Context

The OnePlatform mobile application is Onbe's cardholder-facing mobile interface, enabling:
- Prepaid card management (balance inquiry, transaction history)
- Disbursement acceptance (push-to-card, ACH initiation)
- Card activation and PIN management
- Customer profile management

The mobile API surface is a high-value attack target because it directly interfaces with cardholder data and payment operations. Performance testing validates that the API can handle cardholder demand; penetration testing validates that the API is not exploitable by adversarial actors.

## Strategic Status

**Supporting infrastructure for PCI DSS compliance and release quality gates.**

The empty state of this repository is a strategic concern:
- If penetration testing is not documented in version control, PCI DSS Req 11.4 compliance evidence may be insufficient for QSA review.
- If performance testing is not automated in CI/CD, performance regressions may go undetected until production incidents.
- If the repository was created as a placeholder but testing is occurring informally (local scripts, manual execution, undocumented findings), the organization lacks the visibility and control expected of a PCI DSS Level 1 service provider.

**Recommendation:** This repository should be populated with at minimum: test plan documentation, synthetic test data definitions, CI/CD pipeline configuration, and (for pen testing) a findings register. The repository itself should be subject to the same access controls as other security-sensitive repositories (limited write access, required PR reviews, audit logging).
