# DevOps & Operations View — cs-api_TESTING_AUTO

## Build System
- **Build tool**: Maven (via `mvnw` / `mvnw.cmd` wrapper)
- **Artifact**: `RestAssuredAPI-0.0.1-SNAPSHOT.jar` (no WAR/container packaging)
- **Java version**: Compiled at source/target 1.7 (severely outdated)
- **Test framework**: TestNG 6.10
- **Key dependencies**:
  - `rest-assured 4.4.0` — HTTP client for SOAP calls
  - `testng 6.10` — test runner
  - `jackson-dataformat-xml 2.9.0` — XML parsing
  - `commons-io 2.11.0` — file I/O for reading XML fixtures
  - `org.json 20211205` — JSON utility

## Test Execution
```bash
mvn test
# Runs the TestNG suite defined in testng.xml
# Requires network access to webservice-qa.wirecard.com:4005 and :4007
```
The Maven Surefire plugin (3.0.0-M5) is configured to use `testng.xml` as the suite definition.

## Configuration
- **Base URLs**: Hardcoded in each Java test class — `https://webservice-qa.wirecard.com:4005/` and `https://webservice-qa.wirecard.com:4007/`
- **Request payloads**: Loaded from relative file paths (`.\SoapRequest\*.xml`) — tests must be run from the repository root directory
- **No environment variable support**: No Spring Boot config, no `.env`, no properties files referenced at runtime

## CI/CD
| Platform | File | Purpose |
|---|---|---|
| GitLab CI | `.gitlab-ci.yml` | SAST scanning only (GitLab Security/SAST template); no test execution stage |
| GitHub Actions | `.github/workflows/codeql.yml` | CodeQL static analysis on a weekly schedule (Thursday 05:28 UTC); self-hosted Linux runner |
| GitHub Actions | `.github/dependabot.yml` | Automated dependency version updates |

**Gap**: There is no CI pipeline stage that actually executes the TestNG test suite. Tests appear to be run manually only.

## Observability
- No application monitoring, metrics, or tracing.
- Test output is printed to console via RestAssured's `.log().all()` calls on both request and response — this will print full request and response bodies including any PAN/CVV values to log output.
- No structured logging or log aggregation.

## Infrastructure Dependencies
- Network connectivity to `webservice-qa.wirecard.com` on ports 4005 and 4007 is required for any test execution.
- This is a legacy hostname from the Wirecard era; its DNS/routing must be confirmed active.
- Tests are designed for a QA environment only — no production targeting should occur.

## Risks
1. **Network dependency**: Tests cannot run in isolated CI environments (no mocking, no WireMock stubs).
2. **Log leakage of sensitive data**: `given().log().all()` will write full SOAP request bodies — including any PAN, CVV, and password values — to stdout/log files during test runs.
3. **Hardcoded legacy hostname**: `webservice-qa.wirecard.com` may no longer be valid post-brand migration to Onbe/Northlane.
4. **No retry logic**: A single network failure causes test failure with no retry.
5. **No test reporting**: No Surefire HTML reports, no Allure, no test result publishing.
6. **Java 1.7 target**: Modern JVM versions may produce deprecation warnings or compatibility issues; the Java ecosystem support for 1.7 ended in 2015.
