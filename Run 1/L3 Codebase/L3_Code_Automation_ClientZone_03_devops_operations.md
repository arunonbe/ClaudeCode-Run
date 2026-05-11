# Automation_ClientZone — DevOps & Operations View

## Build & Packaging

- **Build tool**: Maven (`pom.xml`); Maven Wrapper scripts present (`mvnw`, `mvnw.cmd`) for consistent Maven version execution.
- **Artifact**: `qa:qa-ui-test-automation:0.0.1-SNAPSHOT` (group `qa`, artifact `qa-ui-test-automation`).
- **Java version**: Source and target set to Java 21 with `--enable-preview` compiler arg (`pom.xml` lines 68–69). JDK 21+ is required per `README.md`.
- **Key dependencies** (all resolved from Maven Central):
  - `com.microsoft.playwright:playwright:1.45.1` — UI automation engine.
  - `io.cucumber:cucumber-java:7.18.1` + `cucumber-junit:7.18.1` — BDD framework.
  - `com.fasterxml.jackson.core:jackson-databind:2.13.4.2` — JSON deserialization for test data.
  - `com.aventstack:extentreports:5.1.0` + `tech.grasshopper:extentreports-cucumber7-adapter:1.14.0` — HTML reporting.
  - `ru.yandex.qatools.ashot:ashot:1.5.4` — Screenshot comparison (dependency present; used for `diff.png`, `Actual.png`, `Expected_Profile_UI.png` in repo root).
  - `com.microsoft.sqlserver:mssql-jdbc:12.8.1.jre11` — SQL Server JDBC connectivity.
  - `junit:junit:4.11` — JUnit 4 test runner (scope: test).
- **Execution command** (from `README.md`): `./mvnw clean test -D"cucumber.filter.tags=@Demo"`
- **Test phase**: Maven Surefire plugin version `3.0.0-M4` bound to the `integration-test` phase. The plugin includes all classes matching `**/*Runner*.class`.
- **Thread configuration** (`pom.xml` lines 85–87):
  - `parallel=methods`, `threadCount=1`, `perCoreThreadCount=false`. Only one thread is configured, meaning tests run sequentially despite the parallel mode declaration.
- **Default system properties** (set via Surefire):
  - `executionMode=Local`
  - `browser=Chromium`

## Deployment

This is a test-only repository — there is no application deployment. The artifact is run as a Maven test suite against already-deployed QA environments.

**Target environments** (hardcoded in page objects and data files):
| Application | QA URL | Source |
|---|---|---|
| ClientZone (legacy) | `https://q-na-app02.nam.wirecard.sys:9107` | `clientzone/pages/LoginPage.java` line 15 |
| ClientZone (legacy, app01) | `https://q-na-app01.nam.wirecard.sys:9107` | `clientzone/pages/SSLoginPage.java` line 100 |
| ClientZone (SSO/modern) | `https://clientzone-qa.mypaymentadmin.com` | `clientzone/pages/SSLoginPage.java` lines 58, 65, 96, 100 |
| MyPaymentVault | `https://mypaymentvault.qa.onbe.dev` | `mypaymentvault/pages/LoginPage.java` line 14 |
| Wizard | `https://q-na-app05.nam.wirecard.sys:8090` | `wizard/pages/LoginPage.java` line 14 |
| IdPassMe | `https://qa.idpassme.com` | `src/test/resources/data/idpassme.json` |
| SQL Server | `Q-LIS-DB02:2231` | `framework/DatabaseConnection.java` line 21 |

All URLs are overridable via `System.getenv("baseUrl")` using Java's `Optional.ofNullable(...)`.or`Else(...)` pattern (e.g., `BasePage.java` line 24; `LoginPage.java` line 15). The browser type is overridable via `System.getenv("browserType")` (`PlaywrightManager.java` line 12).

## Configuration Management

- **Environment selection**: Controlled by `System.getenv("env")`, defaulting to `"qa"` (`TestData.java` line 13). No `"staging"`, `"prod"`, or other environment keys are defined in any JSON data file — only `"qa"` environment blocks exist.
- **Base URL override**: `System.getenv("baseUrl")` at the page-object level.
- **Browser override**: `System.getenv("browserType")`, accepting `"chromium"` (default, launches Chrome), `"firefox"`, or `"webkit"`.
- **No environment variable inventory**: There is no `.env.example`, no documented list of required environment variables. The overrides are implicit in the page objects.
- **No CI/CD pipeline configuration**: No `Jenkinsfile`, `.github/workflows/`, `azure-pipelines.yml`, `.gitlab-ci.yml`, or similar pipeline definition file is present in the repository.
- **Cucumber properties**: `src/test/resources/cucumber.properties` contains only `cucumber.publish.quiet=true` — suppresses the Cucumber Cloud publish prompt but does not configure any execution behavior.
- **Extent properties**: `src/test/resources/extent.properties` configures:
  - Report output: `target/TestResults.html`
  - Screenshot directory: `target/SparkReport/screenshots/`
  - Theme: dark
  - Timeline and dashboard enabled.

## Observability

- **Test reports**: ExtentReports HTML report at `target/TestResults.html` (Spark reporter). A secondary HTML report is also enabled (`extent.reporter.html.start=true`). Reports include timeline, dashboard, and chart views.
- **Screenshots**: `ashot` dependency is present and screenshot comparison artifacts (`Actual.png`, `Expected_Profile_UI.png`, `diff.png`) exist at the repo root, indicating visual comparison was used previously. Screenshot directory for reports is `target/SparkReport/screenshots/`.
- **Console logging**: Scenario names are printed via `System.out.print` in `Hook.java` line 17. Scenario status (PASSED/FAILED/SKIPPED) is printed with ANSI color codes in `Hook.java` lines 23–28. DB query results and UI counts are logged via `System.out.println` extensively in `SearchableAddendaSteps.java`.
- **Status color bug**: `Hook.java` line 24 uses `==` reference comparison for String (`"PASSED"`), which will never be true in Java — the passed-status color branch is dead code. Only the failed (red) and else (yellow) branches execute.
- **No structured logging**: No SLF4J, Log4J, or other logging framework. All output is `System.out.println`.
- **No APM / tracing**: No application performance monitoring integration.
- **No test failure alerting**: No Slack, email, or webhook notification on test failure.

## Infrastructure Dependencies

The test suite has the following hard infrastructure dependencies at runtime:

| Dependency | Value | Risk if Unavailable |
|---|---|---|
| SQL Server `Q-LIS-DB02` | Port 2231, instance `q-db02\db02`, DB `EcountCore` | Searchable Addenda and Login step DB assertions fail |
| ClientZone QA app02 | `q-na-app02.nam.wirecard.sys:9107` | All legacy CZ login tests fail |
| ClientZone QA app01 | `q-na-app01.nam.wirecard.sys:9107` | SSO legacy CZ tests fail |
| ClientZone modern | `clientzone-qa.mypaymentadmin.com` | SSO, QuickPay, PaymentReversal, and other modern CZ tests fail |
| MPV QA | `mypaymentvault.qa.onbe.dev` | All MyPaymentVault tests fail |
| Wizard QA | `q-na-app05.nam.wirecard.sys:8090` | All Wizard tests fail |
| IdPassMe QA | `qa.idpassme.com` | All IdPassMe KYC tests fail |
| Microsoft Identity Provider | External (Entra ID / AAD) | SSO login flow fails |
| Chrome browser | Must be installed locally | Default browser launch fails (Playwright tries to launch Chrome via channel `"chrome"`) |
| Email delivery (OTP) | `SearchableAddendaSteps.java` line 51–52 | OTP-gated flows fail if email not delivered within 15 seconds |

The `nam.wirecard.sys` domain references the legacy Wirecard/Onbe internal network infrastructure, indicating these hosts are on-premises or internal VPN-accessible servers.

## Operational Risks

1. **Headless mode disabled**: `PlaywrightManager.java` line 59 sets `setHeadless(false)`. Tests require a display. Running in a headless CI environment (e.g., Linux Docker container) will fail unless a virtual display (Xvfb) or headless override is provided via environment variable or code change.
2. **Thread.sleep abuse**: Numerous `Thread.sleep()` calls (1000ms, 2000ms, 3000ms, 5000ms, 10000ms, 15000ms) across step definitions. The 15-second sleep in `SearchableAddendaSteps.java` line 52 is an OTP delivery wait. These sleeps make the suite slow and fragile — any environmental slowness compounds.
3. **Single-threaded execution**: Despite `parallel=methods` in Surefire, `threadCount=1` means tests run sequentially. Full test execution time will be high.
4. **No retry mechanism**: No Surefire retry configuration. Flaky tests (e.g., OTP delivery) will fail the suite without retry.
5. **Static QA test accounts**: Tests depend on specific QA user accounts (e.g., `RPautomation6`, `2531ww`, `RPauto1221`) being present and having specific account states. If QA data is reset or accounts are modified, tests will fail.
6. **No parallel isolation**: `PlaywrightManager` uses `ThreadLocal` correctly, but all scenarios share the same QA accounts. Concurrent execution of scenarios modifying the same account (e.g., Change Password, Change PIN) would produce race conditions.
7. **`--enable-preview`**: Java 21 preview features are enabled in the compiler. Preview features can break on minor JDK updates.

## CI/CD

**No CI/CD pipeline is configured in this repository.** There are no pipeline definition files (Jenkinsfile, GitHub Actions, Azure DevOps, etc.).

The only documented execution method is the Maven Wrapper command:
```
./mvnw clean test -D"cucumber.filter.tags=@Demo"
```

Tag-based test selection supports running specific subsets:
- `@Demo` — demo/framework validation tests
- `@smoketest` — smoke tests across MPV module
- `@loginflow`, `@SSO`, `@WizardRegression`, `@Idpassme`, `@activationflows`, `@registration`, etc. — module-specific full runs

**Recommended CI integration** (not currently implemented): A pipeline agent with JDK 21, Maven, Chrome, and VPN/network access to `nam.wirecard.sys` and `mypaymentadmin.com` would be required. The `headless=false` setting in `PlaywrightManager.java` would need to be changed to `true` or overridden for headless CI execution.
