# Enterprise Architect Analysis — notification-framework_SVC

## Position in Onbe Platform Architecture

The notification framework is a **central shared platform service** used by all Onbe/Northlane payment programs. It sits in the communication layer of the platform:

```
Business Layer (program management, card management)
       ↓ XML-RPC calls to EventHandler
Notification Framework (event routing → template resolution → delivery)
       ↓ API calls
External delivery providers: Mailgun, Office 365 SMTP, IBM MQ
```

The framework is consumed by:
- Legacy applications via XML-RPC (`NotificationEventHandlerXMLRPCClient`)
- Modern services via REST (`notification-service-client_SVC`)

## Module Architecture

The four modules form a pipeline:

```
EventHandler → RulesEngine → Subscriber → Mailer
    ↑                                        ↓
  XML-RPC                              Mailgun/SMTP/SMS
  input                                    output
```

### EventHandler
Receives raw notification events. Has both a client (`notification-event-handler-client`) exposing `HandleNotificationXMLRPCInput`/`Output` for XML-RPC and an implementation module. Also exposes a REST endpoint (the modern path via `notification-service-client_SVC`).

### RulesEngine
Evaluates notification routing rules: which template to use, which channel to send on, under what conditions. This is the business logic layer — program-specific notification behaviour is encoded here.

### Subscriber
Listens to IBM MQ for notification requests from the rules engine output. IBM MQ provides reliable message delivery and decoupling between rules evaluation and actual delivery.

### Mailer
Resolves templates, merges data, delivers emails via Mailgun (primary) or SMTP. Tracks delivery via Mailgun events.

## Legacy Architecture Signals

### IBM MQ vs. Modern Messaging
The framework uses **IBM MQ** (v9.4.0.0) for internal messaging between modules. This is enterprise messaging from the mainframe era, indicating the framework predates cloud-native patterns. MQ provides:
- Guaranteed delivery (persistent messages)
- Transaction support
- Enterprise-grade message ordering

However, IBM MQ requires on-premises or IBM Cloud infrastructure, contrasting with the AWS SQS used in `nlutil-aws_INFRA_TF`. This suggests the notification framework may run on-premises or in a hybrid environment rather than purely on AWS.

### XML-RPC Interface
The `NotificationEventHandlerXMLRPCClient.java` and `NotificationnoMailerServlet.java` use XML-RPC, a protocol from the late 1990s. This indicates the framework has roots in the Citi prepaid era (`com.citi.prepaid.service.core` dependencies) and has been incrementally updated (Java 21, Mailgun integration) without full architectural replacement.

### Velocity Templates
Apache Velocity 2.3 is used for template merging. Velocity is a mature, stable choice for server-side template rendering, appropriate for the scale of this service (65,000 templates).

## Service Dependencies

| Dependency | Purpose | Type |
|---|---|---|
| IBM MQ | Message queuing between modules | Synchronous-ish messaging |
| Mailgun API | Email delivery | External SaaS |
| Office 365 SMTP | Legacy email (SMTP fallback) | External |
| Spring Config Server | Service configuration | Internal (nlutil) |
| Notification DB (Oracle/MS SQL) | Template storage, delivery queue | Internal |
| EhCache | Template metadata cache | In-process |
| `ecount-system`, `xplatform` | Legacy platform libraries | Internal |
| `director-client` | Director service client | Internal |

## Cross-Cutting Concerns

### Environment Routing (`NotificationMailerImpl.java` lines 349–376)
The `agent` property controls environment-specific email redirection. In stage/test environments, all outbound emails are redirected to `defaultToAddress`. This is a cross-cutting operational safety mechanism, but it relies on the `agent` string containing "stage" or "test" — a fragile string-match approach.

### EhCache Configuration
The `claude.md` notes 20 EhCache XML configuration files across the Mailer module. Cache sizes are set at 125,000 and 225,000 entries with `eternal=true`. Since the redesign stores only metadata (~500 bytes per entry), these large cache sizes are appropriate but represent configuration files that predate the redesign — they were intentionally left unchanged per the design doc.

## Architectural Debt Assessment

| Technical Debt Item | Risk | Effort to Resolve |
|---|---|---|
| XML-RPC interface (1990s protocol) | Medium (interop, security) | High (requires all callers to migrate) |
| IBM MQ (requires on-prem infrastructure) | Medium (operational cost) | High |
| `quartz:1.6.3` deserialization risk | High (security) | Low (library upgrade) |
| SMS delivery stub (not implemented) | High (business gap) | Medium |
| Fax delivery stub | Low (obsolete channel) | Low |
| `com.citi` group IDs in dependencies | Low (naming only) | Medium |
| `admin@localhost` in email sender | Medium (email deliverability) | Low |
| Tests skipped in CI | High (quality risk) | Low (enable tests) |

## Scalability Architecture

The Mailer's bottleneck is the stored procedure call per email send (50ms DB round-trip). At 100 concurrent email sends, this is 5 seconds of DB query load from just this service. The framework does not appear to implement connection pooling configuration or async delivery within this codebase (delivery is synchronous from the Mailer's perspective).

For peak notification volumes (e.g., mass card activation event), the system may need horizontal scaling of the Mailer service, with corresponding database connection pool sizing and stored procedure performance tuning.
