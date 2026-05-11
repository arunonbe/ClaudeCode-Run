# Business Analyst View — DS_automated-testing

## Business Purpose
This repository is the Data Platform quality-assurance automation suite. It provides automated regression and integration test coverage for multiple Onbe-era data platform systems: the Data Management Tool (DMT) REST API, the ClientZone web portal, the OnePlatform cardholder portal, and legacy Ecount prepaid-card account management services. Tests validate that core business functions — cardholder creation, account loading, payment selection, configuration management, and database integrity — work correctly across environments.

## Capabilities
| # | Capability | System Under Test |
|---|-----------|-------------------|
| 1 | DMT API tests (config, system, user endpoints) | DMT REST API (Python Flask, localhost:5000) |
| 2 | DMT UI login tests | DMT web application |
| 3 | ClientZone UI tests (login, cardholder admin, dashboard, files, instant issue, new cardholder, PayQuickly, reports) | ClientZone portal |
| 4 | OnePlatform login and payment registration tests | OnePlatform cardholder portal |
| 5 | Legacy Ecount SOAP account creation and loading | Legacy prepaid SOAP WS |
| 6 | SQL Server database assertion tests | SQL Server (ODS / sandbox schemas) |
| 7 | MongoDB collection management and user setup/teardown | MongoDB (dmt-web database) |

## Key Business Entities Tested
- **Cardholder** — first name, last name, address, email, phone, date of birth, card access level
- **System Configuration** — key-value config entities (e.g., "Vendor Remittance Email", "Board Approval", "Cost Center Mapping")
- **User** — automation test user (`AutomationTest@onbe.com`)
- **Account / Program** — program ID (e.g., `04010706`), promotion ID, load amount
- **Invoice** — payload in `Invoices.json`; linked to system config

## Business Rules Validated
1. DMT API returns HTTP 200 with correct JSON body structure for config/system/user endpoints.
2. ClientZone login requires valid credentials; session management via cookies and CSRF token.
3. New cardholder creation validates address, phone, and profile fields.
4. Legacy account creation requires program ID, promotion ID, and transaction ID; load amount 1–N.
5. SQL Server stored procedure (`sp_InsertRecord_QAAutomationTest`) and SQL Agent job (`QA_Test_Job`) must execute successfully.

## Process Flows
```
CI/Manual Trigger
  → Maven Surefire → TestNG suite (testng.xml)
      ├── UI Tests: OPPaymentLoginTest (Selenium WebDriver)
      └── DB Tests: LegacyDBTest (Ecount SOAP → account create/load)

Separate suites (DMTTestSuite.xml, DMTAPITest.xml):
  → DMT API Tests: Prerequisites.Login() → ConfigAPITest / SystemAPITest / UserAPITest
  → DMT UI Tests: DMTLoginTest (Selenium)
```

## Compliance Relevance
- Test credentials (`AutomationTest@onbe.com`) are hardcoded in source; not rotated via secret management — GLBA / PCI DSS Req 8 risk.
- SOAP payload in legacy test includes date_of_birth and email fields (PII under GLBA, CCPA).
- MongoDB test teardown (`DeleteCollection`) deletes data; must not run against production.

## Risks
- Hardcoded credentials and DB connection strings in source code are a security risk.
- Tests reference legacy Wirecard/Ecount infrastructure hostnames; may break post-migration.
- No evidence of test environment isolation; tests could be accidentally run against production data.
