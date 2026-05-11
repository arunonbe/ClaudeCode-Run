# Automation_ClientZone — Enterprise Architect View

## Platform Generation (Gen-1/Gen-2/Gen-3)

This repository tests multiple generations of Onbe platform components simultaneously:

| Module | Generation | Indicators |
|---|---|---|
| **ClientZone (legacy)** | Gen-1 | JSP-based URLs (`.jsp`, `.do` suffixes); `wirecard.sys` internal domain; legacy auth at `q-na-app02.nam.wirecard.sys:9107`; Struts/Java EE action pattern (`/getDomains.do`, `/messageHome.do`, `/login.jsp`) |
| **Wizard / Program Setup Assistant** | Gen-1 | Same `wirecard.sys` infrastructure; Struts action URLs (`/wizard/loginaction.do`, `/wizard/programdashboardaction.do`, `/wizard/configDisplay.do`, `/wizard/websiteSettings.do`) |
| **ClientZone (SSO/modern)** | Gen-1 to Gen-2 transition | Hosted at `clientzone-qa.mypaymentadmin.com` — modern domain but still JSP/Struts underlying architecture; SSO integration via Microsoft Entra ID represents a Gen-2 identity layer overlay on Gen-1 |
| **MyPaymentVault** | Gen-2 | Modern SPA-style routing (`/login`, `/dashboard`, `/registration`, `/banktransfer`, `/transaction`, `/changepin`, `/changePassword`, `/profileDetails`); React/component-based locators (`getByLabel`, `getByRole`, ARIA roles); hosted at `mypaymentvault.qa.onbe.dev` — Onbe-branded domain |
| **IdPassMe** | Gen-2/Gen-3 | Modern React SPA (`qa.idpassme.com`); `/kyc/identity/verification` path; multi-currency, multi-country KYC flow; likely a newer platform service |

## Business Domain

**Payments / Prepaid Card Administration and Cardholder Self-Service**

This repo spans two primary business domains:

1. **B2B Program Management (ClientZone + Wizard)**: Client-facing administration for Onbe's prepaid card programs. Clients use ClientZone to manage cardholder inventory, initiate payments, manage addenda/memo data, and configure program settings. The Wizard is used by Onbe internal teams to configure program profiles and website display settings.

2. **B2C Cardholder Self-Service (MyPaymentVault + IdPassMe)**: Cardholder-facing portal for account registration, card activation, balance viewing, transaction history, fund transfers (ACH, checks), PIN/password management, and KYC identity verification for global disbursements.

## Role in Platform

- **Automation_ClientZone** is the QA automation layer — it has no runtime role in the platform itself.
- It serves as the **acceptance test gate** for four platform applications: ClientZone, MyPaymentVault, the Program Setup Wizard, and IdPassMe.
- The `SearchableAddendaSteps.java` is the most functionally sophisticated component, implementing a UI-to-database reconciliation test that validates the consistency between the `EcountCore` database and the ClientZone cardholder search UI — this is a cross-layer integration test.
- The Wizard `DisplayCardDetails.feature` implements an end-to-end cross-application test: Wizard (admin config change) → MPV (cardholder-facing effect), testing that a program configuration change propagates correctly to the cardholder portal.

## Dependencies

### Upstream Application Dependencies
| Dependency | Type | Evidence |
|---|---|---|
| ClientZone web app | HTTP/browser | `q-na-app02.nam.wirecard.sys:9107`, `clientzone-qa.mypaymentadmin.com` |
| MyPaymentVault web app | HTTP/browser | `mypaymentvault.qa.onbe.dev` |
| Program Setup Wizard | HTTP/browser | `q-na-app05.nam.wirecard.sys:8090` |
| IdPassMe | HTTP/browser | `qa.idpassme.com` |
| EcountCore SQL Server | JDBC | `Q-LIS-DB02:2231`, database `EcountCore` |
| Microsoft Entra ID (AAD) | OAuth/SAML redirect | SSO flow redirects to Microsoft identity provider (`Sign in to your account` page title) |
| AT&T Security Server | External IdP | SSO test for `@att.com` domain routes to `AT&T Security Server: Login` |

### Library Dependencies
- Microsoft Playwright 1.45.1 (Browser automation)
- Cucumber JVM 7.18.1 (BDD framework)
- Jackson 2.13.4.2 (JSON parsing)
- ExtentReports 5.1.0 (HTML reporting)
- AShot 1.5.4 (Visual comparison)
- MSSQL JDBC 12.8.1.jre11 (Database access)
- JUnit 4.11 (Test runner)

### Downstream Dependencies (none)
This is a test-only repository. No other systems depend on it.

## Integration Patterns

1. **Browser Automation (Page Object Model)**: All application interactions use the Page Object Model pattern. `BasePage` (abstract) → concrete page classes (e.g., `LoginPage`, `BankTransferPage`). `BaseSteps` provides the shared Playwright `Page` instance from `PlaywrightManager`.

2. **BDD / Gherkin**: Four-layer stack: Feature files (Gherkin) → Step Definitions (Java) → Page Objects (Java) → Playwright API → Browser.

3. **Data-Driven via JSON**: Test data externalized to JSON files, deserialized through `ConfigData` → `DataMapper` chain. Environment selection via `System.getenv("env")` key matching JSON structure.

4. **Direct JDBC Integration**: `DatabaseConnection.jdbcconnection()` provides direct read access to the EcountCore SQL Server. Used in `SearchableAddendaSteps` for UI-to-DB reconciliation — a pattern more typically seen in API-level or service-level tests. This creates a tight coupling between the test suite and the internal database schema.

5. **Cross-Application End-to-End**: `wizard/steps/MpvLoginSteps.java` imports `mypaymentvault.pages.LoginPage` — the Wizard test module shares page objects from the MPV module to validate cross-application behavior (Wizard config → MPV rendering).

6. **Hook-based Lifecycle**: `framework/Hook.java` uses Cucumber `@Before`/`@After` hooks for Playwright browser lifecycle management. A single browser session (non-persistent context) is created per scenario.

## Strategic Status

| Component Under Test | Assessment |
|---|---|
| **ClientZone (legacy)** | Legacy Gen-1 system on Wirecard-era infrastructure (`wirecard.sys` domain). Multiple page objects are boilerplate shells (InstantIssuePage, PaymentReversalPage, ManageinventoryPage, etc. are identical login-only stubs). Automation coverage is shallow — only login and SSO flows are fully implemented for ClientZone. |
| **MyPaymentVault** | Active Gen-2 product with the most comprehensive automation coverage in this repo (~30 feature files, fully implemented step definitions). This is clearly the primary focus of automation effort. |
| **Wizard** | Gen-1 admin tool with targeted automation for a specific feature (DisplayCardDetails toggle). Narrow scope — only program display settings are tested. |
| **IdPassMe** | Modern KYC service with partial automation. Three feature files covering login/identity verification, edit profile, and edit address. |

**Strategic implication**: The automation investment is asymmetric — MyPaymentVault is well-covered, ClientZone business operations (QuickPay, PaymentReversal, Inventory, Virtual Card, Instant Issue) are effectively unautomated despite having feature file stubs.

## Migration Blockers

1. **Gen-1 ClientZone dependency**: Seven ClientZone feature files exist as stubs with only login scenarios. Any migration or decommission of ClientZone Gen-1 will require these stubs to be either implemented against the new platform or deleted.

2. **`wirecard.sys` hard-coded URLs**: Wizard and legacy ClientZone tests hard-code internal `q-na-app05.nam.wirecard.sys:8090` and `q-na-app02.nam.wirecard.sys:9107` / `q-na-app01.nam.wirecard.sys:9107`. If these hosts are decommissioned as part of a Wirecard infrastructure migration, all tests targeting these hosts break immediately.

3. **EcountCore schema coupling**: `SearchableAddendaSteps.java` contains multi-table SQL joins against the `EcountCore` database schema. Any schema migration (table renames, column changes, new CDE architecture) will break these queries. The queries reference 8 distinct tables with specific column names.

4. **XPath/CSS locator fragility**: Many ClientZone page objects use absolute XPath expressions (e.g., `"//*[@id=\"globalNav\"]/table/tbody/tr[3]/td/a"`, `"//*[@id=\"sd-menu\"]/ul/li[5]/a"`). These will break on any HTML structure change to the ClientZone UI.

5. **JUnit 4 dependency**: The runner pattern uses JUnit 4 (`@RunWith(Cucumber.class)`). Cucumber 7 supports JUnit 5 as well; the suite is tied to the JUnit 4 ecosystem. Migrating to JUnit 5 (Platform) would require runner changes.

6. **Java 21 Preview Features**: `--enable-preview` is active. Any upgrade to a future Java LTS may require feature re-evaluation.

7. **SSO identity provider coupling**: SSO tests are coupled to Microsoft Entra ID (Onbe's `@onbe.com` tenant) and AT&T's external identity provider. Changes to SSO configuration, tenant IDs, or provider redirects will break `SSLogin.feature` tests.

8. **Static account state dependencies**: Tests for bank transfer, request check, change PIN, and change password rely on specific QA accounts with specific card states (active cards, linked bank accounts). A QA environment refresh or account cleanup breaks these tests.
