# Business Analyst View — jobservice_common_LIB

## Repository Identity

- **Artifact**: `com.ecount.service.jobservice:job-common` v4.0.4 (referenced from `jobservice_SVC` `pom.xml` line 58 as `<job-common.version>4.0.4</job-common.version>`)
- **Repository name**: `jobservice_common_LIB`
- **GitHub URL**: `https://github.com/OnbeEast/jobservice_common_LIB` (from `jobservice_SVC/README.md`)
- **Purpose**: Shared data model and interface library for all consumers of the Job Service ecosystem

## Background — Why This Library Exists

As documented in `jobservice_SVC/README.md`, this library was split out from the main `jobservice_SVC` repository to break a **circular dependency**:
- `workflow-service` (workflowagent-svc) depended on `job-common` (for job status types)
- `jobservice_SVC` (jobmanager-svc and jobmanager-war) depended on `workflow-common` and `workflow-xmlrpc`

This circular dependency was resolved by extracting the shared domain types and interfaces into this standalone library, which both the workflow service and the job service can depend on without creating a cycle.

## Business Purpose

This library provides the **canonical shared vocabulary** for the Onbe batch processing platform. Every service that submits, monitors, processes, or reports on batch jobs uses these types. The library defines:

1. **What a job is** — the `Job` value object and all its associated domain types
2. **What a job can do** — the `IJobManager`, `IJobAgent`, `IJobFileManager`, `IJobProfileManager` service interfaces
3. **What can go wrong** — the `JobAgentServiceException`, `JobManagerServiceException` hierarchy
4. **What state a job is in** — the `JobProcessStatus`, `JobRequestStatus`, `JobBatchProcessStatus`, `RunJobStatus`, `JobActionStatus` enumerations

## Key Business Concepts Encoded in This Library

### Job Lifecycle States

**`JobProcessStatus`** — Internal execution state of a job's actions:
- Maps to the processing pipeline within a running job

**`JobRequestStatus`** — Status of a job's request records:
- Tracks individual record-level processing state within a batch

**`JobBatchProcessStatus`** / `JobBatchProcessStatusId`** — Batch-level status codes:
- Used by the batch processing framework to track multi-record processing progress

**`RunJobStatus`** — Status codes for job execution invocations

**`JobActionStatus`** — Status of individual action records within a job (e.g., single card issuance within a batch)

### ETL Operations Taxonomy (`ETLOperations.java`)

The `ETLOperations` class defines the canonical names for all Extract-Transform-Load operations performed on job files:

| Constant | Business Meaning |
|---|---|
| `CREATE_JOB_REPLY_FILE` | Generate the client-facing reply file confirming processing |
| `CREATE_JOB_SERVICE_ERROR_REPORT` | Generate error report file for client |
| `CREATE_JOB_EXCEPTION_FILE` | Generate exception file for records that could not be processed |
| `JOB_VALIDATE_FILE_STRUCTURE` | Validate the structural format of the uploaded client file |
| `JOB_IMPORT_FILE` | Import/parse the client file into the job database |
| `JOB_AWARDS_SPIN_PAYMENTS` | Process randomized spin/prize payment distributions |
| `CREATE_JOB_SERVICE_XML_ERROR_REPORT` | XML format error report (introduced in 2013 R3A) |

These constants are used as keys when configuring ETL agent packages and when tracking which ETL operation a file is currently undergoing.

### Authorization Workflow — `BankerAuthorizeJob.java`

The `BankerAuthorizeJob` class encodes the business rule that certain high-value jobs require a dual-authorization step involving the "Banker" role (a treasury/finance approver). This reflects the segregation of duties control required for disbursement batches above a configured threshold — a direct NACHA and internal controls requirement.

### `AutoAuthorizeStatus.java`

Encodes the auto-authorization capability — when a job meets pre-configured criteria (amount within limits, program is approved for auto-auth), the system can authorize the job without human intervention. This drives straight-through processing (STP) for routine disbursement batches.

### Configuration Constants (`ConfigurationConstants.java`)

Holds system-wide configuration keys used across all job service consumers. These control behavior like maximum retry attempts, sleep intervals, and batch processing thresholds.

### Value Objects

The `com.ecount.job.value` package provides the full domain object model:

| Class | Business Meaning |
|---|---|
| `Job` | A single submitted batch job — the primary unit of work |
| `JobAction` | A single action record within a job (e.g., one card issuance) |
| `JobActionRecord` | Detailed record of an individual action |
| `JobActionAmountSummary` | Financial totals aggregated across all actions in a job |
| `JobActionSummary` | Count/status summary of actions |
| `JobBatch` | A batch grouping of multiple job actions |
| `JobBatchInfo` | Metadata about a batch |
| `JobBatchDetailRecord` | Individual record within a batch |
| `JobBatchSummaryRecord` | Summary row for a batch |
| `JobExecutionParameters` | Parameters passed when running a job |
| `JobFee` | Fee record associated with a job |
| `JobId` | Typed job identifier wrapper |
| `JobOrder` | An order record associated with a job |
| `JobOrderActual` | Actual quantities from order execution |
| `JobProcess` | A processing step within the job execution pipeline |
| `JobProcessingContext` | Runtime context for job processing |
| `JobRequest` | A client's original job submission request |
| `JobRequestRecord` | Individual record from the request |
| `JobStatistics` | Aggregated counts (success, failed, skipped) for a job |
| `JobSummaryRecord` | High-level job summary for UI display |
| `Member` | Value object representing a cardholder/participant |
| `Partner` | Value object for a client partner |
| `Affiliate` | Value object for a client affiliate |
| `SpinDistributionRecord` | Prize/spin payment distribution record |
| `ValidationResult` / `ContentValidationResult` | Results of file validation |
| `StructureValidationResult` | Results of file structure validation |
| `ECountFile` | Reference to an uploaded client file |
| `AutofileWorkflowResult` | Result of an automated file processing workflow step |
| `ProgramPromotion` / `JobPromotion` | Promotion and marketing campaign data |
| `CreateJobServiceErrorReport` | Parameters for error report generation |

## Business Significance

This library is the **dependency that defines how the entire platform talks about batch work**. Any change to an interface here requires coordinated updates across:
- `jobservice_SVC` (job execution)
- `job-scheduler_SVC` (job scheduling)
- `autofile_SVC` (automated file workflow)
- `workflow-service` (workflow orchestration)
- All client integration libraries (`jobserviceintegration_LIB`, `jobservice-integration_LIB`)
- All front-end applications (`clientzone_WAPP`, `Banker API`)

This makes it a **high-impact, high-coordination** library where versioning discipline is critical to platform stability.
