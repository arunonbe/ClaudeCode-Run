# 05 Solution Architect — reminder-notification_LIB

## Technical Architecture
Spring Batch 2.1.1 fat-JAR batch application. Entry point is `ReminderNotification.main()`, which bootstraps a `ClassPathXmlApplicationContext` from a caller-supplied XML path and launches the named job via `JobLauncher`. The job is a two-step chunk-oriented pipeline: (1) count step, (2) member-detail processing step.

Key classes:
- `ReminderNotification` — main entry, properties loader, job launcher
- `YetToEnrollMemberDetailsRowMapper` / `PreparedStatementSetter` — JDBC read
- `MemberDetailsItemWriter` — delegates to `NotificationEventHandler`
- `YetToEnrollMemberNotificationHandlerImpl` + `ServiceHelperImpl` — notification orchestration
- `StoredProcUpdateReminderNotificationHistory` — history write-back
- `JobListener`, `MembersCountSavingListener`, `ProcessedTransactionCountSavingListener` — Spring Batch listeners

## API Surface
No HTTP/REST/RPC API. Interface is purely the command-line invocation:
```
java -jar reminder-notification-1.0.jar <contextXml> <jobBeanName> <purpose> [processingDate=MM/dd/yyyy]
```
Internal programmatic interface: `InstIssueCZSetupScreenCfgManager` (screen-configs integration, separate library). Notification dispatch via xPlatform's `NotificationEventHandler` abstraction.

## Security Posture
- No authentication or authorisation on the batch process itself; security relies entirely on OS-level file and user-account controls
- PII (cardholder name, email address) processed in-memory; no field-level encryption
- Database credentials managed by Director service (no hard-coded credentials in source)
- Log4j 1.x logging: no sensitive data masking enforced; cardholder details could appear in log output — PII/GLBA risk
- Java 6 TLS: limited to TLS 1.0/1.1 by default; TLS 1.2 requires explicit configuration; TLS 1.3 not supported
- No code signing on the fat JAR

## Technical Debt
| Item | Severity |
|---|---|
| Java 6 compile target and runtime | Critical |
| Spring 2.5.6 + Spring Batch 2.1.1 (EOL) | Critical |
| Log4j 1.x (EOL) | High |
| sqljdbc 1.1 (ancient, limited TLS) | High |
| Properties file path hard-coded in constants | Medium |
| No retry/skip policy in batch steps | Medium |
| XML-only Spring configuration (no annotations/Boot) | Medium |
| Raw unchecked generics warnings throughout | Low |
| Duplicate log statements in `ReminderNotification.main()` (lines 117–122) | Low |

## Gen-3 Migration
Recommended migration path:
1. Re-implement as a Spring Boot 3.x / Spring Batch 5.x batch job
2. Replace Director DB connections with Azure Key Vault-sourced JDBC credentials
3. Replace xPlatform email with Azure Communication Services or approved email gateway
4. Containerise and deploy to AKS with a CronJob trigger
5. Export batch execution metrics to Azure Monitor / Application Insights
6. Store notification history in a purpose-built table with a defined retention/purge policy

## Code-Level Risks
- `properties.load(new FileInputStream(...))` without null-check on the file path: if `ReminderNotificationConstants.propFileName` resolves to null, a `NullPointerException` will swallow the error and leave `properties` empty, silently disabling thread-pool configuration
- `jobExecution` is used after the try/catch block without a null-check; if all four launch exceptions are thrown, `jobExecution` remains null and line 117 throws a `NullPointerException`
- `ClassPathXmlApplicationContext` is never closed, leaving DB connection pools open until JVM exit
- Thread-count grid (`member_details_gridsize`) is read from properties but the threading mechanism is in the Spring Batch step XML (not visible in code); a misconfiguration could cause unbounded parallelism
