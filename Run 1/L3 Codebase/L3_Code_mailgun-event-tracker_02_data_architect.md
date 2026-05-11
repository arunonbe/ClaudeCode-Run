# Data Architect View — mailgun-event-tracker

## Overview

`mailgun-event-tracker` operates on two data stores: the `NotificationSvc` SQL Server database (source queue and result store) and the Mailgun Events API (external event data source). Understanding the data schema, data flows, transformation logic, and data quality characteristics is essential for ensuring reliable notification tracking.

## Source Data — `mailgun_events_queue` Table

The `JdbcCursorItemReader` (`BatchConfiguration.java`, lines 34–41) reads:

```sql
SELECT notification_id, message_subscriber_id, message_id
FROM mailgun_events_queue
WHERE last_job_run IS NULL
```

Inferred table schema (from `EmailResultRowMapper.java` and `Email.java`):

| Column | Type | Description |
|---|---|---|
| `notification_id` | VARCHAR | Onbe internal notification reference |
| `message_subscriber_id` | VARCHAR | Cardholder / subscriber identifier |
| `message_id` | VARCHAR | Mailgun-assigned message ID (used as query key) |
| `last_job_run` | DATETIME / VARCHAR | Set when batch processes the record; NULL = unprocessed |
| (additional columns inferred from `MailgunEventQueue`) | | `mailgun_event_type`, `mailgun_event_reason`, `mailgun_message_response`, `mailgun_event_timestamp` |

The `last_job_run IS NULL` predicate is the sole state indicator. This is a simple but fragile pattern — there is no `status` column distinguishing "pending", "processing", "completed", and "failed" states.

## External Data Source — Mailgun Events API

The `EmailItemProcessor` calls `MailgunEventsApi.getEvents(domainName, eventsQueryOptions)` where `eventsQueryOptions` filters by `messageId`.

Mailgun's Events API returns `EventsResponse` containing a collection of `EventItem` objects. Each `EventItem` exposes:

| Field | Usage in Processor |
|---|---|
| `event` | Event type string (ACCEPTED, DELIVERED, FAILED, BOUNCED, COMPLAINED, UNSUBSCRIBED) |
| `reason` | Failure reason (e.g., "bounce", "suppress-bounce") |
| `deliveryStatus.message` | SMTP response message from recipient MTA (truncated to 499 chars, line 107) |
| `userVariables` | Map of custom variables embedded by sender; key `"my-var"` contains JSON with `NOTIFICATION_ID`, `MESSAGE_SUBSCRIBER_ID`, `PROGRAM_ID` |
| `timestamp` | Event timestamp (ZonedDateTime) |

### Data Quality Issue: ACCEPTED Events Skipped

The processor skips `ACCEPTED` events (`line 94`):
```java
if(!eventItem.getEvent().equalsIgnoreCase(MailgunEvent.ACCEPTED.getEventTypeName()))
```
This means if the **only** event returned for a message is `ACCEPTED` (e.g., the email was just sent and not yet delivered), the `mailgunEventQueue` variable remains `null`. The writer then attempts `email.getMailgunEventQueue().toString()` (line 63), which throws a `NullPointerException` for emails with only `ACCEPTED` events. The `try/catch Exception` in `processEmailStatus()` silently swallows this error (line 68–70) — the record is then left with `last_job_run` unset? Actually, reviewing the writer: the `lastJobRun` is set in the **processor** on the `mailgunEventQueue` object. If `mailgunEventQueue` is `null`, the writer will NPE and the catch block logs it. The `last_job_run` column in the database may not be updated, leaving the record in an unresolvable state (never processed but never eligible for retry because... it will be re-queried next run since `last_job_run` is still NULL — this means it will be retried. However, if every run ends in an NPE for this record, it loops forever).

## Data Transformation Pipeline

```
mailgun_events_queue (NotificationSvc DB)
         │ SELECT notification_id, message_subscriber_id, message_id
         │ WHERE last_job_run IS NULL
         ▼
Email (Java object)
         │ EmailItemProcessor.process()
         │   → Mailgun API: getEvents(domainName, {messageId})
         │   → EventsResponse.getItems() iteration
         │   → Skip ACCEPTED events
         │   → Map EventItem → MailgunEventQueue DTO
         │     - action = "update"
         │     - mailgunEventType = eventItem.getEvent()
         │     - mailgunEventReason = eventItem.getReason()
         │     - mailgunMessageResponse = deliveryStatus.getMessage() (max 499 chars)
         │     - mailgunEventTimestamp = formatted timestamp
         │     - lastJobRun = now()
         ▼
MailgunEventQueue (enriched Email object)
         │ EmailItemWriter.write()
         │   → MailgunEventsQueueUpdateSP.updateMailgunEvent()
         │     → Stored procedure in NotificationSvc DB
         ▼
mailgun_events_queue (updated row)
```

## Data Quality Issues

1. **Null MailgunEventQueue on ACCEPTED-only messages**: As described above, leads to NPE in writer.
2. **Last event only**: The processor overwrites `mailgunEventQueue` in each loop iteration (`line 95`), so only the **last non-ACCEPTED event** is persisted. If Mailgun returns multiple events (e.g., FAILED followed by DELIVERED), only the last is stored. This loses event history.
3. **Message response truncation at 499**: Hard-coded truncation (`line 106`) may lose meaningful diagnostic information from SMTP bounce messages.
4. **Timestamp format**: `dateTimeFormat = "yyyy-MM-dd HH:mm:ss:ms"` — note `ms` is not a valid Java `DateTimeFormatter` specifier; the correct pattern for milliseconds is `SSS`. This will likely cause a `DateTimeParseException` or incorrect millisecond representation.
5. **User variable extraction**: The `userVariableStr` JSON is parsed with Gson into `Map<String, Object>`. If the `"my-var"` key is absent, `userVariablesMap` will be null and the `get()` calls will NPE (line 117). No null-check before map access.

## PII / Sensitive Data Classification

| Data Element | Classification | Regulation |
|---|---|---|
| `message_subscriber_id` | PII (cardholder ID) | GLBA, CCPA |
| `notification_id` | Internal identifier | Low sensitivity |
| Email delivery status | Indirect PII | GDPR (links email outcomes to individuals) |
| SMTP bounce messages | Potentially contains email addresses | GDPR, CCPA |
| Mailgun API key | Credential | Must not appear in logs or version control |

## Credential Exposure — Critical Finding

`application.properties` (line 18) contains the Mailgun API private key in plaintext:
```
mailgun.api.key=[REDACTED — rotate immediately]
```

`application-dev.properties` (line 11) contains the same key. This is a **critical security vulnerability**: the private API key is committed to version control and exposed to anyone with repository read access. This key allows:
- Sending emails via the `mail.mypaymentvault.com` domain
- Reading all Mailgun event data for that domain
- Accessing stored message content via the Mailgun Store Messages API

Additionally, `application.properties` lines 5–6 contain `username=b2ctest` / `password=b2ctest` — database credentials in source control.

**Immediate action required**: Rotate the Mailgun API key; remove credentials from source files; use environment variables or Azure Key Vault / Dapr secret store injection.
