# Enterprise Architect View — job-scheduler_SVC

## Platform Generation and Heritage

The Job Scheduler Service is a **second-generation** platform service that emerged from the "53E File Automation" program (referenced throughout `JobSchedulerServiceImpl.java` version comments). The version history shows at least four distinct development phases:
- Version 1: Initial development (pre-2009)
- Version 2: 53E Phase I — Priority queue (`updatePriority`)
- Version 3: 53E Phase II — File-level schedule override (`updateFileSchedule`)
- Version 4: 53E Phase III — Workflow enhancements, Blackout management

Current version 3.0.1-SNAPSHOT on parent `prepaid-parent:6.0.12` (Java 21) represents a significant modernization from the original Java 1.7 baseline (noted in `README.md` line 8).

The `@Slf4j` Lombok annotation (seen in `JobSchedulerServiceImpl.java` line 56 and `BlackoutManagerImpl.java` line 19) indicates recent modernization of the logging layer, though the underlying architecture remains XML-wiring-heavy Spring.

## Role as the Batch Processing Backbone

The Job Scheduler occupies a **central, synchronous-critical position** in the platform architecture:

```
[ClientZone/Banker UI]
        │
        ▼ XML-RPC call
[JobSchedulerWebServices endpoint]
        │
        ├── ScheduleJob → [External Scheduler Engine (SchedulerServiceProxy)]
        │                   ↓
        │         [Callback: JobSchedulerCallbackServiceServer]
        │                   ↓
        │         [xPlatform call to JobManager.RUN]
        │
        ├── CheckBlackout → [BlackoutManager]
        │
        └── UpdatePriority / UpdateSchedule → [JobSchedulerDAO → jobsvc DB]
```

Every batch job submitted by every client flows through this service's schedule gate. There is no path for a job to move from "authorized" to "processing" without the Job Scheduler either:
(a) determining the execution time and registering a callback task, or
(b) executing it immediately (IMMEDIATE mode), or
(c) marking it READY_TO_RUN (NOSCHEDULE mode)

This makes the Job Scheduler a **single point of failure** for the entire batch processing pipeline.

## External Scheduler Engine

The `SchedulerServiceProxy` bean is an abstraction over the underlying timer/scheduler infrastructure. Based on the dependency `com.ecount.service.scheduler:scheduler-common:3.0.1` (`pom.xml` line 46) and the proxy pattern, the underlying engine is the platform's own "Scheduler Service" — a separate application that manages timed task execution and fires callbacks at the configured time. This is the component that actually invokes the `JobSchedulerCallbackServiceServer` when a scheduled time arrives.

## Inter-Service Dependencies

### Inbound (services that call this service)
- **ClientZone WAPP**: Client-facing scheduling UI
- **Banker API**: Operations scheduling UI
- **Autofile SVC** (`autofile-common:3.0.3` referenced in jobservice): automated scheduling triggered by file upload
- **Workflow Service** (`workflowmanager-svc:3.0.5`): calls `scheduleJob` as a workflow step after job authorization

### Outbound (services this service calls)
- **JobManager** (`JobManagerDelegate.resumeBlackoutJob()`, `pauseJob()`): via xPlatform XML-RPC — the actual job execution orchestrator
- **Scheduler Service** (`SchedulerServiceProxy`): underlying timer infrastructure
- **cbaseapp DB**: user/member identity lookup

### Implicit Dependencies
- **Director Service**: Connection string provisioning at startup — if Director is unavailable, the scheduler service cannot start
- **jobsvc SQL Server DB**: primary state store — unavailability means no scheduling operations can complete

## Compliance Architecture Positioning

The scheduler is a **PCI DSS Requirement 6 and 10 in-scope component** as it:
- Controls when CDE batch processing occurs (Req. 6.3: secure development practices for systems in the CDE)
- Generates audit logs of all scheduling actions (Req. 10.2: audit log events)
- Enforces processing blackouts during maintenance windows (Req. 12.3: targeted risk analysis)

The blackout capability is also directly relevant to **NACHA same-day ACH rules** — missing an ACH origination window results in next-day settlement, which has contractual and regulatory implications for Onbe's ODFI (Originating Depository Financial Institution) obligations.

## Technology Stack Assessment

| Layer | Technology | Version | Status |
|---|---|---|---|
| Runtime | Java | 21 | Current |
| Web container | Apache Tomcat | (not version-pinned in this repo) | Current |
| DI / IoC | Spring (XML) | 5.x (via parent) | Legacy XML wiring |
| Logging | SLF4J + Lombok @Slf4j | Current | |
| DB access | Spring JDBC StoredProcedure | Current | |
| RPC protocol | xPlatform XML-RPC | Platform-specific | **High migration complexity** |
| Service discovery | Director (proprietary) | Platform-specific | **Vendor lock-in** |
| Scheduling engine | Scheduler Service (proprietary) | Platform-specific | **High migration complexity** |

## Migration Complexity Assessment

**Overall: VERY HIGH**

1. The `SchedulerServiceProxy` is the most complex migration target — it abstracts an entire proprietary timer/callback infrastructure. Replacing it with Quartz, Spring Scheduler, or a cloud-managed scheduler (Azure Scheduler/AWS EventBridge) requires a complete re-architecture of how callbacks are received.
2. The XML-RPC protocol used to call `JobManager` needs to be replaced with REST throughout.
3. The blackout calculation logic in `BlackoutManagerImpl` (800+ lines) is non-trivial business logic that must be preserved with full test coverage before migration.
4. The Director service dependency means the application cannot be tested outside the Onbe data centre network without mocking.

## Single Point of Failure Risk

Given that **every client batch job** flows through this service, an outage of the Job Scheduler means:
- No new batch jobs can be scheduled
- Jobs already "authorized" are stuck in authorized state
- Blackout windows cannot start/end, leaving jobs either permanently paused or unable to be paused
- No priority adjustments can be made during an SLA incident

A disaster recovery runbook is referenced in `doc/Job Order Synchronizer runbook.docx` (in the related `job-order-synchronization_LIB` repo), but no equivalent runbook was observed for the scheduler itself. This is a gap.
