# Data Architect Report — debit-api_TESTING_AUTO

## 1. Data Stores

This repository has **no application data stores**. It is a test-automation harness that sends SOAP requests to the debit-api_API QA endpoint and asserts on the responses. All data persistence happens in the target service's databases.

---

## 2. Test Data

### 2.1 Committed Test Fixtures

| File | Sensitive Fields | Values Present |
|---|---|---|
| `SoapRequest/beginDebit.xml` | `program_id`, `account_id`, `transaction_id`, `amount` | program=`04016113`, account=`0401611300000021`, txn=`dbt20`, amount=`1000` |
| `SoapRequest/GetRequest.xml` | `program_id`, `account_id`, `transaction_id` | program=`04016113`, account=`0401611300000021`, txn=`dbt13` |
| `SoapRequest/commitDebit.xml` | Same as GetRequest.xml | Identical values |
| `SoapRequest/cancelDebit.xml` | `program_id`, `account_id`, `transaction_id` | Likely similar test values |

**Flag**: Account ID `0401611300000021` is committed to the repository in plain text. The format resembles a prepaid card account number (16-digit with embedded program prefix). Under PCI DSS Req 3.3, PANs must not be stored in non-production systems without masking. The value must be verified as synthetic/test-only and not a live cardholder account in any environment.

### 2.2 Runtime Data Flow

```
Test → SOAP request body (from XML file) → Debit API QA endpoint
     ← SOAP response → REST-Assured XmlPath parser → assertion on "description" field
```

No local data written. Full SOAP request and response logged to stdout via `.log().all()` in `DebitAPI.java` (lines 48–50, 162–164).

---

## 3. Sensitive Data Findings

| Finding | Location | Risk |
|---|---|---|
| Account ID `0401611300000021` in version control | `SoapRequest/beginDebit.xml:9`, `GetRequest.xml:9` | Potential PCI scope if real account |
| Transaction IDs `dbt13`, `dbt20` in version control | `beginDebit.xml:10`, `GetRequest.xml:9` | Low sensitivity but pollutes QA DB if reused |
| Full SOAP response logged to console | `DebitAPI.java:50`, `DebitAPI.java:164` | Balance/account data from response exposed in CI logs |
| QA endpoint URL hardcoded | `DebitAPI.java:35`, `DebitAPI.java:150` | `https://webservice-qa.wirecard.com:4005/` reveals infrastructure details in code |

---

## 4. Encryption

Not applicable — test harness only. No keys, certificates, or credentials are present in this repository.

---

## 5. Data Quality / Test Data Management

- Test data is **static and hardcoded** — no data factory or test data management strategy.
- Dependency on pre-existing QA data means tests are **not idempotent**; re-running `BeginDebit()` may fail if `transaction_id=dbt20` was already processed in QA.
- The `getDebit` test expects `"Transaction already commited."` which means it relies on the prior test run having committed `dbt13` — tests are **sequentially dependent** (TestNG `priority` used, but not guaranteed across test suites).

---

## 6. Compliance Gaps

| Gap | Standard | Detail |
|---|---|---|
| Account ID committed to repo | PCI DSS Req 3.3, 3.4 | Account numbers must not appear in version control unless confirmed as non-production synthetic data |
| Full response body logged in CI | PCI DSS Req 3.5 | If response contains balance or account details, these appear in CI build logs |
| No test data rotation strategy | PCI DSS Req 6.5 | Static test account/transaction IDs with no expiry or rotation mechanism |
