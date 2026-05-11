# prepaid-batch-framework_LIB — Solution Architect View

## 1. Solution Architecture

The framework implements a three-tier solution architecture:

```
[Entry Point] PrepaidBatchMain.main(args)
      |
      v
[Orchestration] BatchProcessorImpl
      |
      |-- ModuleValidationHelper (input validation)
      |-- ModulePluginHelper (plugin classpath management)
      |-- ModulePreparationHelper (library wiring)
      |
      v
[Module Routing] ModuleProcessorContext
      |
      |-- JavaModuleProcessorImpl
      |-- SpringBatchModuleProcessorImpl
      |-- BcpDataOperationsModuleProcessorImpl
      |
      v
[Business Module] (external plugin, loaded from classpath)
      IBatchModule.execute() or IBatchFTPModule.execute()
```

## 2. Core Framework Components

### 2.1 BatchProcessorImpl (`prepaidbatch-impl`)
Central orchestrator. Responsibilities:
1. Validate `BatchModule` configuration via `ModuleValidationHelper`
2. Prepare library context (FTP, Profile, Repository, Job, Security) via `ModulePreparationHelper`
3. Select and invoke the appropriate module processor via `ModuleProcessorContext`
4. Return exit status to `PrepaidBatchMain`

### 2.2 Module Plugin Loading
`ModulePluginHelper` loads business module plugins from the classpath. The `BatchModule` value object (`prepaidbatch-common`) carries:
- `moduleId`: Spring bean name in the module registry XML
- `moduleType`: `SimpleJava`, `SpringBatch`, `DataImport`, or `DataExport`
- `moduleCategory`: `FTP` or empty
- Context XML paths for the module's Spring configuration

### 2.3 FTP Library Integration (`prepaidbatch-library`)
`FTPLibraryImpl` implements `IBatchFTPLibrary`, providing:
- Pre-processing: FTP download of inbound files from partner repositories
- Post-processing: FTP upload of processed/output files
- Repository service integration for file status tracking (attribute IDs 100 = SFL display, 105 = FTP sync per `LibraryConstants`)

### 2.4 BCP Integration
`BcpDataOperationsModuleProcessorImpl` wraps `BCPMain`, which delegates to `BCPImport` and `BCPExport`:
- `BCPImport`: Uses SQL Server `bcp` utility (invoked via process exec or JDBC bulk copy) against `ecountCoreDS` and `ecountCoreProcessDS`
- `BCPExport`: Extracts data from `ecountCoreDS` to `.DAT` files

The `bcpInputFilePath`, `bcpFormatFilePath`, and `bcpExportFilePath` are injected Spring bean references (not visible in committed config; managed externally).

## 3. CMFA Module Solution Design

Each CMFA sub-module follows an identical three-component pattern:

| Component | Pattern | Example |
|---|---|---|
| `CMFA*Configuration` | Spring `@Configuration` / XML | `CMFAAltInboundConfiguration.java` |
| `CMFA*Helper` | Business logic helper | `CMFAAltInboundHelper.java` |
| `CMFA*Input` | Value object for inputs | `CMFAAltInboundInput.java` |

### CMFA AltInbound File Parsing Solution
The `AbstractFileParser` class is extended by three concrete parsers, selected by the `CMFA-AltInbound` module:

```
IFileParser
    |
    AbstractFileParser
    |-- SimpleFileParser    (simple single-field-per-line)
    |-- StandardFileParser  (multi-field fixed/delimited)
    |-- XMLFileParser       (XML structure)
```

`CMFAEmailHelper` and `CMFAEmailNotificationTemplate` provide email alert generation when inbound file processing completes or fails. The notification delegate interface `ICMFANotificationServiceDelegate` is implemented by `CMFANotificationServiceDelegateImpl`.

## 4. Service Library Solution Pattern

All external service integrations follow a consistent interface/implementation pattern:

| Interface | Implementation | Injected Client |
|---|---|---|
| `ProfileServiceLibrary` | `ProfileServiceLibraryImpl` | `profileXMLRPCClient` + `agent` |
| `RepositoryServiceLibrary` | `RepositoryServiceLibraryImpl` | `repositoryServiceXMLRPCClient` |
| `JobServiceLibrary` | `JobServiceLibraryImpl` | `jobFileManagerServiceXMLRPCClient` |
| `SecurityServiceLibrary` | `SecurityServiceLibraryImpl` | `securityHierarchyServiceXMLRPCClient` + `agent` |

This abstraction layer is well-designed — it would allow swapping XML-RPC clients for REST clients without changing module business logic.

## 5. Dependency Injection and Spring Context Loading

The framework uses two separate Spring contexts:
1. **Module registry context** (`FileSystemXmlApplicationContext`): Loaded from `D:\c-base\config\service\prepaidBatch\ModuleRegistry.xml` — contains `BatchModule` bean definitions for each registered batch job.
2. **Framework context** (`ClassPathXmlApplicationContext`): Loaded from classpath `applicationContext.xml` — contains all infrastructure beans (processors, libraries, data sources).

This dual-context approach allows module definitions to be updated without rebuilding the framework JAR, which is architecturally sound for a library used by many modules.

## 6. Error Handling Solution

Error handling is defensive with explicit exit codes:
- `PrepaidBatchException` carries a structured `code` and `message`, logged before exit
- All other `Exception` types result in exit code `1` with stack trace logging
- ActiveBatch reads the exit code and handles retry/alert logic externally

**Gap**: No retry logic is built into the framework itself. Transient failures (FTP timeout, DB unavailable) immediately fail the batch run. This is appropriate when the scheduler handles retries, but means the scheduler must be correctly configured for each module.

## 7. Recommended Solution Modernization (Forward Architecture)

```yaml
# Target Architecture (per prepaid-parent_PARENT standards)
runtime: Java 21 (Spring Boot 3.4.5)
batch-engine: Spring Batch 5.x
file-transfer: Apache MINA SSHD (SFTP) - already in prepaid-parent_PARENT
db-access: Spring JDBC + HikariCP (Spring Boot autoconfigured)
service-calls: OpenFeign REST client (in prepaid-parent_PARENT)
config: Spring Boot application.yml + Azure App Configuration
deployment: Docker + Kubernetes CronJob
ci: GitHub Actions (align with deployment.yml pattern from profile_SVC)
```

The service library abstraction layer (`ProfileServiceLibrary`, etc.) is well-positioned for this migration — replacing XML-RPC clients with Feign clients behind the same interfaces requires only implementation changes, not interface or module changes.
