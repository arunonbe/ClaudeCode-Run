# DevOps and Operations View — mailgun-event-tracker

## Build System

`mailgun-event-tracker` is a Spring Boot 3.3.4 Maven project:

- **Java version**: 21
- **Spring Boot parent**: `3.3.4`
- **Packaging**: JAR
- **Group ID**: `com.onbe.batch`
- **Artifact ID**: `mailgun-event-tracker`
- **Version**: `0.0.1-SNAPSHOT`
- **Maven Wrapper**: bundled (`.mvn/wrapper/maven-wrapper.properties`)

Key dependencies:
| Dependency | Version | Purpose |
|---|---|---|
| `spring-boot-starter-batch` | Via BOM | Spring Batch framework |
| `spring-boot-starter-web` | Via BOM | Embedded web container |
| `spring-boot-starter-data-jpa` | Via BOM | JPA (used indirectly) |
| `mailgun-java` | 1.1.3 | Mailgun API client |
| `mssql-jdbc` | 12.8.1.jre11 | SQL Server JDBC |
| `com.ecount:xPlatform` | 7.0.11-SNAPSHOT | Onbe platform library |
| `gson` | 2.11.0 | JSON parsing |
| `joda-time` | 2.12.5 | Date/time (redundant with Java 8+ time API) |
| `lombok` | Via BOM | Code generation |

The `xPlatform:7.0.11-SNAPSHOT` dependency is a SNAPSHOT — this is a moving target that will pull the latest snapshot build at compile time, creating non-reproducible builds. Snapshots should not be used in production-bound services.

Build command:
```sh
./mvnw clean package
```

## CI/CD Pipeline

GitHub Actions CodeQL workflow (`.github/workflows/codeql.yml`) is present for code scanning. No deployment workflow is visible — there is no Dockerfile, no Kubernetes manifests, and no GitLab CI pipeline. Deployment is likely manual or managed via the broader Onbe CI system with separate deployment automation.

## Deployment Model

The service appears to be deployed as a standalone Spring Boot JAR, scheduled externally (via Windows Task Scheduler, cron, or a job scheduler service). Evidence:
- `server.port=8081` in `application.properties` — the embedded Tomcat server port (likely for actuator)
- Log file path `D:/c-base/logs/mailgun/mailgun-event-tracker.log` — Windows filesystem
- Hikari pool configuration — persistent long-running process, not a function-as-a-service
- No Dockerfile or container manifests

## Environment Configuration

Multiple Spring profiles exist:
| Profile | File | Key Differences |
|---|---|---|
| Default | `application.properties` | Dev DB URL, hardcoded API key |
| dev | `application-dev.properties` | Same DB URL, same API key |
| qa | `application-qa.properties` | (not read — content not examined) |
| staging | `application-staging.properties` | (not read) |
| prod | `application-prod.properties` | (not read) |

**Critical security finding**: The base `application.properties` and `application-dev.properties` both contain the Mailgun API key and database credentials in plaintext. Even if `application-prod.properties` uses environment variable substitution, the dev/test credentials are exposed in source control.

## Operational Scheduling

Spring Batch with `allowStartIfComplete(true)` suggests the job is designed to run repeatedly. The job name is `returnEmailReaderJob`. There is no `@Scheduled` annotation or Spring Batch scheduler configuration visible — the job likely runs once at application startup (Spring Batch default) and then the process exits or stays up waiting for the next scheduled invocation via an external scheduler.

Chunk size: 3 records per transaction. Fetch size: 10 per JDBC cursor fetch. Max rows: 0 (unlimited).

## Monitoring and Observability

- **Log file**: `D:/c-base/logs/mailgun/mailgun-event-tracker.log`
- **Log level**: INFO throughout the processor and writer
- **No actuator health endpoints visible** in application.properties (server.port=8081 present but no actuator configuration)
- **No metrics**: No Micrometer / Prometheus configuration
- **No distributed tracing**: No correlation ID or trace context

### Logging Quality Issues

The processor logs raw field values at INFO level (`EmailItemProcessor.java` lines 72–74):
```java
log.info("email.getNotificationId() --> " + email.getNotificationId());
log.info("email.getMessageSubscriberId() --> " + email.getMessageSubscriberId());
log.info("email.getMessageId() --> " + email.getMessageId());
```

And at line 89:
```java
log.info("EmailItemProcessor::processEmailStatus() - EventsResponse : " + response.toString());
```

These `INFO` log statements expose `notificationId`, `messageSubscriberId`, and the full Mailgun events response (which may include email addresses, SMTP messages with recipient details) to the log file. This is a PII logging violation under GDPR/CCPA and should use DEBUG level with sanitisation.

Also, string concatenation in log statements (`log.info("..." + variable)`) is an anti-pattern with SLF4J — use parameterised logging: `log.info("...: {}", variable)`.

## Security Configuration Issues

1. **Mailgun API key in source** (`application.properties` line 18) — critical; must use environment variable or secret manager.
2. **DB credentials in source** (lines 5–6) — must use environment variable injection.
3. **`trustServerCertificate=true`** in JDBC URL — disables TLS certificate validation for the SQL Server connection. This should use a properly configured trust store instead.
4. **No TLS configuration** for the embedded Tomcat server.

## Recommended Operational Improvements

1. Rotate Mailgun API key immediately; inject via `${MAILGUN_API_KEY}` environment variable.
2. Replace hardcoded DB credentials with environment variable placeholders.
3. Change `trustServerCertificate=true` to a proper certificate trust store.
4. Add Spring Batch job execution monitoring (Spring Batch Admin or Actuator batch endpoints).
5. Implement a `status` column in `mailgun_events_queue` with states: PENDING, PROCESSING, COMPLETED, FAILED.
6. Add retry logic for transient Mailgun API failures (currently the entire chunk fails and is logged as an exception).
7. Remove debug-level PII logging from `EmailItemProcessor`.
8. Replace SNAPSHOT dependency `xPlatform:7.0.11-SNAPSHOT` with a stable release version.
