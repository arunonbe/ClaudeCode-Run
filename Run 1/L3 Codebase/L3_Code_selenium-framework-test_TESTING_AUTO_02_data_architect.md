# Data Architect View — selenium-framework-test_TESTING_AUTO

## Data Models

selenium-framework-test_TESTING_AUTO is a test automation framework with no persistent data store of its own. Data is consumed from external test data sources and from the applications under test.

**Test data sources** (observed in repository):
- **Excel spreadsheets** (`.xlsx`, `.xls` via Apache POI):
  - `CSA Test Data.xlsx` / `CSA Test.xlsx` — Customer Service Agent test scenarios
  - `CZ Test.xlsx` / `CZTest Data.xlsx` — Customer Zone test scenarios
  - `Op Test Data.xlsx` — OnePlatform test scenarios
- **XML prerequisite files** (`.xml`):
  - `04010929_11.xml` — CZ prerequisite test data
  - `PH_6813_37.xml` / `PH_2522_38.xml` — Payment Hub prerequisite data
  - `6575createandload_1.xml` / `6575createandload.xml` — order create-and-load test data
  - `virtual script test data .xml` — virtual card test data
- **Properties files**:
  - `Generic.properties` (root Selenium resources) — browser type, base URLs for all applications under test
  - `OP/Generic.properties` — OnePlatform-specific properties

**In-memory data model** (runtime only):
- `base.java`: holds WebDriver instance, URL strings (`url`, `paymenthuburl`, `iddurl`, `CSAurl`, `CZurl`), and credentials (`pw`, `claimcode`)
- Page object classes: hold Selenium WebElement references populated at runtime

## Sensitive Data Handled

This is where the primary data risk lies for this testing repository:

| Data Category | Presence | Risk |
|---|---|---|
| Test credentials/passwords | `pw` field in `base.java`; `Generic.properties` | Credentials stored in properties files in source code |
| Claim codes | `claimcode` field in `base.java` | Test claim codes may be real or semi-real |
| Application URLs | `CSAurl`, `CZurl`, `paymenthuburl`, `iddurl` | Environment URLs (QA/staging) in properties files |
| Excel test data | `.xlsx` files with PII-like test data | Excel files may contain realistic names, card numbers, account IDs |
| XML prerequisite data | `*.xml` files with order/load data | Order files (`createandload`) may contain program IDs, affiliate IDs, amounts |
| SQL credentials | `DatabaseConnection.java` present | MSSQL credentials may be hardcoded or in properties |

**Critical concern**: The `DatabaseConnection.java` file in the test automation framework establishes a direct SQL Server connection. If this connects to a non-production database with production-like data, or if the credentials are hardcoded, this is a significant PCI DSS and GLBA risk.

## Encryption and Protection Status

- No encryption is implemented in the test framework itself
- Credentials in `Generic.properties` and `base.java` are plaintext
- Excel test data files are unencrypted binary files committed to the repository
- XML prerequisite files are unencrypted
- WebDriver communication to the browser is local (no network encryption needed for browser-driver channel); application TLS is handled by the application under test

## Database Schemas

`DatabaseConnection.java` establishes a direct MSSQL connection using `com.microsoft.sqlserver:mssql-jdbc:9.4.0.jre8`. The schema accessed depends on the connection string configuration. This connection is used to either:
- Set up test prerequisites directly in the database, or
- Validate test outcomes by querying database state

This pattern is common in legacy test frameworks but bypasses the application API layer, creating risk of:
- Using database credentials that have excessive privileges
- Leaving test data in production-like environments

## Data Flows

```
Test runner (TestNG)
  → base.java (WebDriver init from Generic.properties)
    → Chrome/Firefox/Edge browser (Selenium WebDriver)
      → Application under test (OnePlatform, CSA, CZ, Payment Hub, IDD)
  
  → DatabaseConnection.java
    → SQL Server (direct JDBC connection for test setup/teardown)
    
  → Apache POI (read Excel test data)
    → Test data spreadsheets (.xlsx)
  
  → ExtentReports
    → HTML report + screenshots (reports/ directory)
```

## Retention Concerns

- Test execution reports in `reports/` directory: `index.html` and screenshots (`Loginpage.png`, `Reg.png`) are committed to the repository — this is unusual; reports should not be in source control
- Excel test data files committed to source: if these contain real or realistic PII/financial data, they must be purged and replaced with synthetic data
- XML prerequisite files may contain real program/affiliate IDs and order amounts — must be reviewed and synthetic data used instead

## PCI DSS Data Storage Compliance

- Test data must use synthetic data only per PCI DSS Requirement 6.3.4 (use of production data in testing is prohibited unless sanitized)
- The presence of `createandload` XML files with order data suggests real-looking prepaid card order payloads — these must be reviewed to confirm no real PANs or account numbers are present
- Direct database access from tests bypasses application-layer security controls; the SQL credentials used must have minimum required permissions (read-only where possible) and must be rotated regularly
- Test credentials in `Generic.properties` must not be shared with production systems; test environment credentials must be separate and not committed to source control
