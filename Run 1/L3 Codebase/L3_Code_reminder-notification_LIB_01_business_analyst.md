# 01 Business Analyst — reminder-notification_LIB

## Business Purpose
Batch library that identifies prepaid card programme members who have not yet completed digital enrollment (the "yet-to-enroll" population) and dispatches email reminder notifications to encourage activation. Supports cardholder-engagement KPIs and reduces dormant-card risk for programme operators.

## Capabilities
- Queries the member database for cardholders who have not enrolled within a configurable processing window
- Counts the eligible member population before processing (MembersCount step)
- Iterates member details in configurable parallel thread batches (gridsize parameter)
- Generates and sends reminder emails using a templated email notification service
- Records notification history to prevent duplicate sends (reminder notification history table)
- Supports scheduled or on-demand execution via command-line launcher (`ReminderNotification.main`)
- Parameterised processing date (defaults to current date; overridable via CLI argument)

## Entities
- **Member** (`com.ecount.core.batch.dto.Member`): cardholder identity
- **YetToEnrollMember**: member-detail record for a cardholder who has not enrolled
- **MembersCount**: aggregate count of the eligible population for a given processing run
- **ReminderNotificationHistory**: audit record of a notification send event (persisted via stored procedure)

## Business Rules
- Only members with "yet to enroll" status for the programme are processed
- Each batch run is identified by a `purpose` parameter and a unique `jobrun.time` timestamp to allow restart/re-run detection via Spring Batch
- `processingDate` drives the eligibility window; defaults to today if not supplied
- Notification history is recorded to suppress duplicate sends across runs
- Thread count for member detail retrieval is controlled by `member_details_gridsize` property

## Flows
1. Scheduler / operator invokes `ReminderNotification.jar` with: `<contextXml> <jobName> <purpose> [processingDate=MM/dd/yyyy]`
2. Spring Batch `JobLauncher` starts the job
3. Step 1 — Count: queries member count, saves to context via `MembersCountSavingListener`
4. Step 2 — Detail: reads eligible members in pages (JDBC cursor), passes to `MemberDetailsItemWriter`
5. `MemberDetailsItemWriter` calls `NotificationEventHandler` → `YetToEnrollMemberNotificationHandlerImpl` → email template + send
6. Notification history is updated via `StoredProcUpdateReminderNotificationHistory`
7. Job exit status is logged; process exits

## Compliance
- Email notifications containing cardholder names or contact details are PII; must be handled in accordance with GLBA, CCPA, and GDPR (for any EEA cardholders)
- No PAN or financial account data is transmitted in the email body per PCI DSS requirement 3.3
- Spring Batch job repository tables store run metadata in SQL Server; access should be restricted to service accounts only

## Risks
- Spring version 2.5.6 and Spring Batch 2.1.1 are severely end-of-life (EOL > 10 years); known CVEs exist
- Java 6 compile target (`source/target 1.6`) is unsupported; cannot receive security patches
- SQL Server JDBC driver `sqljdbc 1.1` is very old; TLS negotiation may fail against modern SQL Server versions
- Properties file loaded from a file-system path; if missing, the job continues with an empty properties set, silently ignoring `member_details_gridsize`
- No retry or skip configuration visible in the job XML; a transient DB error will fail the entire run
