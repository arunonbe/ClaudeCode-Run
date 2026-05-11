# Enterprise Architect View — selenium-framework-test_TESTING_AUTO

## Platform Generation

**Cross-generation test framework** targeting Gen-1 and Gen-2 applications. The framework itself is neutral (Java 21, Selenium 4), but the applications it tests span the platform generations:

- **Gen-1 targets**: CSA (Customer Service Agent application), CZ (Customer Zone/ClientZone), eCount-era instant-issue workflows
- **Gen-2 targets**: OnePlatform (`opurl`), Payment Hub (`paymenthuburl`), IDD (Instant Disbursement Device, `iddurl`)
- **Framework vintage**: The page object classes and test data patterns reflect legacy eCount testing conventions (manual browser navigation, Excel-driven data), not modern API-layer contract testing

Evidence of multi-generation scope:
- `src/main/java/resources/Selenium/CSA/` — CSA application (Gen-1 era)
- `src/main/java/resources/Selenium/CZ/` — Customer Zone (Gen-1/Gen-2)
- `src/main/java/resources/Selenium/OP/` — OnePlatform (Gen-2/Gen-3 bridge)
- Payment Hub and IDD are Gen-2 Wirecard/Northlane services

## Integration Patterns

- **Browser automation (UI layer)**: Selenium WebDriver drives real browser sessions against application UIs. This is a black-box integration pattern — the test framework has no knowledge of application internals.
- **Direct database access**: `DatabaseConnection.java` establishes a direct JDBC connection to SQL Server for test setup and validation. This is an anti-pattern from a microservices perspective but common in legacy platform testing.
- **Excel-driven testing**: Apache POI reads test scenario data from Excel files. This is a data-driven testing pattern common in legacy QA teams.
- **Page Object Model**: CSA, CZ, and OP page objects (`pageObjects/`, `pageobjects/`) encapsulate UI element selectors — a standard pattern for maintainable Selenium tests.
- **No API-level testing**: The framework operates exclusively at the UI layer. There are no REST/SOAP API test clients in the observed source.

## External Dependencies

| System | Interface | Protocol |
|---|---|---|
| CSA Application (`CSAurl`) | Selenium browser automation | HTTP/HTTPS |
| Customer Zone (`CZurl`) | Selenium browser automation | HTTP/HTTPS |
| OnePlatform (`url`) | Selenium browser automation | HTTP/HTTPS |
| Payment Hub (`paymenthuburl`) | Selenium browser automation | HTTP/HTTPS |
| IDD (`iddurl`) | Selenium browser automation | HTTP/HTTPS |
| SQL Server | Direct JDBC (DatabaseConnection.java) | JDBC/TDS |
| Chrome/Firefox/Edge | WebDriver protocol | Local |

## Position in the Broader Platform

```
QA / Testing layer (this repo)
  → All Gen-1 and Gen-2 web applications (CSA, CZ, OP, Payment Hub, IDD)
    → Gen-1 core (eCount/Citi backend)
    → Gen-2 core (Wirecard/Northlane backend)
```

This framework is a cross-cutting concern used by the QA team to regression-test multiple platform components. It is not a dependency of any production service — it is purely a test execution tool.

Key observations about position:
- The `App.java` class (main class in `OnePlatform.Desktop` package) suggests this was originally conceived as a desktop test runner, not a CI-integrated framework
- The presence of `DatabaseConnection.java` indicates the framework was built to support stateful test setup, not just stateless UI validation
- No integration with a test management system (e.g., Xray, Zephyr) or PACT contract registry is observed

## Migration Blockers

1. **Excel-driven test data**: Migrating to a modern test framework (e.g., Cucumber, RestAssured) requires converting Excel test data to Gherkin feature files or API-level test cases.
2. **Direct database access**: The `DatabaseConnection.java` dependency on direct MSSQL access ties the tests to a specific database topology; migration to API-driven testing (using application APIs for test setup) is required for Gen-3 compatibility.
3. **Page object brittleness**: UI page objects tightly couple test code to the specific HTML structure of each application. Any UI refactoring breaks the test suite.
4. **No CI/CD integration**: Tests are not currently wired into the applications' CI/CD pipelines (no deployment workflow in this repo). Integration with GitHub Actions on application repos is needed.

## Strategic Status

**Maintain with selective investment** for Gen-1/Gen-2 coverage; **replace** for Gen-3 services.

- For Gen-1 applications (CSA, CZ): maintain existing Selenium tests as regression safety net during migration; do not invest in new UI tests
- For Gen-2 applications: supplement with API-level contract testing (PACT) as services are migrated
- For Gen-3 applications: use API-level testing (RestAssured, PACT) and component tests rather than end-to-end UI automation
- Immediate action: move credentials out of source code, replace test data files with synthetic data, and integrate test execution into application CI pipelines as a gate for deployments to QA environments
