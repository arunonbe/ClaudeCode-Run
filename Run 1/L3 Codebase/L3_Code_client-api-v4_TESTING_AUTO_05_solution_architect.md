# client-api-v4_TESTING_AUTO — Solution Architect View

## Technical Architecture

This is a **Maven-based Java test automation project** using the RestAssured HTTP client to exercise a SOAP/XML web service. The architecture is minimal:

```
Project Layout
├── pom.xml                         Maven build descriptor
├── testng.xml                      TestNG suite configuration
├── .mvn/wrapper/
│   ├── maven-wrapper.properties    Pins Maven 3.9.1
│   └── settings.xml                Maven server/mirror config (contains committed secrets)
├── SoapRequest/                    Static SOAP XML fixture files (test input data)
│   ├── AddFundsV4.xml
│   ├── GetRequestStatusV4.xml
│   ├── UpdateAccStatusV4.xml
│   └── UpdateRegV4.xml
└── src/
    ├── ClientAPIV4/                TestNG test classes (one per operation)
    │   ├── AddFundsV4.java
    │   ├── GetRequestStatusV4.java
    │   ├── UpdateAccStatusV4.java
    │   └── UpdateRegV4.java
    └── JsonFiles/
        └── XmltoJson.java          Standalone XML-to-JSON utility (not a test)
```

All four test classes follow an **identical structural pattern** with no abstraction layer:
1. Open `FileInputStream` on a hardcoded relative fixture file path
2. Set `RestAssured.baseURI` to the hardcoded QA endpoint
3. Execute a `given().log().all()...post().then().statusCode(200).log().all()` chain
4. Extract the response as a string
5. Use `XmlPath` to extract `ns2:description`
6. Assert `PROCESSED_SUCCESSFULLY` via regex

There is no base class, no page object equivalent, no shared configuration, no helper utilities, and no externalized test data.

## API Surface

The system under test exposes a single SOAP endpoint:

- **Base URL**: `https://webservice-qa.wirecard.com:4005/`
- **Service path**: `clientapiws/services/ClientApiWebServices/v4`
- **Protocol**: SOAP 1.1 over HTTPS
- **Content-Type**: `text/xml`
- **SOAPAction**: `add` (sent for all four operations — likely copy-paste; the correctness of this for non-add operations is unverified)

Operations exercised:

| Operation | SOAP Body Root Element | Key Input Fields |
|---|---|---|
| Add Funds | `v4:addFundsRequest` | package_id, program_id, transaction_id, amount (100), comment |
| Get Request Status | `v4:getRequestStatusRequest` | package_id, program_id, transaction_id |
| Update Account Status | `v4:updateAccountStatusRequest` | package_id, program_id, transaction_id, status (CLOSED) |
| Update Registration | `v4:updateRegistrationRequest` | package_id, program_id, transaction_id, address, name, phones, ssn, dob, email |

Response assertion: HTTP 200, plus regex match on `ns2:description = "PROCESSED_SUCCESSFULLY"`.

No WSDL file is present in the repository. The fixture XMLs serve as the implicit contract documentation.

## Security Posture

### Critical Issues

**1. SSN committed to source control**
- File: `SoapRequest/UpdateRegV4.xml`
- A 9-digit value in the `<v41:ssn>` element appears consistent with a Social Security Number.
- Risk: Any person with repository read access can obtain this value. Git history retains it even after deletion from HEAD.
- Required action: Immediately determine if the value is real or synthetic. If real: trigger Onbe PII incident response, rewrite Git history, notify affected individual. If synthetic: still rewrite history as the pattern is indistinguishable from real data and constitutes a policy violation.

**2. Plaintext server credentials in settings.xml**
- File: `.mvn/wrapper/settings.xml`
- Three server blocks contain plaintext username/password credentials for Nexus/Maven repository servers (server IDs: `wirecard-mavenproxy-repository`, `nexus-qa`, `ecount.release`/`ecount.snapshot`).
- Passwords are not reproduced here. Rotate all affected credentials immediately and rewrite Git history.
- Required action: Replace with CI/CD environment variable references (e.g., `${env.NEXUS_PASSWORD}`) or remove the `settings.xml` from version control entirely in favour of CI-injected settings.

**3. Employee PII in fixture and source code**
- File: `SoapRequest/UpdateRegV4.xml` — named employee email in `<v41:e_mail>`
- File: `src/JsonFiles/XmltoJson.java` — named external employee email in inline string literal
- Required action: Replace with synthetic values; assess GDPR/CCPA notification obligations.

### Additional Security Observations

- **No authentication in SOAP fixtures**: All four `<soapenv:Header/>` elements are empty. The service may rely on network-level controls (VPN, IP allowlist) or may have no authentication — this cannot be determined from the test code alone. If the QA service is internet-accessible on port 4005 with no application-level authentication, it represents an exposed endpoint.
- **Full request/response logging**: `.log().all()` is active on every test call. In a CI environment, SOAP payloads (including the SSN value) will appear in build logs. CI log access controls must be reviewed.
- **TLS verification**: RestAssured by default validates TLS certificates. No explicit `.relaxedHTTPSValidation()` call is present, which is good — TLS verification is not disabled.
- **No WS-Security**: No message-level security (signing, encryption) is used in the SOAP headers.

## Technical Debt

| Item | Severity | Description |
|---|---|---|
| Committed SSN | Critical | PII in source control; Git history must be rewritten |
| Committed plaintext passwords | Critical | Credential secrets in source control |
| Committed employee email addresses | High | PII in source and fixture files |
| No base class / code duplication | Medium | All 4 test classes are copy-paste identical; common setup (baseURI, headers, log config) should be extracted to a base class or `@BeforeClass`/`@BeforeSuite` |
| Hardcoded endpoints | Medium | Environment cannot be switched without code changes |
| Hardcoded transaction IDs | Medium | Tests are not idempotent; repeat runs will fail |
| Hardcoded relative file paths | Medium | Windows path separator (`.\`) will fail on Linux CI runners |
| Wrong SOAPAction for non-add operations | Low-Medium | All tests send `SOAPAction: add`; UpdateAccStatus and UpdateReg likely require different SOAPAction values |
| Commented-out dead code | Low | Large blocks of DOM parsing code are commented out in all 4 test classes; should be removed |
| `XmltoJson.java` is not a test | Low | This utility class has a `main()` method and is in a non-test source directory (`src/JsonFiles`), but is not exercised by TestNG |
| Java 1.7 compile target | Medium | EOL since 2015; prevents use of modern Java language features and libraries |
| TestNG 6.10 (2016) | Medium | Outdated; upgrade to 7.x |
| REST Assured 4.4.0 | Low | Not the latest (5.x available); minor version upgrade recommended |
| Jackson 2.9.0 | Medium | Multiple CVEs in Jackson 2.9.x; upgrade to 2.15+ |
| org.eclipse.birt dependency | Low | `org.w3c.dom.smil` is included in pom.xml but appears unused in actual code |
| No negative test cases | Medium | Only happy-path (`PROCESSED_SUCCESSFULLY`) is tested; no error/rejection scenarios |
| Single assertion type | Medium | Only response description string is asserted; no field-level validation |

## Gen-3 Migration Requirements

To bring this test automation suite to a Gen-3 standard, the following work is required:

1. **Purge sensitive data from Git history**: SSN, email addresses, and plaintext passwords must be removed from all commits, not just HEAD.

2. **Externalise configuration**: Move `baseURI`, credential references, and file paths to environment variables or a `test.properties` file. Use CI/CD secret variables for credentials.

3. **Replace SOAP with REST (if the service migrates)**: If the underlying Client API v4 is re-exposed as a REST/JSON API in Gen-3, the fixture files and RestAssured calls must be rewritten accordingly.

4. **Synthetic test data**: Replace all real-looking PII (SSN, names, emails, phone numbers) with clearly synthetic values using a naming convention that signals test data (e.g., prefix `TEST_`, use `example.com` email domains).

5. **Dynamic transaction IDs**: Use `UUID.randomUUID()` or timestamp-based generation to ensure test idempotency across runs.

6. **Abstract common setup**: Create a `BaseTest` class with `@BeforeSuite` configuration for `baseURI`, headers, and logging policy.

7. **Cross-platform file paths**: Replace `.\SoapRequest\*.xml` with `System.getProperty("user.dir") + File.separator + "SoapRequest" + File.separator + filename` or use classpath-relative loading.

8. **Upgrade dependencies**: Java 11+, TestNG 7.x, REST Assured 5.x, Jackson 2.15+.

9. **Add CI test execution**: Add a `mvn test` job to the GitLab CI pipeline and/or GitHub Actions workflow so tests are automatically executed on commit/merge.

10. **Expand test coverage**: Add negative test cases, boundary value tests, and field-level response validation beyond the single `PROCESSED_SUCCESSFULLY` string check.

## Code-Level Risks

| Risk | Location | Impact |
|---|---|---|
| `FileInputStream` with relative path | All 4 test classes, line 30 | `FileNotFoundException` if working directory is not project root; fails silently on Linux CI if path separator is wrong |
| `Assert.assertTrue(false)` as failure mechanism | All 4 test classes | Test will fail with generic assertion error and no message; use `Assert.fail("Expected PROCESSED_SUCCESSFULLY but got: " + successMsg)` for debuggability |
| `IOUtils.toString(fis, "UTF-8")` — stream not closed | All 4 test classes | `FileInputStream` is never closed; minor resource leak per test execution |
| Dead code — DOM parser blocks | All 4 test classes (commented out) | Maintenance confusion; the `Document doc = builder.parse(response)` call would have failed anyway since `response` is a `String`, not an `InputStream` or `InputSource` |
| `XmltoJson.java` `main()` method | `src/JsonFiles/XmltoJson.java` | Not reachable via TestNG; only executable manually. Contains hardcoded PII (email address). |
| No timeout configuration | All 4 test classes | If the QA endpoint is slow or unresponsive, tests will hang indefinitely (RestAssured default timeout is effectively no timeout) |
