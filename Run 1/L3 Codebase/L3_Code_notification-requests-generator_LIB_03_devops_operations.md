# DevOps and Operations Analysis — notification-requests-generator_LIB

## Repository Structure

```
notification-requests-generator_LIB/
├── pom.xml                                          — Maven build (Spring Batch, JDBC)
├── notificationRequests.bat                         — Execution script (Windows)
├── autobuild-NotificationRequestsbatch.bat          — Build automation script
├── releases/
│   ├── notification-requests-1.0-SNAPSHOT.jar       — Dev snapshot JAR
│   ├── notification-requests-1.0.jar                — Release JAR
│   ├── NotificationRequestGeneratorBatchJob.bat      — Production execution script
│   └── NotificationRequestGeneratorBatchJob.vbs     — Windows VBScript wrapper
├── src/main/java/...                                — Java source
├── src/main/resources/
│   ├── log4j.properties                             — Logging configuration
│   ├── notificationRequests.xml                     — Spring context
│   ├── dataSourceContext.xml                        — JDBC data source
│   ├── job/generateNotificationRequestsBatchJob.xml — Spring Batch job definition
│   └── job/context/                                 — Spring context files
└── .github/
    ├── dependabot.yml
    └── workflows/codeql.yml
```

## CI/CD Pipeline

Only a **CodeQL security scan** is configured (`.github/workflows/codeql.yml`). There is **no deployment pipeline**. The library is built and deployed manually.

The `autobuild-NotificationRequestsbatch.bat` and `notificationRequests.bat` files indicate the build and deployment process is Windows batch-script-based — engineers run these scripts locally to build and deploy.

**Build artifact management:** Pre-built JARs are committed to the `releases/` directory in the repository. This is an anti-pattern: binary artifacts in version control create repository bloat, and the committed JARs may diverge from source without clear traceability. Onbe should use an artifact repository (Nexus, GitHub Packages, Artifactory) to manage released JARs.

## Execution Model

The batch job is invoked via command-line with arguments:
```
java -jar notification-requests-1.0.jar <context-xml> <job-name> [parameters]
```

Parameters are passed as semicolon-delimited key=value pairs:
```
processing_date=2026-05-07 10:00;minutes=60;rechecking_minutes=30
```

**Execution wrapper (`NotificationRequestGeneratorBatchJob.vbs`):** The VBScript wrapper (`releases/`) suppresses the command-line window on Windows, making the batch run silently in the background. This is appropriate for scheduled tasks but makes it harder to observe runtime output without checking log files.

## Scheduling

The library is designed to be invoked by an external scheduler. Based on the Windows deployment artifacts, this is likely:
- **Windows Task Scheduler** — simple, built-in
- **Control-M or similar enterprise scheduler** — typical in banking/payments environments

The exit code mapper (`ExitCodeMapperImpl`) provides standard Spring Batch exit codes for scheduler integration:
- `COMPLETED` → exit code 0
- `FAILED` → non-zero
- Other Spring Batch statuses → mapped accordingly

## Logging Configuration (`log4j.properties`)

Three log appenders are configured:
1. **stdout** (Console): INFO threshold, pattern: `NRG: %d [%t] %-5p %c - %m%n`
2. **FILE** (Rolling file): INFO threshold, `d:/c-base/logs/batch/notificationRequests.log`, max 10 MB, 100 backup files (max 1 GB total)
3. **SYSLOG**: INFO threshold, remote syslog at `10.1.1.130` (LOCAL0 facility), **no TLS/encryption**

**Log rotation:** 100 backup files × 10 MB = 1 GB maximum log storage. No automatic deletion of old logs is configured — the `MaxBackupIndex = 100` means Log4j will overwrite the oldest backup after 100 rotations, providing approximately 100 × (however long it takes to fill 10 MB) of log history.

**Syslog concern:** Syslog appender transmits log entries (including PII) to `10.1.1.130` using the default unencrypted syslog protocol. This IP should be identified: if it is a central log aggregation server (e.g., Splunk, SIEM), then PII is traversing the network in plaintext.

## Operational Runbook (Inferred)

1. Schedule the VBS/BAT file via Windows Task Scheduler with appropriate processing date parameters.
2. Monitor job completion via exit code (0 = success, non-zero = failure).
3. Review `d:/c-base/logs/batch/notificationRequests.log` for run details.
4. For failures: check Spring Batch job repository (database) for failed step details.
5. For reprocessing: adjust `processingDate` parameter and re-run.

## Missing Operational Controls

| Control | Status |
|---|---|
| Automated deployment pipeline | Missing — manual batch scripts only |
| Artifact repository integration | Missing — JARs committed to repo |
| Structured/JSON logging | Missing — pattern-based log format |
| Metrics/monitoring (Prometheus, CloudWatch) | Missing |
| Alerting on job failure | Not visible (depends on external scheduler) |
| Log encryption at rest | Not configured |
| Encrypted syslog transport | Not configured |
| Database credential management | Not visible (in `dataSourceContext.xml`) |

## Dependency Currency

The library's key dependencies are not visible in `pom.xml` directly (it references a parent POM `prepaid-parent:6.0.13`). Based on the code, Spring Batch and Spring JDBC are the key frameworks. The use of `ClassPathXmlApplicationContext` and `Log4j 1.x` (`log4j.rootLogger` syntax) indicates the codebase uses legacy Spring XML configuration and Log4j 1.x (end-of-life). Log4j 1.x has known security vulnerabilities and should be migrated to Log4j 2.x or SLF4J/Logback.
