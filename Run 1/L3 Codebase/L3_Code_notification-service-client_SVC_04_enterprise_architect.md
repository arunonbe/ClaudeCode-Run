# Enterprise Architecture — notification-service-client_SVC

## Platform Generation
**Gen-1 / Gen-2 (NorthLane / eCount)** — Legacy shared library from the NorthLane/Wirecard era, now consumed by Gen-1 and Gen-2 services within the Onbe portfolio.

## Business Domain
Notification / Communications. Provides the client-side abstraction for all outbound email notification dispatch across the legacy Onbe/NorthLane platform.

## Role in the Platform
| Attribute | Value |
|-----------|-------|
| Type | Shared client library (JAR) |
| Deployed standalone | No |
| Consuming platforms | Gen-1 / Gen-2 services (eCount-based, OnePlatform, clientzone, etc.) |
| Gen-3 relevance | Indirect — Gen-3 services should NOT import this library; they should use a Gen-3 notification client |

## Dependencies
### Upstream (callers of this library)
- Any Gen-1/Gen-2 Java service that needs to send email notifications (clientzone, account-management, enrollment flows, etc.).

### Downstream (services this library calls)
| Service | Protocol | Notes |
|---------|---------|-------|
| Notification Service REST API | HTTP/Feign | `${notification.urls.base-url}` |

### Library Dependencies
- `notification-event-handler-common:2.0.0-SNAPSHOT` — NorthLane internal.
- `notification-rest-controller:2.0.0-SNAPSHOT` — NorthLane internal.
- `correlation-web:1.0.0` — eCount correlation library.
- Spring Framework 4.3.27 (plain Spring, no Boot).
- OpenFeign 11.0.
- Resilience4j 1.6.1.

## Integration Patterns
- **Library / Shared Kernel** — imported as a Maven dependency, runs in-process with the consumer.
- **Circuit Breaker** — per-operation circuit breakers using Resilience4j; failure threshold, wait duration, and slow-call threshold configurable.
- **Correlation ID propagation** — `CorrelationIdInterceptor` injects correlation ID into outbound Feign headers.
- **Typed notification objects** — one class per notification event type; validated before sending.
- **Batch email** — create batch context, associate emails, release batch.

## Strategic Status
- **Legacy / Gen-1 artifact** — actively used but not on a Gen-3 migration path within this repo.
- The package namespace `com.northlane` and group ID confirm NorthLane (pre-Onbe) origin; SCM URL points to a GitLab instance at `northlane` organisation.
- For Gen-3 NexPay microservices, a new notification client should be built or the notification service should be called directly via the Gen-3 service-to-service REST pattern (not this library).
- Lombok 1.18.12 (2019 vintage); Feign 11.0 (early 2021) — all dependencies are 3-5 years behind current.

## Migration Blockers
- Callers importing this library on Java 8 / Spring 4.x cannot easily be upgraded without full service migration.
- SNAPSHOT dependencies mean build reproducibility is not guaranteed.
- Nexus at `wirecard.sys` must remain reachable until all consumers are migrated or the artifact is promoted to a stable internal registry.
- Low JaCoCo thresholds suggest test coverage is insufficient to validate behaviour during migration refactoring.
