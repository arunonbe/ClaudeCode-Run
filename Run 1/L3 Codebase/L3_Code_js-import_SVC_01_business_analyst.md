# Business Analyst View — js-import_SVC

## Executive Summary

`js-import_SVC` (artifact ID `jsimport`, WAR final name `jsvalidator`) is a legacy Java EE batch-import service that processes structured fixed-width import files — referred to internally as "JS files" (Job Service files) — submitted by enterprise clients. Each file encodes one or more cardholder lifecycle operations: account creation, fund loading, ACH/check withdrawal, payment management, card issuance, and user management. The service parses, validates, and persists these instructions into the `jobsvc` SQL Server database for downstream fulfilment by the Job Service engine.

## Business Purpose

The JS Import Service underpins Onbe's client-facing B2C disbursement onboarding workflow. A corporate client (e.g., a health insurer, auto-finance company, or rebate program) generates a JS-format flat file containing thousands of cardholder records and submits it via SFTP or a web endpoint (`/jsvalidator`). The service validates the file structure, converts the records into relational DAO inserts, and then signals the Job Service (`jobservice_SVC`) to begin asynchronous processing.

Key business capabilities enabled by this service:

| Capability | Record Class | Business Use Case |
|---|---|---|
| Create Account | `CreateAccountsRequest` (record type 7) | New prepaid cardholder enrollment |
| Create Extended Account | `CreateExtendedAccountRequest` | International / enhanced-profile enrollment |
| Add Funds | `AddFundsRequest` | Load disbursement funds onto a cardholder account |
| Add Funds Certificate | `AddFundsCertRequest` / `AddFundsCertMemoRequest` | Branded-currency / e-certificate loading |
| Spin Payment | `SpinPaymentRequest` | Conversion of a card-based balance to another rail |
| Stop Payment | `StopPaymentRequest` | Halt a pending payment |
| Withdraw (ACH / Check) | `WithdrawRequest` | Pull funds off the account to bank or check |
| Create Certificate | `CreateCertificateRequest` | Issue a branded-currency instrument |
| Issue Card | `JobActionIssueCardDAO` | Associate a physical or virtual card |
| Create / Update Web User | `CreateWebUserRequest` / `UpdateWebUserRequest` | Cardholder portal access provisioning |
| Set Location Code | `SetLocationCodeRequest` | Assign redemption geography restrictions |
| Set Inventory Location Attributes | `SetInvLocationAttributesRequest` | Inventory placement for card stock |
| Email Notification | `EmailNotificationRequest` | Trigger transactional email upon account creation |

## Actors and Stakeholders

- **Enterprise Clients** — submit JS import files (healthcare, insurance, gig, auto-finance).
- **Operations / File Processing Team** — monitors import job status through the JSValidator web UI (`index.jsp`).
- **Job Service Engine** — consumes the records persisted by this service and executes the actual card and payment actions.
- **Database Administrators** — manage `jobsvc` SQL Server schema accessed via JNDI data source `java:comp/env/jdbc/JobSvcDataSource`.

## Data Processed

The `CreateAccountsRequest` record (as defined in `CreateAccountsRequest.java`, lines 20–41) accepts the following cardholder PII fields inline:

- `FIRST_NAME` (25 chars), `MIDDLE_NAME` (25), `LAST_NAME` (25), `SUFFIX_NAME` (25)
- `HOMEEMAIL` (50 chars)
- `ADDRESS_1` (26), `ADDRESS_2` (26), `CITY` (18), `STATE` (2), `POSTAL` (10), `COUNTRY` (2)
- `HOMEPHONE` (16), `WORKPHONE` (16), `CELLPHONE` (16)
- `PASS_THROUGH` (32) — client-defined reference field

The `CreateAccountsSecureInfoAddenda` class holds SSN and other Sensitive Authentication Data. The `CreateExtendedAccountRequest` holds additional KYC fields for international programs.

Financial fields are present in `AddFundsRequest` (amount, program ID, promotion ID) and `WithdrawRequest` (ACH routing/account data or check details).

## File Format and Processing Model

JS files use a hierarchical fixed-width record structure. The `RequestFileParser` (`RequestFileParser.java`) implements a deterministic state machine with approximately 70 parser rules. The file structure is:

```
FileHeader (state 0)
  BatchHeader (state 10)
    Request (state 11)
      [Action Record e.g. CreateAccountsRequest type 7] (state 12+)
        [Optional Addenda records]
    Request...
  BatchFooter
FileFooter
```

The lexer (`JobSvcParserLineLexer`) reads lines, the parser delegates to listeners (`ParserListener` interface), and DAO managers (`InsertRecordsDAOManager`) persist each record type to the appropriate `jobsvc` table.

## Compliance and Business Risk

- The service processes PII (names, addresses, phone numbers, email) and potentially SSN (in `CreateAccountsSecureInfoAddenda`) — placing it squarely within PCI DSS scope as a CDE-adjacent component and under GLBA/CCPA obligations for individual data subjects.
- File-based ingestion model lacks TLS-at-rest enforcement within the service itself; it relies on the upstream SFTP layer.
- There is no field-level encryption within the service; all PII is written to `jobsvc` database in plaintext columns.
- The "forced run mode" feature (`ForcedRunMode.java`, `UpdateJobFileForcedRunModeDAO`) allows overriding the normal batch/realtime processing path — this should be access-controlled.

## Integration Dependencies

- **Upstream**: Client SFTP / direct HTTP POST to `JobValidatorServlet`
- **Downstream**: `jobsvc` SQL Server database → `jobservice_SVC` picks up and processes records
- **Supporting**: Redis cache (`RedisCacheUrl.java`) for environment-specific configuration; Spring XML application context (`jobsvc_import.xml`) loaded at startup from `D:/c-base/config/service/jobservice/JSImporter/service.properties`

## Business Continuity

The service exposes a `DBConnectionTestDAO` bean for health-check purposes. Failure modes include: malformed file format (throws `ParsingException`), DB connectivity loss (JNDI pool exhaustion), and Redis cache unavailability (affects environment-specific char-type validation). There is no visible retry or dead-letter logic within this service — failed files presumably require manual resubmission or intervention by the Operations team.
