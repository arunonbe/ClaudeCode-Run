# account-management-api_TESTING_AUTO — Solution Architect View

## Technical Architecture

This is a **Java-based SOAP API test automation project** using the RestAssured HTTP client library with TestNG as the test framework. The architecture is minimal and flat:

```
account-management-api_TESTING_AUTO/
├── pom.xml                          Maven build descriptor
├── testng.xml                       TestNG suite definition (17 test classes)
├── SoapRequest/                     Static SOAP XML request fixtures (18 files)
├── src/
│   ├── AccMgmtAPI/                  14 test classes — prepaid account management
│   │   ├── CreateAccount.java
│   │   ├── CreateAccountLink.java
│   │   ├── AddFunds.java
│   │   ├── AssignPackage.java
│   │   ├── ActivationStatusInquiry.java
│   │   ├── CreateBulkOrder.java
│   │   ├── CreatePackage.java
│   │   ├── GetRequest.java
│   │   ├── LinkCard.java
│   │   ├── SetPin.java
│   │   ├── UpdateAccStatus.java
│   │   ├── UpdateReg.java
│   │   ├── WithdrawAch.java
│   │   └── WithdrawCheck.java
│   ├── AccMgmtAPI_Payout/           3 test classes — payout card management
│   │   ├── ActivateCard.java
│   │   ├── ActivationStatusInquiryPayout.java
│   │   └── SetPinPayout.java
│   └── JsonFiles/                   2 utility/experimental classes (not in test suite)
│       ├── CreateAccountJson.java
│       └── XmltoJson.java
└── .github/ / .gitlab-ci.yml        CI security scanning only (no test execution)
```

**Design pattern**: Each test class has a single `@Test` method. There is no shared base class, no page/service object pattern, no data provider, and no test hooks (`@BeforeClass`, `@AfterClass`, etc.). All 17 test classes are structurally identical — copy-paste clones differing only in the XML fixture filename, base URI, endpoint path, and the XPath expression used to extract the assertion value.

## API Surface

The test suite exercises **one SOAP service with two deployment instances**:

### Service 1: Prepaid Account Management
- **Base URI**: `https://webservice-qa.wirecard.com:4005/`
- **Endpoint**: `accountmanagementapiws/services/AccountManagementApiWebServices`
- **WSDL namespaces**:
  - `http://ws.accountmanagementapi.prepaid.citi.com`
  - `http://request.accountmanagementapi.prepaid.citi.com`
  - `http://domain.accountmanagementapi.prepaid.citi.com`
  - `http://common.accountmanagementapi.prepaid.citi.com`
- **Operations tested** (14): createAccountRequest, addFundsRequest, assignPackageRequest, activationStatusInquiryRequest, createBulkOrderRequest, createPackageRequest, serviceRequest, linkCardRequest, setPinRequest, updateAccountStatusRequest, updateRegistrationRequest, withdrawRequest (ACH), withdrawRequest (check), createAccountRequest (with link)

### Service 2: Payout Account Management
- **Base URI**: `https://webservice-qa.wirecard.com:4007/`
- **Endpoint**: `accountmanagementpayoutapiws/services/AccountManagementApiWebServices`
- **Operations tested** (3): activationStatusInquiryRequest, setPinRequest (payout), and a card activation variant

### Response Assertion Strategy
Two XPath patterns are used for success detection:
- `xml.getString("ns2:description")` — matched against `PROCESSED_SUCCESSFULLY` (used by: CreateAccount, CreateAccountLink, AddFunds, AssignPackage, GetRequest, LinkCard, ActivateCard)
- `xml.getString("sub_code")` — matched against `PROCESSED_SUCCESSFULLY` (used by: ActivationStatusInquiry, CreateBulkOrder, CreatePackage, SetPin, UpdateAccStatus, UpdateReg, WithdrawAch, WithdrawCheck, ActivationStatusInquiryPayout, SetPinPayout)

The inconsistency in XPath expressions across tests for what appears to be the same underlying response schema suggests the SOAP response structure varies by operation, or that different test authors made different assumptions about the response schema.

## Security Posture

### Critical Vulnerabilities

**1. SAD/PCI Data in Source Control (CRITICAL)**
- Files: `SoapRequest/ActivateCard.xml`, `SoapRequest/ActivationStatusInquiry.xml`, `SoapRequest/ActivationStatusInquiryPayout.xml`
- PANs committed: `5115531022041490` (BIN 511553 — MasterCard range), `5445446554206695` (BIN 544554 — MasterCard range)
- CVVs committed: `308`, `319`
- These values exist permanently in git history (`pack-b8cf506...` and `pack-2742099...` pack files in `.git/objects/pack/`)
- Remediation: Immediate git history rewrite (`git filter-repo` or BFG), replace with Luhn-valid synthetic test PANs, and conduct an investigation to determine if these are real cards.

**2. SSN and DOB in Source Control (CRITICAL)**
- File: `SoapRequest/UpdateReg.xml` line 48: `ssn` = `741859632`, line 30: `date_of_birth` = `01/04/1997`
- Remediation: Replace with synthetic values; rewrite git history.

**3. PIN Values in Source Control (HIGH)**
- Files: `SoapRequest/SetPin.xml` line 11, `SoapRequest/SetPinPayout.xml` line 10
- PIN `1234` paired with hardcoded account numbers. If the account numbers are real, this constitutes exposure of a PIN-account pair.

**4. Bank Routing and Account Number in Source Control (HIGH)**
- File: `SoapRequest/WithdrawAch.xml` lines 24–25
- `account_number`: `99087060252122451`, `routing_number`: `096001013`
- Remediation: Replace with synthetic bank details.

**5. Full Payload Logging of Sensitive Data (HIGH)**
- Every test class uses `given().log().all()` and `.log().all()` in the response chain (present in all 17 test methods at lines ~38–50)
- This will log complete SOAP request/response bodies — including all SAD and PII — to stdout and any connected CI log store on every test execution.
- Remediation: Use `given().log().ifValidationFails()` to suppress successful-run logging; implement a custom log filter to mask sensitive fields.

**6. No Authentication on Test Calls (MEDIUM)**
- No WS-Security (`<wsse:Security>` header), no API key header, no OAuth token, no Basic Auth is present in any fixture or Java class.
- Either the QA endpoint has no authentication (a security misconfiguration) or it uses network-level controls (IP whitelist/VPN) not visible in this codebase.

**7. Java 7 Runtime (HIGH)**
- `maven.compiler.source=1.7` and `maven.compiler.target=1.7` (`pom.xml` lines 9–10)
- Java 7 has known, unpatched CVEs. Running tests on a Java 7 JVM exposes the test runner to JVM-level vulnerabilities.
- Remediation: Update to Java 17 LTS or Java 21 LTS.

**8. Outdated Dependencies (MEDIUM)**
- `jackson-dataformat-xml` 2.9.0 (current: 2.17+) — multiple known CVEs in the 2.9.x series.
- `testng` 6.10 (current: 7.10+) — multiple known CVEs.
- `rest-assured` 4.4.0 (current: 5.x) — may have transitive dependency CVEs.
- Dependabot is configured (`dependabot.yml`) but PRs must be reviewed and merged.

**9. `.mvn/wrapper/settings.xml` (MEDIUM — unconfirmed)**
- This file was not read as it may contain Maven repository credentials. It should be reviewed for embedded passwords, tokens, or internal repository URLs.

## Technical Debt

| Debt Item | Location | Severity | Description |
|---|---|---|---|
| Copy-paste code duplication | All 17 test Java files | HIGH | All test classes are structurally identical. A base class with parameterised test method would reduce 17 × 90 LOC to ~20 LOC + 17 data rows. |
| Hardcoded base URI in every class | All 17 Java files, line 31 | HIGH | `RestAssured.baseURI` set inline in each test; no shared configuration. |
| Relative file paths (Windows-specific) | All Java files, e.g. `.\\SoapRequest\\CreateAccount.xml` | HIGH | Backslash-separated Windows paths will fail on Linux/macOS CI runners. Should use `File.separator` or `Paths.get()`. |
| Non-standard Maven source layout | `src/AccMgmtAPI/`, `src/AccMgmtAPI_Payout/` | HIGH | Maven will not compile these source files without additional `<sourceDirectory>` configuration. |
| Java 1.7 compiler target | `pom.xml` lines 9–10 | HIGH | 10+ years EOL; incompatible with modern frameworks. |
| TestNG 6.10 | `pom.xml` line 39 | MEDIUM | 8-year-old release; missing modern features (data providers, retry analyser improvements). |
| Dead `JsonFiles` package | `src/JsonFiles/` | MEDIUM | `CreateAccountJson` and `XmltoJson` are utility/experimental classes not wired into `testng.xml`. Dead code in production repository. |
| Dead/unused dependency | `org.eclipse.birt.runtime.3_7_1:org.w3c.dom.smil` | LOW | No usage found in any Java source file; transitive risk with no benefit. |
| Commented-out DOM parser code | All Java files, lines 71–81 | LOW | Identical commented-out block in all 17 test files; should be removed. |
| Typo in WSDL field | All `registation` XML elements | LOW | The SOAP element `<req:registation>` (missing second 'r') is hardcoded in all fixtures. This is a WSDL contract typo. |
| No negative/error path coverage | testng.xml, all test classes | HIGH | Zero tests for error conditions; the suite provides false confidence. |
| Static, non-idempotent test data | All XML fixtures | HIGH | Transaction IDs and partner user IDs are hardcoded; repeated runs fail. |
| `useSystemClassLoader=false` | `pom.xml` line 80 | LOW | Required workaround for Surefire/TestNG classloader issues; indicates version incompatibility between Surefire 3.0.0-M5 and TestNG 6.10. |

**Estimated total technical debt LOC**: ~1,500 LOC across 17 test files of which ~95% is duplicated boilerplate.

## Gen-3 Migration Requirements

To migrate this test suite to a Gen-3-compatible quality engineering posture:

1. **Replace SAD/PII with synthetic data** (mandatory compliance prerequisite before any other work):
   - Replace PANs with Luhn-valid synthetic numbers (e.g., BIN `411111` + generated last digits)
   - Replace CVVs with `000`
   - Replace SSN with `000-00-0000` or generated synthetic SSN
   - Replace PINs with `9999`
   - Replace bank account/routing numbers with synthetic NACHA test values
   - Rewrite git history to remove existing committed values

2. **Upgrade Java baseline**: Migrate from Java 7 to Java 17 or 21 LTS.

3. **Refactor test architecture**:
   - Introduce a `BaseTest` abstract class with `RestAssured.baseURI` configuration read from system properties or environment variables
   - Use TestNG `@DataProvider` or a YAML/JSON data-driven approach for test data
   - Implement a `SoapRequestBuilder` utility to construct requests programmatically with dynamic transaction IDs (e.g., UUID-based)
   - Use `given().log().ifValidationFails()` to suppress sensitive data in logs on passing tests

4. **Fix Maven source directory configuration**: Add `<sourceDirectory>` and `<testSourceDirectory>` to `pom.xml`, or restructure to standard Maven layout (`src/test/java/`).

5. **Fix path separators**: Replace `".\\SoapRequest\\..."` with `Paths.get("SoapRequest", "...").toString()` for cross-platform compatibility.

6. **Update all dependencies** to current stable versions.

7. **Implement CI test execution**: Add a `maven test` step to `.gitlab-ci.yml` so the suite actually runs in the pipeline.

8. **Expand test coverage**: Add negative path tests for at minimum: invalid account numbers, duplicate transaction IDs, insufficient funds, closed account operations, and authentication failure.

9. **Evaluate service under test**: Confirm whether `webservice-qa.wirecard.com` is still the correct QA target or whether the service has been migrated to Onbe-owned infrastructure. Update base URIs accordingly.

10. **Investigate REST/JSON migration**: The `JsonFiles` experimental code suggests the API may be evolving toward REST. If a REST interface is available or planned, migrate the test suite to target REST endpoints using standard RestAssured REST patterns.

## Code-Level Risks

| Risk | File(s) | Line(s) | Detail |
|---|---|---|---|
| PAN in committed file | `SoapRequest/ActivateCard.xml` | 5 | Full 16-digit card number in plaintext |
| PAN in committed file | `SoapRequest/ActivationStatusInquiry.xml` | 5 | Full 16-digit card number in plaintext |
| PAN in committed file | `SoapRequest/ActivationStatusInquiryPayout.xml` | 5 | Full 16-digit card number in plaintext |
| CVV in committed file | `SoapRequest/ActivateCard.xml` | 6 | 3-digit CVV in plaintext |
| CVV in committed file | `SoapRequest/ActivationStatusInquiry.xml` | 6 | 3-digit CVV in plaintext |
| CVV in committed file | `SoapRequest/ActivationStatusInquiryPayout.xml` | 6 | 3-digit CVV in plaintext |
| SSN in committed file | `SoapRequest/UpdateReg.xml` | 48 | 9-digit SSN `741859632` |
| DOB in committed file | `SoapRequest/UpdateReg.xml` | 30 | `01/04/1997` |
| Bank acct number in committed file | `SoapRequest/WithdrawAch.xml` | 24 | 17-digit bank account number |
| Bank routing number in committed file | `SoapRequest/WithdrawAch.xml` | 25 | `096001013` |
| PIN in committed file | `SoapRequest/SetPin.xml` | 11 | `1234` alongside account number |
| PIN in committed file | `SoapRequest/SetPinPayout.xml` | 10 | `1234` alongside account number |
| Employee email in source | `SoapRequest/CreateAccount.xml` | 46 | `gaurav.sharma@onbe.com` |
| Employee email in source | Multiple XML fixtures | Various | `gaurav.sharma@onbe.com` repeated |
| Employee email in source | `src/JsonFiles/XmltoJson.java` | 75 | `himanshu.goyal@external.wirecard.com` |
| Employee email in JSON inline string | `src/JsonFiles/CreateAccountJson.java` | 40 | `gaurav.sharma@onbe.com` |
| Full payload logging | All 17 Java test files | ~38,50 | `given().log().all()` + `.log().all()` logs SAD/PII |
| Windows-only file paths | All 17 Java test files | ~30 | `.\\SoapRequest\\` backslash paths |
| Hardcoded QA URI | All 17 Java test files | ~31 | `webservice-qa.wirecard.com` |
| No authentication | All 17 Java test files | N/A | No auth headers in any SOAP call |
| Jackson 2.9.0 CVEs | `pom.xml` | 20–23 | Known deserialization vulnerabilities in jackson 2.9.x |
