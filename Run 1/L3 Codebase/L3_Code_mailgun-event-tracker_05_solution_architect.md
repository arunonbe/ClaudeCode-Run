# Solution Architect View — mailgun-event-tracker

## Solution Design

`mailgun-event-tracker` implements a classic Spring Batch ETL pipeline with three components: a JDBC cursor reader, a REST API processor, and a stored procedure writer. The solution processes untracked email notifications from a queue table, enriches them with delivery status from the Mailgun Events API, and writes results back to the database.

## Component Design Analysis

### Reader (`JdbcCursorItemReader<Email>`)

Configured in `BatchConfiguration.java` (lines 33–42):
```java
reader.setSql("select notification_id, message_subscriber_id, message_id " +
              "from mailgun_events_queue where last_job_run is null");
reader.setMaxRows(0);  // unlimited
reader.setFetchSize(10);
reader.setQueryTimeout(10000);  // 10 seconds
```

**Design risks:**
1. `setMaxRows(0)` — unlimited. If the queue has millions of unprocessed rows (e.g., after a long outage), a single run will attempt to process them all. This could cause: OOM (cursor open for full result set), Mailgun rate-limiting, extended transaction locks on the queue table.
2. No pagination or upper bound on single-run processing. Recommend: `reader.setMaxRows(1000)` with multiple scheduled runs.
3. The `JdbcCursorItemReader` holds a JDBC cursor open for the duration of the job. Long-running jobs risk cursor timeout or connection expiry.

### Processor (`EmailItemProcessor`)

The processor is stateless (implements `ItemProcessor<Email, Email>`). Key design issues:

**Issue 1 — Null return on ACCEPTED-only events** (`EmailItemProcessor.java` lines 91–128):
```java
MailgunEventQueue mailgunEventQueue = null;
for(EventItem eventItem : response.getItems()) {
    if(!eventItem.getEvent().equalsIgnoreCase(MailgunEvent.ACCEPTED.getEventTypeName())) {
        mailgunEventQueue = new MailgunEventQueue();
        // ... populate
    }
}
return mailgunEventQueue;  // may be null
```
When `mailgunEventQueue` is null, the writer calls `email.getMailgunEventQueue().toString()` → NPE. The try/catch swallows this, logs an exception, and the record's `last_job_run` remains NULL — leading to infinite retry loops.

**Fix**: In `ItemProcessor`, return `null` to signal Spring Batch to skip the item (Spring Batch contract: returning null from `process()` causes the item to be skipped by the writer). Update the processor to return null explicitly when no non-ACCEPTED event is found:
```java
if (mailgunEventQueue == null) {
    return null;  // skips writer for this item
}
email.setMailgunEventQueue(mailgunEventQueue);
return email;
```

**Issue 2 — Last event wins, history lost**:
The inner `mailgunEventQueue` variable is overwritten on each iteration. Only the final event in `response.getItems()` is persisted. If Mailgun returns events in historical order (oldest first), the final event is the most recent — this may be correct. However, it is implicit behaviour that is not documented and could silently drop meaningful intermediate events (e.g., FAILED followed by DELIVERED on retry).

**Issue 3 — Blocking HTTP call per item**:
Each `Email` item triggers a synchronous `MailgunEventsApi.getEvents()` call. With chunks of 3 and a batch that could process thousands of items, this serialises all Mailgun API calls. A parallel step configuration or batch API call would improve throughput.

**Issue 4 — Timestamp format bug** (`EmailItemProcessor.java` line 84):
```java
String dateTimeFormat = "${date.time.format}";  // from application.properties
```
`application.properties` line 20: `date.time.format=yyyy-MM-dd HH:mm:ss:ms`
The `ms` is not a valid `DateTimeFormatter` pattern symbol. The correct symbol for milliseconds is `SSS`. This will either cause a `DateTimeParseException` at runtime or produce incorrect output (the literal characters `m` and `s` may be interpreted differently). This is a latent bug.

**Issue 5 — String concatenation in logger calls**:
```java
log.info("email.getNotificationId() --> " + email.getNotificationId());
```
This forces string construction even when the log level is above INFO. Should use parameterised logging: `log.info("email.getNotificationId() --> {}", email.getNotificationId())`.

### Writer (`EmailItemWriter`)

The writer delegates to `MailgunEventsQueueUpdateSP` (from the `xPlatform` library), which executes a stored procedure to update the `mailgun_events_queue` record.

The writer calls `processEmailStatus(email)` which calls:
```java
log.info("Updating DB, MailgunEventQueue :" + email.getMailgunEventQueue().toString());
```
This NPE path (for null `mailgunEventQueue`) is the second crash point. The `try/catch Exception` at line 62 handles it, but a better solution is for the processor to return `null` to skip the item entirely.

## Security Architecture

### API Key Injection

`@Value("${mailgun.api.key}")` injects the API key from `application.properties`. The key is used directly:
```java
MailgunEventsApi mailgunEventsApi = MailgunClient.config(apiKey)
        .createApi(MailgunEventsApi.class);
```
A new `MailgunClient` is created **per processed email** (line 76). This is inefficient — the client should be a Spring bean injected once per application context, not instantiated per-item. Beyond performance, creating a new client per-item means the API key is re-read and a new HTTP client initialised for every record.

### Credential Management

All credentials must be moved to environment variables or a secret manager:
```yaml
# application.yml (replace application.properties)
mailgun:
  api:
    key: ${MAILGUN_API_KEY}
  domain:
    name: ${MAILGUN_DOMAIN}
spring:
  datasource:
    username: ${NOTIFICATIONSVC_DB_USER}
    password: ${NOTIFICATIONSVC_DB_PASSWORD}
```

### TLS Trust Configuration

`trustServerCertificate=true` in the JDBC URL disables SQL Server certificate validation. This enables man-in-the-middle attacks on the database connection. The correct approach:
```
trustServerCertificate=false;encrypt=true;trustStore=/path/to/truststore;trustStorePassword=...
```

## Solution Gaps Summary

| Gap | Severity | Fix |
|---|---|---|
| API key committed to source | Critical | Rotate key; use environment variable |
| DB credentials in source | Critical | Use environment variable injection |
| NPE on null MailgunEventQueue | High | Return null from processor to skip |
| Unlimited batch size | High | Add max rows limit |
| Blocking per-item HTTP calls | Medium | Batch or parallelise Mailgun calls |
| New MailgunClient per item | Medium | Inject as Spring bean |
| Timestamp format bug `ms` | Medium | Fix to `SSS` |
| PII logged at INFO level | Medium | Move to DEBUG, add sanitisation |
| trustServerCertificate=true | Medium | Use proper trust store |
| String concat in log calls | Low | Use SLF4J parameterised logging |
| joda-time redundant | Low | Replace with java.time |
| xPlatform SNAPSHOT version | Medium | Pin to stable release |
