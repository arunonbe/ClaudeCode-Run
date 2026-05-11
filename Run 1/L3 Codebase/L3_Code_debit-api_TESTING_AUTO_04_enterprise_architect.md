# Enterprise Architect Report — debit-api_TESTING_AUTO

## 1. Platform Generation Classification

| Attribute | Value |
|---|---|
| Generation | Gen-2 test tooling — prototype/exploratory quality |
| Runtime | JVM (Java 1.7 target; not containerized) |
| Test framework | TestNG + REST-Assured (industry standard, but outdated versions) |
| Integration style | Black-box SOAP testing via HTTP |
| Maturity | Low — 2 active tests, partial coverage, no CI integration |

---

## 2. Domain Context

**Domain**: Test Engineering  
**Scope**: Smoke / sanity testing of the Debit API SOAP endpoint in QA environment  
**Owner history**: Originally in GitLab under `northlane/testing/automation/api`; migrated to GitHub under Onbe

---

## 3. Role in Platform

This repository represents the **only automated test suite for the debit-api_API** that is committed to a repository. It is not production code and not integrated into the deployment pipeline.

```
Developer / QA Engineer (manual trigger)
  │
  ▼
debit-api_TESTING_AUTO (local Maven execution)
  │ SOAP HTTP
  ▼
debit-api_API (QA environment)
  │
  ▼
ECount Core2 QA Database
```

---

## 4. Dependencies

| Direction | System | Interface |
|---|---|---|
| External | Debit API QA endpoint | SOAP over HTTPS |
| Internal | QA SQL Server databases | Indirect (populated externally) |
| None | No other service dependencies | — |

---

## 5. Architectural Patterns

| Pattern | Implementation | Quality |
|---|---|---|
| Data-driven test | SOAP fixtures in `SoapRequest/` XML files | Partial — files are static, not parameterized |
| Priority-ordered test sequence | TestNG `priority=0`, `priority=1` on `BeginDebit`, `getDebit` | Weak — no shared state object between tests |
| Black-box HTTP test | REST-Assured `given().when().post().then()` chain | Correct pattern |

---

## 6. Current Status

| Aspect | Status |
|---|---|
| Active tests | 2 of 4 operations covered |
| CI integration | None (CodeQL only) |
| Last known branch | `master` (not `main`) |
| Test maintainability | Low |

---

## 7. Blockers for Improvement

| Blocker | Detail |
|---|---|
| Commented-out tests | `cancelDebit` and `commitDebit` must be restored and fixed |
| Java 1.7 target | Must be updated to Java 11+ minimum |
| Static test data | Must be replaced with dynamic test data generation or environment setup |
| No CI pipeline | Must be integrated into deployment pipeline as a post-deploy smoke test |
| Hardcoded URLs | Must be parameterized via environment variables or test profiles |
| No Pact consumer contract | debit-api_API has Pact configured but no consumer contract published from this repo |
