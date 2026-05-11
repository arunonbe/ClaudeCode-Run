# Data Architect — qa-ui-test-automation

## Data Stores

This repository does not manage persistent application data. Test infrastructure touches:

| Store | Purpose | Access Pattern |
|---|---|---|
| Azure Key Vault | Runtime credential retrieval (test passwords, API tokens) | `azure-security-keyvault-secrets` SDK at test startup |
| MS SQL Server | Database validation assertions in some tests | `mssql-jdbc` JDBC driver |
| Local filesystem | Screenshots, ExtentReports HTML, test data files (Excel) | Written during test execution |
| GitHub Actions artefacts | Test execution reports uploaded post-run | Ephemeral (GitHub default retention) |

## Schema / Test Data Structure

Test data is managed via:
- **External configuration files** (HOCON via `com.typesafe:config:1.4.3`) — environment-specific base URLs, credentials (sourced from Azure Key Vault)
- **Excel files** (Apache POI) — `poi:5.5.1`, `poi-ooxml:5.4.0` — likely used for data-driven tests
- **JSON data** in feature step payloads

No test data schema definitions are visible in the source explored; specific data files were not read.

## Sensitive Data

| Data Class | Source | Risk |
|---|---|---|
| Login credentials (usernames, passwords) | Retrieved from Azure Key Vault at runtime | Correctly managed — not committed to VCS |
| API tokens / bearer tokens | Retrieved from Azure Key Vault | Correctly managed |
| Test card numbers / account numbers | Feature file step parameters or data files | Must be synthetic — must not be real PANs |
| PIN values in `SetPin.feature` | Feature file step parameters | Must be synthetic |
| CVV status in `GetCvvStatus.feature` | Feature file interactions | CVV must never be stored or logged |
| MS SQL Server connection strings | From Azure Key Vault or HOCON config | Must be environment-specific secrets |
| Screenshots | Captured on failure to `screenshots/` directory | May capture sensitive UI state |

## Encryption

| Layer | Mechanism |
|---|---|
| Credential storage | Azure Key Vault (FIPS 140-2, TLS 1.2+) |
| Transit to Azure Key Vault | TLS via `azure-identity` (`DefaultAzureCredential` or service principal auth) |
| Test traffic to applications | HTTPS (TLS) — depends on application endpoints |
| Local screenshot files | Unencrypted on CI runner filesystem (ephemeral) |

## Data Flow

```
CI Workflow trigger
  --> AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, AZURE_VAULT_URL (GitHub Secrets)
      --> azure-security-keyvault-secrets SDK
          --> Azure Key Vault retrieves test credentials
              --> Credentials injected into test configuration (HOCON)
                  --> Playwright/Cucumber tests execute against target application
                      --> Screenshots captured on failure
                      --> ExtentReports HTML generated
                          --> Uploaded as GitHub Actions artefact
                          --> (Optional) Emailed to @onbe.com addresses
```

## Data Quality / Retention

| Concern | Detail |
|---|---|
| Test isolation | No explicit test data reset visible; tests may share mutable state in test environments |
| Screenshot retention | Screenshots uploaded as GitHub artefacts; may capture PII from UI |
| Report retention | HTML test reports retained for GitHub artefact lifetime (default 90 days) |
| DB assertions via JDBC | Direct SQL queries in tests may expose schema details in test code |
| Excel test data files | `poi-ooxml` dependency suggests Excel-driven tests; files not committed or not visible |

## Compliance Gaps

| Gap | Standard | Impact |
|---|---|---|
| Screenshots may capture sensitive UI data (card numbers, balances, PINs) | PCI DSS Req 3.3 | Screenshots stored in CI artefacts may contain CHD; retention and access control required |
| MS SQL Server direct access in tests bypasses application-layer controls | PCI DSS Req 7 | DB-level queries may access data the application would restrict |
| No explicit synthetic/masked test data policy documented | PCI DSS Req 3 | Features testing `SetPin`, `GetBalance`, `GetCvvStatus` must use synthetic data only |
| Azure Key Vault `AZURE_CLIENT_SECRET` in GitHub Secrets | PCI DSS Req 8.3 | Correct practice — but secret rotation schedule not visible in this repo |
