# Solution Architect View — jobservice_common_LIB

## Complete Class and Method Inventory

### Package `com.ecount.job.config`

| Class | Purpose |
|---|---|
| `AutoAuthorizeStatus` | Status codes/constants for the auto-authorization feature (straight-through processing) |
| `BankerAuthorizeJob` | Constants/logic for the dual-authorization step requiring Banker (treasury) approval |
| `ConfigurationConstants` | System-wide configuration property keys (retry attempts, sleep intervals, batch thresholds) |
| `ETLOperations` | ETL operation name constants: `CREATE_JOB_REPLY_FILE`, `CREATE_JOB_SERVICE_ERROR_REPORT`, `CREATE_JOB_EXCEPTION_FILE`, `JOB_VALIDATE_FILE_STRUCTURE`, `JOB_IMPORT_FILE`, `JOB_AWARDS_SPIN_PAYMENTS`, `CREATE_JOB_SERVICE_XML_ERROR_REPORT` |
| `JobActionStatus` | Status codes for individual action records within a job |
| `JobAgentExceptionConstants` | Error code constants for `JobAgentServiceException` |
| `JobBatchProcessStatus` | Status values for batch-level processing state |
| `JobBatchProcessStatusId` | Numeric ID constants for batch process status values |
| `JobManagerExceptionConstants` | Error code constants for `JobManagerServiceException` |
| `JobProcessStatus` | Status values for job execution process steps |
| `JobRequestStatus` | Status values for individual job request records |
| `JobServiceConstants` | Master constants class: service name, mode strings, key names, timeout defaults, file package types, FILE_STATUS_MAP, status IDs |
| `ProcessControlStatus` | Status codes for process control operations (STOP/START/PAUSE) |
| `RunJobStatus` | Status codes returned from job execution invocations |
| `StructureValidationErrorLevels` | Error severity levels for file structure validation (FATAL, WARNING, etc.) |

### Package `com.ecount.job.exception`

| Class | Purpose |
|---|---|
| `JobAgentServiceException` | Checked exception for Job Agent service failures; carries error code from `JobAgentExceptionConstants` |
| `JobManagerServiceException` | Checked exception for Job Manager service failures; carries error code from `JobManagerExceptionConstants` |

### Package `com.ecount.job.service`

| Interface | Purpose |
|---|---|
| `IJobAgent` | Contract for job agent: `runProcess(String execAgent, String memberId, String jobAgentName, boolean isBatch)` |
| `IJobFileManager` | Contract for file lifecycle: `loadJobFileChecker()`, `completeJobProcessing()`, `completeJobArchivalWithErrors()`, `createTextFileStatusReport()`, `createXMLFileStatusReport()`, plus autofile notification methods |
| `IJobManager` | Contract for all job state transitions and queries: `runJob()`, `endJob()`, `resetJob()`, `authorizeJob()`, `unAuthorizeJob()`, `denyJob()`, `cancelJob()`, `archiveJob()`, `archiveJobWithErrors()`, `markJobPendingFunds()`, `markJobPendingFinance()`, `markJobFailed()`, `markJobFailedContent()`, `adminCancelJob()`, `jobFeesCalcEstimate()`, `jobFeesCalcActual()`, `getPendingList()`, `getHistoryList()`, `getActiveList()`, `getJobSummary()`, `getJobProcessList()`, `getJobBatchDetails()`, `getJobActionDetails()`, `jobAccountMapSet()`, `jobAccountMapUpdate()`, `jobAccountMapGet()`, `jobAccountMapCleanup()`, `jobCompleteEvent()`, `jobCreateNotifications()`, `jobRandomizeSpinPayments()`, `jobAwardSpinPayments()`, `jobSummaryCreate()`, `jobInitializeStatistics()`, `jobValidateContent()`, `jobCreateJobOrders()`, `jobPostCompletedJobOrders()`, `jobUpdateOrderStatus()`, `reprocessJobFiles()`, `finalizeBatchedJobs()`, `jobGetJobsReferencedJobIds()`, `jobAssignRecordIds()`, `getJobBatchInfo()`, `jobGetJobPromotions()`, `jobGetJobActionAmountSummary()`, `jobGetJobStatus()`, `jobCreateSummary()`, `resetFullJob()` |
| `IJobProfileManager` | Contract for program profile CRUD: `createProfileClass()`, `deleteProfileClass()`, `retrieveProfileClass()`, `updateProfileClass()` |

### Package `com.ecount.job.value`

| Class | Key Fields / Notes |
|---|---|
| `Affiliate` | affiliateId, name |
| `AutofileWorkflowResult` | Workflow step result for autofile processing |
| `ContentValidationResult` | `is_valid` (boolean), `error_file` (ECountFile) |
| `CreateJobServiceErrorReport` | Parameters for error report ETL operation |
| `ECountFile` | file_id, file_name, physical file reference |
| `Job` | Primary job entity — all lifecycle fields |
| `JobAccountMapDetails` | Account mapping result: ecountId, ememberId, partnerUserId |
| `JobAccountMapGetInput` / `SetInput` / `UpdateInput` | Account map operation inputs |
| `JobAction` | action_id, action_code, status, amount, all key references |
| `JobActionAmountSummary` | action_code, total_amount, action_count |
| `JobActionRecord` | Detailed action record with all key fields |
| `JobActionSummary` | Summary counts by status |
| `JobBatch` | batch_id, records, summary |
| `JobBatchDetailRecord` | Individual record within a batch |
| `JobBatchInfo` | Batch metadata — program, promotion, count |
| `JobBatchSummaryRecord` | Aggregate batch data |
| `JobExecutionParameters` | execAgent, memberId, isBatch, agentPackage |
| `JobFee` | fee_type_id, amount, program_id |
| `JobId` | job_id (int wrapper) |
| `JobJobStatus` | job_id + status_id for bulk status query results |
| `JobLocationData` | Location code, card count data for card distribution |
| `JobOrder` | order_id, job_id, quantity, status |
| `JobOrderActual` | Actual processed quantities per order |
| `JobOrderActualWithOrigJobId` | Adds origJobId to JobOrderActual for split-job scenarios |
| `JobOrderWithOrigJobId` | Adds origJobId to JobOrder for split-job scenarios |
| `JobProcess` | Process step within a job: process_id, status, timestamps |
| `JobProcessingContext` | Runtime context: agent, member, configuration |
| `JobProfileManagerInput` | Profile manager operation parameters |
| `JobPromoId` | Promotion identifier wrapper |
| `JobPromotion` | Promotion details linked to a job |
| `JobReferencedIds` | Cross-job references (original job IDs for split/re-batch scenarios) |
| `JobRequest` | Client's original request data |
| `JobRequestRecord` | Individual record from the request file |
| `JobServiceProgramProfile` | Program-level ETL configuration profile |
| `JobStatistics` | actionFailed, actionSuccess, actionSkipped, actionTotal |
| `JobSummaryRecord` | High-level summary for UI list display |
| `Member` | member_id, partner_id — participant identity |
| `Partner` | partner_id, name — client partner |
| `ProfileActionCode` | Action code configuration for a program profile |
| `ProgramId` | program_id wrapper |
| `ProgramPromotion` | Program-level promotion configuration |
| `SpinDistributionRecord` | Prize distribution record: range, amount, count |
| `StructureValidationResult` | Structural validation errors with severity levels |
| `ValidationResult` | Generic validation result |

## Security Vulnerabilities and Technical Debt

### SV-1: `VIRTUAL_EXPRESS_URL` in `JobAction` — Log Exposure Risk (HIGH)
`JobServiceConstants.VIRTUAL_EXPRESS_URL = "virtual_express_url"` (line 67) is a key name used in action records. If virtual card delivery URLs contain embedded credentials or one-time tokens (common in virtual card delivery), and `JobAction` objects are logged by consumers (e.g., in debug logging of `JobManagerDataHandlerImpl`), these URLs would appear in log files. PCI DSS Requirement 3.4.1 prohibits storage of sensitive authentication data. **Priority: HIGH** — add a `@Sensitive` annotation or masking wrapper; audit all log statements that output `JobAction` objects.

### SV-2: Version Fragmentation Across Consumers (HIGH)
`job-order-synchronization_LIB` consumes version 2.0.13 while `jobservice_SVC` is on 4.0.4. Any breaking change between these versions means the synchronizer is operating with a different domain model than the main service. **Priority: HIGH** — conduct an urgent version audit; enforce a policy of same-version consumption.

### SV-3: `FILE_STATUS_MAP` as a Mutable Static Field (MEDIUM)
`JobServiceConstants.FILE_STATUS_MAP` is a `public static final Map<String, String>` but the map itself is mutable (a `HashMap`). Any consumer could call `.put()` or `.remove()` on it, modifying the client-facing status strings at runtime without any notification or logging. Source: `JobServiceConstants.java` lines 122–139. **Priority: MEDIUM** — replace with `Collections.unmodifiableMap()` or an `ImmutableMap`.

### SV-4: `MEMBER_ID_WITH_ZEROS` Hardcoded Identity (MEDIUM)
`JobServiceConstants.MEMBER_ID_WITH_ZEROS = "{00000000-0000-0000-0000-000000000000}"` (line 104) represents a system/default member identity. Using a hardcoded all-zeros UUID as a system identity can appear in audit logs as a legitimate member ID, making it difficult to distinguish system-initiated actions from user-initiated ones. This is an audit log integrity concern under PCI DSS Req 10. **Priority: MEDIUM** — use a named system account or a clearly distinct sentinel value.

### SV-5: Default Email and Phone in `BatchFileConstants` (LOW)
`BatchFileConstants.DEFAULT_EMAIL_ADDRESS = "none@ecount.com"` and `DEFAULT_PHONE_NUMBER = "555-555-5555"` (in the integration library). These are vestigial defaults from legacy client integration code. If these are ever used as fallback values in actual notifications, they would send disbursement notifications to a non-recipient. **Priority: LOW** — remove defaults; fail explicitly if no contact info is provided.

## Remediation Priority

1. **Immediate**: Audit `VIRTUAL_EXPRESS_URL` logging exposure; add masking in all log statements
2. **Short-term**: Align all consumers to `job-common:4.0.4`; deprecate 2.x line
3. **Short-term**: Make `FILE_STATUS_MAP` immutable
4. **Medium-term**: Replace int status code constants with proper enums throughout
5. **Long-term**: Migrate value objects to Java records (Java 16+); eliminate null-accepting constructors
