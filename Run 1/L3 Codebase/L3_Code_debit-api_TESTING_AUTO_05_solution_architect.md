# Solution Architect Report — debit-api_TESTING_AUTO

## 1. Architecture Overview

debit-api_TESTING_AUTO is a single-module Maven project containing **REST-Assured black-box SOAP tests** for the Debit API. It is not a deployed service. The architecture is simple:

```
src/
  DebitAPI/DebitAPI.java    — TestNG test class (2 active, 2 commented-out tests)
  JsonFiles/XmltoJson.java  — Utility (XML-to-JSON conversion; not used by active tests)
  main/java/module-info.java — Java module declaration (Java 9+ module system)

SoapRequest/
  beginDebit.xml            — SOAP envelope for beginDebit
  commitDebit.xml           — SOAP envelope for commitDebit (referenced by inactive test)
  cancelDebit.xml           — SOAP envelope for cancelDebit (referenced by inactive test)
  GetRequest.xml            — SOAP envelope for commitDebit re-submission (active "getDebit" test)

testng.xml                  — TestNG suite definition
```

---

## 2. API Coverage

| Target API Operation | Test Method | Status | Assertion |
|---|---|---|---|
| `beginDebit` | `BeginDebit()` (line 31) | Active | Response description matches `"Processed Successfully."` |
| `commitDebit` (idempotency) | `getDebit()` (line 145) | Active | Response description matches `"Transaction already commited."` |
| `cancelDebit` | Commented out (lines 74–108) | Inactive | — |
| `commitDebit` (success path) | Commented out (lines 110–143) | Inactive | — |

The test name `getDebit` is misleading — it actually tests a re-submitted commit call, not a `getStatus` operation.

---

## 3. Security Architecture

| Control | Status |
|---|---|
| HTTPS to QA endpoint | Yes — `https://webservice-qa.wirecard.com:4005/` |
| Request authentication | None observed — no Authorization or WS-Security headers |
| Test data masking | None — full SOAP payloads logged to console/CI |
| Credentials in repo | None |
| Test account PII/PAN | Account ID `0401611300000021` committed to XML fixtures — must be confirmed synthetic |

---

## 4. Technical Debt

| Item | Location | Severity |
|---|---|---|
| Java 1.7 compiler target | `pom.xml` lines 9–10 | High — must be updated |
| 2 of 4 tests commented out | `DebitAPI.java` lines 74–143 | High |
| No data cleanup / teardown | Entire test class | Medium |
| `getDebit` method name misleading | `DebitAPI.java` line 145 | Low |
| `XmltoJson.java` unused | `src/JsonFiles/XmltoJson.java` | Low — dead code |
| Deprecated TestNG 6.10 | `pom.xml` | Low |
| REST-Assured 4.4.0 (EOL) | `pom.xml` | Low |
| Hardcoded test data in XML files | `SoapRequest/*.xml` | Medium |

---

## 5. Gen-3 Migration Considerations

If the Debit API migrates from SOAP to REST, this test repo must be substantially rewritten:

1. Replace REST-Assured SOAP XML calls with JSON REST calls
2. Replace `SoapRequest/` XML fixtures with JSON request templates or a test data builder
3. Adopt Pact for consumer-driven contract testing against the Debit API
4. Parameterize all test data via environment variables
5. Integrate test execution into the CI pipeline (`deployment.yml` post-deploy stage)
6. Update Java target to 21 to match the service runtime

---

## 6. Recommended Immediate Actions

| Action | Priority |
|---|---|
| Confirm `account_id=0401611300000021` is synthetic test-only data (PCI scope check) | Critical |
| Uncomment and fix `cancelDebit` and `commitDebit` tests | High |
| Update Java compiler target to 17 or 21 | High |
| Add CI workflow to run tests post-deployment to QA | High |
| Parameterize QA URL via environment variable | Medium |
| Add log masking for account IDs in REST-Assured output | Medium |
