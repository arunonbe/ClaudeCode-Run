# Data Architect Analysis — notification-requests-generator_LIB

## Data Model

### Primary DTO: `NotificationRequest.java`

The central data transfer object carries all data for a single notification request:

| Field | Type | PII? | Notes |
|---|---|---|---|
| `uid` | int | No | Unique ID of the queue record |
| `msgTemplateName` | String | No | Template identifier |
| `mergeData` | String | YES | URL-encoded field=value pairs (see below) |
| `eventData` | String | Possibly | Event context data |
| `deliveryDate` | String | No | Scheduled delivery date |
| `toEmailAddress` | String | YES | Cardholder email address |
| `fromEmailAddress` | String | No | Sender email address |
| `friendlyFromAddress` | String | No | Display name for sender |
| `friendlyToAddress` | String | YES | Cardholder display name |
| `subject` | String | No | Email subject |
| `dateSubmitted` | String | No | Record creation date |
| `messageId` | String | No | Message identifier |
| `application` | String | No | Program application |
| `partner` | String | No | Partner/client identifier |
| `notificationBatchId` | int | No | Batch run identifier |
| `bounceBackEmail` | String | Possibly | Reply-to/bounce address |

### MergeData Field Analysis

The comment on `mergeData` (`NotificationRequest.java` line 33) reveals the full PII content:
```
//MOBILEPHONE=&HOMEPHONE=6109414600&BUSINESSPHONE=&PHONE=6109414600
//&CITY=Wynnewood&SUFFIXNAME=&LASTNAME=Eastern&STATE=PA&POSTAL=19096
//&FIRSTNAME=North&MIDDLENAME=&ADDRESS2=STE+22&ADDRESS1=50+E+Wynnewood+RD
```

This example comment (which should be removed from production code as it contains what appears to be a real or test address) shows that `mergeData` contains:
- Phone numbers (mobile, home, business)
- Full street address (address line 1, line 2, city, state, zip)
- Full name (first, middle, last, suffix)

This is a **comprehensive PII payload** concatenated as a URL-encoded string. Every notification request carries this full cardholder profile data.

### Secondary DTO: `NotificationRequestsCount.java`

Tracks counts of notifications processed per batch run — used for audit and monitoring purposes. Does not contain PII.

## Data Access Layer Architecture

### Spring Batch Item Reader Pattern

The batch uses Spring Batch's `JdbcCursorItemReader` pattern (inferred from `NotificationRequestDetailsRowMapper` and `NotificationRequestDetailsPreparedStatementSetter`):

1. `NotificationRequestDetailsPreparedStatementSetter` — Sets SQL query parameters (processing date, minutes window)
2. `NotificationRequestDetailsRowMapper` — Maps JDBC `ResultSet` rows to `NotificationRequest` objects
3. `NotificationRequestDetailsItemWriter` — Writes processed records to the output queue

### Stored Procedures

Two stored procedures are managed by Spring:
- `StoredProcNotificationRequestBatch` — Fetches notification request records for the processing window
- `StoredProcUpdateNotificationRequestHistory` — Updates history after processing

### DAO Layer

```
NotificationRequestHistoryDAO (interface)
    ↓
NotificationRequestHistoryDAOImpl (Spring JDBC implementation)
```

The DAO uses Spring's `JdbcTemplate` for all database operations, with JDBC prepared statements for parameterised queries.

## PII Data Flow

```
Database (notification_queue table)
    ↓ StoredProcNotificationRequestBatch (SQL query)
NotificationRequestDetailsRowMapper
    ↓ mapRow() — logs each PII field at INFO level
NotificationRequest DTO (contains full PII)
    ↓ toString() — serialises all PII fields
Application Log (d:/c-base/logs/batch/notificationRequests.log)
    ↓ (simultaneously)
Syslog (UDP/TCP to 10.1.1.130) — unencrypted transmission
    ↓ (batch processing)
Notification Framework (passed via Spring Batch ItemWriter)
```

**Critical PII logging path:** At every stage of this data flow, PII is logged. The `NotificationRequestDetailsRowMapper` logs each field individually (lines 41–113), and `NotificationRequest.toString()` serialises everything together. Both are logged at INFO level.

## Database Schema Observations (Inferred)

From the column constants in `NotificationRequestConstants.java` (inferred from the row mapper field accesses):

| Column Constant | Data |
|---|---|
| `NOTIFICATION_REQUEST_UID_COLUMN` | Record ID |
| `NOTIFICATION_REQUEST_TEMPLATE_NAME_COLUMN` | Template name |
| `NOTIFICATION_REQUEST_MERGE_DATA_COLUMN` | URL-encoded PII payload |
| `NOTIFICATION_REQUEST_APPLICATION_COLUMN` | Application/program |
| `NOTIFICATION_REQUEST_PARTNER_COLUMN` | Partner identifier |
| `NOTIFICATION_REQUEST_EMAIL_ADDRESS_COLUMN` | Recipient email |
| `NOTIFICATION_REQUEST_FROM_ADDRESS_COLUMN` | Sender email |
| `NOTIFICATION_REQUEST_FRIENDLY_FROM_ADDRESS_COLUMN` | Sender display name |
| `NOTIFICATION_REQUEST_FRIENDLY_TO_ADDRESS_COLUMN` | Recipient display name |
| `NOTIFICATION_REQUEST_NOTIFICATION_BATCH_ID_COLUMN` | Batch ID |
| `NOTIFICATION_REQUEST_REPLYTO` | Reply-to/bounce email |

## Spring Batch Job Configuration

**File:** `src/main/resources/job/generateNotificationRequestsBatchJob.xml` — Spring Batch XML configuration defining the job steps, readers, processors, and writers.

**File:** `src/main/resources/job/context/generateNotificationRequestsContext.xml` — Spring application context for the batch job (data sources, DAO beans).

**File:** `src/main/resources/dataSourceContext.xml` — Database connection configuration.

**Data residency concern:** The `dataSourceContext.xml` likely contains JDBC connection strings for the Onbe operational database. If these include embedded credentials, that is a critical security finding (cannot be confirmed without reading this file).

## Data Integrity

The `NotificationRequestDetailsLimitDecider` implements a `JobExecutionDecider` that controls whether to continue processing based on count limits. This prevents unbounded processing in runaway scenarios (e.g., if a large backlog accumulates).

`ProcessedTransactionCountSavingListener` saves processing metrics (transaction count) as Spring Batch job execution context, enabling monitoring of throughput per run.
