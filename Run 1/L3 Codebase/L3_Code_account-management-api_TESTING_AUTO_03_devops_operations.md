# account-management-api_TESTING_AUTO — DevOps & Operations View

## Build & Packaging

- **Build Tool**: Apache Maven. Wrapper scripts (`mvnw`, `mvnw.cmd`) are present for hermetic builds without a pre-installed Maven.
- **Maven Wrapper version**: Defined in `.mvn/wrapper/maven-wrapper.properties`.
- **`pom.xml` coordinates**:
  - `groupId`: `RestAssuredAPI`
  - `artifactId`: `RestAssuredAPI`
  - `version`: `0.0.1-SNAPSHOT`
- **Java source/target**: Java 1.7 (`maven.compiler.source` and `maven.compiler.target` both set to `1.7` in `pom.xml` lines 9–10). Java 7 is end-of-life; this is a significant operational risk.
- **Test framework**: TestNG 6.10 (`pom.xml` line 39) with `maven-surefire-plugin` 3.0.0-M5.
- **Test execution**: `mvn test` triggers Surefire which loads `testng.xml` as the suite definition (`pom.xml` line 78).
- **Source layout**: Source files are in `src/` (non-standard Maven layout; the default Maven `src/main/java` / `src/test/java` structure is not used). The `pom.xml` does not redefine `<sourceDirectory>` or `<testSourceDirectory>`, which means the Maven compiler will not find these sources unless the Eclipse `.classpath` is used to drive compilation outside of Maven. This is a build correctness gap.
- **Packaging**: There is no `<packaging>` element in `pom.xml` (defaults to `jar`). However, since the source files are in a non-standard directory and not declared as test sources in Maven, the build may not compile cleanly via Maven alone.
- **Resources**: `pom.xml` declares `src/Resources` as a resource directory with filtering enabled, but no `src/Resources` directory exists in the repository.

## Deployment

- This is a **test-only repository**. There is nothing to deploy as a service.
- Tests execute against a remote QA environment: `https://webservice-qa.wirecard.com:4005/` and `:4007/`.
- The QA environment is a pre-existing external service (former Wirecard/Citi infrastructure). The test suite has no ability to deploy, configure, or manage the target environment.
- No Docker image, Kubernetes manifest, Helm chart, or deployment descriptor exists.

## Configuration Management

- **No externalised configuration**: All configuration is hardcoded in Java source files and XML fixtures:
  - Base URIs: `RestAssured.baseURI="https://webservice-qa.wirecard.com:4005/"` (set in every test class, lines 31 in each Java file)
  - Endpoint paths: `accountmanagementapiws/services/AccountManagementApiWebServices` (hardcoded in every `when().post(...)` call)
  - Request payloads: `SoapRequest/*.xml` files loaded by relative path (e.g., `.\\SoapRequest\\CreateAccount.xml`)
- **No environment profiles**: No Maven profiles, no Spring Boot properties, no YAML config file. Switching between environments (QA, staging, prod) requires editing source code.
- **Commented-out alternatives**: Each Java test class contains commented-out `baseURI` lines pointing to internal hostnames (`q-na-app01.nam.wirecard.sys:9313` and `ppnaut.nam.wirecard.sys:9313`), indicating previous or alternate environment targeting — but these are internal-only Wirecard hostnames, likely no longer resolvable.
- **Maven settings**: `.mvn/wrapper/settings.xml` is present but its content was not examined as it may contain repository credentials. It should be reviewed for embedded credentials.
- **Eclipse project files**: `.classpath`, `.project`, and `.settings/` are committed. These are IDE-specific files that do not belong in version control for a CI-first project. The `.classpath` drives compilation in Eclipse but not in Maven.

## Observability

- **Logging**: The only "observability" in this suite is `log().all()` in Rest-Assured on every request and response (`given().log().all()` ... `.log().all()`). This writes the full SOAP envelope — including sensitive data — to standard output.
- **No structured logging**: No SLF4J, Logback, Log4j, or log level configuration. All output is to stdout.
- **No test reporting beyond TestNG defaults**: No Allure, ExtentReports, or other reporting framework is configured. TestNG will generate its default XML/HTML reports in `target/surefire-reports/`.
- **No metrics or tracing**: No APM integration, no distributed tracing, no metrics emission.
- **CI log exposure**: Since `log().all()` emits full request/response bodies, any CI system (GitLab CI, GitHub Actions) will capture full SOAP payloads — including PANs, CVVs, PINs, and SSNs — in its pipeline log storage. This creates a secondary persistent storage of SAD/PII.

## Infrastructure Dependencies

- **External QA endpoint**: `webservice-qa.wirecard.com` (ports 4005 and 4007). This domain is associated with Wirecard AG, which entered insolvency proceedings in 2020. Domain and service availability cannot be guaranteed. If this domain has been decommissioned or reassigned, all tests will fail.
- **Java Runtime**: Java 7+ required (compiled to Java 1.7 class files). A JDK/JRE must be present on the runner.
- **Maven**: Maven 3.x or the bundled Maven Wrapper.
- **Network access**: The test runner must have outbound HTTPS access to `webservice-qa.wirecard.com:4005` and `:4007`. In a locked-down CI environment (e.g., GitHub self-hosted runners in a private network), this may not be available.
- **No containerisation**: No Dockerfile. Tests must run on a bare-metal or VM runner with Java and Maven installed.

## Operational Risks

1. **Java 7 EOL**: The compiler target is Java 1.7, which reached end-of-life in April 2015. No security patches are available. Any JVM vulnerabilities introduced after 2015 are unmitigated if a Java 7 JRE is used at test execution time.
2. **Wirecard domain dependency**: All tests are hard-coupled to `webservice-qa.wirecard.com`. If this domain is unavailable (highly likely given Wirecard's insolvency), the entire suite will fail with connection errors, not test failures. There is no mock/stub fallback.
3. **Non-standard Maven source layout**: The `src/AccMgmtAPI/` structure is not Maven-standard. Maven will not compile these sources without additional plugin configuration. Builds likely rely on the Eclipse `.classpath` rather than a clean `mvn compile`.
4. **Static test data / non-idempotent tests**: Running the suite twice against the same QA environment will likely produce failures on the second run because `transaction_id` values and `partner_user_id` values are hardcoded and non-unique across runs.
5. **No test isolation**: Tests in `testng.xml` run sequentially but share no state, and there is no QA environment reset between runs.
6. **Full-payload logging in CI**: All sensitive data (PANs, CVVs, PINs, SSNs, bank account numbers) will appear in CI logs on every run. CI log retention policies determine the exposure window.
7. **Missing `src/Resources` directory**: The `pom.xml` references `src/Resources` as a resource directory but this directory does not exist. This will produce a Maven warning on every build.

## CI/CD

### GitLab CI (`.gitlab-ci.yml`)
- Single stage: `test`
- Uses GitLab SAST template: `Security/SAST.gitlab-ci.yml`
- **No test execution step is defined** in `.gitlab-ci.yml`. The GitLab pipeline only runs static analysis (SAST) — it does not run the TestNG test suite. This means CI does not automatically execute the API tests.

### GitHub Actions (`.github/workflows/codeql.yml`)
- Triggered on `workflow_dispatch` (manual) and weekly schedule (`52 7 * * 0` — Sunday 07:52 UTC)
- Uses Onbe's shared CodeQL workflow: `Onbe/om-ci-setup/.github/workflows/codeql-auto.yml@main`
- Runner: self-hosted (`['self-hosted', 'X64', 'Linux', 'ubuntu-docker']`)
- Inherits secrets from the repository
- **This also does not run the TestNG tests** — it only performs CodeQL static analysis.

### Dependabot (`.github/dependabot.yml`)
- Monitors Maven dependencies weekly for version updates.
- Configured against the root `pom.xml`.

### Net Assessment
There is **no CI pipeline step that actually executes the test suite**. Both CI configurations (GitLab and GitHub) run only security scanning tools. The TestNG tests must be run manually by a developer/tester. This means the test suite provides no automated regression gate in the delivery pipeline.
