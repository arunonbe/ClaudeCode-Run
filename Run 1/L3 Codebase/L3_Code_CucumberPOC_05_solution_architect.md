# CucumberPOC — Solution Architect View

## Architecture Overview
Standalone Maven project with a classic Cucumber-JUnit-Selenium stack. No application server, no database. Executes entirely client-side by driving a browser against the Payment Vault staging URL.

```
TestRunner.java (JUnit @RunWith Cucumber)
    |
    +-- Hooks.java (Before/AfterStep/After lifecycle)
    |       +-- DriverFactory.initializeDriver()
    |       +-- ScreenshotUtil.captureScreenshot() on failure
    |
    +-- Feature files (Login.feature, Registration.feature)
            |
            +-- LoginSteps.java  --> LoginPage.java --> WebDriver
            +-- UserRegistrationSteps.java --> UserRegistrationPage.java --> WebDriver
```

## Page Object Design
- `LoginPage.java`: locators for username (`By.id("username")`), password (`By.id("password")`), login button (`By.id("login")`), error popup (`By.xpath("//div[@class='modal-content']")`), language dropdown.
- `UserRegistrationPage.java`: locators for cardNumber, cvv, postalCode, password, confirmPassword, socialSecurityNumber, dob, termAndCondition, Submit, Continue.

## Security Observations
- `config.properties` (lines 6–9) contains card number, CVV, SSN, and DOB for a test cardholder. File is committed to the repository without encryption.  
  **Risk:** If this file were ever populated with real cardholder data, it would violate PCI DSS Req 3 (protect stored account data) and applicable privacy law (CCPA/GLBA). Confirm values are synthetic.
- `EmailLib.java` (line 24): SMTP password is an empty string literal — credential placeholder left in code.
- No HTTPS certificate pinning or proxy configuration; tests trust the staging TLS certificate implicitly.

## Technical Debt
| Item | File | Description |
|---|---|---|
| `Thread.sleep(30000)` | `UserRegistrationSteps.java:99` | Hard-coded 30s wait — brittle, slow |
| `Thread.sleep(5000)` | `LoginSteps.java:28` | Hard-coded 5s wait on page load |
| `Thread.sleep(1000/2000/3000)` | Multiple | Scattered throughout page objects and steps |
| Deprecated `junit.framework.Assert` | `LoginSteps.java:6` | Should use `org.junit.jupiter.api.Assertions` for JUnit 5 |
| Empty SMTP password | `EmailLib.java:24` | Email feature non-functional |
| Email call commented out | `Hooks.java:39` | Dead code path |
| `screenshots/` in source tree | `.` | Binary assets (3 PNGs) committed to repo |

## Gen-3 Migration Readiness
- This is a test project, not a production service; Gen-3 migration is not directly applicable.
- To align with Gen-3 CI/CD standards: migrate to GitHub Actions workflow, add secret management for `config.properties` values, enable headless Chrome, and tag scenarios for smoke/regression gates.

## Code Risks
- `DriverFactory.getDriver()` returns `null` until `initializeDriver()` is called; `LoginSteps.java` line 16 calls `DriverFactory.getDriver()` at class construction time (before `@Before` hook runs) — this will return `null` and cause NPE if `initializeDriver()` hasn't been called yet. Mitigated in practice by Cucumber lifecycle, but fragile.
- `AnnoationHelper.java` (in custom-files_LIB, referenced by context) — typo in class name ("Annoation") is cosmetic but indicates legacy heritage.
