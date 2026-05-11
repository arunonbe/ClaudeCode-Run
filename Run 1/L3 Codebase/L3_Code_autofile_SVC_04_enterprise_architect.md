# autofile_SVC — Enterprise Architect View

## Platform Generation (Gen-1/Gen-2/Gen-3)

**Classification: Gen-2 (containerized legacy)**

Evidence for this classification:

| Indicator | Evidence |
|---|---|
| Spring XML configuration (not annotation-driven Spring Boot) | All bean wiring via `autofile-core.xml`, `workflow-step.xml`, `domain-helpers.xml`, etc. |
| Apache Axis SOAP client | `axis:jakarta-axis:*` dependencies; `BankerServiceHelperImpl` uses `AxisFault` exception handling |
| Spring HTTP Invoker remoting | `org.springframework:jakarta-spring-remoting`; `scheduler-proxy.xml`, `jobScheduler-proxy.xml` |
| WAR packaging deployed into standalone Tomcat | `autofile-service` module packages as WAR; Tomcat 10.1.28 downloaded in Dockerfile |
| cbase platform SDK (`xplatform:6.5.8`) | `com.cbase.business.*` classes for WorkflowManager, JobService, RepositoryService, ProfileService |
| No Spring Boot, no Spring Cloud, no reactive stack | Confirmed absence across all POMs |
| Containerized and deployed to AKS | Dockerfile present; deployment.yml targets AKS — this is the Gen-2 "lift-and-shift to container" step |
| Java 21 runtime | Upgraded from legacy Java 1.5 (as per README) to 21 — runtime modernized but architecture unchanged |
| Jakarta EE 10 / Servlet 6.0 | `web.xml` declares `web-app_6_0` — migrated from javax to jakarta namespace |

The service has not been re-architected as a Spring Boot application with REST endpoints, embedded server, or event-driven messaging. It is a containerized version of the original Spring XML / SOAP / cbase-platform monolith.

## Business Domain

**Domain**: Prepaid Disbursement File Processing — Funds Authorization & Job Lifecycle Orchestration

This service belongs to the **Job Service suite** (as stated in `README.md`). Within Onbe's platform taxonomy:
- It is a **processing-control plane** service, not a payments-execution service.
- It gates the transition of a disbursement batch file from "loaded" to "running" by enforcing financial authorization (Banker service) and scheduling checks (JobScheduler service).
- It does not directly initiate card loads, ACH transfers, or any payment rail transaction. It authorizes the program-level fund reservation and then hands off to the Job Service for execution.

## Role in Platform

| Role | Description |
|---|---|
| **Workflow step executor** | Executes named workflow steps (e.g., `BankerAuthorizeJob`, `RunJobServiceJob`) dispatched by the Workflow Engine via HTTP GET to `/AutoFile.do` |
| **State machine manager** | Maintains the canonical job status in `autofile_job` table; all other services query this for file lifecycle state |
| **Authorization gatekeeper** | Enforces Banker fund authorization before any disbursement batch is allowed to run |
| **Retry coordinator** | Manages retry policies for loading failures, banker unavailability, insufficient funds, processing errors, and report generation failures |
| **FIFO enforcer** | `ProgramJobOrderHelper` ensures jobs within a program are authorized in upload-time order, preventing out-of-order disbursements |
| **Pause/Resume controller** | Provides operator-facing controls to pause, resume, and rollback in-flight jobs |

## Dependencies

### Upstream (callers of autofile_SVC)
- **Workflow Engine** (`WorkflowManager` / cbase platform) — calls `/AutoFile.do` for each workflow step transition
- **AJL (Admin Job List) UI** — calls `AutofileServiceProxy` methods: `pauseJob`, `resumeJob`, `rollbackJob`, `getFileDetailList`, `getJobDetailList` via Spring HTTP Invoker
- **Other JobSuite services** — call `AutofileServiceProxy.execute(agent, caller, step, fileId, jobId)` for programmatic workflow step dispatch

### Downstream (autofile_SVC calls these)
| Service | Artifact | Protocol | Used For |
|---|---|---|---|
| Banker Service | `banker-common:4.0.3` | Apache Axis SOAP | Fund authorization / un-authorization |
| Scheduler Service | `scheduler-common:3.0.1` | Spring HTTP Invoker | Schedule retry callbacks |
| Job Scheduler Service | `jobscheduler-common:3.0.0` | Spring HTTP Invoker | Check blackout, isJobScheduleAvailable, getVolFlexFlag, schedule/remove schedule |
| Job Service | `xplatform:6.5.8` (`com.cbase.business.jobsvc.*`) | cbase RPC | Run job, stop job, authorize job, retrieve batch info |
| Repository Service | `xplatform:6.5.8` (`com.cbase.business.repository.*`) | cbase RPC | Get file attributes (ETLAgentPackage), get file data |
| Profile Service | `xplatform:6.5.8` (`com.cbase.business.profile.*`) | cbase RPC | Retrieve "Auto Authorization" and "Banker" label flags per program |
| Workflow Engine | `xplatform:6.5.8` (`com.cbase.business.workflow.WorkflowManager`) | cbase RPC | Start workflow processes, advance steps, rollback |
| JobSvc SQL Server | JDBC | SQL over TCP | All job state persistence |
| CbaseApp SQL Server | JDBC | SQL over TCP | User/member resolution |

### Peer dependencies (platform constants)
- `prepaid-parent:6.0.13` — governs all library versions and enforcer rules

## Integration Patterns

| Pattern | Implementation |
|---|---|
| **Workflow step callback (HTTP GET)** | `/AutoFile.do` servlet (`AutoFileServiceAdapter`) — Workflow Engine calls this URL with step parameters; service processes and returns an integer return code |
| **Spring HTTP Invoker (RMI over HTTP)** | Used for inbound client access (`AutofileServiceProxy`) and outbound to Scheduler/JobScheduler services. Client XML: `autofile-common/src/main/resources/com/ecount/autofile/autofileService-client.xml` |
| **Apache Axis SOAP** | Outbound calls to Banker Service via `BankerServiceAPI`. Legacy SOAP stack (Axis 1.x wrapped as `jakarta-axis`). |
| **cbase RPC** | Opaque platform-native RPC for Job Service, Repository Service, Profile Service, Workflow Engine — all accessed via `xplatform` library |
| **Stored procedures** | All database access for file/job CRUD goes through named stored procedures (`StoredProcedure` subclasses). Inline JDBC is used only for the newer `autofile_funds_retry_queue` table operations. |
| **Background scheduler** | `InsufficientFundsRetryScheduler` uses `ScheduledExecutorService` (in-JVM, single thread). Not a distributed scheduler — no quartz, no K8s CronJob. |
| **Service Locator (Spring)** | `WorkflowStepFactory` is implemented as `ServiceLocatorFactoryBean`, looking up beans by name suffix (`-WorkflowStep`, `-WorkflowRetry`). |

## Strategic Status

**Status: Active — Modernization Candidate**

| Dimension | Assessment |
|---|---|
| Business criticality | High — funds authorization gating for all prepaid disbursement files |
| Technical currency | Low — Spring XML, Apache Axis, cbase proprietary RPC, no REST API, no observability stack |
| Migration urgency | Medium — containerized and operational, but tightly coupled to legacy cbase platform |
| Ownership clarity | Code authored by OFSS; maintainer per Dockerfile: `anil.tadigiri@onbe.com` |
| Test coverage | None — all builds skip tests |

## Migration Blockers

The following are concrete blockers to a Gen-3 (Spring Boot / REST / event-driven) migration:

1. **cbase platform SDK (`xplatform:6.5.8`)** — `WorkflowManager`, `JobService`, `RepositoryService`, `ProfileService`, and `WorkflowCache` are all tightly coupled to `com.cbase.business.*` classes. Until these platform services have modern REST/gRPC equivalents, autofile cannot be replatformed.

2. **Apache Axis SOAP for Banker Service** — `BankerServiceHelperImpl` calls `BankerServiceAPI.auth()`, `authMultiple()`, `unAuth()` via Axis. Banker Service must expose a REST API or the Banker client must be re-implemented before migration.

3. **Spring HTTP Invoker (Java serialization RPC)** — both inbound (`AutofileServiceProxy` client) and outbound (Scheduler, JobScheduler) use Spring HTTP Invoker, which relies on Java object serialization. All calling systems must migrate simultaneously or an adapter layer is needed.

4. **`/AutoFile.do` servlet contract** — the Workflow Engine calls this URL pattern with plain HTTP GET parameters. Changing this contract requires coordinating the Workflow Engine and all workflow process definitions.

5. **Spring XML wiring** — ~8 XML configuration files define the full bean graph. Migration to Spring Boot annotation-driven configuration requires significant refactoring of all bean definitions and property resolution.

6. **Shared database schema** — `autofile_job`, `job_file`, `job_file_ingest`, and `autofile_status` are shared with Job Service and likely other platform services. Schema ownership and migration must be coordinated across teams.

7. **`WorkflowCache` startup dependency** — cache loads from the Workflow Engine at bean initialization. A Gen-3 version would need an event-driven or lazy-loading equivalent. Currently, startup sequencing depends on the Workflow Engine being healthy.

8. **No tests** — zero test coverage means any migration carries unknown regression risk. Test harness must be built before safe refactoring.
