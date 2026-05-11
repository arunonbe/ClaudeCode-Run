# Enterprise Architect — qa-ui-test-automation

## Platform Generation
**Cross-generational testing tool** — Tests Gen-1 through Gen-3 web applications. The test framework itself (Playwright 1.58, Cucumber 7, Java 21) is Gen-3 compatible. Older test packages (e.g., `accountmanagement` with Java-based API clients) may reflect Gen-2 patterns.

## Business Domain
**Quality Engineering / UI Test Automation** — Horizontal capability serving all cardholder self-service and admin UI domains.

## Role in the Architecture
This repository is the **central UI test automation platform** for Onbe's web applications. It:
- Provides post-deployment smoke test gating via GitHub Actions
- Covers regression testing for payment and admin flows
- Acts as a secondary API test layer (Java-based REST clients) for some services
- Integrates with Azure Key Vault for secure credential management in CI

## Applications Under Test Mapping

| Business Domain | Application | Test Package |
|---|---|---|
| Cardholder Self-Service | MyPaymentVault (west) | `mypaymentvault` |
| Admin / Back-Office | MyPaymentAdmin (SPA) | `mypaymentadmin` |
| Card Activation | ClientZone | `clientzone` |
| Financial Accounting | Compass SPA | `compass` |
| Communication Platform | CRCP | `crcp` |
| API Account Management | Account Management | `accountmanagement` (API) |
| API Client | Client API | `clientapi` (API) |
| Messaging | Communication Hub | `communicationhub`, `CommunicationHubAPI` |
| Digital / Embedded Payments | Embedded Payments, OEP | `embeddedpayments`, `devportal` |
| Internal tools | OMSI, OASIS, Job Service | Various |
| Stand-In Processing | Stand-In API | `stand-in-processing` |

## Key External Dependencies

| System | Role |
|---|---|
| Azure Key Vault | Credential store for test secrets |
| All Onbe web applications (QA/PROD) | Systems under test |
| `test-automation-runners` GitHub runner group | CI execution infrastructure |
| Office365 SMTP | Email notification delivery |
| `Onbe/om-ci-setup` (inferred) | Shared CI patterns |

## Integration Patterns

| Pattern | Implementation |
|---|---|
| Page Object Model (POM) | `pages/` packages per application (e.g., `clientzone/pages/LoginPage.java`) |
| BDD via Cucumber | `.feature` files with Gherkin; steps in Java `steps/` packages |
| Azure Key Vault secret injection | `azure-security-keyvault-secrets` SDK at test startup |
| Reusable CI workflow | `playwright-test.yml` called by all per-app workflows |
| Data-driven testing | Apache POI (Excel) and HOCON config |

## Strategic Status
**Active investment.** This repository is actively maintained with:
- Recent dependency updates (Playwright 1.58.0, Cucumber 7.34.2, POI 5.x, Log4j 2.25.3)
- Multiple AI agent definitions in `.github/agents/` (Onbe QA Agent, Test Runner Agent, Code Coverage Agent)
- A **Tricentis Migration Agent** (`Onbe_Tricentis_Migration_Agent.md`) — indicating evaluation or planned migration to Tricentis Tosca/NeoLoad as a replacement test platform

## Risks to Enterprise Architecture

| Risk | Impact |
|---|---|
| Planned Tricentis migration may deprecate this entire codebase | High — investment in new Playwright tests may be wasted if migration proceeds |
| Azure Key Vault hard dependency — all CI fails without Azure connectivity | High |
| Mixed UI + API tests in one repo — responsibilities not cleanly separated | Medium |
| Screenshots from production smoke tests may contain CHD | Medium — PCI DSS CDE concern |
| `test-automation-runners` runner group — if runners are on-premises, infra maintenance burden | Medium |
| 300-minute timeout per job — can exhaust runner capacity | Medium |
