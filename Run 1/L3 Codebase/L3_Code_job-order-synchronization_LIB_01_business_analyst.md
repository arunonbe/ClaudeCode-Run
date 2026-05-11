# Business Analyst View — job-order-synchronization_LIB

## Repository Identity

- **Artifact**: `com.citi.prepaid.service.client:job-order-synchronization` v2.0.3-SNAPSHOT
- **Packaging**: Executable JAR with dependencies (`jar-with-dependencies`), entry point `com.ecount.service.jobordersync.Main`
- **Parent POM**: `com.citi.prepaid.service:service-parent:8`
- **Description** (from `pom.xml` line 16): _"The batch process that would attempt to synchronize jobs with the file-orders"_

## Business Purpose

This library implements a **standalone batch reconciliation process** that bridges the internal Job Service state machine with the external Order Service. Its core business problem is data consistency: a client submits a file (e.g., a card-issuance batch), the Job Service processes it in stages (`LOADING → PROCESSING → ARCHIVED`), and a parallel Order Service record tracks the commercial lifecycle (`LOADING → PROCESSING → PROCESSED`). Network timeouts, partial failures, or race conditions can cause these two systems to drift out of sync. This tool re-aligns them.

## Business Operations Performed

### 1. Order Creation (Create Path)
When a `job_file` record exists in the Job database but no corresponding `file_order` record exists in the Order Service, the synchronizer creates the missing order. This handles cases where the initial order-creation call failed silently during original job submission. Source: `JobOrderSynchronizer.java` lines 264–291, method `createOrder()`.

### 2. Order Status Synchronization (Update Path)
When an order record exists but its status does not match the mapped expectation derived from the Job's current status, the synchronizer calls the Order Service to update it. The full status mapping is defined in `applicationContext.xml` lines 22–40:

| Job Status | Mapped Order Status |
|---|---|
| UNINITIALIZED / LOADING | LOADING |
| FAILED_CONTENT_VALIDATION | LOADING_FAILED_CONTENT |
| READY_TO_RUN | PENDING_PROCESSING |
| PROCESSING / STOPPING / STOPPED | PROCESSING |
| GENERATING_REPORTS | PROCESSING |
| LOADED_PENDING_FINANCE | PENDING_FINANCE_AUTHORIZATION |
| PENDING_FUNDS | PENDING_FUNDS |
| ARCHIVED (no errors) | PROCESSED |
| ARCHIVED (with errors) | PENDING_CORRECTION |
| CANCELED_BY_USER / CANCELED_BY_ADMIN | CANCELLED |

### 3. Failed-Event Retry
On each run the synchronizer first reads all previously failed sync events (via `jobDao.getFailedJobOrderSyncEvents(maxAttemptCount)`) and attempts to re-process them before moving on to the current window. This provides an automatic retry mechanism for transient Order Service outages. Source: `JobOrderSynchronizer.java` lines 99–117.

### 4. Force-Status Mode (Operational Override)
A `--forceStatus` command-line flag allows operations teams to forcibly push an order status directly via a database write when the Order Service API call fails. This is an emergency procedure used when the Order Service is unavailable but jobs have finished. Source: `JobOrderSynchronizer.java` lines 399–472, method `forceUpdateOrderStatus()`.

### 5. Dry-Run Mode
A `--dryRun` flag allows the process to simulate what would happen without making any changes. Used for pre-run validation in non-production environments. Source: `JobOrderSynchronizer.java` lines 488–495.

## Business Significance in the Payments Context

The Order Service is the commercial record used for billing, reporting, and client invoicing. If the Order status does not reach `PROCESSED`, client reporting dashboards will show incorrect job states, fee calculations may be skipped, and reconciliation audits will flag discrepancies. Because Onbe operates as a PCI DSS Level 1 service provider, accurate audit trails of disbursement batches are a compliance requirement. This synchronizer is therefore a **financial integrity control**, not merely a housekeeping utility.

## Execution Model

The library runs as a command-line process invoked by an external scheduler (the job-scheduler_SVC or a cron job on the application server). Arguments are passed via command line and Spring property placeholders in `service.default.properties`. The run window is defined by `--fromDate` and `--toDate` parameters; if `--fromDate` is omitted, the process looks up the `to_date` of the most recent successful sync event from the `job_order_sync_event` table to use as its start point.

## Operational Guardrails

To prevent runaway processing, the following per-run limits are configurable:
- `maxTotalCount` — maximum jobs to examine per run
- `maxCreateCount` — maximum new orders to create
- `maxUpdateCount` — maximum orders to update
- `maxFailedCount` — maximum tolerated failures before aborting
- `maxAttemptCount` — maximum prior failed events to retry

These are defined as Spring-injected properties in `applicationContext.xml` lines 45–57.

## Key Business Risk

If this job does not run or fails silently, Order Service records can permanently diverge from Job Service state. In a disbursement-heavy batch day (e.g., ACH payroll run or prepaid card issuance), hundreds of thousands of records could be left in a `PENDING_PROCESSING` state, triggering false-failure alerts, blocking billing, and generating compliance findings under SOC 1 audit scope.
