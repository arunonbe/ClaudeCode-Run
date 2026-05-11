# Data Architect View — DS_automated-testing

## Data Stores Accessed by Tests
| Store | Type | Connection Details | Usage |
|-------|------|--------------------|-------|
| MongoDB | NoSQL document store | `localhost:27020`, db `dmt-web`, collection `user` | DMT user creation, teardown, collection management |
| SQL Server | RDBMS | `//q-db03.nam.wirecard.sys\db03:2232`, db `sandbox` | Legacy DB test: stored proc, SQL Agent job, query |
| DMT REST API | HTTP JSON | `http://localhost:5000/` | Config / system / user CRUD |
| Legacy SOAP (Ecount) | SOAP/HTTP | `https://webservice-qa.wirecard.com:4005/accountmanagementapiws/services/AccountManagementApiWebServices` | Account creation and loading |

## Sensitive Data in Test Payloads
| Element | Source File | Classification |
|---------|------------|---------------|
| Automation user email (`AutomationTest@onbe.com`) | `Prerequisites.java` | PII |
| Automation user plaintext password | `Prerequisites.java` | Credential — HIGH RISK (hardcoded) |
| MongoDB credentials (`my-root-user` / `secret`) | `Prerequisites.java` | Credential — HIGH RISK (hardcoded) |
| SQL Server credentials (`TestAutomation` / `T3st@ut0m@t10n`) | `LegacyDBTest.java` (commented-out code) | Credential — present in source |
| Date of birth in SOAP payload | `LegacyDBTest.java` | PII — GLBA / CCPA |
| Email address in SOAP payload | `LegacyDBTest.java` | PII |
| Card Access Level | `LegacyDBTest.java` | Operational |
| Program ID (`04010706`) | `LegacyDBTest.java` | Operational reference |

**Note:** All credential values noted above are test/QA values present in source code. They should not represent production credentials. Verify with Security that these values have never been used in production. Rotate immediately if there is any doubt.

## Schema Awareness
### MongoDB (`dmt-web`)
- Collection `user` — documents have `email` field (used for lookup/delete)
- Additional collections created/deleted via `DeleteCollection()` in tests

### SQL Server (`sandbox`)
- Table `dbo.QAAutomationTest` — fields: `FirstName`, `LastName`, `Occupation`, `Salary`, `ID`
- Stored procedure `dbo.sp_InsertRecord_QAAutomationTest`
- SQL Agent Job `QA_Test_Job`

## Test Data Files
| File | Location | Content |
|------|----------|---------|
| `NewCardholder1.json` | `src/test/resources/` | New cardholder payload for ClientZone |
| `Create_System_Configuration_p2ptest.JSON` | `src/test/resources/DMT/API/` | DMT system config payload |
| `Create_System_p2ptestsetup.json` | `src/test/resources/DMT/API/` | DMT system setup payload |
| `Invoices.json` | `src/test/resources/DMT/API/` | Invoice data for API tests |

## Data Quality / Isolation Risks
- Tests modify and delete MongoDB collections; if run against a shared/production environment this is destructive.
- SQL Server tests are partially commented out but the connection string targets a named QA server.
- No data masking; test PII (DOB, email) matches typical real-user patterns.

## Compliance Gaps
1. **PCI DSS Req 6.3.2** — dependency versions not tracked via approved process (plain Maven without a vulnerability gate).
2. **PCI DSS Req 8.2** — hardcoded credentials in source violate shared-credential and password-management requirements.
3. **GLBA / CCPA** — PII (DOB, email) used in test payloads should use synthetic data only.
