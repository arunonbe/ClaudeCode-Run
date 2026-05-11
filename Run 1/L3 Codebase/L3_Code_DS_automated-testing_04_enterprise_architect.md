# Enterprise Architect View — DS_automated-testing

## Platform Generation
**Cross-generation test harness.** Tests cover:
- **Gen-1 legacy** systems: Ecount/Wirecard SOAP web services, legacy SQL Server `sandbox` DB
- **Gen-2 transitional** systems: DMT (Data Management Tool) REST API (Python Flask), ClientZone portal
- **Gen-2/3 boundary**: OnePlatform cardholder portal

## Domain Placement
- **Domain:** Data Platform — Quality Assurance
- **Subdomain:** Integration and regression testing across the CCP/prepaid cardholder data ecosystem
- **Consumers:** QA engineers, data platform team, CI/CD pipeline (aspirational)

## Role in the Ecosystem
Acts as a cross-cutting test harness for the Data Platform domain. It does not produce or transform data but validates that the data systems behave correctly. Key systems under test are:

```
DS_automated-testing
  ├── tests → DMT API (Data Management Tool)
  ├── tests → ClientZone Portal
  ├── tests → OnePlatform
  ├── tests → Legacy Ecount SOAP (AccountManagementApiWebServices)
  └── tests → SQL Server (sandbox) + MongoDB (dmt-web)
```

## Key Dependencies
| System | Protocol | Status |
|--------|----------|--------|
| DMT REST API | HTTP/JSON | Active; localhost suggests dev/QA only |
| Wirecard SOAP endpoint | SOAP/HTTPS | Legacy; `wirecard.com` domain — may be decommissioned post-Onbe branding |
| MongoDB `dmt-web` | MongoDB wire protocol | Active in DMT environment |
| SQL Server `sandbox` | JDBC | QA-only server |
| ClientZone | Selenium / HTTP | Active portal |
| OnePlatform | Selenium / HTTP | Active portal |

## Architectural Patterns
- **Page Object Model (POM)** — UI test pages abstracted into page objects under `com.qa.apps.page.object.*`
- **API client abstraction** — `API.java` base class, extended by `ConfigAPI`, `SystemAPI`, `UserAPI`
- **Credential object pattern** — `Credentials.java` wraps encrypted password (AES via `Encrypt`/`Decrypt`); however, plaintext passwords also present in `Prerequisites.java`

## Current Status
Active but partially outdated:
- Wirecard-branded SOAP endpoint URLs suggest pre-rebrand artefacts.
- `LegacyDBTest` test methods are mostly commented out.
- `testng.xml` only activates `OPPaymentLoginTest` and `LegacyDBTest` by default.

## Blockers / Concerns
1. Wirecard-branded endpoint URLs (`webservice-qa.wirecard.com`, `sftp-qa.nam.wirecard.com`) likely no longer valid post-Onbe migration.
2. No formal test data management strategy — tests rely on hardcoded test-account IDs and live QA databases.
3. Lack of CI/CD pipeline integration means test regressions may go undetected between manual runs.
