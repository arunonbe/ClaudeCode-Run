# autofile_SVC — Business Analyst View

## Business Purpose

autofile_SVC is a batch-file workflow orchestration service that sits within the "JobService suite" at Onbe. Its core function is to accept uploaded prepaid disbursement files (job files) and drive them through a multi-phase processing lifecycle: Loading → Finance/Authorization → Scheduling → Processing → Report Generation. It acts as the state-machine broker between the file repository, the funds-authorization service (Banker), the job-scheduling service, the job-execution service, and the workflow engine. The service was originally developed by OFSS (Oracle Financial Services) for the Wirecard/ecount platform and has been migrated to Onbe's Azure container infrastructure.

## Business Capabilities

1. **File lifecycle management** — tracks each uploaded file from initial ingest through completion across three phases (Loading, Processing Preparation, Processing Completion).
2. **Pause / Resume / Rollback** — operators can pause a running job, resume it at the exact step it paused, or rollback the workflow to a prior phase. Implemented in `AutofileServiceImpl.pauseJob`, `resumeJob`, and `rollbackJob`.
3. **Finance authorization** — integrates with the Banker service to authorize funds for each file. Supports automatic (via profile-service "Auto Authorization" flag) and manual authorization paths.
4. **FIFO job ordering per program** — `ProgramJobOrderHelper.authorizeOldestFirst` enforces upload-time ordering within a program to ensure first-uploaded files get funds authorized first.
5. **Insufficient-funds retry scheduling** — `InsufficientFundsRetryScheduler` runs on a configurable time-based schedule (default: 09:00, 13:00, 17:00 ET, weekdays) to re-attempt authorization for jobs blocked by insufficient funds.
6. **Status querying** — bulk retrieval of file and job status lists via stored procedures (`autofile_get_file_list_details`, `autofile_get_job_list_details`).
7. **Scheduler blackout-aware resume** — before resuming a paused processing-phase job, the service checks for blackout windows via `JobSchedulerServiceHelper.checkBlackout`.

## Business Entities

| Entity | Java Representation | DB Table / Source |
|---|---|---|
| Job/File | `JobInfo` (dto) | `autofile_job` table, `job_file` table |
| Workflow execution context | `WorkflowInputContext` (dto) | Runtime only |
| Workflow result | `WorkflowOutput` (dto) | Runtime only |
| Funds retry queue entry | `FundsRetryQueueEntry` (dto) | `dbo.autofile_funds_retry_queue` |
| Retry configuration | `RetryProperties` | Spring-injected properties |
| Workflow process definition | `WorkflowCache` (wraps `WorkProcessDefinition[]`) | Loaded via `WorkflowManager` on startup |

Key fields in `JobInfo`:
- `jobId`, `repositoryFileId` (the external file identifier)
- `jobStatusId` / `jobStatus` (integer + string pair, ~25 named statuses)
- `phaseId` (1=Loading, 2=ProcessingPreparation, 3=ProcessingCompletion)
- `workflowInstanceId`, `workflowStepName`
- `pauseStatus` (I=Initialized, E=Effective, T=Terminated)
- `programId`, `retryAttempts`, `volFlexFlag`

## Business Rules & Validations

1. **Input validation** — all workflow calls require non-null/non-empty: `EXEC_AGENT`, `CALLER_ID`, `STEP_NAME`, `FILE_ID`. Validated in `AutofileInputValidator` (both common and web layers). Missing any field sets `workflowInputContext.valid = false` and short-circuits processing.
2. **Pause rule** — pausing a job in Processing/Processing:Pending Resources/Processing:Initialization Failed triggers a stop on the underlying job-service job, not just a status flag. Logic in `AutofileServiceImpl.pauseJob` lines 96–110.
3. **Pause application** — `AbstractWorkflowStep.checkApplyPause` enforces that pause becomes "Effective" (E) only at phase-transitional or retriable steps (as enumerated in `AutoFileConstants.phaseTransitionalStatus` and `retriableStatusList`).
4. **FIFO authorization** — when a job enters `BankerAuthorizeJob`, `ProgramJobOrderHelper.authorizeOldestFirst` checks whether older Insufficient Funds jobs exist for the same program. If they do, those are authorized first (in upload-time order) before the current job is processed.
5. **Auto-authorization flag** — `ValidateAutoAuthorize` calls the profile service to retrieve "Auto Authorization" label for the program. Return code 0 = auto ON (proceed to `BankerAuthorizeJob`), return code 2 = auto OFF (route to manual approval). Constant values in `AutoFileConstants.AUTHORIZATION_AUTO_ON/OFF`.
6. **Banker OFF override** — when the "Banker" profile label is OFF, the service substitutes `forceAuthorizeUserID` (level-3 user) for the authorization call (`BankerServiceHelperImpl` lines 196–198).
7. **Test file funds limit** — `BankerAuthTestException` is treated as authorization failure (not insufficient funds), preventing test files over $501 from entering the insufficient-funds retry path (`AutoFileConstants.BANKER_AUTH_ERROR_MSG_TEST_FILE_FUNDS_EXCEPTION`).
8. **Race-condition guard on resume** — `workflowInstanceId` is passed through `WorkflowInputContext` to prevent two concurrent executions of the same step (comment in `AutofileInputValidator.validate` line 76).
9. **Idempotent funds retry enqueue** — `ScheduleFundsRetry` calls `hasPendingFundsRetryForProgram` before inserting a row, preventing duplicate queue entries per program.
10. **Queue archival (not delete)** — processed `autofile_funds_retry_queue` rows are set to `STATUS_ARCHIVED` ("Archived") rather than deleted, preserving audit trail.

## Business Flows

### A. Normal File Processing (Happy Path)
```
File Upload →
  [Loading Phase]
    AutoRetryLoadingSystemError (retry on load failure)
    AutoNotifyValidateStructureFailed (invalid structure)
    AutoNotifyJobValidateContentFailed (invalid content)
    NotifyAutoFinancePhase → kicks off ProcessingPreparation workflow
  [Processing Preparation Phase]
    ValidateAutoAuthorize → (auto=ON → BankerAuthorizeJob) | (auto=OFF → manual queue)
    BankerAuthorizeJob → (success → ValidateSchedule) | (service down → RetryBankerAvailability) |
                         (insufficient funds → ScheduleFundsRetry)
    ValidateSchedule → (schedule available → ScheduleJob) | (not available → AwaitingSchedule)
    ScheduleJob → job scheduled in JobScheduler
  [Processing Completion Phase]
    RunJobServiceJob → executes job in Job Service
    AutoNotifyProcessingStatus → monitors completion
    AutofileNotifyGeneratingReportStatus → report generation
    AutofileRemoveGeneratingReportStatus → cleanup
```

### B. Insufficient Funds Retry Path
```
ScheduleFundsRetry → inserts row into autofile_funds_retry_queue
  → InsufficientFundsRetryScheduler ticks at 09:00/13:00/17:00 ET (weekdays)
    → checks auto-auth flag (if OFF → moves to PENDING_AUTHORIZATION for manual)
    → calls startProcessingPreparationWorkflow → BankerAuthorizeJob
    → on success → marks queue entry ARCHIVED
```

### C. Pause/Resume
```
Pause: retrieve current status → determine pause applicability → 
       (Processing status → stop job-service job) |
       (AwaitingSchedule → remove schedule) →
       updateFilePauseInfo

Resume: set pause=Terminated → 
        (Processing/Pending Resources → check blackout → runJob) |
        (ReadyToRun/AwaitingSchedule → scheduleJob) |
        (other → re-execute paused step via WorkflowStepFactory)
```

## Compliance & Regulatory Concerns

1. **Funds authorization gating** — the service enforces that no disbursement job runs without Banker authorization. This is the funds-control gate for prepaid disbursement batches (relevant to program-level financial controls and Reg E disbursement accuracy).
2. **Audit trail** — queue rows are archived (not deleted), providing a timestamp record of when insufficient-funds conditions were detected and resolved. `FundsRetryQueueEntry.createdUtc` uses DATETIME2/SYSUTCDATETIME.
3. **Caller identity propagation** — `InsufficientFundsRetryScheduler` fetches `caller_member_id` from `dbo.job_file` to run the workflow under the original caller's identity, not a system account. This preserves auditability of who submitted the file.
4. **No PAN/SAD exposure** — no payment card data (PAN, CVV, track data) is processed or stored within this service. The service handles job/file metadata and fund amounts only.
5. **FIFO for fair treatment** — the FIFO ordering rule ensures files are processed in submission order per program, mitigating any favoritism or timing-based inequities in fund access.
6. **Feature flag risk** — `BankerServiceHelperImpl.simulateInsufficientFunds` is a simulation flag (`feature.simulate.insufficient.funds`) that bypasses real Banker authorization. If accidentally enabled in production, all files would be blocked. No production safeguard (e.g., environment check) is coded beyond a log warning.

## Business Risks

1. **Insufficient-funds scheduler single-threaded** — `InsufficientFundsRetryScheduler` uses a `newSingleThreadScheduledExecutor`. If one program's retry loop hangs, no other program's retries fire in that window.
2. **FIFO busy-spin under contention** — `ProgramJobOrderHelper.authorizeOldestFirst` uses a spin-retry loop with exponential back-off (50 ms → 1000 ms max) but no hard timeout. Under sustained database contention this could hold a Tomcat thread indefinitely.
3. **testingMode flag in production** — `InsufficientFundsRetryScheduler.testingMode` fires every 15 minutes when true. The property `insufficientFunds.testingMode` is injected from external config; accidental production misconfiguration would trigger excessive Banker authorization calls.
4. **Rollback ambiguity** — `workflowServiceHelper.rollbackWorkflowInstance` can return error messages prefixed with `ERROR_MSG_WORKFLOW_ROLLBACK_NOWHERETOGO` or `ERROR_MSG_WORKFLOW_ROLLBACK_NOLOG`, indicating no prior state or no history. These conditions surface to callers as failures but do not trigger alerts.
5. **No unit tests present** — all Maven builds use `-Dmaven.test.skip`. There is no evidence of test classes in the codebase, which is a significant quality risk for a financial state-machine service.
