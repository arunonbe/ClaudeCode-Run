# DevOps / Operations View — selenium-framework-test_TESTING_AUTO

## Build System

- **Build tool**: Maven with Maven Wrapper (`mvnw`, `mvnw.cmd`)
- **Java version**: Java 21 (`maven.compiler.source=21`, `maven.compiler.target=21` in `maven-compiler-plugin` config); note the `pom.xml` erroneously sets `<maven.compiler.source>3.13.0</maven.compiler.source>` as a property (this appears to be a Maven plugin version mistakenly placed in the compiler source property — the actual compiler plugin configuration correctly sets source/target to 21)
- **GroupId**: `OnePlatform`; `ArtifactId`: `Desktop`; `Version`: `0.0.2-SNAPSHOT`
- **Test runner**: TestNG 6.10 via Maven Surefire Plugin 3.0.0-M5; suite defined in `testng.xml`
- **Key dependencies**:
  - `org.seleniumhq.selenium:selenium-java:4.22.0` — Selenium WebDriver
  - `io.github.bonigarcia:webdrivermanager:5.9.1` — automatic browser driver management
  - `com.microsoft.sqlserver:mssql-jdbc:9.4.0.jre8` — SQL Server JDBC
  - `com.aventstack:extentreports:5.0.9` — HTML test reporting
  - `org.apache.poi:poi:5.1.0` / `poi-ooxml:5.1.0` — Excel test data reading
  - `commons-io:2.11.0` — file utilities (screenshot capture)
  - `org.testng:testng:6.10` — test framework (EOL; current is 7.x)

## CI/CD Pipeline

- **GitHub Actions**: `.github/workflows/codeql.yml` — CodeQL static analysis (Java)
- **Dependabot**: `.github/dependabot.yml` — automated dependency update PRs
- **No deployment pipeline**: Test automation frameworks are typically not deployed to production; they are run on demand or scheduled against test environments
- **No GitLab CI**: Only GitHub Actions observed
- **Test execution**: Tests are run manually or triggered by CI pipelines of the applications under test (not by this repository's own CI)

## Deployment Model

- **Not deployed**: This is a test automation project; it is executed as a Maven test run, not deployed as a service
- **Execution environment**: Developers or CI agents run `mvn test` with a `testng.xml` suite file on machines with Chrome/Firefox/Edge browsers installed
- **Browser driver management**: WebDriverManager automatically downloads appropriate browser drivers at runtime; no manual driver installation required
- **Reports**: ExtentReports generates `reports/index.html` with screenshots; currently committed to source (should use CI artifact storage instead)

## Runtime

- **Java 21** (configured in compiler plugin)
- **Selenium 4.22.0**: Modern Selenium with W3C WebDriver protocol
- **TestNG 6.10**: EOL (7.x is current); lacks some modern test features
- **Browsers**: Chrome, Firefox, Edge (configured in `Generic.properties`)
- **Application servers targeted**: OnePlatform (CSA, CZ), Payment Hub, IDD — these are Tomcat/JBoss-hosted applications

## Secrets Management

- **Credentials in `Generic.properties`**: Browser configuration and application URLs are stored in properties files committed to source. If passwords (`pw` field in `base.java`) are loaded from `Generic.properties`, they are in plaintext in source control. **This is a critical finding.**
- **Database credentials**: `DatabaseConnection.java` connects directly to SQL Server; connection credentials must be externalized to environment variables or a secrets manager, not hardcoded or stored in checked-in properties files
- **No secrets management integration**: No Azure Key Vault, HashiCorp Vault, or similar integration observed
- **Recommendation**: Move all credentials to environment variables injected at runtime by the CI system or a secrets manager; remove any credentials from checked-in files

## Observability

- **ExtentReports**: HTML test report with pass/fail status, screenshots, and test step details
- **Screenshot capture**: `getscreenshot()` method in `base.java` captures browser screenshots on test events; output to `reports/` directory
- **No logging framework**: No SLF4J or Log4j integration observed; test output is via System.out and ExtentReports
- **No metrics or alerting**: Test framework has no operational metrics; pass/fail results are the primary output

## Known EOL Runtimes and CVEs

- **TestNG 6.10**: EOL; current is 7.10.x. Some dependency vulnerabilities may be present.
- **Apache POI 5.1.0**: Not the latest (5.3.x is current); update to address any security fixes.
- **`0.0.2-SNAPSHOT` version**: Confirms this is an active development artifact, not a stable release.
- **Reports committed to source**: `reports/index.html`, `reports/Loginpage.png`, `reports/Reg.png` are in the repository. This pollutes the source tree and may inadvertently expose test environment screenshots showing sensitive data.
- **Prerequisite XML files**: XML files such as `04010929_11.xml` (CZ test data) and `PH_6813_37.xml`/`PH_2522_38.xml` (Payment Hub) committed to source. Content must be reviewed to confirm no real PAN, account numbers, or other SAD is present.
- **`implicitlyWait` usage**: Selenium's `implicitlyWait` is deprecated in Selenium 4 in favor of explicit waits; this may cause test flakiness.
