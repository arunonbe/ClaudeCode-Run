# Business Analyst View — job-scheduler_SVC

## Repository Identity

- **Artifact**: `com.ecount.service.jobscheduler:jobscheduler` v3.0.1-SNAPSHOT
- **Parent POM**: `com.parents:prepaid-parent:6.0.12`
- **Modules**: `jobscheduler-common`, `jobscheduler-impl`, `jobscheduler-service`
- **Deployment**: WAR deployed to Apache Tomcat (`jobscheduler-service.war`)
- **Java**: 21 (compiler source/target in `pom.xml` lines 20–21)

## Business Purpose

The Job Scheduler Service is the **centralized scheduling authority** for all batch jobs processed across the Onbe payment platform. It answers two fundamental business questions:
1. "When should a client's batch job run?" (schedule management)
2. "Is this job currently blocked from running?" (blackout management)

Every client-submitted batch file that requires future execution (disbursement runs, card issuance batches, fee collection jobs, ACH origination files) passes through this service to be placed on a schedule, monitored for execution status, and either executed immediately or queued for a future time.

## Jobs Scheduled and Their Business Significance

The scheduler does not define the specific jobs itself — it provides the **scheduling infrastructure** that other services use. Based on the XML-RPC interface exposed (`/services/JobSchedulerWebServices`), the following job lifecycle events are managed:

### Schedule Modes (from `JobSchedulerServiceImpl.java` lines 198–234)

| Mode | Business Meaning |
|---|---|
| `IMMEDIATE_MODE` | Job is authorized and should execute as soon as possible (pending blackout check) |
| `SCHEDULE_MODE` | Job is authorized for a specific future date/time (client-scheduled batch runs) |
| `NOSCHEDULE_MODE` | Job is authorized but has no scheduler dependency — goes directly to "Ready to Run" |

### Blackout Management — Critical Business Function

The blackout system (`BlackoutManagerImpl.java`) is one of the most significant business controls in the platform. A **blackout** is a configured maintenance or settlement window during which certain batch jobs are suspended to prevent processing during:
- End-of-day settlement windows
- Network maintenance periods
- Banking cutoff times (e.g., ACH same-day origination deadlines)
- Regulatory quiet periods

Blackout types (from `BlackoutManagerImpl.java` lines 1009–1017):
- `BLACKOUT_TYPE_ALL` — suspends all jobs
- `BLACKOUT_TYPE_LIVE` — suspends only live (non-flexible) jobs
- `BLACKOUT_TYPE_BATCH` — suspends only batch/flexible jobs

Blackout frequencies:
- `DAILY` — recurring every day at configured times
- `WEEKLY` — recurring on configured days of the week
- `DATE` — one-time on a specific date
- `ADHOC` — immediate ad-hoc blackout (manual override)

### Priority Management

Introduced in "53E File Automation Phase I" (documented in `JobSchedulerServiceImpl.java` comments), the `updatePriority()` method allows operations teams to re-order jobs in the scheduling queue. This is critical during high-volume processing days (e.g., payroll disbursement deadlines) when certain clients' jobs need to be elevated.

### Schedule Lifecycle Operations

From `JobSchedulerService` interface and `JobSchedulerServiceImpl`:

| Operation | Business Trigger |
|---|---|
| `scheduleJob()` | Client authorizes a job and a schedule exists |
| `removeSchedule()` | Client or operations cancels a scheduled job |
| `reapplySchedule()` | Schedule time has passed; recalculate next occurrence |
| `unAuthorizeSchedule()` | Client retracts authorization before execution |
| `insertSchedule()` | New program-level schedule defined (first time setup) |
| `updateSchedule()` | Program schedule modified by client or operations |
| `updateFileSchedule()` | Per-file schedule override — individual job gets different schedule from program default |
| `overrideBlackout()` | Operations manually forces a job through despite active blackout |
| `checkBlackout()` | Pre-flight check before executing any job |

## Business Significance to Onbe Operations

The job-scheduler is the **single point of control** for:
1. **ACH origination timing**: ACH files must reach the Federal Reserve by specific cutoff times. The scheduler enforces these deadlines by blocking late jobs (blackout) and prioritizing time-critical ones.
2. **Card issuance batch windows**: Card embossers and fulfillment partners have physical processing windows. The scheduler aligns job execution with these external SLAs.
3. **Fee collection timing**: Program-level fee jobs must run on configured cycle dates to ensure correct billing.
4. **Regulatory quiet periods**: Some programs have UDAAP or state-mandated processing restrictions that are implemented as blackout windows.

## Client-Facing Features

Program managers and clients interact with scheduling through the ClientZone UI or the Banker application, which call this service's XML-RPC API. Key client-visible features:
- View the Active Job List (AJL) — all jobs currently in the scheduling system
- Override execution time for a specific file submission
- Request immediate execution vs. next scheduled window
- View schedule history

## Audit and Compliance

Every scheduling action is logged to the `sch_job_actions_log` table via `StoredProcInsertJobActionsLog`. Every blackout event is logged to `blackout_actions_log` via `InsertBlackoutActionsLog`. These logs provide the audit trail required under:
- PCI DSS Requirement 10: Audit logging of all access to payment system components
- SOC 1 controls for timely processing of disbursements
- NACHA Rule 2.3.1: Originating Depository Financial Institution must retain records of ACH entries for a minimum period
