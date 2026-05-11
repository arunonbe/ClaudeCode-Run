# Solution Architect View — job-scheduler_SVC

## Module Structure

```
jobscheduler/
├── jobscheduler-common/     # Interfaces, DTOs, client API
├── jobscheduler-impl/       # Business logic implementation
└── jobscheduler-service/    # WAR packaging, Spring XML, web.xml
```

## Complete Class and Method Inventory

### Module: `jobscheduler-common`

| Class / Interface | Package | Purpose |
|---|---|---|
| `JobSchedulerService` | `jobscheduler` | Service interface — all scheduling operations |
| `JobSchedulerServiceClient` | `jobscheduler` | HTTP Invoker client for remote callers |
| `JobScheduleInfo` | `jobscheduler.dto` | DTO: per-job scheduling state (jobId, scheduleMode, scheduleTime, statusId, affiliateId, userId, sysAgentName, volFlexFlag, scheduleTaskId) |
| `ProgramScheduleInfo` | `jobscheduler.dto` | DTO: program-level recurring schedule definition |
| `Week` | `jobscheduler.dto` | DTO: day-of-week flags for weekly schedule |
| `JobSchedulerServiceException` | `jobscheduler.exception` | Checked exception for scheduler service failures |
| `JobSchedulerConstants` | `jobscheduler.util` | Static constants: `IMMEDIATE_MODE`, `SCHEDULE_MODE`, `NOSCHEDULE_MODE`, `STATUS_ID_READY_TO_RUN=1`, `STATUS_ID_AWAITING_SCHEDULED_EXECUTION=2`, `RETURN_STATUS_SUCCESS`, `RETURN_STATUS_FAIL`, `VOL_FLEX_FLAG_YES/NO`, `ERROR_CODE_NOT_IN_RUNNABLE_STATE` |
| `JobSchedulerUtils` | `jobscheduler.util` | Utility methods |
| `BlackoutInfo` | `blackout.dto` | DTO: blackout definition (blackoutId, blackoutType, blackoutFrequency, startTime, endTime, userId, sysAgentName, status, retryToStopJob flag) |
| `BlackoutScheduleInfo` | `blackout.dto` | DTO: computed schedule for a blackout (startTaskId, endTaskId, nextStartTime, nextEndTime, inEffect flag) |
| `BlackoutWeek` | `blackout.dto` | DTO: day flags (sun/mon/tue/wed/thu/fri/sat booleans) for weekly blackout |
| `BlackoutConstants` | `blackout.util` | Constants: `BLACKOUT_TYPE_ALL/LIVE/BATCH`, `BLACKOUT_IN_EFFECT_YES/NO/PROGRESS/TERMINATING`, `SCHEDULE_FREQUENCY_DAILY/WEEKLY/DATE/ADHOC`, `BLACKOUT_STATUS_DELETED`, `RETURN_STATUS_PAUSED_BY_ANOTHER_BLACKOUT` |

### Module: `jobscheduler-impl`

| Class | Package | Purpose |
|---|---|---|
| `JobSchedulerServiceImpl` | `jobscheduler` | Main service implementation (see method list below) |
| `BlackoutManager` | `blackout` | Interface for all blackout operations |
| `BlackoutManagerImpl` | `blackout` | Full blackout lifecycle: create, start, finish, end, delete, check, override, retry stop-job |
| `BlackoutDAO` | `blackout.dao` | Interface for blackout DB operations |
| `BlackoutDAOImpl` | `blackout.dao` | JDBC implementation delegating to stored procedure wrappers |
| `DeleteBlackoutJob` | `blackout.dao` | SP wrapper: `blackout_delete_blackout_job` |
| `InsertBlackoutActionsLog` | `blackout.dao` | SP wrapper: `blackout_insert_blackout_actions_log` |
| `InsertBlackoutInfo` | `blackout.dao` | SP wrapper: `blackout_insert_blackout_info` |
| `InsertBlackoutJob` | `blackout.dao` | SP wrapper: `blackout_insert_blackout_job` |
| `InsertBlackoutSchedule` | `blackout.dao` | SP wrapper: `blackout_insert_blackout_schedule` |
| `RetrieveBlackoutData` | `blackout.dao` | SP wrapper: `blackout_retrieve_blackout_info` |
| `RetrieveBlackoutJob` | `blackout.dao` | SP wrapper: `blackout_retrieve_blackout_job` |
| `RetrieveProcessingJobList` | `blackout.dao` | SP wrapper: `blackout_get_processing_job_list` |
| `UpdateBlackoutInfo` | `blackout.dao` | SP wrapper: `blackout_update_blackout_info` |
| `UpdateBlackoutSchedule` | `blackout.dao` | SP wrapper: `blackout_update_blackout_schedule` |
| `UpdateJobStatus` | `blackout.dao` | SP wrapper: `blackout_update_job_status` |
| `JobSchedulerDAO` | `jobscheduler.dao` | Interface for schedule DB operations |
| `JobSchedulerDAOImpl` | `jobscheduler.dao` | JDBC implementation |
| `StoredProcGetScheduleInfo` | `jobscheduler.dao` | SP: `GET_SCH_INFO` |
| `StoredProcGetSchJobStatus` | `jobscheduler.dao` | SP: `GET_SCH_JOB_STATUS` |
| `StoredProcGetUserInfo` | `jobscheduler.dao` | SP: `GET_USER_INFO` (cbaseapp) |
| `StoredProcInsertJobActionsLog` | `jobscheduler.dao` | SP: `INSERT_JOB_ACTION_LOG` |
| `StoredProcInsertJobExecInfo` | `jobscheduler.dao` | SP: `INSERT_SCH_JOB_EXEC_INFO` |
| `StoredProcInsertScheduleHistory` | `jobscheduler.dao` | SP: `INSERT_SCHEDULE_HISTORY` |
| `StoredProcInsertScheduleInfo` | `jobscheduler.dao` | SP: `INSERT_SCHEDULE_INFO` |
| `StoredProcUpdateJobInfo` | `jobscheduler.dao` | SP: `UPDATE_JOB_INFO` |
| `StoredProcUpdatePriority` | `jobscheduler.dao` | SP: `UPDATE_PRIORITY` |
| `StoredProcUpdateScheduleInfo` | `jobscheduler.dao` | SP: `UPDATE_SCHEDULE_INFO` |
| `JobExecutionStatusProcessor` | `jobscheduler.domain` | Interface for updating execution status after scheduling decisions |
| `JobExecutionStatusProcessorImpl` | `jobscheduler.domain` | Updates `sch_job_exec_status`, writes action logs |
| `JobManager` | `jobscheduler.domain` | Interface for calling the Job Manager (pause/resume operations) |
| `JobManagerDelegate` | `jobscheduler.domain` | Delegates to xPlatform JobManager XML-RPC calls: `pauseJob()`, `resumeBlackoutJob()` |
| `JobSchedulerCalculator` | `jobscheduler.domain` | Interface for schedule time arithmetic |
| `JobSchedulerCalculatorImpl` | `jobscheduler.domain` | `isSchedulePassed()`, `isScheduleTimeEqual()` — date comparison logic |
| `JobSchedulerCallbackServiceServer` | `jobscheduler.domain` | Receives callbacks from Scheduler Service when a task fires |
| `ScheduleJobListManager` | `jobscheduler.domain` | Interface for bulk-fetching schedule status for AJL |
| `ScheduleJobListManagerImpl` | `jobscheduler.domain` | `getScheduleDetailsList()` — enriches array of JobScheduleInfo from DB |
| `SchedulingOperationsHandler` | `jobscheduler.domain` | Interface for schedule operation delegates |
| `SchedulingOperationsHandlerImpl` | `jobscheduler.domain` | `scheduleJob()`, `removeSchedule()`, `reapplySchedule()`, `getNextScheduleTime()`, `scheduleBlackoutJob()`, `removeBlackoutJob()`, `executeImmediateJob()`, `setupFileScheduleUpdateData()`, `updateScheduleJobStatus()`, `updateRemoveScheduleStatus()`, `updateReapplyScheduleStatus()`, `updateUnauthorizeStatus()` |

### Module: `jobscheduler-service`

| File | Purpose |
|---|---|
| `HealthCheck.java` | HTTP health endpoint |
| `JobScheduler-datasource.xml` | Spring data source beans (Director-configured) |
| `Scheduler-proxy.xml` | HTTP Invoker proxy export of the service |
| `JobScheduler-webapp.xml` / `web.xml` | Spring DispatcherServlet configuration |

## Key Method Signatures — `JobSchedulerServiceImpl`

```java
public String scheduleJob(JobScheduleInfo jobScheduleInfo)        // Schedule or run immediately
public String removeSchedule(JobScheduleInfo jobScheduleInfo)     // Un-schedule a job
public String reapplySchedule(JobScheduleInfo jobScheduleInfo)    // Re-schedule past-due job
public String unAuthorizeSchedule(JobScheduleInfo jobScheduleInfo) // Reverse authorization
public ProgramScheduleInfo insertSchedule(ProgramScheduleInfo)    // Create program schedule
public String updateSchedule(ProgramScheduleInfo programScheduleInfo) // Modify program schedule
public String updateFileSchedule(JobScheduleInfo jobScheduleInfo) // Per-file schedule override
public JobScheduleInfo[] getSchStatusList(JobScheduleInfo[] list) // Bulk status for AJL
public JobScheduleInfo getSchStatus(int jobId)                    // Single job status
public ProgramScheduleInfo getScheduleInfo(ProgramScheduleInfo)   // Get program schedule
public String updatePriority(JobScheduleInfo jobScheduleInfo)     // Change queue priority
public String overrideBlackout(JobScheduleInfo jobScheduleInfo)   // Force job through blackout
public boolean checkBlackout(int jobId)                           // Pre-run blackout check
public String createBlackout(BlackoutInfo blackoutInfo)           // Define new blackout
public String updateBlackout(BlackoutInfo blackoutInfo)           // Modify blackout
public String deleteBlackout(BlackoutInfo blackoutInfo)           // Remove blackout
public String endBlackout(BlackoutInfo blackoutInfo)              // Immediately end active blackout
public BlackoutScheduleInfo[] retrieveBlackout(BlackoutInfo)      // Get blackout details
public String getBlackoutStatus()                                  // Overall blackout state
```

## Security Vulnerabilities

### SV-1: Race Condition in Blackout Start/Finish (HIGH)
`BlackoutManagerImpl.startBlackout()` sets `in_effect = PROGRESS` (line 223) before iterating over processing jobs, attempting to prevent concurrent execution. However, this is a DB-level flag, not a transaction lock. Two concurrent callers can both read `in_effect = NO` before either writes `PROGRESS`, resulting in double blackout application and all jobs being double-paused. The `startOrFinishBlackout()` retry loop (lines 927–948) uses `Thread.sleep(2000)` as a soft guard — not a transactional lock. **Priority: HIGH** — use `SELECT ... WITH (UPDLOCK)` or a `MERGE` pattern in the stored procedure.

### SV-2: `Thread.sleep()` in Web Request Thread (MEDIUM)
`BlackoutManagerImpl.startOrFinishBlackout()` lines 939–946 calls `Thread.sleep(2000)` in what is likely a Tomcat request thread, blocking the thread for up to 6 seconds (3 attempts × 2s). This reduces Tomcat thread pool availability and can cascade into service timeouts under load. **Priority: MEDIUM** — use async processing or a message-based trigger for blackout callbacks.

### SV-3: `userId` Resolution Crosses Database Boundary Without Error Handling (MEDIUM)
`BlackoutManagerImpl` lines 167–175 attempts to resolve `userId` from `cbaseapp`; on failure it falls back to `jobScheduleInfo.getUserId()` (a member ID string from the caller). If the caller is the scheduler system itself, this fallback may log the wrong actor in audit records, creating an audit trail integrity issue. Under PCI DSS Requirement 10.2.1, audit logs must accurately record the user responsible for each action. **Priority: MEDIUM**.

### SV-4: No Authentication on XML-RPC Endpoint (HIGH)
The `web.xml` exposes `XmlRPCServlet` at `/dispatch.asp` with no visible authentication filter. Scheduling operations (including `overrideBlackout()` which forces jobs through settlement windows) are callable by any HTTP client that can reach the server. In PCI DSS-regulated environments, all management interfaces must require authentication. This requires verification — network-level access controls may compensate. **Priority: HIGH** — verify WAF/network-layer controls; add application-layer auth if not present.

### SV-5: Service Proxy URL Exposure in `Scheduler-proxy.xml` (LOW)
The `Scheduler-proxy.xml` exposes the service interface via Spring `HttpInvokerServiceExporter` over Java serialization. This carries the same deserialization risk as noted in the synchronizer. **Priority: MEDIUM** — replace with Spring MVC REST endpoints or gRPC.

## Technical Debt Summary

| Item | Severity | Location |
|---|---|---|
| Race condition in blackout | HIGH | `BlackoutManagerImpl.java:222-225` |
| No auth on XML-RPC | HIGH | `web.xml` / network controls |
| HTTP Invoker serialization | HIGH | `Scheduler-proxy.xml` |
| Thread.sleep in request thread | MEDIUM | `BlackoutManagerImpl.java:939` |
| Blackout next-time calculation logic duplication | MEDIUM | `getNextStartTime()` and `getNextEndTime()` — 300+ lines of near-identical day-of-week logic |
| No unit tests | HIGH | Entire codebase |
| XML-only Spring wiring | MEDIUM | All Spring XML files — prevents Spring Boot migration |
| xPlatform XML-RPC coupling to JobManager | HIGH | `JobManagerDelegate.java` — blocking platform modernization |
