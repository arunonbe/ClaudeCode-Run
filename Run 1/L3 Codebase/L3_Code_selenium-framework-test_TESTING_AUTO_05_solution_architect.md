# Solution Architect Report — selenium-framework-test_TESTING_AUTO

## Architectural Assessment

### Repository Role in the Broader Platform

`selenium-framework-test_TESTING_AUTO` sits at the top of the Onbe test automation pyramid as the UI/E2E layer. It validates three web application surfaces (OnePlatform, ClientZone, CSA) that form the primary human-facing interfaces of the Onbe prepaid payments platform. As a Level 1 PCI DSS service provider, Onbe is obligated to maintain comprehensive regression testing as part of its change management and release governance processes.

### Current Architectural Model

The framework uses a traditional local Selenium WebDriver model:

```
[Test Machine] → [Browser WebDriver] → [Application Under Test]
```

There is no Selenium Grid, remote execution, or containerised browser infrastructure. All tests run sequentially on the machine where Maven is invoked. This limits parallelism and scalability.

### Dependency Architecture

```
Maven POM (pom.xml)
├── Selenium Java 4.22.0
├── WebDriverManager 5.9.1
├── TestNG 6.10
├── ExtentReports 5.0.9
├── Apache POI 5.1.0
├── mssql-jdbc 9.4.0.jre8 (unused — empty DatabaseConnection.java)
└── commons-io 2.11.0
```

The project has no parent POM relationship with the Onbe platform's standard Maven hierarchy (`prepaid-parent`, `service-parent`). This is appropriate for a standalone test module but means it does not inherit organisation-wide dependency management, plugin versions, or SAST/DAST configurations.

### Data Flow Architecture

```
Excel files (shared UNC / local) → ExcelUtils.java → Test methods
                                                         ↓
                                   base.java → WebDriver → AUT (QA environment)
                                                         ↓
                                         ExtentReports → HTML Report (reports/)
```

The data flow has a single point of failure at the Excel file layer. Files stored on `\\q-na-app05.nam.wirecard.sys` create a dependency on internal QA infrastructure that is unavailable outside the corporate network.

### Target Architecture Recommendation

For a PCI DSS Level 1 compliant test automation architecture, the following target state is recommended:

```
CI/CD Pipeline (GitLab CI / GitHub Actions)
     ↓
Docker container (Selenium + Chrome headless)
     ↓                           ↓
Test execution              Selenium Grid Hub
     ↓                           ↓
Test data from              Browser node(s)
Vault/Secrets Manager
     ↓
ExtentReports → Artifact storage
```

**Key architectural changes:**
1. **Containerise the test environment**: Use a Docker image with Java 21, Maven, Chrome headless, and WebDriverManager. This eliminates local driver setup and network share dependencies.
2. **Selenium Grid for parallelism**: Deploy Selenium Grid (Docker Compose or Kubernetes) to support parallel test execution across browsers.
3. **Secrets management integration**: Integrate with HashiCorp Vault or AWS Secrets Manager to retrieve test credentials at runtime. Never store credentials in source code or Excel files.
4. **Test data management**: Replace Excel files with a structured test data repository (database or API-backed service) with access controls aligned to PCI DSS Requirement 7.
5. **Parameterised configuration**: Replace `Generic.properties` with environment-variable-driven configuration using Spring Boot test config or a similar mechanism.

### Integration Points with Onbe Platform

| Integration | Mechanism | Risk |
|---|---|---|
| QA environment URLs | Hardcoded in properties | HIGH — breaks portability |
| Test data | UNC network share | HIGH — network dependency |
| Credential storage | Source code / Excel | CRITICAL — PCI DSS violation |
| Database validation | Not implemented | MEDIUM — incomplete verification |
| Reporting | Local file system | MEDIUM — ephemeral on CI |

### Version Compatibility Risks

- **TestNG 6.10** (2016) is end-of-life. TestNG 7.x introduced `@BeforeMethod` context improvements and better parallel execution. Migration path is straightforward.
- **Java 21 compilation** (`maven-compiler-plugin source/target=21`) is correct but the POM also specifies `<maven.compiler.source>3.13.0</maven.compiler.source>` which is invalid and likely to cause a warning or failure.
- **Selenium 4.22.0** is relatively recent and aligns with WebDriverManager 5.9.1. No version conflict risk here.

### Alignment with Onbe CI/CD Maturity

The repository contains a `.github/workflows/` directory stub and a `.mvn/wrapper/` folder, suggesting aspirations toward CI integration. However, without `testng.xml` committed, no parameterised configuration, and UNC path dependencies, the framework cannot be successfully executed in a CI/CD pipeline today without significant modification.

### Recommended Roadmap

| Phase | Action | Priority |
|---|---|---|
| Immediate | Audit `5445446557563720` card number against production/QA card inventory | P0 |
| Immediate | Remove all hardcoded PANs, CVVs, PINs from source code | P0 |
| Sprint 1 | Commit `testng.xml` and parameterise all URLs/paths | P1 |
| Sprint 1 | Migrate from UNC paths to environment-variable-driven data paths | P1 |
| Sprint 2 | Containerise execution environment (Docker + headless Chrome) | P2 |
| Sprint 3 | Integrate Selenium Grid for parallel execution | P3 |
| Sprint 3 | Connect to secrets manager for credential retrieval | P3 |
