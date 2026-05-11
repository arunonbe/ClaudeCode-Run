# prepaid-batch-framework_LIB — Data Architect View

## 1. Data Architecture Overview

`prepaid-batch-framework_LIB` is a data-intensive framework. Its core data architecture involves three planes:
1. **File-based data exchange** (inbound/outbound settlement and activity files via FTP)
2. **Relational database operations** (SQL Server via BCP and JDBC)
3. **Service-mediated data access** (XML-RPC calls to Profile, Repository, Job, and Security services)

## 2. Database Configuration

Data sources are not hardcoded but are dynamically provisioned at runtime through the **Director Service** — a service registry/config provider. The `data-source-context.xml` (`prepaidbatch-impl`) declares:

| Bean ID | Database | Factory Method |
|---|---|---|
| `ecountCoreDS` | `ecountcore` (inferred from `FdrProfileClassExtract.DB_NAME`) | `DirectorConfiguredDBCPdatasourceCreator.getNewDatasource()` |
| `ecountCoreProcessDS` | `ecountcore_process` | Same factory |

The Director URI and Agent are injected as Spring bean references (`ref="directorURI"`, `ref="Agent"`, `ref="ecountcoreDatabase"`, etc.) from `propertyPlaceHolder.xml` and `ExternalServicesContext.xml`, which resolve to externally-managed property files.

## 3. File Data Exchange Formats

The `CMFA-AltInbound` module supports three file parser implementations:

| Parser Class | Format | File Source |
|---|---|---|
| `StandardFileParser` | Fixed-width / delimited standard bank file format | Banking partner inbound |
| `SimpleFileParser` | Simplified single-record-per-line format | Internal ops files |
| `XMLFileParser` | XML-structured activity files | Partner XML feeds |

File status tracking uses the `FileStatusTableColumns` enum and `TableColumnsVO` value object (`prepaidbatch-library`) — indicating a SQL-backed status table that tracks file processing state.

## 4. BCP (Bulk Copy Protocol) Data Flow

The `BCPMain`, `BCPImport`, and `BCPExport` classes implement SQL Server BCP operations for high-volume data movement:

| Component | Direction | Target Table/DB |
|---|---|---|
| `BCPImport` | File → SQL Server | `ecountCoreDS` and `ecountCoreProcessDS` |
| `BCPExport` | SQL Server → File | `ecountCoreDS` |

The `DataOperationConstants` in `PrepaidBatchConstants.java` reveals the settlement table: `ecountCoreProcessDS` table `ecs_encashment_settlement_file` (line 69), with `.STS`, `.DAT`, and `.TXT` file extensions used for status, data, and text files respectively. Batch size is 1,000 records (`BATCHSIZE=1000`, line 68).

## 5. Inquiry Data Structures

The `CMFA-Inquiry` module processes five inquiry context types (from `src/main/resources/`):

| Context File | Inquiry Type | Business Data Content |
|---|---|---|
| `CMFAInquiryContext.xml` | General CMFA inquiry | Program-level inquiry records |
| `ErrorInquiryContext.xml` | Error records | Failed transaction error data |
| `ExceptionInquiryContext.xml` | Exception records | Exceptional condition records |
| `JobStatusInquiryContext.xml` | Job status | Batch job completion status |
| `ReplyInquiryContext.xml` | Reply confirmations | Bank reply confirmation data |

The `CMFAReportSync` module processes `BusinessInquiryContext.xml` and `ProgramInquiryContext.xml`, handling financial report synchronization at both business entity and program levels.

## 6. Service Data Contracts

The framework uses XML-RPC to access several data services. Based on the library interfaces:

| Service Library | Key Data Objects |
|---|---|
| `ProfileServiceLibraryImpl` | `ClassRetrieve`, `ClassGet`, `ClassPut` — program configuration key-value pairs |
| `RepositoryServiceLibraryImpl` | File repository entries with FTP sync attributes (attribute IDs 105, 100 per `LibraryConstants`) |
| `JobServiceLibraryImpl` | Job file management records — job IDs, file associations |
| `SecurityServiceLibraryImpl` | Security hierarchy records — for agent/program authorization |

## 7. Module Input Value Objects

| Class | Fields | Purpose |
|---|---|---|
| `ModuleInputBase` | Base module input fields | Common input for all module types |
| `BCPInput` | BCP-specific input parameters | SQL Server BCP operation inputs |
| `BatchModule` | `moduleId`, `moduleType`, `moduleCategory`, spring context XML paths | Module registry descriptor |
| `ModuleValidationResult` | Validation status and messages | Module pre-validation results |

## 8. Data Retention and Compliance Notes

- **Settlement files**: Inbound files from banking partners (CMFA AltInbound) likely contain settlement amounts, transaction counts, and possibly account identifiers. These are NACHA-regulated data and must be retained per NACHA rules (typically 6 years).
- **Log output**: The `log4j.xml` configuration (referenced in `processBatch.bat` but not committed in the repo) determines how long batch processing logs are retained — critical for SOX and NACHA audit trails.
- **BCP data files**: The `.DAT` files created/consumed by BCP operations at `bcpInputFilePath`, `bcpFormatFilePath`, `bcpExportFilePath` (Spring bean references in `applicationContext.xml`) may contain cardholder data depending on the calling batch module. These file paths must be in PCI DSS-scoped, access-controlled directories.
- **FTP transfer data**: `FTPLibraryImpl` transfers files to/from banking partners. File content classification must be assessed per batch job — settlement files are in PCI DSS scope.
