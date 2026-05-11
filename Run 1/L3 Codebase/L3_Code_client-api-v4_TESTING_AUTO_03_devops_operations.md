# client-api-v4_TESTING_AUTO — DevOps & Operations View

## Build & Packaging

- **Build tool**: Apache Maven 3.9.1 (via Maven Wrapper `mvnw` / `mvnw.cmd`)
- **Project coordinates**: `groupId=RestAssuredAPI`, `artifactId=RestAssuredAPI`, `version=0.0.1-SNAPSHOT`
- **Java compile target**: Java 1.7 (source and target both set to `1.7` in `pom.xml` properties)
- **Packaging**: Default JAR (no explicit packaging type declared, defaults to `jar`)
- **Test runner**: Maven Surefire Plugin 3.0.0-M5, configured to execute `testng.xml` as the test suite
- **Test framework**: TestNG 6.10 (scoped to `test`)

Key runtime dependencies:

| Dependency | Version | Purpose |
|---|---|---|
| io.rest-assured:rest-assured | 4.4.0 | HTTP client for SOAP-over-REST testing |
| com.fasterxml.jackson.dataformat:jackson-dataformat-xml | 2.9.0 | XML serialization (not actively used in current tests) |
| org.testng:testng | 6.10 | Test framework |
| org.json:json | 20211205 | JSON/XML conversion (used in XmltoJson utility) |
| commons-io:commons-io | 2.11.0 | File reading (IOUtils.toString) |
| org.eclipse.birt.runtime.3_7_1:org.w3c.dom.smil | 1.0.0 | DOM SMIL (imported in pom but not actively used) |

The build has no production packaging goal — it exists solely to compile and run tests.

## Deployment

This repository is a **test automation project, not a deployable service**. There is nothing to deploy to a runtime environment.

Test execution produces:
- Maven Surefire HTML/XML reports in `target/surefire-reports/`
- Console log output (RestAssured logs full request and response via `.log().all()`)

The "deployment" model is: clone repository, set up Maven environment, run `mvn test` (or `./mvnw test`).

## Configuration Management

- **Endpoint configuration is hardcoded** in each Java test class:
  - Active: `https://webservice-qa.wirecard.com:4005/`
  - Commented-out alternatives: `http://q-na-app01.nam.wirecard.sys:9313/` (internal hostname) and `http://ppnaut.nam.wirecard.sys:9313/` (another internal hostname)
  - No environment variable, properties file, or external configuration mechanism is used to switch between environments.
- **SOAP fixtures are hardcoded files** at relative paths (`.\SoapRequest\*.xml`). The test uses a relative file path, meaning the working directory at execution time must be the project root.
- **Maven settings**: `.mvn/wrapper/settings.xml` configures two Maven mirrors:
  - Public Maven Central via `https://repo1.maven.org/maven2`
  - Internal Wirecard/Onbe Nexus server at `https://d-na-stk01.nam.wirecard.sys:8081/nexus/content/groups/public/` (internal hostname, may not be resolvable outside the corporate network)
  - GitHub Packages registry at `https://maven.pkg.github.com/onbe/onbe_maven_releases`
- **Committed credentials**: Three server entries in `settings.xml` contain plaintext passwords (see Data Architect view). This is a critical operational security risk.
- No Spring profiles, YAML config files, or `.properties` files exist in the repository.

## Observability

- **Logging**: RestAssured is configured with `.log().all()` on both the request and response sides in all four test classes. This logs full HTTP headers and bodies — including any sensitive data in SOAP payloads — to stdout.
- **Test reports**: Maven Surefire generates XML and HTML reports to `target/surefire-reports/`. No custom reporting library (e.g., Allure, ExtentReports) is configured.
- **No application metrics or monitoring**: This is a test suite; there is no metrics endpoint, health check, or APM instrumentation.
- **CI log risk**: Because `.log().all()` is unconditional, SOAP request bodies (including the SSN value in `UpdateRegV4.xml`) will appear in CI pipeline logs, extending the sensitive data exposure surface.

## Infrastructure Dependencies

| Dependency | Type | Notes |
|---|---|---|
| `webservice-qa.wirecard.com:4005` | External QA endpoint | SOAP service under test; must be reachable |
| `d-na-stk01.nam.wirecard.sys:8081` | Internal Nexus server | Maven artifact repository; `.sys` domain suggests internal DNS, not resolvable from public internet |
| `repo1.maven.org` | Public Maven Central mirror | Required for dependency resolution if internal Nexus unavailable |
| `maven.pkg.github.com/onbe/onbe_maven_releases` | GitHub Packages | Onbe internal Maven package registry |
| Java runtime (JDK 1.7+) | Build/test runtime | Java 1.7 is EOL; any modern JDK with 1.7 compatibility mode will work |

The dependency on the internal Wirecard `.sys` hostname in `settings.xml` means builds outside the corporate network will fail unless the internal Nexus is bypassed and all dependencies are resolved from Maven Central or GitHub Packages.

## Operational Risks

1. **Hardcoded QA endpoint**: Switching to a different environment requires code changes. There is no configuration-driven environment selection.
2. **Internal hostname dependency**: `d-na-stk01.nam.wirecard.sys` is an internal hostname; builds from CI runners outside the corporate network (e.g., GitHub-hosted runners) will fail at dependency resolution unless the `nexus` profile is disabled.
3. **Relative file paths**: Test fixtures are loaded via `.\SoapRequest\*.xml` (Windows-style relative paths). This will fail on Linux CI runners that use `/` path separators unless the working directory is set correctly.
4. **Java 1.7 compilation target**: Java 7 reached end-of-life in April 2015. Modern JDKs (17+) still support compiling to target 1.7 but this is a fragile compatibility dependency.
5. **TestNG 6.10 is outdated**: Released circa 2016; does not benefit from subsequent security or compatibility fixes.
6. **Committed plaintext passwords**: Server credentials in `settings.xml` are immediately usable by anyone who can read the repository.
7. **No retry or resilience logic**: A single transient network failure causes a test failure with no retry mechanism.

## CI/CD

### GitLab CI (`.gitlab-ci.yml`)

- **Pipeline**: Single `test` stage
- **Configuration**: Uses GitLab Auto DevOps template `Security/SAST.gitlab-ci.yml`
- **Purpose**: Static Application Security Testing (SAST) only — no build, unit test, or deployment jobs are defined
- **Origin**: Repository was originally hosted on GitLab (`gitlab.com/northlane/testing/automation/api/client-v4-api`)

### GitHub Actions (`.github/workflows/codeql.yml`)

- **Trigger**: Manual (`workflow_dispatch`) and scheduled (weekly, Fridays at 18:31 UTC)
- **Job**: Calls reusable workflow `Onbe/om-ci-setup/.github/workflows/codeql-auto.yml@main` with `secrets: inherit`
- **Runner**: Self-hosted runner with labels `['self-hosted', 'X64', 'Linux', 'ubuntu-docker']`
- **Purpose**: CodeQL security analysis for Java code

### GitHub Dependabot (`.github/dependabot.yml`)

- **Ecosystem**: Maven
- **Schedule**: Weekly
- **Purpose**: Automated dependency version update PRs

### Gaps

- No CI job actually **runs the tests** (`mvn test`) in either pipeline. SAST and CodeQL are present, but there is no automated test execution gate.
- No artifact publishing, Docker build, or deployment step exists (appropriate for a test-only repo, but the lack of test execution in CI is a quality gap).
