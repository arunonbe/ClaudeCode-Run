# Business Analyst Report — debit-api_TESTING_AUTO

## 1. Business Purpose
debit-api_TESTING_AUTO is a **manual/smoke-test automation harness** for the Debit API SOAP service. It is not a production service. Its purpose is to provide developers and QA engineers with scripted REST-Assured test cases that can be run against the QA environment SOAP endpoint to verify that core debit operations (Begin Debit, Commit Debit, Get Status) work end-to-end.

The repository is in an early/prototype state — most test methods are commented out and only two live tests (`BeginDebit` and `getDebit`) are active.

---

## 2. Capabilities

| Test Method | Class | Operation Tested | Status |
|---|---|---|---|
| `BeginDebit()` | `DebitAPI.java` (line 31) | `beginDebit` SOAP action | Active (`@Test priority=0`) |
| `getDebit()` | `DebitAPI.java` (line 145) | Re-submits a commit request to validate "Transaction already committed" guard | Active (`@Test priority=1`) |
| `cancelDebit()` | `DebitAPI.java` (lines 74–108) | `cancelDebit` SOAP action | Commented out |
| `commitDebit()` | `DebitAPI.java` (lines 110–143) | `commitDebit` SOAP action | Commented out |

The test framework uses TestNG + REST-Assured for HTTP calls and Jackson XML for parsing.

---

## 3. Key Entities Referenced

| Entity | Value in Test Fixtures |
|---|---|
| Program ID | `04016113` (in `SoapRequest/beginDebit.xml` line 6) |
| Account ID | `0401611300000021` (`beginDebit.xml` line 9) |
| Transaction ID | `dbt20` (`beginDebit.xml` line 10) / `dbt13` (`GetRequest.xml` line 9) |
| Amount | `1000` (cents = $10.00; `beginDebit.xml` line 13) |
| Target environment | QA (`https://webservice-qa.wirecard.com:4005/`) |
| SOAP path | `debitapiws/services/DebitService` |

**Sensitive Data Notice**: The SOAP XML test fixture files (`SoapRequest/beginDebit.xml`, `GetRequest.xml`) contain **committed test account IDs and program IDs**. Account ID `0401611300000021` is present in version control. These appear to be test/demo values but should be confirmed as non-production and subject to data-at-rest review per PCI DSS requirements.

---

## 4. Business Rules Tested

1. **Begin Debit success path**: Expects HTTP 200 and response body containing `"Processed Successfully."` (`DebitAPI.java` line 58).
2. **Idempotency guard**: Re-submitting a previously committed transaction ID returns `"Transaction already commited."` (note: typo matches the service-side `ServiceFailureExceptionType.TRANSACTION_ALREADY_COMMITED`).

---

## 5. Business Flows Covered

```
Test harness
  → POST https://webservice-qa.wirecard.com:4005/debitapiws/services/DebitService
      [SOAP beginDebitRequest with program=04016113, account=0401611300000021, amount=1000]
  ← HTTP 200 + SOAP response with "Processed Successfully."
  ASSERT: response contains "Processed Successfully."

Test harness (getDebit)
  → POST same endpoint [SOAP commitDebitRequest, re-using prior transaction_id dbt13]
  ← HTTP 200 + response with "Transaction already commited."
  ASSERT: response contains "Transaction already commited."
```

---

## 6. Compliance Risks (Testing Repo)

| Risk | Severity | Detail |
|---|---|---|
| Test account ID in version control | Medium | `account_id=0401611300000021` committed in `SoapRequest/beginDebit.xml` and `GetRequest.xml`; if this maps to a real cardholder account in any environment, it violates PCI DSS Req 3.4 |
| Hardcoded QA URL in test code | Low | `https://webservice-qa.wirecard.com:4005/` hardcoded in `DebitAPI.java` (lines 35, 150); cannot be overridden without code change |
| No credential management | Low | No auth headers in test requests; relies on network trust |
| No sensitive-value masking | Low | REST-Assured `.log().all()` logs full request/response bodies to console/CI |

---

## 7. Risks

| Risk | Severity | Detail |
|---|---|---|
| Only 2 of 4 operations tested | High | `cancelDebit` and `commitDebit` tests commented out; reduces regression coverage |
| Tests tightly coupled to QA env data | High | Program `04016113` and account `0401611300000021` must exist in QA DB |
| No CI pipeline integration | Medium | No GitHub Actions workflow runs the tests; `.gitlab-ci.yml` is a copy but empty/default |
| Java 1.7 compiler target | Medium | `pom.xml` targets Java 1.7 while the API runs Java 21; potential compatibility gaps |
| No assertion on error scenarios | Medium | Tests do not cover insufficient funds, invalid program, or inactive account paths |
| GitLab README template content | Low | README contains default GitLab template text; no actual setup instructions |
