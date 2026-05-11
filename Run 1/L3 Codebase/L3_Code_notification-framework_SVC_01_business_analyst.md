# Business Analyst Analysis — notification-framework_SVC

## Repository Overview

`notification-framework_SVC` is a foundational shared service responsible for delivering notifications to cardholders and clients across all Onbe/Northlane prepaid card programs. It is a J2EE multi-module Maven project (version 3.0.8-SNAPSHOT, Java 21) that routes notification events through a rules engine and delivers them via email (via Mailgun or SMTP), SMS, push notifications, and application in-app messages.

## Business Purpose

This service underpins cardholder communications for all programs on the platform. Key business capabilities:

### 1. Notification Event Processing
The `EventHandler` module receives notification events (e.g., card loaded, transaction approved, password reset, enrollment completed) via an XML-RPC interface and routes them through the rules engine to determine which notification template to use and which channel to deliver on.

### 2. Template-Based Personalised Communications
The `Mailer` module resolves notification templates from a database cache (up to 65,000 templates), merges cardholder-specific data (name, address, program-specific fields) using Apache Velocity templating, and delivers personalised emails. The template caching architecture was recently redesigned (`claude.md`) to reduce memory footprint from ~19.5 GB to ~30 MB by caching only metadata and fetching template bodies on demand.

### 3. Multi-Channel Delivery
The `Subscriber` module orchestrates delivery across channels:
- **Email**: Via Mailgun API (primary) or SMTP (legacy fallback). The `EmailDeliveryImpl.java` shows a legacy SMTP implementation; `NotificationMailerImpl.java` shows Mailgun integration via `mailgunEventsQueueInsert`.
- **SMS**: Stub implementation (`ChannelDeliveryImpl.java` line 46: `//TO DO: Implement SMS Delivery Functionality`). SMS delivery is not implemented in the version in this repository — this is a significant gap if SMS notifications are expected.
- **Application/Push**: Partial implementation via `ApplicationDelivery`.
- **Fax**: Stub implementation (line 62: `//TO DO: Implement FAX Delivery Functionality`).

### 4. Email Delivery Tracking (Mailgun Integration)
`NotificationMailerImpl.java` lines 173–208 insert Mailgun delivery events into a tracking table (`mailgunEventsQueueInsert`). This enables operations teams to track email delivery status (accepted, delivered, bounced, failed) per notification ID.

## Business Processes Supported

Based on the `notification-service-client_SVC` email classes and the event handler, this service supports:

| Event | Email Type |
|---|---|
| Account creation | `CreateAccountEmail` |
| Card load | `LoadAccountEmail`, `CreateAndLoadEmail` |
| Enrollment completed | `EnrollmentCompletedParent`, `EnrollmentCompletedTeen`, `EnrollmentCompletedWellness` |
| Enrollment invitation | `EnrollmentParentInvitation`, `EnrollmentInvitiationConfirmation` |
| ACH account ready | `ACHAccountReadyForVerification` |
| Instant ACH primary/secondary confirmation | `InstantACHPrimaryConfirmationEmail`, `InstantACHSecondaryConfirmationEmail` |
| Direct deposit subscription | `DirectDepositSubscriptionDetailsEmail` |
| Allowance management | `AllowanceDeletionConfirmationEmail`, `AllowanceModificationConfirmationEmail` |
| Password reset | `ResetPasswordEmail` |
| Profile updated | `ProfileUpdatedConfirmationEmail` |
| User registered | `UserRegisteredEmail` |
| Add fund reminder | `AddFundReminderEmail` |

This breadth indicates the service is the primary transactional email backbone for prepaid card cardholder lifecycle management.

## IBM MQ Integration

`pom.xml` line 192: `com.ibm.mq.jakarta.client` version `9.4.0.0` — IBM MQ is used for internal message queuing (likely for the Subscriber module receiving notification requests from the event handler). This is a legacy enterprise messaging stack, contrasting with the SQS-based architecture in the utility layer.

## Regulatory Context

- **Reg E (Electronic Fund Transfers)**: Email notifications for ACH transfers and load events are required disclosures under Reg E. Delivery failures could constitute a compliance violation.
- **TCPA**: SMS implementation (once built) must comply with TCPA consent requirements.
- **PCI DSS Req 3.4**: Email content containing card last-four digits or cardholder data must be masked in logs.

## Known Business Issues

1. **SMS delivery is not implemented**: The `ChannelDeliveryImpl.java` stub returns `true` for SMS without actually sending. If the system routes SMS notifications through this code path, cardholders will receive no SMS despite the system recording a successful delivery. This could affect fraud alert notifications or OTP delivery.

2. **Hardcoded sender email**: `EmailDeliveryImpl.java` line 25 shows `message.setFrom("admin@localhost", "Avinish Agarwal")` — a developer's name and a localhost email address hardcoded in the SMTP delivery path. This is old legacy code in the `Delivery` module (separate from the production `Mailer` module) and may not be the active code path, but it indicates incomplete cleanup of development artifacts.

3. **Stage/test environment email redirection**: `NotificationMailerImpl.java` lines 349–376 show that in stage/test environments, all emails are redirected to a `defaultToAddress` (configured in properties), with the original recipient appended to the subject line. This is correct behaviour but means test emails could leak cardholder email addresses in subject lines if logs capture email subjects.
