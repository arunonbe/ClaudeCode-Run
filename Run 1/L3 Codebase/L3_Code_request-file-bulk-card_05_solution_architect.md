# 05 Solution Architect — request-file-bulk-card

## Technical Architecture
Single-class JAR with a `main()` entry point (`RequestfileBulkCardGenClient`). Spring 2.0.4 `ClassPathXmlApplicationContext` loads two XML contexts (bulk-card-gen + inventory-management). No Spring Batch, no multi-threading. Sequential file-read → profile-lookup → file-build pipeline.

Key classes:
- `RequestfileBulkCardGenClient` — main class; arg parsing, context init, `processFile()` orchestration
- `DelimitedRecordParser` — CSV tokeniser (comma-delimited)
- `InstantIssueRequestFileBuilder` — builds `PaymentRequestFile`; updates order records in DB
- `RequestContext` / `Member` — cbase identity objects
- `AppProgramInstantIssueProfileClass` / `AppProgramUserManagementProfileClass` — profile retrieval via cbase API

## API Surface
No HTTP API. Command-line interface only:
```
java -jar requestfile-bulk-card-gen-impl-2013.2.1.jar <inputFile> <outputFile> <programID> <createDate> <memberId>
```
Exit codes: 0 = success; -1 = Spring context failure; -2 = wrong argument count; -3 = unhandled exception.

## Security Posture
- **Credentials in plain-text properties file** (`D:/c-base/config/jobsvc-ds.properties`): `jobsvc.password` is read as plain text — critical PCI DSS Req. 8 violation
- No authentication on the batch process; anyone with OS access and the JAR can run it
- Log4j properties at `D:/c-base/config/requestfile-bulk-card-gen/log4j.properties`; path hard-coded in source — if file absent, Spring context init fails
- Input CSV containing PII is read from an operator-supplied path; no access-control check on the input file
- XStream used only for error-case XML serialisation of args array; not a deserialisation attack surface in this usage
- Java 5 TLS: no TLS 1.2 support for JDBC connections; network sniffing risk on DB connections

## Technical Debt
| Item | Severity |
|---|---|
| Java 5 compile target (EOL > 15 years) | Critical |
| Spring 2.0.4 (EOL > 15 years) | Critical |
| Plain-text JDBC password in properties file | Critical |
| sqljdbc 1.2 + msbase/mssqlserver/msutil 2.2 (ancient) | High |
| Hard-coded `D:/c-base/` Windows paths | High |
| `e.printStackTrace()` instead of logging in `processFile()` | Medium |
| `RuntimeException` wrapping all file-read exceptions (no specific handling) | Medium |
| No input file size/row-count validation | Medium |
| `System.exit()` in main (prevents JVM reuse / testing) | Low |
| XStream 1.1 (deserialisation CVEs in later versions not applicable here but version is ancient) | Low |

## Gen-3 Migration
Recommended migration path:
1. Replace the batch CLI with a REST API endpoint (`POST /bulk-card-requests`) accepting a multipart CSV upload
2. Validate and parse CSV server-side; store in a database for tracking and idempotency
3. Retrieve programme profiles via a Gen-3 programme configuration API
4. Build the request file asynchronously and store in Azure Blob Storage
5. Expose status and download endpoints
6. Retire `D:/c-base/` file system dependency; move credentials to Azure Key Vault

## Code-Level Risks
- `processFile()` calls `builder.updRequestFileIdInInstantIssueOrder(null, request_file_id)` before reading the file; if `request_file_id` is null (env var not set), both the pre-call and the per-order update calls pass `null` — downstream DB behaviour depends on the stored procedure's null handling
- `AppProgramInstantIssueProfileClass.retrieve()` and `AppProgramUserManagementProfileClass.retrieve()` throw checked `ReturnStatus`; the catch block logs but does not halt processing — subsequent `request.setAccesslevel(Integer.parseInt(instantIssueProfile.getAccessLevel()))` will throw a `NullPointerException` if the profile retrieval failed
- `IOUtils.closeQuietly(inputFileReader)` in a `finally` block is correct; however the outer `try-catch` wrapping the Spring context init uses `System.exit(-1)` before the finally block for `fis` executes — the `IOUtils.closeQuietly(fis)` in the outer finally is safe but only if the catch block is reached, not if an unchecked exception escapes
