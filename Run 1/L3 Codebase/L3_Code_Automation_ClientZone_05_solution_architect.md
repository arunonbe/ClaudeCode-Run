# Automation_ClientZone — Solution Architect View

## Technical Architecture

### Framework Stack
```
Test Runner (JUnit 4 + Cucumber)
    ↓
BaseRunner (abstract, @CucumberOptions with ExtentReports plugin)
    ↓
Concrete Runners: clientzone/TestRunner, mypaymentvault/TestRunner,
                  wizard/TestRunner, IdPassMe/TestRunner, demo/TestRunner
    ↓
Hook.java (@Before/@After — PlaywrightManager lifecycle)
    ↓
BaseSteps → Step Definitions (clientzone/steps, mypaymentvault/steps, etc.)
    ↓
BasePage (abstract) → Page Objects (concrete per page)
    ↓
PlaywrightManager (ThreadLocal browser/context/page management)
    ↓
Microsoft Playwright 1.45.1 (chromium/firefox/webkit)
```

### Package Structure
```
src/test/java/
├── framework/          — Core framework classes (8 files)
│   ├── BasePage.java           — Abstract page base (URL navigation, baseUrl resolution)
│   ├── BaseRunner.java         — Abstract Cucumber runner with ExtentReports plugin
│   ├── BaseSteps.java          — Provides Page instance to step definitions
│   ├── ConfigData.java         — Jackson deserialization root (Map<String, DataMapper>)
│   ├── DataMapper.java         — Flat POJO with 90+ test data fields
│   ├── DatabaseConnection.java — JDBC wrapper returning ResultSet
│   ├── Hook.java               — Cucumber @Before/@After lifecycle
│   ├── PlaywrightManager.java  — ThreadLocal Playwright/Browser/Context/Page
│   └── TestData.java           — Static factory: reads JSON → DataMapper
│
├── clientzone/         — ClientZone portal (9 pages, 3 step files, 1 runner, 12 features)
├── mypaymentvault/     — MPV portal (28 pages, 26 step files, 1 runner, 29 features)
├── wizard/             — Program Setup Wizard (5 pages, 7 step files, 1 runner, 2 features)
├── IdPassMe/           — KYC portal (2 pages, 3 step files, 1 runner, 3 features)
└── demo/               — Framework demo/validation (5 pages, 6 step files, 1 runner, 6 features)
```

### Test Module Summary
| Module | Features | Page Objects | Step Files | DB Access | Status |
|---|---|---|---|---|---|
| clientzone | 12 | 9 | 3 | Yes (JDBC) | Partial — 7 stubs, only Login + SSO + SearchableAddenda fully implemented |
| mypaymentvault | 29 | 28 | 26 | No | Active — most comprehensive coverage |
| wizard | 2 | 5 | 7 | No | Active — targeted DisplayCardDetails test |
| IdPassMe | 3 | 2 | 3 | No | Active — KYC flows |
| demo | 6 | 5 | 6 | No | Framework demos (PlaywrightAssertion, Vision, NetworkMonitor, AutoWait, MultipleTab) |

## API Surface

This is a test-only repository — it exposes no API. However, it exercises the following application API surfaces through browser automation:

### ClientZone Application Endpoints (URL paths verified in page objects)
- `GET /login.jsp` — Legacy login page
- `POST → /messageHome.do` — Successful single-user login redirect
- `POST → /getDomains.do` — Multi-program selection page
- `GET /sso.jsp` — SSO login entry
- `GET /sso.jsp?login_error=2` — SSO error state
- `POST → /login/getDomains.do` — SSO post-authentication redirect
- `GET /wizard/loginaction.do?method=loginprocess` — Wizard authentication result
- `GET /wizard/programdashboardaction.do?method=find` — Wizard program profile
- `GET /wizard/configDisplay.do?method=opSetupDisplay` — One Platform setup
- `GET /wizard/websiteSettings.do?method=initial` — Website display settings

### MyPaymentVault Application Routes
- `/login` — Login page
- `/dashboard` — Cardholder dashboard
- `/registration` — Account registration
- `/banktransfer` — ACH bank transfer
- `/transaction` — Transaction history
- `/changepin` — PIN change
- `/changePassword` — Password change
- `/profileDetails` — Profile view
- `/updateContactInfo` — Edit contact information
- `/requestCard` (implied) — Request plastic card
- `/requestCheck` (implied) — Request check
- `/disputeForm` (implied) — Dispute form
- `/fraudForm` (implied) — Fraud form
- `/forgotPassword` (implied) — Password recovery
- `/forgotUserName` (implied) — Username recovery

### EcountCore Database (via JDBC — read-only)
Queries in `SearchableAddendaSteps.java` exercise the following logical API:
- Addenda profile lookup by `program_id` and `searchable` flag.
- Cardholder account search by addenda value, filtered by program prefix.
- Card role classification (primary/secondary/temporary) via `core_device_eCard_extended.role`.
- DDA-only account identification (accounts without type_id `47%` devices).

## Security Posture

### Critical Issues

1. **Hardcoded database credentials** (`framework/DatabaseConnection.java` line 25): Username `b2cstage`, password `b2cstage` committed in source code. Severity: **Critical**. Any developer with repo access gains SQL Server read access to the QA EcountCore database.

2. **Plaintext sensitive data in source-controlled JSON** (`mypaymentvault.json`): 12+ card numbers with corresponding CVV values, SSN `987654321`, DOB `06-04-1985`, bank account number `7835676345435`, routing number `021000021`, PINs. Severity: **High** (PCI DSS, GLBA, CCPA implications).

3. **Real employee email + password** (`clientzone.json`): `bhagyashree.bijagarni@onbe.com` with password `[REDACTED — rotate immediately]` stored in source code. If this is an actual Onbe employee's password (vs. a QA-only account), this is a credential leak. Severity: **High**.

4. **Hardcoded credentials in step definitions** (`SSLoginSteps.java` lines 148, 170–172): Username `"Bhagyashree"`, password `"[REDACTED — rotate immediately]"` hardcoded as string literals — not parameterized through the test data layer. Severity: **Medium**.

5. **SQL injection risk** (`SearchableAddendaSteps.java`): All SQL queries are constructed via string concatenation using `AddendaValue` and `ProgramId` parameters. Example at line 207: `"WHERE addenda.value in('" + AddendaValue + "')"`. Although these values originate from Cucumber step parameters (not user input), the pattern is unsafe and should use `PreparedStatement`. Severity: **Medium** (code quality / pattern risk).

6. **`trustServerCertificate=true`** (`DatabaseConnection.java` line 21): Disables SQL Server TLS certificate validation. Man-in-the-middle attacks against the JDBC connection are possible. Severity: **Medium**.

7. **`setIgnoreHTTPSErrors(true)`** (`PlaywrightManager.java` line 38): Playwright silently ignores all HTTPS certificate errors. Certificate issues on application under test are not detected. Severity: **Low** (test environment) / **Medium** (if pattern is adopted for production testing).

8. **PII in locator values** (`RegistrationPage.java` lines 78, 80, 82, 84, 88, 89): Address `1300 fayette street`, city `Conshohocken`, zip `19428`, email `rashmi1dhandar@gmail.com`, phone numbers `6106057162`/`6106057163` hardcoded as `input[value='...']` locators. This embeds real PII in source code that will appear in test reports. Severity: **Medium**.

### Moderate Issues

9. **Playwright headless=false**: `PlaywrightManager.java` line 59. Not a security issue per se, but reduces isolation and increases attack surface in CI.

10. **No test result sanitization**: DB query results and credentials are printed to stdout (`System.out.println`) and will appear in CI build logs and ExtentReports HTML output.

## Technical Debt

### High Priority
1. **Boilerplate ClientZone page objects**: `InstantIssuePage.java`, `NewCardHolderPage.java`, `PaymentReversalPage.java`, `ManageinventoryPage.java`, `QuickPayPage.java`, and `VirtualCard.java` are all identical copies of the login page object. None has any unique selectors or methods for their named functionality. These are placeholder files that were never implemented.

2. **`Thread.sleep()` pervasive use**: 20+ instances of `Thread.sleep()` across step definitions (values: 1000ms, 2000ms, 3000ms, 5000ms, 10000ms, 15000ms). Playwright provides auto-waiting; `Thread.sleep` is an anti-pattern that makes tests slow, masks real timing issues, and creates fragile suites. Every `Thread.sleep` should be replaced with Playwright's built-in `waitFor`, `waitForSelector`, or `waitForLoadState`.

3. **Broken assertion in SSLoginSteps.java line 219**: 
   ```java
   if(text.equals("bhaggggggggggggggggggggggggggggggggggggggg@onbe.com"));
   assert(false);
   ```
   The `if` statement has an empty body (semicolon terminates it), so `assert(false)` runs unconditionally. This scenario always fails — it is dead test code.

4. **String `==` comparison in Hook.java line 24**:
   ```java
   } else if (scenario.getStatus().toString() == "PASSED") {
   ```
   Java String `==` compares references, not values. This condition will never be true. The PASSED (green) branch is unreachable. Should be `.equals("PASSED")`.

5. **Unclosed JDBC ResultSets**: `DatabaseConnection.jdbcconnection()` returns a `ResultSet` with the `Connection` and `Statement` as local variables that are never closed. This leaks database connections. The `Connection` goes out of scope after the method returns, leaving the underlying TCP connection open until garbage collection. Multiple scenario runs will exhaust the connection pool.

### Medium Priority
6. **No prepared statements**: All SQL in `SearchableAddendaSteps.java` uses `Statement.executeQuery(query)` with concatenated strings. Should use `PreparedStatement` throughout.

7. **`DataMapper` God Object**: `DataMapper.java` has 95 public fields covering all test data for all four applications (MPV, CZ, Wizard, IdPassMe). No encapsulation, no type safety, no null handling. A proper design would use separate data model classes per application context.

8. **`cucumber-junit` scope mismatch**: `pom.xml` line 27 declares `cucumber-junit` with `<scope>compile</scope>` instead of `<scope>test</scope>`. This unnecessarily includes the test framework in non-test compilation.

9. **Duplicate step definition namespace**: `"I am on the login page"` is defined in multiple step classes across different packages: `clientzone/steps/LoginSteps.java`, `demo/steps/LoginSteps.java`, `wizard/steps/LoginSteps.java`, `mypaymentvault/steps/LoginSteps.java`. These are separated by Cucumber `glue` configuration in each runner, preventing conflicts — but it is a fragile design that would break if runners are merged.

10. **`de.erichseifert.vectorgraphics2d.VectorGraphics2D` import**: `SSLoginPage.java` line 5 imports `VectorGraphics2D` from a library not listed in `pom.xml`. This appears to be a phantom import that would cause a compilation error — either the build is broken or there is a transitive dependency resolving this.

11. **`jackson-databind 2.13.4.2`**: This version has known CVEs (e.g., CVE-2022-42003, CVE-2022-42004). Should be upgraded to 2.15.x or 2.16.x.

12. **`ashot 1.5.4`**: Last released in 2017. Unmaintained library. Playwright has built-in screenshot capabilities that should be used instead.

### Low Priority
13. **`mvnw` without Maven version pinning**: The Maven Wrapper does not specify a Maven version in the repository (`.mvn/wrapper/maven-wrapper.properties` is not present in the glob results). This is inconsistent across developer machines.

14. **`pom.xml` comment typo**: Line 53 comment `<!-- Latest stable version as of now -->` for `mssql-jdbc:12.8.1.jre11` — a maintenance antipattern; version comments become stale.

15. **`LogoutFlow.feature` stub**: `LogoutFlow.feature` contains only a login scenario, not a logout scenario. The feature description says "Logout from ClientZone" but no logout action is automated.

## Gen-3 Migration Requirements

If ClientZone, MyPaymentVault, or Wizard are migrated to a Gen-3 architecture (modern API-first, cloud-native), the following changes are required in this test suite:

1. **URL reconfiguration**: All 11 hardcoded `baseUrl` defaults across page objects and JSON data files must be updated. The `wirecard.sys` internal domains and `mypaymentadmin.com` domains would change. Recommend centralizing all base URLs in the JSON data files (rather than page object defaults) for single-point reconfiguration.

2. **Locator redesign for ClientZone**: Absolute XPath expressions (e.g., `//*[@id="sd-menu"]/ul/li[5]/a`, `//*[@id="globalNav"]/table/tbody/tr[3]/td/a`) used throughout ClientZone page objects (`SSLoginPage.java`, `SearchableAddendaPage.java`) are structure-dependent and will not survive a UI rewrite. These must be replaced with semantic locators (`getByRole`, `getByLabel`, `data-testid`) as was done for MPV.

3. **Database query updates**: The `SearchableAddendaSteps.java` JDBC queries reference the `EcountCore` schema by table name. A Gen-3 migration involving database consolidation or schema changes will require query rewrites. Recommend abstracting DB assertions into a dedicated repository/service layer rather than inline SQL in step definitions.

4. **ClientZone stub implementation**: The seven stub-only ClientZone features (QuickPay, PaymentReversal, ManageInventory, InstantIssueAssign, InstantIssueLinktoPrimary, IssueVirtualCard, VirtualResendLink) must be implemented before any Gen-3 migration can be validated by automation. Currently these features are completely unverified.

5. **Authentication modernization**: If SSO is expanded to replace all legacy CZ authentication, the legacy login path (`LoginPage.java`, `LoginSteps.java` in clientzone module) will become obsolete. The SSO test suite (`SSLogin.feature`) covers this path but has several commented-out assertions and dead assertion code that needs remediation.

6. **Headless mode enablement**: Change `PlaywrightManager.java` line 59 from `setHeadless(false)` to environment-variable-controlled: `setHeadless(!"false".equals(System.getenv("HEADLESS")))` to support CI pipeline execution.

7. **Secrets externalization**: Before Gen-3 CI pipeline integration, all credentials must be removed from source-controlled JSON files and moved to a secrets management solution (HashiCorp Vault, AWS Secrets Manager, Azure Key Vault, or CI/CD pipeline secret variables). This is a prerequisite for any regulated environment test execution.

8. **JDBC replacement**: If Gen-3 exposes database state via REST APIs, the JDBC integration in `DatabaseConnection.java` and `SearchableAddendaSteps.java` should be replaced with API calls. This eliminates the direct DB dependency and the schema coupling risk.

## Code-Level Risks

| Risk | Location | Severity | Description |
|---|---|---|---|
| Hardcoded DB credentials | `framework/DatabaseConnection.java:25` | Critical | `b2cstage`/`b2cstage` in source |
| CVV stored in JSON | `src/test/resources/data/mypaymentvault.json:17,56,etc.` | High | 12 CVV values stored plaintext |
| SSN stored in JSON | `src/test/resources/data/mypaymentvault.json:21` | High | `"987654321"` stored plaintext |
| Employee credential | `src/test/resources/data/clientzone.json:9` | High | Named employee email + password |
| Broken assertion | `clientzone/steps/SSLoginSteps.java:219` | High | `assert(false)` unconditional — test always fails |
| String `==` comparison | `framework/Hook.java:24` | Medium | PASSED branch unreachable |
| SQL injection pattern | `clientzone/steps/SearchableAddendaSteps.java:197-257` | Medium | String concatenation in SQL |
| JDBC connection leak | `framework/DatabaseConnection.java:11-36` | Medium | Connection/Statement never closed |
| Unused import (compile error risk) | `clientzone/pages/SSLoginPage.java:5` | Medium | `VectorGraphics2D` not in POM |
| `Thread.sleep` overuse | Multiple step files | Medium | 20+ instances, up to 15 seconds |
| Headless=false | `framework/PlaywrightManager.java:59` | Low | CI incompatible |
| Jackson CVE | `pom.xml:32` — `jackson-databind:2.13.4.2` | Low | Known deserialization CVEs |
| `trustServerCertificate=true` | `framework/DatabaseConnection.java:21` | Low | TLS cert bypass on DB connection |
| `setIgnoreHTTPSErrors(true)` | `framework/PlaywrightManager.java:38` | Low | HTTPS errors silently ignored |
| PII hardcoded in locators | `mypaymentvault/pages/RegistrationPage.java:78-89` | Low | Real address/email/phone in page object |
