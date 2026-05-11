# Solution Architect View — cs-api_TESTING_AUTO

## Architecture
The test suite is a standalone Maven project with no runtime container. Its structure:

```
cs-api_TESTING_AUTO/
├── pom.xml                  (Maven project, Java 1.7, RestAssured + TestNG)
├── testng.xml               (Suite definition — 9 test classes, sequential except V1 parallel)
├── SoapRequest/             (8 XML fixture files — SOAP envelopes)
│   ├── AccountInquiryV1.xml
│   ├── AccountInquiryV3.xml  ← contains PAN (CRITICAL)
│   ├── AuthenticationReq.xml ← contains credentials
│   ├── ForgotUserName.xml
│   ├── PayoutAccountInquiry.xml ← contains DDA number
│   ├── RegistrationReq.xml  ← contains PAN + CVV + credentials
│   ├── ReissueCard.xml
│   ├── UpdatePasswordReq.xml
│   └── UpdateRegReq.xml     ← contains PII
└── src/
    ├── CSAPI/               (3 test classes: V1 inquiry, V3 inquiry, reissue)
    ├── CSAPI_Payout/        (6 test classes: auth, forgot-user, payout inquiry, reg, updatepwd, updatereg)
    └── JsonFiles/           (XmltoJson utility — unused in suite)
```

## API Surface Tested
- SOAP 1.1 over HTTPS
- Endpoint pattern: `{base-url}/{context}/services/AccountManagement`
- No OAuth, no JWT, no API key in HTTP headers — authentication is via application_id in the SOAP body
- Content-Type: `text/xml`
- SOAPAction header: `add` (used uniformly; not operation-specific — a potential interoperability concern)

## Security Analysis
| Finding | Severity | Description |
|---|---|---|
| PAN in source control | CRITICAL | Full card number in AccountInquiryV3.xml and RegistrationReq.xml |
| CVV in source control | CRITICAL | 3-digit CVV in RegistrationReq.xml |
| Credentials in source control | HIGH | Username + password in AuthenticationReq.xml and RegistrationReq.xml |
| DDA number in source control | HIGH | Account number in PayoutAccountInquiry.xml |
| PII in source control | HIGH | Name, address, phone, email in UpdateRegReq.xml |
| Application IDs in source control | MEDIUM | API keys in multiple XML files — rotate if any are live |
| Full request/response logging | MEDIUM | `.log().all()` will dump PAN/CVV to stdout during test runs |
| Hardcoded QA URL | LOW | No TLS certificate pinning, no timeout configuration |

## Technical Debt
1. Java 1.7 target — 11 years behind current LTS (Java 21 used in production repos)
2. TestNG 6.10 — multiple major versions behind current (7.x)
3. RestAssured 4.4.0 — not at latest, but not critically outdated
4. Jackson 2.9.0 — outdated, known CVEs in older 2.9.x releases; should upgrade to 2.15+
5. No abstraction layer — each test class duplicates the identical HTTP invocation pattern
6. No page-object or fixture-object pattern — changing the endpoint URL requires editing every class
7. Dead code: `XmltoJson.java` is present but not included in the TestNG suite
8. Commented-out DOM parser code in multiple test classes — cleanup needed

## Gen-3 Migration Path
If the CS API family migrates fully to the v3 Spring Boot architecture, this test suite should be replaced with:
1. **Contract tests** using Pact (already referenced in cs-api-v3_API deployment workflow via `PACT_PACTICIPANT`)
2. **Integration tests** using WireMock stubs (already a dependency in cs-api-v3_API pom.xml)
3. **Synthetic fixture data** generated programmatically using Luhn-valid test card numbers and masked identifiers
4. **Environment-aware configuration** using Spring profiles or environment variable injection

## Code-Level Risks
1. **NullPointerException risk**: `xml.getString("completion_message")` will throw if the response does not contain the expected element — no null check.
2. **File path fragility**: `new FileInputStream(".\\SoapRequest\\AccountInquiryV1.xml")` uses a relative path; tests will fail if executed from any directory other than the repo root.
3. **No exception-specific handling**: All exceptions propagate as `throws Exception` — no distinction between network failures, assertion failures, and parse errors.
4. **Pattern.compile inside test method**: The regex compilation (`Pattern.compile("OK")`) happens on every test execution — trivial overhead but reflects lack of test design standards.
