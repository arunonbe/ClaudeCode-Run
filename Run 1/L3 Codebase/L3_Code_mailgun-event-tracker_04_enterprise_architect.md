# Enterprise Architect View — mailgun-event-tracker

## Architectural Classification

`mailgun-event-tracker` is a **notification infrastructure service** — specifically, an outbound email delivery monitoring component. It bridges Onbe's internal notification system (`NotificationSvc` database) with the Mailgun third-party email delivery platform. Within the Onbe enterprise architecture, it supports the consumer communication layer that is required for Reg E compliance, cardholder experience, and customer service operations.

## Position in Onbe Enterprise Architecture

```
Onbe Services (card issuance, disbursement, etc.)
         │ triggers notification
         ▼
Notification Framework / notification-framework_SVC
         │ sends email via Mailgun
         │ records messageId → mailgun_events_queue
         ▼
Mailgun Email Delivery Platform
         │ delivers / bounces / fails
         ▼
Mailgun Events API (event data retained for 30 days)
         │
         ▼
mailgun-event-tracker (this service)  ◄── polls Mailgun, updates queue
         │ writes event outcomes
         ▼
NotificationSvc Database
         │ read by
         ▼
Customer Service / Operations dashboards
```

## Architectural Concerns

### 1. Polling Architecture vs Event-Driven

The current design polls Mailgun's Events API on a scheduled basis. Mailgun supports webhook delivery of events in near-real-time. A webhook-based architecture would:
- Eliminate polling lag (potentially hours between email send and status update)
- Reduce Mailgun API call volume and associated rate-limit risk
- Enable real-time operational alerting on bounce spikes

### 2. SNAPSHOT Dependency Risk

`com.ecount:xPlatform:7.0.11-SNAPSHOT` is a moving target. SNAPSHOT dependencies create non-reproducible builds — the same source code may compile differently at different times if the SNAPSHOT is updated. In a regulated environment (PCI DSS, SOC 2), builds must be reproducible. This dependency should be promoted to a stable release version.

### 3. Third-Party API Integration Governance

Mailgun is an external vendor processing email addresses (PII) on behalf of Onbe. Enterprise governance requirements:
- **DPA (Data Processing Agreement)**: Verify that a current DPA is in place with Mailgun under GDPR Art 28 and CCPA obligations.
- **Data residency**: Mailgun may route email through servers outside Onbe's primary jurisdiction — verify compliance with GDPR data transfer requirements if sending to EU data subjects.
- **API key rotation policy**: The committed API key must be rotated and a rotation policy enforced.

### 4. Single Point of Failure

If the `NotificationSvc` database is unavailable, the batch job will fail silently (exception caught in `processEmailStatus()`). There is no alerting or circuit-breaker mechanism. A bounce spike that could indicate a fraudulent sending campaign goes undetected.

### 5. No Deduplication

The Mailgun API may return the same event for a message across multiple runs (within the 30-day retention window). The processor will `UPDATE` the same `mailgun_events_queue` row on each run, potentially overwriting a DELIVERED status with an older FAILED status if events are returned in non-chronological order.

## Integration Architecture

| Integration | Protocol | Data Sensitivity | Governance |
|---|---|---|---|
| NotificationSvc SQL Server | JDBC (mssql-jdbc 12.8.1) | PII (subscriber IDs) | Internal, TLS partially disabled |
| Mailgun Events API | HTTPS REST | PII (email delivery metadata) | Vendor DPA required |
| com.ecount:xPlatform | Library | N/A | Internal |

## Regulatory Architecture Alignment

| Regulation | Requirement | Status |
|---|---|---|
| Reg E | Consumer notification delivery evidence | Enabled by this service |
| CAN-SPAM | Honour bounces / unsubscribes | Data available; enforcement depends on consumer |
| GDPR Art 28 | DPA with processor (Mailgun) | Verify externally |
| GDPR Art 5(1)(e) | Data minimisation | Event data retained beyond operational need? |
| CCPA | Email as PII | Delivery records are personal data processing logs |
| PCI DSS | No direct card data | Low PCI scope |

## Modernisation Recommendations

1. **Migrate to webhook model**: Register a Mailgun webhook endpoint in `notification-framework_SVC` to receive events push-style. Deprecate polling in `mailgun-event-tracker`.
2. **Event sourcing**: Store all Mailgun events as immutable event records (not UPDATE pattern) to preserve full delivery history per message.
3. **Secret management**: Migrate all credentials to Azure Key Vault or Dapr secret store (pattern used in `manage-payment-rest-api`).
4. **Observability**: Add Micrometer metrics for bounce rate, delivery rate, failed events per run, and expose via `/actuator/metrics`.
5. **Stable dependency versions**: Pin `xPlatform` to a released version; remove `joda-time` in favour of `java.time`.
6. **Dead-letter handling**: Records that fail processing after N retries should be moved to a separate error table for manual review.
