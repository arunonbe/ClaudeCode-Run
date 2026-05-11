# Data Architect Analysis — notification-framework_SVC

## Data Model Overview

The notification framework operates on several core data entities:

### 1. Notification Template (`NotificationTemplate.java`)
Fields: `id`, `name`, `subject`, `value` (body), `altValue` (HTML alt body), `format`, `locale`, `urlEncoded`, `mergeDataType`, `application`, `bodyLoaded`.

**Architecture pattern (from `claude.md`):** Templates are stored as URL-encoded CLOBs in the database (up to 100K–150K characters each). As of the latest architectural change:
- **Cache stores:** `id`, `name`, `subject`, `format`, `locale`, `urlEncoded`, `mergeDataType`, `application` (metadata only — ~500 bytes per entry)
- **Cache never stores:** `value` (template body), `altValue` (alt template body)
- **Every email send** triggers a stored procedure call to fetch the template body from the database.

This design prevents the original startup memory explosion (~13–19.5 GB) but introduces a database round-trip per email sent (~50ms stored proc latency). At high email volumes this may become a bottleneck.

### 2. Notification Queue (`NotificationQueue` — referenced from rules engine)
Contains: `notificationId`, `messageSubscriberId`, `templateId`, `toAddress`, `ccAddress`, `bccAddress`, `fromAddress`, `friendlyFromAddress`, `friendlyToAddress`, `friendlyCcAddress`, `friendlyBccAddress`, `mergeData` (Map), `channelId`, `deliveryAttempts`.

**PII data fields in NotificationQueue:**
- `toAddress` — cardholder email address
- `ccAddress`, `bccAddress` — additional email addresses
- `mergeData` — free-form map containing template variables (may include cardholder name, address, last 4 digits)

### 3. Notification Delivery (`NotificationDelivery.java`)
Transformed object passed to the delivery service: `notificationId`, `messageSubscriberId`, `toAddress`, `ccAddress`, `bccAddress`, `fromAddress`, `friendlyToAddress`, `subject`, `notificationBody`, `notificationAltBody`, `attachmentFile`, `channelId`, `deliveryAttempts`.

**PII data fields in NotificationDelivery:**
- `toAddress` — cardholder email address
- `notificationBody` — rendered email body containing merged cardholder data
- `notificationAltBody` — HTML alternate body

### 4. Mailgun Event Queue (`MailgunEventQueue`)
Fields: `notificationId`, `messageSubscriberId`, `programId`, `messageId`, `mailgunEventType`, `mailgunMessageResponse`, `emailSubject`.

**PII concern:** `emailSubject` is stored in the Mailgun tracking table. Email subjects may contain cardholder names (e.g., "Account Statement for Jane Doe") — this should be verified against all template subjects.

## PII Logging Assessment

### Critical: `NotificationRequest.toString()` Logs PII to Application Log

**File:** `notification-requests-generator_LIB/src/main/java/com/ecount/core/batch/dto/notification/request/NotificationRequest.java`, lines 282–319

The `toString()` method serialises all fields including:
- `getToEmailAddress()` — cardholder email
- `getMergeData()` — contains fields like `MOBILEPHONE`, `HOMEPHONE`, `FIRSTNAME`, `LASTNAME`, `ADDRESS1`, `ADDRESS2`, `CITY`, `STATE`, `POSTAL` (see comment at line 33)
- `getEventData()` — event-specific data

The row mapper `NotificationRequestDetailsRowMapper.java` explicitly logs each field at INFO level (lines 41–113):
```java
log.info("Email Queue Uid :" + uid);
log.info("TemplateName :" + templateName);
log.info("MergeData :" + mergeData);
log.info("ToEmailAddress :" + toEmailAddress);
```

The `log4j.properties` sets `log4j.rootLogger=debug` with `stdout.Threshold=info` and `FILE.Threshold=info`. This means **cardholder email addresses, names, phone numbers, and postal addresses are logged at INFO level to both the console and rolling file appender** (`d:/c-base/logs/batch/notificationRequests.log`).

**PCI DSS / GDPR risk:** Logging PII (email, name, phone, address) to flat files creates an uncontrolled PII data store. File-based logs may not have the same access controls and retention policies as the database.

### Notification Mailer Logging (`NotificationMailerImpl.java`)

`NotificationMailerImpl.java` line 57–58:
```java
log.debug("NotificationMailerImpl::processMessage " + notificationQueue.toString());
```
If `debug` logging is enabled, the full `NotificationQueue` object (including `toAddress` and `mergeData`) is logged. The `mergeData` map may contain card-related data depending on the template.

Line 115:
```java
log.debug("NotificationMailerImpl::processMessage notificationDelivery: " + notificationDelivery);
```
The rendered `notificationDelivery` object includes `notificationBody` — the fully merged email body. If card last-four digits appear in the body (e.g., "Your card ending in 1234"), they would be logged in debug mode.

**Positive finding:** Debug logging is used (not INFO), so production systems with `debug` disabled would not log the rendered body. However, if debug is ever enabled for troubleshooting in production, PII exposure occurs immediately.

## Database Architecture

### Stored Procedures
The system is heavily stored-proc-centric:
- `StoredProcGetTemplateDetails` — fetches template body by ID
- `StoredProcGetTemplates` — fetches all templates
- `StoredProcUpdateNotificationMessageStatus` — updates delivery status
- `StoredProcNotificationRequestBatch` — batch reads notification requests
- `StoredProcUpdateNotificationRequestHistory` — updates batch history

No ORM is used; all data access is via Spring JDBC. This is a legacy pattern but acceptable for high-throughput batch notification processing.

### IBM MQ
The subscriber module consumes notification request messages from IBM MQ. The message payload contains the serialised `NotificationQueue` object. MQ message bodies containing PII should be encrypted at the MQ level or the message payload should not contain raw PII fields.

## Data Retention

No explicit data retention policies are visible in this repository. The notification queue table and mailgun tracking table will accumulate records indefinitely unless cleaned up by a separate process. For GDPR/CCPA compliance, PII in notification queue records must be subject to right-to-erasure procedures.
