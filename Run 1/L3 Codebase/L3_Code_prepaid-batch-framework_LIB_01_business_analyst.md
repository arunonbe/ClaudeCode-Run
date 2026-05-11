# prepaid-batch-framework_LIB — Business Analyst View

## 1. Repository Purpose and Business Context

`prepaid-batch-framework_LIB` is the **shared batch processing engine** for Onbe's prepaid card platform. It provides a plugin-based, module-driven architecture that enables consistent execution, validation, logging, and integration for all batch jobs across the prepaid platform — including ACH settlement, fee collection, report synchronization, hierarchy submissions, and inquiry processing.

The framework was originally developed under the Citi/Northlane prepaid program (package namespace `com.citi.prepaid.batch`) and is now maintained as a core shared library under the Onbe/Northlane platform.

## 2. Business Capabilities Provided

| Capability | Sub-module | Description |
|---|---|---|
| Core batch execution engine | `prepaidbatch-impl` | Validates modules, selects processor type (Java/Spring Batch/BCP), executes batch logic |
| FTP-based file transfer | `prepaidbatch-library` | FTP library for receiving and transmitting settlement/report files |
| BCP data operations | `prepaidbatch-library` | SQL Server Bulk Copy Protocol (BCP) for high-volume data import/export |
| CMFA alternate inbound file processing | `CMFA-AltInbound` | Parses inbound files in Standard, Simple, or XML formats; sends email notifications |
| CMFA alternate outbound file generation | `CMFA-AltOutbound` | Generates outbound files for CMFA processing |
| CMFA inquiry processing | `CMFA-Inquiry` | Processes error, exception, job status, and reply inquiry types |
| CMFA report synchronization | `CMFAReportSync` | Synchronizes business and program-level inquiry reports |
| Hierarchy submission | `submithierarchy` | Submits hierarchy structures for batch processing |
| Submit inquiry | `submitinquiry` | Submits date-range-based inquiry jobs |

## 3. Module Types Supported

The framework supports three execution types for batch modules, defined in `PrepaidBatchConstants.ModuleTypes` (`PrepaidBatchConstants.java` lines 33–37):

| Module Type | Constant | Execution Strategy |
|---|---|---|
| Simple Java | `"SimpleJava"` | Direct reflective invocation of `IBatchModule.execute()` |
| Spring Batch | `"SpringBatch"` | Loads and executes Spring Batch job context |
| Data Import/Export | `"DataImport"` / `"DataExport"` | SQL Server BCP bulk copy operations |

Additionally, `FTP` is a module category (`ModuleCatagories.FTP`) that wraps the above types with FTP file transfer pre/post processing.

## 4. Batch Processing Business Flow

1. **Job submission**: An external scheduler (ActiveBatch, based on comments in `PrepaidBatchMain.java` line 91) invokes `PrepaidBatchMain.main()` with a module ID as the first argument.
2. **Module registry lookup**: The framework loads a module registry XML from `D:\c-base\config\service\prepaidBatch\ModuleRegistry.xml` to find the `BatchModule` configuration for the given module ID.
3. **Validation**: `ModuleValidationHelper` validates the module configuration.
4. **Preparation**: `ModulePreparationHelper` sets up the library context (FTP library, Profile service, Job service, Repository service, Security service).
5. **Execution**: The appropriate processor (`JavaModuleProcessorImpl`, `SpringBatchModuleProcessorImpl`, or `BcpDataOperationsModuleProcessorImpl`) invokes the actual batch logic.
6. **Exit code**: Returns `0` for success, `1` for failure — as required by ActiveBatch scheduler.

## 5. External Service Integrations

The framework integrates with several platform services via XML-RPC clients:

| Service | Client Bean | Purpose |
|---|---|---|
| Profile Service | `profileClient` / `ProfileServiceLibraryImpl` | Reads program/scope configuration |
| Repository Service | `repositoryServiceXMLRPCClient` / `RepositoryServiceLibraryImpl` | File repository operations |
| Job Service | `jobFileManagerServiceXMLRPCClient` / `JobServiceLibraryImpl` | Job status management |
| Security Service | `securityHierarchyServiceXMLRPCClient` / `SecurityServiceLibraryImpl` | Security hierarchy lookups |
| Director Service | `directorAddress` | Data source configuration discovery |

## 6. CMFA Module Business Context

The `CMFA-*` modules handle **Citi/Onbe MFA (Master File Activity)** batch file exchange:
- **AltInbound**: Receives bank activity files in three formats (Standard, Simple, XML); parses them using `IFileParser` implementations; sends email notifications on completion.
- **AltOutbound**: Produces outbound activity files.
- **Inquiry**: Processes bank inquiry responses — error records, exceptions, job status, and reply confirmations.
- **ReportSync**: Synchronizes program and business level inquiry data.

These CMFA flows represent the **ACH/settlement file exchange pathway** between Onbe's prepaid program and its banking partners, making them mission-critical for regulatory compliance (NACHA Rule compliance, Reg E obligations).

## 7. Business Risks

1. **Module registry stored locally**: The `ModuleRegistry.xml` is read from a hardcoded Windows path (`PrepaidBatchConstants.java` line 25). Any misconfiguration or file access failure silently prevents all batch jobs from running.
2. **Tests skipped in CI**: `.gitlab-ci.yml` passes `-Dmaven.test.skip=true` for all phases. There is zero automated test validation in the CI pipeline.
3. **Spring 2.5.6 framework**: This version (from 2008) has multiple known CVEs and is not supported. Batch jobs processing settlement files run on vulnerable runtime.
4. **CMFA email notifications**: `CMFAEmailHelper` sends operational alerts — if SMTP is misconfigured, settlement failure notifications would be silently suppressed.
