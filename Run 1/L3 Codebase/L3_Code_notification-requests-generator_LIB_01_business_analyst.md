# Business Analyst Analysis — notification-requests-generator_LIB

## Repository Overview

`notification-requests-generator_LIB` is a Java batch library (Spring Batch) that generates notification requests from database records. It was initially developed in 2011 (per class header comments) and serves as the **data pipeline** that reads pending notification events from the Onbe database and feeds them into the notification processing queue. It is not a service — it is a batch job executed as a scheduled JVM process via command-line invocation.

## Business Purpose

The library solves the problem of converting raw business events stored in the database into structured notification requests that the notification framework can process. Its primary responsibilities are:

### 1. Batch Notification Request Generation
Reads records from the `notification_queue` or similar database table using Spring Batch's chunk-oriented processing model. For each record, it creates a `NotificationRequest` DTO containing all data needed to send a notification (template name, merge data, recipient email, program, partner).

### 2. Notification History Tracking
Uses `NotificationRequestHistoryDAO` and helpers to record which notification batch runs have been processed, supporting idempotent re-processing and audit trails.

### 3. Job Scheduling and Orchestration
The `NotificationRequestGenerator.java` main class accepts command-line arguments specifying:
- The Spring context XML file (job definition)
- The job bean name
- Processing date parameters (in `processing_date=yyyy-MM-dd HH:mm`, `minutes`, `rechecking_minutes` format)

This allows the batch to be scheduled by an external scheduler (cron, Windows Task Scheduler, or enterprise job schedulers like Control-M). The `.bat`, `.vbs`, and release JAR files in the `releases/` directory indicate deployment as a Windows batch job.

### 4. Bounded Reminder Notifications
The `NotificationRequestDetailsLimitDecider.java` and `NotificationRequestsCountSavingListener.java` suggest the batch processes notifications in bounded chunks with count tracking — likely for reminder-type notifications where only a certain number should be sent per run.

## Business Context

This library sits at the intersection of:
- **Core banking/prepaid data** (reading from the program's operational database)
- **Notification platform** (feeding the notification framework)

It handles the "trigger → request" transformation: a business event (e.g., "card was loaded 30 days ago with no activity") becomes a structured notification request that results in a reminder email to the cardholder.

## Business Processes Supported

Based on the field structure of `NotificationRequest.java` and the job name `generateNotificationRequestsBatchJob.xml`:

| Process | Evidence |
|---|---|
| Periodic reminder notifications | `processingDate`, `minutes`, `rechecking_minutes` parameters |
| Multi-program support | `application` and `partner` fields in `NotificationRequest` |
| Batch-scoped notifications | `notificationBatchId` field |
| Reply-to routing | `bounceBackEmail` field |

## Deployment Model

The `releases/` directory contains:
- `notification-requests-1.0.jar` — runnable JAR
- `NotificationRequestGeneratorBatchJob.bat` — Windows batch script for execution
- `NotificationRequestGeneratorBatchJob.vbs` — VBScript wrapper (suppresses command window)

This indicates **Windows Server on-premises deployment**, consistent with a legacy batch processing environment. The log file path `d:/c-base/logs/batch/notificationRequests.log` confirms a Windows server deployment to the `d:/c-base` directory structure.

## Stakeholder Impact

| Stakeholder | Impact |
|---|---|
| Cardholders | Receive or miss time-sensitive reminder notifications |
| Program Clients | SLA on notification delivery depends on this batch completing successfully |
| Operations | Monitors job execution via log files and exit codes |
| Compliance | Notification delivery audit trail for Reg E disclosures |

## Business Risks

1. **Silent processing gaps**: If the batch fails to run (scheduler failure, job error), cardholders may miss notifications. The exit code mapper (`ExitCodeMapperImpl`) provides exit codes for the external scheduler, but whether alerts are configured on non-zero exits is not visible in this repo.

2. **Processing date dependency**: The batch uses a `processingDate` parameter to control which records to process. If the date is incorrectly set (e.g., timezone mismatch), notifications may be sent for the wrong period or not at all.

3. **Single-threaded batch risk**: The thread count is read from properties (`notification_request_details_gridsize`), suggesting it supports multi-threaded processing. However, if the grid size is not tuned for the volume of pending notifications, batch processing time may exceed the scheduling interval.

4. **Windows-specific deployment**: `.bat` and `.vbs` files indicate Windows-only deployment. Any migration to Linux (AWS/containerised) requires rewriting the execution scripts and potentially the log file path conventions.
