# Business Analyst Analysis: repository_LIB

## Business Purpose
repository_LIB is a Gen-1 internal Java library providing a DAO/repository abstraction layer for two related concerns:

1. **File Repository Management** (`RepositoryManager`): Provides programmatic access to store, retrieve, list, and manage files that are associated with prepaid card programs and member accounts. Files include job files, request files, and reports.

2. **Report Management** (`ReportManager`): Provides read access to a catalog of reports associated with programs, including lookup by name, ID, and category.

The library is consumed by other internal services (e.g., repository-service_SVC, client zone web applications, order processor services) to perform file operations against the platform's file storage infrastructure and to surface report metadata to UI layers.

## Capabilities
1. Store a file associated with a member/program, with optional overwrite control and file type classification.
2. Retrieve a specific file by fileId, memberId, and programId.
3. List files for a member/program with date range or days-back filters, with pagination support.
4. Set/read file attributes on stored files.
5. Upload and store a request file (for batch processing workflows).
6. Process a job file (for batch/job scheduling integration).
7. Look up reports by name, by ID, or by report category.
8. File comparison/sorting via comparator utilities (by date, by name, ascending/descending).
9. FTP utility support for file transfer operations.

## Key Business Entities
| Entity | Description |
|---|---|
| ECountFileJournalTO | Transfer object representing a file journal entry (file metadata + content pointer) |
| ECountFileDefinitionTO | Transfer object describing a file's definition (name, type, program association) |
| ECountFileAttributeTO | Transfer object for file attributes (key-value metadata on a file) |
| ECountClientHostTO | Transfer object for client host information |
| FileExtensionVO | Value object for file extension metadata |
| Report | Entity: report definition (id, name, category linkage) |
| ReportCategory | Entity: report category classification |
| ProgramReport | Entity: maps a report to a program |

## Business Rules
- Files are always associated with a memberId and programId; file operations are scoped to these identifiers.
- Time period filters support three modes: `all-dates`, `last-30-days`, `selected-range-dates` (constants in `RepositoryManager` interface).
- Report lookup returns null (not an exception) if no matching record is found.
- File retrieval and storage operations declare `ReturnStatus` as a checked exception, enforcing explicit error handling by callers.
- File attribute setting is a separate operation from file storage.
- An `isMaker` flag is supported on upload operations, indicating maker-checker workflow integration.

## Business Flows
### File Store Flow
1. Caller assembles `ECountFileDefinitionTO` with file name, content, program/member context.
2. Calls `RepositoryManager.storeFile()` or `uploadAndStoreFile()`.
3. Library delegates to `RepositoryManagerImpl` which calls the repository service (XML-RPC based — see `repository-client` module).
4. Returns `ECountFile` with persisted file reference.

### Report Lookup Flow
1. Caller provides report name, ID, or category ID.
2. `ReportManagerImpl` queries the SQL Server database via Hibernate (`ReportDAO`, `ReportCategoryDAO`, `ProgramReportDAO`).
3. Returns entity objects for UI consumption.

## Compliance Relevance
- Files stored/retrieved may contain PII or financial data (batch files, request files, report data) depending on program context.
- File attribute framework can store metadata including potential sensitivity markers.
- No direct PAN handling visible in this library layer, but batch/request files it manages may contain card data.

## Risks (Business Perspective)
- **No authorisation checks** within the library: file access is controlled only by memberId/programId parameters passed by callers; if callers pass incorrect parameters, cross-program data access is possible.
- **Batch file content is opaque** to this library: the library does not inspect or validate file contents.
- **FTP utility** (`FTPUtil`) implies use of unencrypted file transfer in some paths.
