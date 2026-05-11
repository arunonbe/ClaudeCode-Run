# Solution Architect — qa-ui-test-automation

## Technical Architecture

```
qa-ui-test-automation/
├── pom.xml                        -- Maven project (Java 21, Playwright + Cucumber)
├── src/test/java/
│   ├── framework/                 -- Base classes (BasePage, BaseSteps, BaseRunner)
│   ├── {application}/
│   │   ├── features/              -- Gherkin .feature files
│   │   ├── pages/                 -- Page Object Model classes
│   │   ├── steps/                 -- Cucumber step definitions
│   │   └── runners/               -- TestRunner.java (CucumberOptions)
│   └── ...
├── .github/
│   ├── agents/                    -- AI agent instructions
│   │   ├── Onbe_QA_Agent.md
│   │   ├── Onbe_Test_Runner_Agent.md
│   │   ├── Onbe_Code Coverage_Report_Agent.md
│   │   └── Onbe_Tricentis_Migration_Agent.md
│   ├── copilot-instructions.md    -- GitHub Copilot guidance
│   ├── instructions/
│   │   └── cucumber-runners.instructions.md
│   ├── skills/
│   │   └── page-locator-inspector/ -- SKILL.md for locator inspection
│   └── workflows/                  -- ~25 workflow files
└── screenshots/                   -- Failure screenshots (committed examples)
```

### Framework Architecture

Based on the copilot instructions and package structure:

```
BaseRunner          <- CucumberOptions(features, glue, plugin)
  TestRunner (per application package)

BaseSteps           <- Playwright Page instance
  {Application}Steps

BasePage            <- Playwright Page, navigation helpers
  {Application}Page
```

PicoContainer provides dependency injection between Cucumber steps (shared `Page` instance).

## API Surface
No Onbe-owned API exposed. This is a test framework only.

## Security Posture

### Azure Key Vault Integration
Secrets are retrieved from Azure Key Vault at test startup:
- Authentication: Service Principal (`AZURE_CLIENT_ID` + `AZURE_CLIENT_SECRET`) or Managed Identity
- Library: `com.azure:azure-security-keyvault-secrets:4.10.4` + `com.azure:azure-identity:1.18.2`
- This is the correct pattern — secrets never committed to VCS

### Email Notification Security
The `playwright-test.yml` reusable workflow enforces `@onbe.com`-only email notification:
```bash
if [[ ! "$email" =~ @([A-Za-z0-9-]+\.)*onbe\.com$ ]]; then
  echo "ERROR: Non-Onbe email detected: '$email'. Only @onbe.com addresses are allowed."
  exit 1
fi
```
This prevents test reports (which may contain sensitive application data) from being emailed externally.

### SMTP Security
Office365 SMTP at port 587 with STARTTLS (`secure: false` in workflow — this means no SSL wrapping, relies on STARTTLS upgrade). Credentials via GitHub Secrets.

### Screenshots
Committed example screenshots (`screenshots/confirmTransfer.png`, `screenshots/CurrentBalance.png`) suggest screenshots from real application sessions may be stored in the repository. These should be replaced with synthetic examples.

## Technical Debt

| Item | Location | Severity |
|---|---|---|
| `poi-ooxml-schemas:4.1.2` while `poi` is `5.5.1` and `poi-ooxml` is `5.4.0` — version mismatch | `pom.xml:77–84` | Medium — may cause runtime `ClassNotFoundException` or method signature conflicts |
| `ashot:1.5.4` (screenshot utility) — unmaintained since 2017 | `pom.xml:93–96` | Low — Playwright has built-in screenshot capability |
| `slf4j-log4j12:2.0.17` adapter bridges to Log4j 1.x but Log4j 2 is also on classpath | `pom.xml:128–135` | Medium — logging bridge conflict; should use `log4j-slf4j2-impl` instead |
| Committed screenshots may contain real application state | `screenshots/` | Medium |
| `Onbe_Tricentis_Migration_Agent.md` — planned platform migration | `.github/agents/` | High — may deprecate this codebase |
| `threadCount=1` in Surefire — no test parallelisation | `pom.xml:201` | Low — tests run sequentially; slower CI |
| 300-minute workflow timeout | `playwright-test.yml:42` | Medium |

## Gen-3 Migration Requirements
This framework is already relatively modern (Java 21, Playwright 1.58, Cucumber 7). For Gen-3 alignment:
1. Standardise on Azure Key Vault for all environment credentials (already done)
2. Remove Apache Commons HttpClient-based API test packages; replace with RestAssured or Spring WebClient
3. Upgrade `poi-ooxml-schemas` to match `poi-ooxml` version (both to 5.4.x)
4. Replace `slf4j-log4j12` with `log4j-slf4j2-impl`
5. Enable test parallelism (`threadCount > 1`)
6. Assess Tricentis migration impact before further investment

## Code-Level Risks (file:line references)

| Risk | File | Line | Detail |
|---|---|---|---|
| POI version mismatch (`poi-ooxml-schemas:4.1.2` vs `poi-ooxml:5.4.0`) | `pom.xml` | 77–84 | Mismatched Apache POI artifact versions on classpath |
| SLF4J + Log4j bridge conflict (`slf4j-log4j12` + `log4j-core` both present) | `pom.xml` | 128–144 | Dual logging framework — `slf4j-log4j12` routes to Log4j 1.x; `log4j-core` is 2.x |
| Screenshots committed to VCS may contain sensitive application data | `screenshots/` | — | `screenshots/CurrentBalance.png`, `screenshots/confirmTransfer.png` — should be scrubbed |
| `secure: false` in email workflow (STARTTLS not explicitly enforced) | `playwright-test.yml` | ~128 | `secure: false` relies on STARTTLS auto-upgrade; explicit TLS preferred |
| `executionMode=Local` hardcoded in Surefire config | `pom.xml` | 213 | `<executionMode>Local</executionMode>` — may not be correct for CI runner environment |
