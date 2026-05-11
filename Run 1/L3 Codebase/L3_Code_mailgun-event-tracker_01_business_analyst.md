# Business Analyst View — mailgun-event-tracker

## Executive Summary

`mailgun-event-tracker` is a Spring Boot Batch service that tracks the delivery status of transactional emails dispatched through Mailgun. It operates as a scheduled batch job that queries a local `mailgun_events_queue` database table, calls the Mailgun Events API for each queued email, retrieves the latest delivery event (delivered, bounced, failed, etc.), and writes the result back to the notification database. This service is a critical operational component for Onbe's transactional communications infrastructure, enabling the business to monitor whether financial notification emails (disbursement alerts, card activation notices, receipt confirmations) actually reach cardholders.

## Business Context

Onbe sends transactional emails to cardholders and program participants as part of disbursement workflows. These emails are routed through Mailgun (sending domain: `mail.mypaymentvault.com`, from `application.properties` line 18). The business needs visibility into:

1. **Delivered**: Email successfully received by the recipient mail server.
2. **Bounced**: Email permanently rejected (invalid address, domain does not exist).
3. **Failed**: Temporary delivery failure.
4. **Complained**: Recipient marked the email as spam.
5. **Unsubscribed**: Recipient opted out.

Without this tracking, Onbe has no way to know if a cardholder received their disbursement notification — a requirement for regulatory compliance (consumer notification obligations under Reg E for electronic funds transfers) and for customer service operations.

## Process Flow

The `BatchConfiguration.java` defines a three-step Spring Batch pipeline:

1. **Reader** (`JdbcCursorItemReader<Email>`): Queries `mailgun_events_queue` for records where `last_job_run IS NULL` — meaning they have never been processed. SQL (line 36–37):
   ```sql
   select notification_id, message_subscriber_id, message_id
   from mailgun_events_queue
   where last_job_run is null
   ```
   Fetches in chunks of 10 (`setFetchSize(10)`) with a 10-second query timeout.

2. **Processor** (`EmailItemProcessor`): For each queued email:
   - Calls `MailgunEventsApi.getEvents(domainName, EventsQueryOptions)` filtering by `messageId`.
   - Iterates over returned `EventItem` objects.
   - Skips events of type `ACCEPTED` (the initial acceptance event, not meaningful for delivery tracking).
   - Extracts: event type, event reason, delivery status message (truncated to 499 chars), user variables (JSON blob containing `NOTIFICATION_ID`, `MESSAGE_SUBSCRIBER_ID`, `PROGRAM_ID`), and timestamp.
   - Returns the populated `MailgunEventQueue` DTO.

3. **Writer** (`EmailItemWriter`): Persists each `MailgunEventQueue` via `MailgunEventsQueueUpdateSP` (a stored procedure call to the `NotificationSvc` database).

The job processes in chunks of 3 (`<Email, Email>chunk(3, transactionManager)`, line 65) and `allowStartIfComplete(true)` — the job can be re-run.

## Business Data Elements

The `Email` domain object (`Email.java`) tracks:

| Field | Source | Business Purpose |
|---|---|---|
| `notificationId` | Database queue | Onbe notification identifier |
| `messageSubscriberId` | Database queue | Cardholder / subscriber identifier |
| `messageId` | Database queue | Mailgun-assigned unique message ID |
| `mailgunEventType` | Mailgun API | Delivery outcome (delivered, bounced, etc.) |
| `mailgunEventReason` | Mailgun API | Reason for failure/bounce |
| `mailgunMessageResponse` | Mailgun API | SMTP response message from recipient server |
| `mailgunEventTimestamp` | Mailgun API | When the event occurred |
| `lastJobRun` | Computed | Timestamp when this batch job processed the record |
| `programId` | Mailgun user variables | Client program identifier |

## Business Value and Risk

### Value
- Enables Operations and Customer Service to identify cardholders who did not receive critical financial notifications
- Supports bounce management and email list hygiene to protect Mailgun sending reputation
- Provides an audit trail of notification delivery for Reg E compliance documentation
- Allows re-send workflows to be triggered when permanent failures are detected

### Business Risks

1. **Hardcoded Mailgun API Key** (`application.properties` line 18): The Mailgun private API key (`[REDACTED — rotate immediately]`) is committed to the source repository in plaintext. This is a critical security finding — if this key is live, it must be rotated immediately. Any party with the key can send emails on behalf of `mail.mypaymentvault.com` and access all Mailgun event data.

2. **Hardcoded database credentials** (`application.properties` lines 5–6): `username=b2ctest`, `password=[REDACTED — rotate immediately]` for the `NotificationSvc` database. Test credentials in source code.

3. **Only "not yet processed" records**: The reader only fetches `last_job_run IS NULL`. Records that fail processing will have `last_job_run` set and will not be retried — there is no error/retry state management.

4. **Email content exposure**: Delivery status responses from Mailgun may contain fragments of email subject lines or recipient addresses, which are logged at INFO level without sanitisation.

## Integration Dependencies

| System | Role | Connection |
|---|---|---|
| NotificationSvc SQL Server | Source queue and result store | JDBC (`d-az-db01.nam.wirecard.sys:2231`) |
| Mailgun API | Event query | REST API over HTTPS (`apiKey` + `domainName`) |
| com.ecount:xPlatform | Platform utility library | `7.0.11-SNAPSHOT` |

## Regulatory Considerations

- **Reg E**: Electronic fund transfer notifications must be demonstrably delivered to consumers. The event tracking data supports compliance evidence.
- **CAN-SPAM / CASL**: Bounce and unsubscribe events must be honoured to comply with anti-spam regulations. The tracker provides the data needed for suppression list management.
- **GDPR / CCPA**: Email addresses are PII — the delivery status data links notification IDs to message delivery outcomes, which may be considered personal data processing records.
