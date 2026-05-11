# DevOps / Operations View — job-order-synchronization_LIB

## Build System

- **Build tool**: Maven, wrapper provided (`mvnw`, `mvnw.cmd`)
- **Maven settings**: `.mvn/wrapper/settings.xml` (points to internal Nexus/GitHub Packages)
- **Packaging**: `maven-assembly-plugin` produces `job-order-synchronization-jar-with-dependencies.jar` at `package` phase. Main class: `com.ecount.service.jobordersync.Main`
- **Java target**: Java 8 (source/target not explicitly set in this POM; parent `service-parent:8` governs)
- **CI**: GitHub Actions workflow defined in `.github/workflows/codeql.yml` (CodeQL SAST scan only). No deployment pipeline exists in this repo — deployment is handled by the consumer (typically job-scheduler_SVC or a cron configuration)
- **Dependency scanning**: `.github/dependabot.yml` present — automated dependency PRs

## Deployment Model

This is a library/executable JAR, not a continuously-running service. It is invoked as a one-shot process by:
1. A cron job on an application server (historically Windows Task Scheduler on `d-na-app*` hosts)
2. The director/scheduler infrastructure calling it as a scheduled task

The JAR is typically placed in a shared directory such as `D:\c-base\opt\...` and invoked with a wrapper script. No Docker/container deployment artifacts exist in this repo.

## Configuration

Runtime configuration is supplied via:
- `service.default.properties` (`src/main/resources/com/ecount/service/jobordersync/`) — Spring property placeholder values including `agent`, `director.address`, `fromDate`, `toDate`, `maxTotalCount`, `maxCreateCount`, `maxUpdateCount`, `maxFailedCount`, `maxAttemptCount`, `dryRun`, `ignoreFailedEvents`, `forceStatus`, `ignoreOrderService`, `toDateOffset`, and HTTP timeout values for the Order Service client
- `dataSource.xml` — JDBC data source configuration (director-driven connection pooling)
- `log4j.properties` — logging configuration

## Monitoring and Alerting

There is **no built-in monitoring endpoint** (no HTTP health check, no metrics export). Operational visibility relies entirely on:

1. **Log output**: `log4j.properties` configures file-based logging. The synchronizer logs INFO/WARN/ERROR messages through Apache Commons Logging backed by Log4j. Key log messages include:
   - `SYNCHRONIZING_FOUND_JOBS` — number of jobs in window
   - `SYNCHRONIZING_SUMMARY` — total/create/update/fail counts at end of run
   - `SYNCHRONIZING_FAILED` — per-job failure with exception details
   - `WARNING_ORDER_NOT_AVAILABLE` — Order Service ping failure (triggers `System.exit(3)`)

2. **Exit codes**: The `Main` class (not fully read but implied by `synchronize()` return boolean) exits non-zero on failure, allowing shell-level alerting.

3. **`job_order_sync_event` table**: The database row written at the end of each run provides a persistent audit trail. Operations can query `fail_count > 0` to detect degraded runs.

## Failure Modes and Recovery

| Failure Mode | Behavior | Recovery |
|---|---|---|
| Order Service unavailable at ping | `System.exit(3)` immediately | Rerun after Order Service recovery; failed event recorded for next retry run |
| Order Service timeout mid-run | `JobOrderSyncException` thrown; `ignoreOrderService=false` propagates exception | Rerun; failed events recorded; `--ignoreOrderService=true` can suppress ping |
| Single-job Order API failure | Increments `fail_count`; continues to next job | Failed events retried on next run automatically |
| `forceStatus` write failure | Logged as error; fail_count incremented | Manual DB investigation required |
| Concurrent duplicate run | No locking mechanism — both instances would process the same jobs | Operational procedure required to prevent duplicate scheduling |

## Retry Policy

Automatic retry of previously failed sync events occurs at the **start of every run**. The retry window is controlled by `maxAttemptCount`: any `job_order_sync_event` row whose `attempt_count < maxAttemptCount` and `fail_count > 0` will be re-processed. There is no exponential back-off. There is no dead-letter mechanism — records that exceed `maxAttemptCount` are simply skipped.

## Dead-Letter / Escalation

There is no dead-letter queue. Failed sync events that exceed the attempt threshold are silently skipped. The only escalation path is:
1. A monitoring query on `job_order_sync_event` detecting persistent `fail_count > 0`
2. Manual intervention using `--forceStatus --jobId=<id>` to force a single job update

This represents a **significant operational gap** for a payments reconciliation process. A PCI DSS-aware operations team should add alerting on `fail_count > 0` and a maximum tolerated age for unsynced events.

## Release Management

- No `Dockerfile` or container build in this repo
- Git tags are managed via `maven-release-plugin` (version 3.0.0-M1)
- Source is published alongside binary via `maven-source-plugin`
- SCM connection points to GitLab: `gitlab.com/northlane/development/application-development/libraries/job-order-synchronization.git` (`pom.xml` lines 16–22)
