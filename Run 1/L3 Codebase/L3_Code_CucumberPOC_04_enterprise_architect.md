# CucumberPOC — Enterprise Architect View

## Platform Generation
- **Generation:** Test Tooling / QA Automation — not a production service.
- **Technology stack:** Java 21, Maven, Cucumber 7, Selenium 4, JUnit 5, ExtentReports.
- **Maturity:** POC / early prototype. No CI pipeline. Email reporting disabled. Thread-sleep-based synchronisation.

## Domain
- QA / Test Automation domain, subordinate to the **ClientZone / Payment Vault** product domain.
- Targets the consumer cardholder self-service web application (`mypaymentvault.stage.onbe.dev`).

## Role in the Ecosystem
- Provides functional regression coverage for the Login and Card Registration flows of Payment Vault.
- Currently decoupled from any CI/CD gate; results are not blocking any deployment pipeline.

## Upstream Dependencies
| Dependency | Type |
|---|---|
| Payment Vault staging environment | Runtime target (browser-driven) |
| Onbe staging network / VPN | Network access |
| Chrome browser + chromedriver | Local infrastructure |

## Downstream Consumers
- QA team / developers running tests manually.
- Intended future consumer: CI pipeline (not yet wired).

## Architectural Patterns
- **Page Object Model (POM):** `LoginPage.java`, `UserRegistrationPage.java` encapsulate element locators.
- **BDD (Gherkin):** Feature files in `src/test/resources/features/`; step definitions in `stepDefinitions/`.
- **Factory pattern:** `DriverFactory.java` manages `ThreadLocal<WebDriver>` creation/teardown.
- **Configuration externalisation:** `ConfigReader.java` reads all environment-specific values from `config.properties`.

## Strategic Alignment
- Aligns with Onbe's quality-assurance objectives for the Payment Vault product.
- Should be elevated to a proper CI-gated automation suite (see Blockers).

## Blockers / Gaps
1. No CI/CD pipeline integration — tests must be run manually.
2. `config.properties` with sensitive test data (card number, CVV, SSN) is committed to version control — needs secret-store migration (Azure Key Vault, GitHub Secrets, or `.env` pattern with `.gitignore`).
3. Email reporting is non-functional (empty password, call commented out).
4. No tagging strategy for smoke vs regression; all scenarios run together.
5. No cross-browser matrix or headless execution configuration for CI.
