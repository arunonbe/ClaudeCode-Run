# Business Analysis — notification-service-client_SVC

## Business Purpose
A shared Java library (packaged as a JAR) that provides a typed, validated REST client for the Onbe/NorthLane Notification Service. Consuming applications import this library to send, handle, or stop email notifications without implementing direct HTTP logic. It encapsulates notification business rules, validation, and circuit-breaker resilience, and abstracts the notification REST API contract from callers.

## Capabilities
- Deliver email notifications (synchronous REST via OpenFeign + circuit breaker).
- Handle notification events via `DefaultNotificationEvent`.
- Stop/cancel in-progress notifications.
- Create and release batch email contexts (for bulk batched sending).
- Typed email notification classes for 20+ specific notification types (account creation, enrollment, ACH, allowance changes, direct deposit, password reset, etc.).
- Input validation per notification type (event name, recipient email, program ID required).
- Correlation ID propagation via request interceptor (`CorrelationIdInterceptor`).
- Circuit breaker per operation (`create-notification`, `handle-notification`, `stop-notification`) via Resilience4j.
- Configurable HTTP timeouts and circuit-breaker thresholds via Spring `@Value` properties.

## Key Notification Types (Email)
| Class | Trigger |
|-------|---------|
| `CreateAccountEmail` | New account created |
| `UserRegisteredEmail` | User registration completed |
| `ResetPasswordEmail` | Password reset request |
| `LoadAccountEmail`, `CreateAndLoadEmail` | Funds loaded to account |
| `EnrollmentCompletedParent/Teen/Wellness` | Enrollment completion |
| `EnrollmentParentInvitation`, `EnrollmentInvitiationConfirmation` | Enrollment invitation flow |
| `ACHAccountReadyForVerification` | ACH account verification step |
| `InstantACHPrimaryConfirmationEmail`, `InstantACHSecondaryConfirmationEmail` | Instant ACH confirmation |
| `AllowanceDeletionConfirmationEmail`, `AllowanceModificationConfirmationEmail` | Allowance management |
| `DirectDepositSubscriptionDetailsEmail` | Direct deposit subscription |
| `AddFundReminderEmail` | Low balance reminder |
| `ProfileUpdatedConfirmationEmail` | Profile update |

## Key Entities / Interfaces
| Entity | Description |
|--------|-------------|
| `INotificationManager` | Primary interface: `deliver()`, `createBatch()`, `releaseBatch()`, `getShouldValidate()` |
| `IEmailNotification` | Interface for all typed email notifications |
| `AbstractEmailNotification` | Base class: event name, merge data, recipient email, program ID, BCC, CC, attachment info |
| `RequestContext` | Carries agent, affiliateId, correlationId for each notification call |
| `NotificationReceipt` | Return value from `deliver()` — contains messageId |

## Business Rules
- Validation is enabled by default (`shouldValidate = true`).
- Required fields per notification: `eventName`, `recipientEmail`, `programId`.
- Validation errors accumulate in `ValidationExceptionList` before throwing.
- Circuit breaker records `IOException` and `TimeoutException` as failures; other exceptions are ignored.
- Correlation ID from `RequestContext` is propagated as an HTTP header via `CorrelationIdInterceptor`.
- Batch emails: create a batch ID, associate emails to it, then release the batch.

## Compliance Relevance
- Email addresses (`recipientEmail`) are PII — handled transiently, not persisted by this library.
- `mergeData` Hashtable may contain personalised content (names, account numbers) — transmitted to notification service.
- No cardholder data (PAN, CVV) should be placed in merge data; no enforcement exists at this layer.
- Correlation ID propagation supports audit trail linking across service calls.

## Risks
- Uses `java.util.Hashtable` (thread-safe but legacy) for `mergeData` and `attachmentInfo` — older API style.
- Library targets **Java 8 / Spring Framework 4.3.27** — significantly behind Gen-3 standards.
- Nexus/Artifactory URL hardcoded to internal Wirecard/NorthLane address (`d-na-stk01.nam.wirecard.sys`) — legacy infrastructure reference.
- No encryption of merge data content — sensitive values in notification templates transmitted in plain HTTP (HTTPS assumed but not enforced by library).
- Low JaCoCo coverage thresholds (instruction 37%, branch 27%) — quality bar below industry standard.
