# DevOps & Operations Report — debit-api_TESTING_AUTO

## 1. Build System

| Attribute | Value |
|---|---|
| Build tool | Maven (Maven Wrapper `mvnw`) |
| Java compiler target | 1.7 (`pom.xml` lines 9–10) — **critical mismatch with Java 21 runtime** |
| Artifact | `RestAssuredAPI:RestAssuredAPI:0.0.1-SNAPSHOT` |
| Test framework | TestNG 6.10 + REST-Assured 4.4.0 |
| Test runner | Maven Surefire 3.0.0-M5 with `testng.xml` suite file |
| Resources directory | `src/Resources` (with filtering enabled) |

### Key Dependencies

| Library | Version | Purpose |
|---|---|---|
| `io.rest-assured:rest-assured` | 4.4.0 | HTTP client + XML path assertions |
| `org.testng:testng` | 6.10 | Test runner |
| `com.fasterxml.jackson.dataformat:jackson-dataformat-xml` | 2.9.0 | XML deserialization |
| `org.json:json` | 20211205 | JSON handling |
| `commons-io:commons-io` | 2.11.0 | File I/O (reading XML fixtures) |

---

## 2. CI/CD

### 2.1 GitHub Actions
One workflow is present:
- `.github/workflows/codeql.yml` — CodeQL SAST analysis only
- **No test execution workflow exists** — tests are not run in CI

### 2.2 GitLab CI
`.gitlab-ci.yml` is present but contains only a default template comment. No pipelines are defined. The README references the original GitLab source at `https://gitlab.com/northlane/testing/automation/api/debit-api.git`.

### 2.3 TestNG Suite
`testng.xml` controls test execution. Content was not read but inferred to include the `DebitAPI` test class. Tests must be run manually:
```bash
mvn test -s ./.mvn/wrapper/settings.xml
```

---

## 3. Configuration Management

All configuration is **hardcoded in source code**:

| Config Item | Hardcoded Location |
|---|---|
| Target URL | `DebitAPI.java` lines 35, 150: `https://webservice-qa.wirecard.com:4005/` |
| SOAP path | `DebitAPI.java` lines 47, 161: `debitapiws/services/DebitService` |
| Test account/program IDs | `SoapRequest/` XML fixture files |

There is no externalized configuration, no `.properties` file for environment switching, and no parameterized test data.

---

## 4. Observability

| Signal | Mechanism |
|---|---|
| Test output | TestNG console output + REST-Assured `.log().all()` dumps full request/response |
| CI reporting | TestNG produces Surefire XML reports (if CI ran tests) |
| No structured logging | System.out / TestNG assertion output only |

---

## 5. Infrastructure

The test harness has no infrastructure of its own. It depends entirely on:
- Network access to `webservice-qa.wirecard.com:4005` (QA environment)
- A pre-populated QA database with the test program/account data

---

## 6. Operational Risks

| Risk | Severity | Detail |
|---|---|---|
| Java 1.7 compiler target | High | Incompatible with modern Maven/JDK 21 environments; build may fail or produce incompatible bytecode |
| No CI test execution | High | Tests are never automatically run; regressions go undetected |
| Hardcoded QA URL | Medium | Any QA environment change breaks tests without code change |
| Sequential test dependency | Medium | `getDebit` depends on prior state left by `BeginDebit`; test ordering issues possible |
| Missing test coverage | High | `cancelDebit` and `commitDebit` are commented out |
| TestNG 6.10 EOL | Low | Current TestNG is 7.x; dependency is outdated |
| REST-Assured 4.4.0 | Low | Current is 5.x; outdated dependency |
| No test data teardown | Medium | Each test run creates/modifies data in QA; no cleanup step |
