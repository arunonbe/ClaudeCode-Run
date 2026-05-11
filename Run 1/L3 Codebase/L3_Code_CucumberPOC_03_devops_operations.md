# CucumberPOC — DevOps / Operations View

## Build System
- **Maven** (`pom.xml`), groupId `automation`, artifactId `paymentvault`, version `0.0.1-SNAPSHOT`.
- Java 21 (`maven.compiler.source/target = 21`).
- Maven Surefire plugin 3.0.0-M5 configured for parallel execution: `methods` mode, `threadCount=5`, matches `**/*Test.java`.
- Maven Clean plugin 3.2.0.
- No parent POM; standalone build.

## Key Dependencies
| Dependency | Version | Purpose |
|---|---|---|
| cucumber-java / cucumber-junit / cucumber-core | 7.10.1 | BDD test framework |
| selenium-java | 4.20.0 | Browser automation |
| extentreports | 5.1.0 | HTML reporting |
| extentreports-cucumber7-adapter | 1.14.0 | Bridge Cucumber 7 → ExtentReports |
| junit-jupiter-api/engine | 5.9.2 | Test runner |
| javax.mail | 1.4.7 | Email report dispatch |
| lombok | 1.18.34 | Compile-time code generation |

## CI/CD
- No GitHub Actions workflow or Jenkinsfile found in the repository.
- No pipeline configuration; the project appears to be a developer-local / manual-run POC.
- Running: `mvn test` invokes Surefire which discovers and runs `TestRunner.java`.

## Execution Entry Point
- `runner/TestRunner.java` — `@RunWith(Cucumber.class)` with `@CucumberOptions`:
  - `features = "src/test/resources/features"`
  - `glue = {"stepDefinitions", "hooks"}`
  - `plugin = {"com.aventstack.extentreports.cucumber.adapter.ExtentCucumberAdapter:"}`

## Configuration
- All test parameters in `src/test/resources/config.properties` (read by `ConfigReader.java`).
- Browser selection via `browser` property; supports `chrome`, `firefox`, `edge`.
- WebDriver managed by `DriverFactory.java` using `ThreadLocal<WebDriver>` for thread-safety under parallel execution.

## Observability
- ExtentReports HTML output at `target/SparkReport/ExtentSparkReport.html`.
- Failure screenshots captured by `Hooks.afterStep()` and embedded in the report.
- Email dispatch via `EmailLib.sendEmail()` is commented out (`Hooks.java` line 39).
- No structured logging framework; `System.out.println` used in `ConfigReader` and `EmailLib`.

## Infrastructure
- No containerisation.
- No infrastructure-as-code.
- Requires local browser binary (chromedriver by default).

## Risks
- Parallel test execution (`threadCount=5`) requires the stage environment to handle concurrent sessions and not enforce single-session cardholder constraints.
- No CI pipeline means tests can be skipped pre-merge.
- Hard-coded 30-second sleep in `UserRegistrationSteps.java` line 99 will cause timeouts in resource-constrained CI environments.
- No browser version pinning; Selenium 4.20.0 auto-manages chromedriver, but Firefox/Edge require separate setup.
