# Solution Architecture — notification-service-client_SVC

## Technical Architecture
- **Language / Runtime**: Java 8.
- **Framework**: Spring Framework 4.3.27 (plain Spring context, no Spring Boot).
- **HTTP client**: OpenFeign 11.0 with Jackson serialiser and SLF4J logger.
- **Resilience**: Resilience4j 1.6.1 circuit breaker; io.vavr `Try.ofSupplier` for error wrapping.
- **Package root**: `com.northlane.notification.restclient`.
- **Structure**: flat source tree; packages: `appConfig`, `configuration`, `exceptions`, `service/business`, `service/impl`.

## API Surface (library interface)
| Interface / Class | Method | Description |
|------------------|--------|-------------|
| `INotificationManager` | `deliver(batchId, notification, member, requestContext, description)` | Send email notification |
| `INotificationManager` | `createBatch()` | Create batch context |
| `INotificationManager` | `releaseBatch(batchId)` | Release batch for sending |
| `NotificationRestService` | `createNotification(input)` | Raw REST create |
| `NotificationRestService` | `handleNotification(event)` | Raw REST handle |
| `NotificationRestService` | `stopNotification(input)` | Raw REST stop |

## Security Posture
- **Authentication**: No authentication mechanism built into the Feign client — authentication headers must be configured externally by the consuming application or are absent.
- **Transport**: `${notification.urls.base-url}` — HTTP or HTTPS depending on configuration value; library does not enforce HTTPS.
- **Secrets**: No secrets stored in this library; the base URL and timeouts are injected by the consumer.
- **Correlation ID**: `CorrelationIdInterceptor` adds a correlation ID to each outbound request — no security function; tracing only.
- **CVE exposure**: 
  - `commons-lang:2.2` (2004) — known vulnerabilities exist in old Apache Commons Lang versions.
  - `regexp:1.3` (Apache ORO, 2001) — unmaintained; CVE history may apply.
  - Spring Framework 4.3.27 — reached EOL in December 2020; no further security patches.
  - `feign:11.0` — superseded by versions with security fixes.
  - Resilience4j 1.6.1 — check for known CVEs.

## Technical Debt
- Java 8 target — incompatible with modern Spring Boot 3+ / Jakarta EE; prevents direct use in Gen-3 services.
- `AbstractEmailNotification` uses raw `Hashtable` for `mergeData` and `attachmentInfo` — no generics, no type safety; deprecated API style.
- `validate()` in `AbstractEmailNotification` uses deprecated `StringValidator` from `com.ecount.core.utils` — tightly coupled to legacy eCount utility.
- `INotificationManager.deliver()` signature includes `Member` from `com.ecount.core.value` — tight coupling to legacy eCount domain model.
- `NotificationManagerImpl` not shown directly but its test `NotificationManagerImplTest` references it — internal implementation not independently reviewable here.
- Coverage thresholds (37% instruction, 27% branch) are well below the 80% industry standard.
- Multi-CI setup (GitLab + Jenkins + GitHub) — fragmented pipeline; unclear which is canonical.

## Code-Level Risks
| File | Risk |
|------|------|
| `AbstractEmailNotification.java:14` | Raw `Hashtable` for `mergeData` — thread-safe but legacy; NPE risk if caller passes null value |
| `AbstractEmailNotification.java:120-136` | Validation uses `com.ecount.core.utils.StringValidator` — external Gen-1 dependency; breaks if eCount library is removed |
| `NotificationServiceRestImpl.java:45-48` | `Try.ofSupplier(decoratedSupplier).get()` — Vavr `Try.get()` re-throws as unchecked `RuntimeException`; callers must handle unchecked exceptions |
| `HttpClientConfig.java:21-24` | `@Value` fields `read-timeout` and `connect-timeout` are `int` (milliseconds) — no unit annotation; callers must document units |
| `pom.xml:21-22` | `commons-lang:2.2` and `regexp:1.3` — extremely old; known CVEs in commons-lang prior to 2.6 |
| `pom.xml:14-15` | Nexus URL `http://d-na-stk01.nam.wirecard.sys:8080` — plain HTTP; artifact download is unencrypted |

## Gen-3 Migration Requirements
- **Do not import this library into Gen-3 NexPay services.** The Java 8 / Spring 4.x / eCount domain model coupling is incompatible with the Gen-3 stack.
- A Gen-3 notification client should be built using Spring Boot 3+, Java 21+, and the standard `RestClient` / WebClient pattern consistent with other Gen-3 service clients.
- During the migration period, Gen-3 services that must send notifications should either call the notification REST API directly or use a thin, Gen-3-compatible wrapper that avoids the eCount `Member` and `StringValidator` coupling.
- All SNAPSHOT library dependencies must be resolved to stable versions before the consuming services can be migrated.
