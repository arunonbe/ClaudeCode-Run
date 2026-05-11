# 01 Business Analyst — request-file-bulk-card

## Business Purpose
Batch process that generates a bulk instant-issue card request file from a CSV input file. Operators supply a list of cardholder location requests and the process builds a structured payment request file consumed by the card inventory management system, enabling mass instant-issue card orders for programme operators.

## Capabilities
- Parses a comma-delimited input file containing location-level card requests (quantity, cardholder name, address, country, remark, location code)
- Resolves the programme's instant-issue profile and user-management profile from the backend (access level, plastic-only flag)
- Builds a `PaymentRequestFile` via `InstantIssueRequestFileBuilder`
- Writes the output request file to a specified path
- Updates instant-issue order records with the `request_file_id` (read from environment variable) before and after file construction
- Reports pass/fail based on `RequestFileStatus`

## Entities
- **InstantIssueLocationRequest**: per-row request — card count, name, address (street, city, state, postal, country), remark, location code, access level, plastic-only flag
- **PaymentRequestFile**: the constructed output artefact linking all location requests under a programme
- **Member**: identity of the operator initiating the bulk run
- **AppProgramInstantIssueProfile**: programme configuration for instant issuance (access level, etc.)
- **AppProgramUserManagementProfile**: programme user management settings (plastic-only flag)

## Business Rules
- Exactly 5 CLI arguments required: inputFileName, outputFileName, programID, createDate, memberId; any deviation exits with code -2
- `request_file_id` is read from the OS environment variable; if absent, the order-update calls pass `null`
- Country defaults to "US" if not supplied or empty in the input file
- Access level is set from the programme's instant-issue profile
- Plastic-only flag is set from the programme's user-management profile
- Output file name is injected into the payment data builder; the file is written by `constructRequestFile()`
- Return code 0 or negative = success (status ≤ 0); positive = failure

## Flows
1. Operator invokes the JAR with 5 CLI args (input file path, output file path, program ID, create date, member ID)
2. Spring context loaded from two XML config files (bulk-card-gen + inventory management)
3. Programme profiles retrieved via cbase API
4. Input CSV parsed line by line into `InstantIssueLocationRequest` objects
5. `request_file_id` read from environment; `updRequestFileIdInInstantIssueOrder(null, request_file_id)` called first (marks as in-progress)
6. `PaymentRequestFile` built and written to the output path
7. Each order record updated with the actual `request_file_id`
8. Success/failure logged; process exits

## Compliance
- Cardholder name and address (PII) appear in the input CSV and are processed in-memory and written to the output request file
- Output file may be ingested by downstream card printing/fulfilment systems; PCI DSS requirement 3 (protect stored data) applies to the output file if it contains card-account data
- No PAN or financial account data observed in the input CSV schema — access level and plastic settings are programme-level, not account-level
- GLBA / CCPA: cardholder name and address are PII and must be handled with appropriate access controls on the file system

## Risks
- JDBC password for `jobsvc` stored in a plain-text properties file at `D:/c-base/config/jobsvc-ds.properties` — credential exposure risk (PCI DSS Req. 8)
- `System.exit(-1/−2/−3)` on any error; no structured error reporting or alerting
- Input file has no size or format validation beyond field-count checks; malformed records will throw a `RuntimeException` and abort the run mid-file
- Version 2013.2.1 from Subversion SCM (ecount.com internal); very old, no active maintenance
- Spring 2.0.4 and Java 5 compile target: > 15 years past EOL
