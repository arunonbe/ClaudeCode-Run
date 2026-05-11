# Business Analyst — qa-ui-test-automation

## Business Purpose
A **Selenium/Playwright-based UI test automation framework** using Cucumber BDD for Onbe's web applications. It provides end-to-end browser tests that validate user journeys across cardholder self-service portals, admin tools, and back-office applications. The framework is used for smoke testing post-deployment and regression testing of UI changes.

It also covers a secondary scope: REST API testing via RestAssured/Java HTTP clients (the `accountmanagement`, `clientapi`, `communicationhub` packages), making it a hybrid UI + API test suite.

## Capabilities

| Capability | Mechanism | Description |
|---|---|---|
| Playwright browser automation | `com.microsoft.playwright:playwright:1.58.0` | Cross-browser end-to-end UI tests |
| BDD test authoring | Cucumber 7.34.2 + Gherkin `.feature` files | Human-readable test scenarios |
| REST API testing (Java) | `accountmanagement`, `clientapi`, `communicationhub` packages | Java-based API clients (RestAssured or HTTP) |
| Azure Key Vault integration | `azure-security-keyvault-secrets:4.10.4` + `azure-identity:1.18.2` | Runtime secret retrieval (passwords, tokens) from Azure Key Vault |
| Allure / ExtentReports | `extentreports-cucumber7-adapter:1.14.0` | HTML test reporting |
| MS SQL Server DB access | `mssql-jdbc:13.2.1.jre11` | Database validation steps |
| MS Teams notifications | Referenced in README | Test result posting to Teams channels |
| Email notifications | `dawidd6/action-send-mail@v3` in workflows | HTML report delivery on test completion |

## Applications Under Test

| Application | Package | Test Type |
|---|---|---|
| My Payment Admin (MPA) | `mypaymentadmin` | Playwright UI smoke + regression |
| My Payment Vault (MPV) West | `mypaymentvault` | Playwright UI smoke |
| Account Management | `accountmanagement` | REST API (Java client) |
| Client API | `clientapi` | REST API (Java client) |
| ClientZone | `clientzone` | Playwright UI |
| Communication Hub | `communicationhub`, `CommunicationHubAPI` | REST API + Playwright |
| Compass (accounting/analytics) | `compass` | Playwright UI (Login, Entities, ASC606, Accrual) |
| CRCP (Communication Platform) | `crcp` | Playwright UI |
| DevPortal / OEP | (in codebase) | Playwright UI |
| Embedded Payments | `embeddedpayments` | Playwright UI |
| Job Service | (workflow) | Smoke |
| OM Compass SPA | (workflow) | Smoke |
| OMSI | `omsi` | Playwright UI smoke |
| One Platform React (OEP) | (workflow) | Playwright UI smoke |
| Order SVC | (workflow) | Smoke |
| OASIS | `oasis` | Playwright UI |
| Stand-In Processing | (workflow) | Playwright regression |
| West UI / MPA West | (workflow) | Playwright smoke |

## Key Business Flows Under Test

From `.feature` files (partial list):

| Feature | Domain |
|---|---|
| `ActivateCard.feature` | Card lifecycle |
| `AddFunds.feature`, `WithdrawFundsViaACH.feature`, `WithdrawFundsViaCheck.feature` | Fund management |
| `CreateAccountAndLink.feature`, `CreateAccountWithCards.feature` | Account creation |
| `GetBalance.feature`, `GetCardDetails.feature`, `GetCvvStatus.feature` | Card inquiry |
| `SetPin.feature` | PIN management |
| `TransactionSummary.feature` | Transaction history |
| `UpdateAccountStatus.feature`, `UpdateAccountDetails.feature` | Account maintenance |
| `LoginAndLogout.feature` (ClientZone) | Authentication |
| `Login.feature` (Compass) | Admin authentication |
| `Entities.feature`, `ASC606Adjustment.feature`, `AccrualPlatformSettings.feature` | Financial reporting/accounting |
| `CrcpBackendSinchSmsProviderIntegration.feature` | Communication provider |

## Compliance Relevance

| Standard | Relevance |
|---|---|
| PCI DSS Req 6.2 | UI smoke tests provide post-deploy functional validation |
| PCI DSS Req 6.3 | End-to-end tests cover payment flows (add funds, withdraw, activate card, set PIN) |
| SOC 2 (Availability, Processing Integrity) | Smoke tests confirm payment flow availability after deployments |
| GLBA / CCPA | Tests involving cardholder login, registration, and profile access exercise PII-handling flows |

## Business Risks

| Risk | Severity | Notes |
|---|---|---|
| Azure Key Vault dependency — tests fail if Key Vault unreachable | High | All CI runs require Azure identity (`AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`, `AZURE_VAULT_URL`) |
| MS SQL Server JDBC driver present — direct DB access in tests may bypass application controls | Medium | DB-level test assertions need review for data isolation |
| Email notification list validation (`@onbe.com` only) enforced in CI | Low (mitigated) | Email whitelist in playwright workflow provides data leakage protection |
| `SetPin.feature` — PIN management flows must use masked/synthetic data | High | Test scenarios involving PIN must never use real cardholder PINs |
| Long timeout (300 minutes) in playwright workflow | Medium | Runaway tests may tie up CI runners for 5 hours |
