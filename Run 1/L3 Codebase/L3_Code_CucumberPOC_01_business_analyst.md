# CucumberPOC — Business Analyst View

## Business Purpose
CucumberPOC is a Selenium-based UI test-automation proof-of-concept targeting the **Payment Vault** consumer-facing web application (base URL: `mypaymentvault.stage.onbe.dev`). It is not a production service; its role is to validate that the cardholder registration and login flows work correctly before or after a release.

## Capabilities
| Capability | Status |
|---|---|
| Cardholder login (valid / invalid / inline-error scenarios) | Implemented — `Login.feature` |
| Language dropdown verification (EN / ES / FR) | Implemented — `Login.feature` |
| Static link verification on login page | Implemented — `Login.feature` |
| Full card-registration flow (7-screen wizard) | Implemented — `Registration.feature` |
| Post-run HTML report emailed to team | Partially implemented — `EmailLib.java`; email send is commented out in `Hooks.java` line 39 |

## Key Entities
| Entity | Source |
|---|---|
| Cardholder / payee | UI subject; credentials come from `config.properties` |
| Card | Identified by card number field; tested in Registration flow |
| Username | Auto-generated via `UserNameGenerate.java` (prefix `RPA` + epoch ms) |

## Business Rules Tested
- Login must redirect to `/dashboard` on success.
- Invalid credentials must surface a modal error popup.
- Leaving username/password fields blank then clearing must show inline validation text.
- Registration wizard must pass through: Register Card → Username & Password → Contact Information → Terms & Conditions → Confirm → Congratulations.
- CVV and SSN values are read from `config.properties`; these fields have test values present in the file (see Compliance section).

## Test Flows
1. **Happy Path Login** (`@valid`) — navigate → enter credentials → assert dashboard URL.
2. **Unhappy Path Login** (`@invalid`) — enter bad credentials → assert modal popup.
3. **Inline Validation** (`@inlineError`) — type then clear each field → assert inline error text.
4. **Link Check** (`@links`) — assert 8 links visible on login page.
5. **Language Dropdown** (`@lanDD`) — open dropdown → assert EN/ES/FR options.
6. **Create Account** (`@CreateAccount`) — full 7-screen wizard.

## Compliance / Risk Notes
- `config.properties` contains **test credential data** including a card number, CVV code, SSN, and date of birth. These values appear to be synthetic/test values for the staging environment. Storing real PANs or real SSNs in source control would violate PCI DSS Requirement 3 and applicable privacy regulations. The team must confirm these are purely synthetic test values and not real cardholder data.
- Email recipient hard-coded as `rashmi.dhandar@onbe.com` in `EmailLib.java` (line 23); email password field is empty (line 24) — email function is therefore non-operational.
- No data-masking of card or SSN values in test logs; if ever run against a non-synthetic environment, log output could expose sensitive data.

## Risks
- `Thread.sleep` calls scattered throughout step definitions (e.g., `UserRegistrationSteps.java` line 99 — 30-second sleep) make tests brittle and slow.
- Browser driver is hard-coded to Chrome default; CI agents must have chromedriver on PATH.
- No retry logic or explicit wait strategy beyond WebDriverWait in page objects.
- Target URL is a `stage` environment; running against production is one config-property change away.
