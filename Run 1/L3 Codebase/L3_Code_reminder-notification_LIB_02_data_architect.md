# 02 Data Architect — reminder-notification_LIB

## Data Stores
| Store | Technology | Purpose |
|---|---|---|
| ecountcore (SQL Server) | Microsoft SQL Server | Member eligibility queries (YetToEnroll members, counts) |
| batchrepodatabase (SQL Server) | Microsoft SQL Server | Spring Batch job repository (execution metadata) |
| cbaseapp (SQL Server) | Microsoft SQL Server | Supplemental member/programme data |
| File system (properties) | Flat file | Runtime configuration (`member_details_gridsize`, email settings) |

Data source connections are resolved at runtime via the Director service (`DirectorConfiguredDBCPdatasourceCreator`), which acts as a connection-string registry.

## Schema / Tables
Inferred from DAO and stored-procedure layer:
- `ReminderNotificationHistory` — stores per-member notification send records; populated/updated via `StoredProcUpdateReminderNotificationHistory`
- Spring Batch schema tables (`BATCH_JOB_INSTANCE`, `BATCH_JOB_EXECUTION`, `BATCH_STEP_EXECUTION`, etc.) in the batchrepodatabase
- Member eligibility result set sourced via `YetToEnrollMemberDetailsRowMapper` / `YetToEnrollMembersCountRowMapper` (exact table names not visible without reviewing stored procedures)

## Sensitive Data
| Data Element | Sensitivity | Location |
|---|---|---|
| Cardholder name | PII (GLBA / CCPA) | YetToEnrollMember DTO, email body |
| Email address | PII | YetToEnrollMember DTO, email send call |
| Member ID | Internal identifier | Member DTO, job parameters |
| Processing date | Non-sensitive | Job parameter |

No PAN, CVV, or SAD fields observed in the DTO layer.

## Encryption
- No application-level encryption of member PII in transit between the batch job and the database; relies on network-layer controls (SQL Server SSL/TLS)
- SQL Server JDBC driver `sqljdbc 1.1` may not enforce TLS 1.2 — this is a PCI DSS / GLBA risk
- Email transmission encryption depends on the `xPlatform` email service implementation (not visible in this repo)
- No field-level encryption of PII in the `ReminderNotificationHistory` table

## Data Flow
```
Director Service (connection registry)
  --> ecountcore DB  -->  YetToEnrollMembers query  -->  YetToEnrollMember DTOs
                                                         --> MemberDetailsItemWriter
                                                             --> NotificationEventHandler
                                                                 --> Email service (xPlatform)
                                                                     --> Cardholder inbox
  --> batchrepodatabase  -->  Spring Batch job repository (run tracking)
  --> ecountcore DB  -->  StoredProcUpdateReminderNotificationHistory (write-back)
```

## Quality / Retention
- No data quality validation on YetToEnrollMember fields before email dispatch
- Spring Batch job metadata is retained in the batchrepodatabase indefinitely unless pruned by a separate housekeeping job (none observed)
- Notification history table has no visible purge policy; potential unbounded growth
- `processingDate` defaults to today but can be overridden; no guards against future-dating or back-dating

## Compliance Gaps
- PII (cardholder name, email) flows through a Java 6 / Spring 2.5.6 stack with no current CVE patching — GLBA / CCPA data-protection gap
- No explicit data-at-rest encryption for PII in ReminderNotificationHistory
- No data-lineage or audit log beyond Spring Batch execution records
- Retention schedule for notification history and batch metadata not defined — conflicts with CCPA right-to-deletion if member data is retained after programme close
