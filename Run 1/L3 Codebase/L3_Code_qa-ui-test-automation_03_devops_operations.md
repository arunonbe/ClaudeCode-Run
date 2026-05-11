# DevOps / Operations — qa-ui-test-automation

## Build System

| Property | Value |
|---|---|
| Build tool | Apache Maven (Wrapper `./mvnw` provided) |
| Java version | 21 |
| Root artifact | `qa:qa-ui-test-automation:0.0.1-SNAPSHOT` |
| Test framework | Playwright 1.58.0 + Cucumber 7.34.2 |
| DI for Cucumber | PicoContainer |
| Report | ExtentReports 5.1.2 + extentreports-cucumber7-adapter |
| Browser install | `./mvnw exec:java -D exec.mainClass=com.microsoft.playwright.CLI -D exec.args="install chrome"` |

Maven Surefire is configured to run `**/*Runner*.class` in the `integration-test` phase with `threadCount=1` (sequential) and `-Xmx2g`.

## Deployment
No service deployment. Workflow triggers execute the Maven test runner against a target environment.

## CI/CD Workflows

### Core Reusable Workflow: `playwright-test.yml`

The central reusable workflow that all per-application workflows call:

| Step | Action |
|---|---|
| Setup JDK 21 | `actions/setup-java@v4` (Temurin distribution) |
| Checkout | `actions/checkout@v4` |
| Install Playwright Chrome | `./mvnw exec:java ... install chrome` |
| Execute tests | `./mvnw -X clean test -Dtest={package}.runners.TestRunner [-Dcucumber.filter.tags=...]` |
| Rename report | `mv target/TestResults.html target/test-report-{package}.html` |
| Upload report | `actions/upload-artifact@v4` |
| Validate notification emails | Bash regex — only `@onbe.com` addresses allowed |
| Send email (optional) | `dawidd6/action-send-mail@v3` via Office365 SMTP |

Runner: custom runner group `test-automation-runners` (self-hosted or managed).
Timeout: 300 minutes.

### Per-Application Workflows

| Workflow | Application | Trigger |
|---|---|---|
| `om-mypaymentadmin-spa-smoke.yml` | MyPaymentAdmin SPA | `workflow_dispatch` (qa/prod), push to `src/test/java/mypaymentadmin/**` |
| `om-mypaymentadmin-spa-regression.yml` | MyPaymentAdmin SPA | Manual |
| `mypaymentvaultwest-production-smoke-test.yml` | MyPaymentVault West | Production smoke |
| `omsi-smoke.yml` | OMSI | Smoke |
| `om-compass-spa-smoke.yml` | Compass SPA | Smoke |
| `devportal.yml` | Dev Portal | Smoke/regression |
| `embedded-payments-ui-tests.yml` | Embedded Payments | UI tests |
| `oasis.yml` | OASIS | UI tests |
| `internal-apps-playwright-test.yml` | Internal apps | Playwright tests |
| `communicationhub-api-tests.yml` | Communication Hub | API tests |
| `stand-in-processing-api-regression.yml` | Stand-In Processing | Regression |
| `jobservice-smoke.yml` | Job Service | Smoke |
| `west-ui-smoke-test.yml` | West UI | Smoke |
| `oneplatform-react_WAPP-smoke.yml` | OEP | Smoke |
| `playwright-e2e-tests.yml` | General E2E | All Playwright |

## Configuration Management

| Parameter | Source |
|---|---|
| `ONBE_PLAYWRIGHT_ENV` | Workflow input (`qa`, `prod`, etc.) |
| `ONBE_PLAYWRIGHT_HEADLESS_BROWSER` | Hardcoded `true` in workflow |
| `AZURE_VAULT_URL` | GitHub Secret — required for all runs |
| `AZURE_TENANT_ID` | GitHub Secret — required for all runs |
| `AZURE_CLIENT_ID` | GitHub Secret — required for all runs |
| `AZURE_CLIENT_SECRET` | GitHub Secret — required for all runs |
| `SMTP_USERNAME` / `SMTP_PASSWORD` | GitHub Secret — optional for email notifications |

Application-specific URLs and test data are loaded from Azure Key Vault at runtime.

## Observability

| Signal | Mechanism |
|---|---|
| Test execution logs | Maven Surefire output in GitHub Actions runner log |
| HTML test reports | `target/test-report-{package}.html` — uploaded as artefact |
| Screenshots on failure | Captured to `screenshots/` directory (visible in `screenshots/*.png`) |
| MS Teams notifications | Referenced in README; implementation not fully visible |
| Email notifications | Via `dawidd6/action-send-mail@v3` (Office365 SMTP) |

## Infrastructure Dependencies

| Dependency | Purpose |
|---|---|
| Azure Key Vault | Credential retrieval at test runtime |
| `test-automation-runners` runner group | GitHub Actions execution environment |
| Target web applications (QA/PROD) | Applications under test |
| Office365 SMTP (`smtp.office365.com:587`) | Test result email delivery |
| Playwright Chromium | Browser automation |
| MS SQL Server | Database assertions |

## Operational Risks

| Risk | Severity | Notes |
|---|---|---|
| 300-minute workflow timeout — runaway tests block runners | High | Long-running tests may tie up `test-automation-runners` group |
| Azure Key Vault unavailability fails all CI test runs | High | Key Vault is a hard dependency for all test executions |
| `playwright-e2e-tests.yml` appears to be a catch-all — may overlap other workflows | Medium | Potential duplicate test execution |
| Cucumber agent instructions in `.github/agents/` include `Onbe_Tricentis_Migration_Agent.md` — suggests planned tool migration | Medium | Migration to Tricentis may invalidate current Playwright investment |
| SMTP credentials in GitHub Secrets — rotation schedule unclear | Medium | Office365 credentials must be rotated per policy |
| Screenshots may expose PII/CHD | Medium | See data architect findings |
| `poi-ooxml-schemas:4.1.2` while `poi` is `5.5.1` and `poi-ooxml` is `5.4.0` — version mismatch | Low | May cause classpath conflicts |

## CI/CD Pipeline Summary

```
Application deployment (or manual trigger)
  --> {app}-smoke.yml
      --> playwright-test.yml (reusable)
          1. Setup JDK 21 (Temurin)
          2. Checkout
          3. Install Playwright Chrome
          4. Run: ./mvnw clean test -Dtest={package}.runners.TestRunner
                  -Dcucumber.filter.tags=@{app}-smoke
          5. Upload HTML report artefact
          6. (Optional) Email report to @onbe.com recipients
```
