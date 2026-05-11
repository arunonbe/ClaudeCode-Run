# autofile_SVC — Solution Architect View

## Technical Architecture

### Module Layout
```
autofile (parent POM 3.0.3)
├── autofile-common (JAR)       — Public API interface, DTOs, proxy, validator
│   └── AutofileService         — Service interface (7 methods)
│   └── AutofileServiceProxy    — Client-side proxy wrapping the HTTP Invoker stub
│   └── dto/                    — JobInfo, WorkflowInputContext, WorkflowOutput, FundsRetryQueueEntry
│   └── validation/             — AutofileInputValidator (programmatic input guard)
│   └── util/                   — AutoFileConstants, AutofileServiceUtils
│
├── autofile-impl (JAR)         — All business logic, domain steps, DAO
│   └── AutofileServiceImpl     — Implements AutofileService; orchestrates helpers
│   └── dao/                    — AutofileDAO (interface) + AutofileDAOImpl + 11 StoredProc classes
│   └── domain/                 — ~20 workflow step classes + InsufficientFundsRetryScheduler
│   └── domain/helpers/         — 10 helper interface+impl pairs
│   └── domain/retry/           — 7 workflow retry classes
│   └── properties/             — RetryProperties bean
│
└── autofile-service (WAR)      — HTTP entry point, Spring MVC health, Tomcat config
    └── AutoFileServiceAdapter  — HttpServlet at /AutoFile.do (main workflow trigger)
    └── HealthCheck             — Spring MVC @RestController at /hc
    └── AutofileInputValidator  — Servlet-layer HTTP parameter validator
```

### Request Processing Model

Two inbound paths exist:

**Path 1 — Workflow Step Trigger (primary)**
```
HTTP GET /AutoFile.do
  params: EXEC_AGENT, CALLER_ID, STEP_NAME, FILE_ID, JOB_ID
  → AutoFileServiceAdapter.doGet()
  → AutofileInputValidator.validate(HttpServletRequest)
  → AutofileServiceImpl.execute(WorkflowInputContext)
  → WorkflowStepFactory.getWorkflowStep(stepName + "-WorkflowStep")
  → WorkflowStep.execute(WorkflowInputContext)
  → returns integer return code in HTTP response body
```

**Path 2 — Spring HTTP Invoker (operator/client calls)**
```
Spring HTTP Invoker endpoint (URL configured externally)
  → AutofileServiceImpl.[pauseJob|resumeJob|rollbackJob|
                          getFileDetailList|getJobDetailList|
                          getJobInfo|updateJobStatus]
```

**Path 3 — Background scheduler (internal)**
```
InsufficientFundsRetryScheduler (daemon thread, fires at configured ET times)
  → AutofileDAOImpl.getDistinctProgramIdsForInsufficientFunds()
  → per-program: getFundsRetryQueueEntry → getJobDetails → startProcessingPreparationWorkflow
```

### Workflow Step Dispatch

Bean naming convention drives step lookup:
- `AutofileServiceImpl.execute()` appends `"-WorkflowStep"` to the step name → `WorkflowStepFactory.getWorkflowStep(name)`
- `AutofileServiceImpl.executeRetry()` appends `"-WorkflowRetry"`
- `WorkflowStepFactory` is a Spring `ServiceLocatorFactoryBean` — performs `applicationContext.getBean(name)` lookup

All ~20 workflow step beans are registered in `workflow-step.xml` and `workflow-retry.xml`.

## API Surface

### Inbound HTTP Endpoints

| Endpoint | Method | Servlet/Controller | Purpose |
|---|---|---|---|
| `/AutoFile.do` | GET, POST | `AutoFileServiceAdapter` | Primary workflow step trigger |
| `/hc` | GET | `HealthCheck` (`@RestController`) | Health probe (returns "OK") |
| `/*.service` (URL pattern) | — | Spring `DispatcherServlet` | Spring HTTP Invoker service endpoints |

### Spring HTTP Invoker Service Methods (via `AutofileService` interface)

| Method | Signature | Notes |
|---|---|---|
| `pauseJob` | `(fileId, memberId, agent) → String` | Pauses job; stops job-service job if in Processing state |
| `resumeJob` | `(fileId, memberId, agent) → String` | Resumes paused job; blackout-aware for Processing-state jobs |
| `rollbackJob` | `(fileId, memberId, agent) → String` | Rolls back workflow instance to prior phase |
| `getFileDetailList` | `(String[] fileIds) → JobInfo[]` | Batch file status query (batched in groups of 30) |
| `getJobDetailList` | `(JobInfo[] job, JobInfo[] jobSchInfo) → JobInfo[]` | Merged job status list |
| `execute` | `(WorkflowInputContext) → WorkflowOutput` | Direct workflow step execution |
| `executeRetry` | `(WorkflowInputContext) → WorkflowOutput` | Direct workflow retry execution |
| `getJobInfo` | `(int jobId) → JobInfo` | Single job lookup |
| `updateJobStatus` | `(JobInfo) → void` | Job status update (used by external callers for admin operations) |

### Workflow Return Codes (outbound to Workflow Engine)

| Code | Constant | Meaning |
|---|---|---|
| 0 | `WORKFLOW_RETURN_CODE_SUCCESS` / `WORKFLOW_RETURN_CODE_BANKER_AUTHORIZATION_SUCCESS` | Success / proceed |
| 1 | `WORKFLOW_RETURN_CODE_FAIL` | General failure |
| 2 | `WORKFLOW_RETURN_CODE_AUTHORIZATION_AUTO_OFF` / `WORKFLOW_RETURN_CODE_BANKER_SERVICE_DOWN` / `WORKFLOW_RETURN_CODE_JOB_SCHEDULE_NOT_AVAILABLE` / `WORKFLOW_RETURN_CODE_PROCESSING_INITIALIZATION_SUCCESS` | Step-specific secondary outcomes |
| 3 | `WORKFLOW_RETURN_CODE_BANKER_AUTHORIZATION_FAILED` | Auth failed (not funds) |
| 4 | `WORKFLOW_RETURN_CODE_INSUFFICIENT_FUNDS` | Insufficient funds detected |

## Security Posture

### Authentication & Authorization
- **No application-level authentication** on any inbound endpoint. `/AutoFile.do` is callable by any HTTP client with network access.
- **No authorization check** on the `/hc` health endpoint.
- The Spring HTTP Invoker endpoints have no documented authentication mechanism in the codebase. Security relies entirely on network-layer controls (AKS network policy, service mesh, or ingress restrictions).
- Inbound caller identity is passed as a plain HTTP parameter (`CALLER_ID`) — no cryptographic validation.

### Input Validation
- Servlet layer (`AutoFileServiceAdapter`): validates `EXEC_AGENT`, `CALLER_ID`, `STEP_NAME`, `FILE_ID`, `JOB_ID` are non-null/non-empty. No sanitization beyond null checks.
- Proxy layer (`AutofileServiceProxy.validate`): delegates to `AutofileInputValidator` for the same checks.
- No injection-prevention beyond parameterized stored procedures. Inline SQL in `AutofileDAOImpl` uses `PreparedStatement` via `JdbcTemplate`, which prevents SQL injection.
- `FILE_ID` is used as a stored-proc parameter only — no filesystem or path traversal risk.

### Secrets Management
- Database credentials are environment variables (`AUTOFILESVC_CBASEAPPDB_PASSWORD`, `AUTOFILESVC_JOBSVCDB_PASSWORD`) — not hardcoded.
- No secrets are present in any checked-in configuration file.
- JVM truststore uses default `changeit` password (standard for Alpine JRE containers; not a secret in this context).

### Network Security
- Tomcat HTTP connector on port 80 — no TLS. All traffic is plaintext between the pod and any caller unless a service mesh (e.g., mTLS via Istio/Linkerd) is applied at the AKS layer.
- No CSRF protection, no security headers configured in web.xml or servlet.

### CVE Allowlist
Six CVEs are explicitly suppressed in `.github/containerscan/allowedlist.yaml`:
- CVE-2018-1000632 (dom4j)
- CVE-2020-10683 (dom4j)
- CVE-2024-22262 (Spring Web)
- CVE-2024-38816 (Spring Web/MVC)
- CVE-2024-47072 (XStream)
- CVE-2024-52316 (Apache Tomcat)

**CVE-2024-52316** (Apache Tomcat authentication bypass) and **CVE-2024-22262 / CVE-2024-38816** (Spring Web open redirect / path traversal) are particularly notable for a service with unauthenticated HTTP endpoints.

## Technical Debt

### High Priority

1. **Zero test coverage** — no unit tests, no integration tests, no contract tests (Pact provider verification disabled). The entire business-critical authorization and state-machine logic is untested. All Maven builds skip tests (`-Dmaven.test.skip`).

2. **Apache Axis SOAP (EOL)** — `BankerServiceHelperImpl` uses `org.apache.axis.AxisFault` and `BankerServiceAPI` via Axis 1.x (repackaged as `jakarta-axis`). Apache Axis 1.x reached end-of-life in 2006. It is the source of the multiple `--add-opens` JVM flags required for Java 21 compatibility.

3. **Spring HTTP Invoker (deprecated since Spring 5.3, removed in Spring 6.x)** — used for both inbound client proxy (`AutofileServiceProxy`) and outbound scheduler service calls. Spring HTTP Invoker relies on Java serialization and was deprecated for security reasons. Migration to REST is required before Spring 6 upgrade.

4. **Mixed DAO access patterns** — `AutofileDAOImpl` uses two different patterns:
   - `StoredProcedure` subclasses (Spring JDBC stored procedure objects) for legacy operations
   - Direct `JdbcTemplate` inline SQL for newer `autofile_funds_retry_queue` operations
   This inconsistency complicates testing and maintenance.

5. **`ThreadLocal<Logger>` anti-pattern** — `AutofileServiceProxy` and `AutofileInputValidator` (common module) instantiate loggers via `ThreadLocal<Logger>`, an incorrect pattern that creates a new Logger per thread rather than per class. `@Slf4j` is used correctly in impl classes.

6. **FIFO spin-wait without timeout** — `ProgramJobOrderHelper.authorizeOldestFirst` contains an unbounded `while(true)` loop with exponential back-off (lines 50–124). There is no maximum iteration count or wall-clock timeout. A stuck claim in the database would hold a Tomcat thread permanently.

### Medium Priority

7. **Raw type usage** — Multiple DAO classes use raw types: `Map out = execute(in)`, `List objList = (List) out.get("result_set")`, raw `RowMapper` (non-generic). These generate unchecked cast warnings and reduce type safety.

8. **TODO comments throughout** — Many domain classes carry `@<br>TODO Description` in their Javadoc (e.g., `BankerAuthorizeJob`, `ValidateSchedule`, `RunJobServiceJob`, `WorkflowCache`). These classes have never received proper documentation.

9. **Hardcoded legacy hostnames** — `docker-compose.yaml` contains `extra_hosts` with hardcoded Wirecard IPs (`10.91.22.253`, `10.91.22.254`). These are environment-specific and should be in environment-specific compose overrides.

10. **`ScheduleFundsRetry` idempotency logic is a no-op** — Lines 55–69 of `ScheduleFundsRetry.execute()` check `hasPendingFundsRetryForProgram` but insert a new row regardless of whether one already exists. The `if (alreadyPending)` and `else` branches both call `insertFundsRetryQueue` with identical arguments. The idempotency check achieves nothing.

11. **`WorkflowCache` is not thread-safe** — `loadcache()` writes to `HashMap` without synchronization. If two threads race on an empty cache check (`if(null==processList || processList.length==0)`), both call `loadcache()` concurrently, causing undefined HashMap state.

12. **`getFileDetailList` array sizing** — `AutofileServiceImpl.getFileDetailList` (line 255) allocates the result array with size `fileIds.length + (fileIds.length/30 + 1)`, which over-allocates and leaves null entries in the returned array. Callers must null-check every element.

### Low Priority

13. **`com.citi.*` exclusion in enforcer** — `autofile-impl/pom.xml` enforcer exclude list contains `com.citi.*`, suggesting historical Citibank dependency artifacts. This is dead configuration.

14. **GitLab CI file present** — `.gitlab-ci.yml` exists alongside GitHub Actions workflows, suggesting incomplete SCM migration or dual-system operation.

15. **README references Wirecard GitLab URL** — `README.md` still points to `https://gitlab.wirecard-cloud.com/...` as the clone URL.

## Gen-3 Migration Requirements

To migrate autofile_SVC to a Gen-3 (Spring Boot, REST-native, cloud-native) architecture, the following must be addressed:

| Requirement | Effort | Blocking On |
|---|---|---|
| Replace `xplatform:6.5.8` cbase RPC calls with REST clients | High | Platform team must expose REST APIs for WorkflowManager, JobService, RepositoryService, ProfileService |
| Replace Apache Axis SOAP Banker client with REST/gRPC | Medium | Banker Service REST API availability |
| Replace Spring HTTP Invoker with REST endpoints | Medium | All callers (AJL, Workflow Engine, other JobSuite services) must migrate simultaneously or adapter pattern needed |
| Rewrite `/AutoFile.do` as `POST /workflow/steps/{stepName}` REST endpoint | Low | Workflow Engine must be updated to call new URL |
| Migrate Spring XML config to Spring Boot auto-configuration | Medium | None (pure refactoring) |
| Build test suite (unit + integration) | High | None (prerequisite for safe migration) |
| Distribute `InsufficientFundsRetryScheduler` (e.g., K8s CronJob) | Low | Externalize scheduler to avoid single-JVM limitation |
| Add structured logging (JSON + MDC) | Low | None |
| Add Micrometer/Prometheus metrics | Low | None |
| Add database health check to /hc | Low | None |
| Review and remediate CVE allowlist | Medium | Upstream library updates |

## Code-Level Risks

1. **`AutofileServiceImpl.rollbackJob`** (line 224): calls `workflowServiceHelper.rollbackWorkflowInstance(...)`. If this returns a success string that starts with "Success" but the subsequent `updateFileInfo` throws, the workflow instance is rolled back in the engine but the autofile DB record is not updated — leaving the two systems in inconsistent state. No compensating transaction exists.

2. **`BankerServiceHelperImpl.authorizeJob`** (lines 113–121): on `AutofileServiceException` after partial Banker authorization, the service attempts to un-authorize `availableSources[0]` — a hardcoded array index. If `availableSources` was successfully built with multiple sources but only index 0 is un-authorized, the remaining sources remain authorized in Banker, causing a financial inconsistency.

3. **`StoredProcAutoFileGetJobDetails.execute`** (line 106): does `objList.get(0)` without null or empty-list check. If the stored procedure returns zero rows, this throws `IndexOutOfBoundsException` which is caught as a generic `Exception` in `AutofileDAOImpl.getJobDetails` and swallowed (logged as error, returns null). Callers then null-check inconsistently — some immediately call methods on the returned `JobInfo` without null guard (e.g., `AutofileServiceImpl.resumeJob` line 139 calls `jobInfo.getPausedStepName()` after `autofileDAO.getFileInfo(fileId)` with no null check).

4. **`AutofileServiceImpl.resumeJob`** (line 139): `String workflowStepName = jobInfo.getPausedStepName()` — `jobInfo` is the result of `autofileDAO.getFileInfo(fileId)`. If `getFileInfo` returns null (which `AutofileDAOImpl.getFileInfo` can silently do on exception — line 151 logs error but continues), calling `getPausedStepName()` throws `NullPointerException`, which is caught as `AutofileServiceException` but leaves the pause status inconsistent (the exception handler sets pause to Effective and calls `updateFilePauseInfo`).

5. **`InsufficientFundsRetryScheduler.tick()`**: the production mode schedule check uses `if (minute <= 1)` to provide a 1-minute drift tolerance (lines 158–170). However, it checks `slot == currentHourSlot` where `currentHourSlot = hour * 100` (always `XX00`). If the scheduler ticks at minute=1 (e.g., 09:01), `currentHourSlot = 900` and `slot = 900` matches, so the slot fires. But if a server time drift causes the tick to land at minute=2, the window is missed entirely until the next configured time. This is a silent retry miss with no alerting.

6. **`domain-helpers.xml` `simulateInsufficientFunds` injection** (line 41): value is `${feature.simulate.insufficient.funds}`. If this property is absent from the config file, Spring will throw a `BeanCreationException` at startup, preventing the service from starting. There is no default value declared in the XML (`value="${...}"` without a fallback). This is a deployment risk if the property is omitted during environment provisioning.

7. **Concurrency in `WorkflowCache.loadcache()`**: `processStepDefinitions` and `processStateMachines` are `HashMap` (not `ConcurrentHashMap`). The lazy-reload checks (`if(null==processList || processList.length==0)`) in `getProcessList()`, `getProcessStepDefinitions()`, and `getProcessStateMachines()` are not synchronized. Under concurrent HTTP requests at startup, multiple threads can call `loadcache()` simultaneously, resulting in lost map entries or `ConcurrentModificationException`.
