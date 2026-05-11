# Data Architecture — notification-service-client_SVC

## Data Stores
This is a **stateless client library** — it holds no data stores. All data is passed through to the downstream Notification Service via HTTP.

## Data Structures (in-memory / in-transit)
| Structure | Type | Sensitivity |
|-----------|------|------------|
| `mergeData` | `java.util.Hashtable<String, String>` | May contain PII (name, email, account details) |
| `attachmentInfo` | `java.util.Hashtable<String, String>` | Attachment metadata |
| `recipientEmail` | String | PII — email address |
| `programId` | String | Program identifier |
| `agent` (in RequestContext) | String | Service/agent identity |
| `affiliateId` (in RequestContext) | String | Affiliate identifier |
| `correlationId` (in RequestContext) | String | Distributed tracing ID |
| `NotificationReceipt.messageId` | String | Returned notification ID |

## Sensitive Data
- `recipientEmail` — PII email address.
- `mergeData` values — may contain personalised content including names, dates, amounts; depends on the calling service.
- No PAN, CVV, or other SAD should be placed in merge data; this constraint is not technically enforced.

## Encryption
- No application-level encryption.
- HTTPS assumed at HTTP client level (Feign); not enforced in this library.
- Correlation ID interceptor adds `X-Correlation-Id` or equivalent header — not sensitive.

## Data Flow
1. Caller creates an `IEmailNotification` subclass, populates `mergeData` with template variables and `recipientEmail`, `programId`.
2. Caller invokes `INotificationManager.deliver(batchId, notification, member, requestContext, description)`.
3. `NotificationManagerImpl` validates the notification if `shouldValidate = true`.
4. Validated notification serialised to `NotificationEventInputUsingMaps` DTO.
5. `NotificationServiceRestImpl` calls Feign client `NotificationRestServiceClient` with circuit breaker wrapping.
6. Feign makes HTTP POST to `${notification.urls.base-url}` with notification payload.
7. `NotificationEventOutput` returned containing the notification result.

## Data Quality / Retention
- No persistence in this library.
- Merge data values are caller's responsibility for accuracy and completeness.
- Validation ensures `eventName`, `recipientEmail`, `programId` are non-empty; no other format validation.

## Compliance Gaps
- `Hashtable` for merge data allows null values to be stored (NullPointerException risk if merge data key absent).
- No type-safety on merge data keys — callers can pass arbitrary key names; misspelled keys silently produce empty template slots.
- `NotificationEventInputUsingMaps` serialised via Jackson — content including PII transmitted as plaintext JSON to notification service (transport encryption is caller's responsibility).
- No data masking or redaction in logging — if merge data is logged by the downstream service, PII may appear in logs.
- Repository URL hardcoded to legacy internal Nexus (`wirecard.sys`) — artifact source may be inaccessible or insecure.
