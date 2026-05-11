# CucumberPOC — Data Architect View

## Data Stores
This project does not own or maintain any database. All persistent state is the Payment Vault web application under test.

## Runtime Data Sources
| Source | Location | Contents |
|---|---|---|
| `config.properties` | `src/test/resources/config.properties` | Base URL, credentials, card number, CVV, postal code, SSN, DOB, browser setting |
| `extent.properties` | `src/test/resources/extent.properties` | ExtentReports output configuration |
| Screenshot files | `screenshots/` and `target/SparkReport/screenshots/` | PNG captures on step failure |
| HTML report | `target/SparkReport/ExtentSparkReport.html` | Execution results |

## Sensitive Data Inventory
| Field | Location | Nature |
|---|---|---|
| `card.number` | `config.properties` line 6 | 16-digit card number (test environment value) |
| `cvv.code` | `config.properties` line 7 | 3-digit CVV (test environment value) |
| `ssn.code` | `config.properties` line 9 | 9-digit SSN-format value (test environment value) |
| `date.birth` | `config.properties` line 10 | Date of birth (test environment value) |
| `valid.password` | `config.properties` line 3 | Plaintext password for test account |

> Note: Values are not reproduced here per data-handling policy. Confirm with the QA team that all values in `config.properties` are synthetic test data and not derived from real cardholders.

## Encryption
- No encryption is applied to `config.properties`; it is a plaintext file committed to the repository.
- SMTP password field (`EmailLib.java` line 24) is empty string — no credential stored.
- Screenshots are unencrypted PNG files; failure screenshots during registration could capture card number or SSN values displayed in the browser.

## Data Flow
```
config.properties
      |
      v
ConfigReader.getProperty()  (static init, ClassLoader resource)
      |
      v
Step Definitions (LoginSteps, UserRegistrationSteps)
      |
      v
Page Objects (LoginPage, UserRegistrationPage) --> Browser via Selenium WebDriver
      |
      v
Target App (Payment Vault) --> Response / DOM
      |
      v
Assertions / Screenshots --> target/SparkReport/
```

## Data Quality
- No input validation on properties values; if a key is missing `ConfigReader.getProperty()` returns `null` and Selenium will silently type "null" into form fields.
- Username uniqueness enforced programmatically via epoch timestamp (`UserNameGenerate.java`).

## Compliance Gaps
- Sensitive test data (card number, CVV, SSN, DOB) stored in plaintext VCS-tracked file.
- Failure screenshots may inadvertently capture PAN or SSN from the browser DOM; screenshots are stored unencrypted in the repo's `target/` directory.
- No `.gitignore` entry to exclude `config.properties` or the `screenshots/` directory from commits; screenshots from prior runs are already present in the `screenshots/` folder in source.
