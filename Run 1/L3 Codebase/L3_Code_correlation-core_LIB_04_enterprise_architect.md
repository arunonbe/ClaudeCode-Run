# correlation-core_LIB — Enterprise Architect View

## Platform Generation (Gen-1/Gen-2/Gen-3)

**Assessment: Gen-2 library with Gen-3 applicability.**

Evidence:
- Java 21 compiler target (`pom.xml` lines 21–22) — current LTS, compatible with modern containerised runtimes.
- Parent BOM `com.parents:prepaid-parent:6.0.12` indicates integration into Onbe's existing internal Maven ecosystem (not a cloud-native starter or Spring Boot 3.x autoconfigure).
- No Spring Boot autoconfiguration, no reactive/non-blocking support, no OpenTelemetry integration — patterns consistent with a Gen-2 shared library.
- The original author comment `"Created by fabio.oliveira on 25.06.2016"` (in `CorrelationExecutorServiceDecorator.java` and `CorrelationThreadFactoryDecorator.java`) places the library's origins in 2016, making it a long-lived cross-cutting component.
- The code itself is clean, minimal, and dependency-light — no barriers to Gen-3 adoption other than missing reactive-stream and OpenTelemetry propagation support.

## Business Domain

**Cross-cutting infrastructure / observability platform.** This library does not encode any payments business logic. It is a horizontal concern that serves all Onbe business domains:
- Prepaid card disbursements
- ACH/push-to-card payouts
- Incentive and refund processing
- Marketplace and gig/creator payouts

All domains require end-to-end transaction traceability for PCI DSS, SOC 2, and Reg E compliance.

## Role in Platform

`correlation-core` is a **foundational infrastructure library** — one of the lowest-level shared components in the Onbe JVM platform. Its role is analogous to a tracing context propagator in modern observability frameworks. Specifically:

- It is the authoritative source for the `correlationId` MDC key name and the `CORRELATION-ID` / `APP_CorrelationID` header names used across all HTTP and JMS integrations.
- It defines the propagation contract for async work (thread pools, executors) within any consuming service.
- Without it (or a replacement), all Onbe services lose the ability to correlate log events across threads and service calls — directly impacting incident response, fraud investigation, and regulatory audit capability.

Consumer services are expected to:
1. Call `CorrelationIDContext.requiresNew(headerValue)` at inbound request boundaries.
2. Use `CorrelationExecutorServiceDecorator` or `CorrelationCallable`/`CorrelationRunnable` for all thread-pool work.
3. Read `LogContextConstants` for header names when forwarding requests.

## Dependencies

### Upstream (this library depends on)
| Dependency | Type | Notes |
|---|---|---|
| `com.parents:prepaid-parent:6.0.12` | Maven parent BOM | Governs all transitive dependency versions |
| SLF4J API (`org.slf4j.MDC`) | Runtime | Core mechanism — MDC thread-local context |
| Lombok | Compile-time | `@Slf4j` on `CorrelationIDContext`, `CorrelationExecutorServiceDecorator` |
| Log4j2 (test scope) | Test only | `log4j2-test.xml` config |
| JUnit 5 | Test scope | `CorrelationLogTest` |

### Downstream (services that depend on this library)
Not enumerable from this repository alone. Any Onbe JVM service that uses correlated logging or the `CORRELATION-ID` HTTP header should be a consumer. The `LogContextConstants` header name constants are the integration contract.

## Integration Patterns

| Pattern | Mechanism | Details |
|---|---|---|
| Thread-local context propagation | SLF4J MDC | Core pattern — `CorrelationIDContext` reads/writes `MDC.put/get/remove` |
| Decorator pattern | `CorrelationExecutorServiceDecorator`, `CorrelationThreadFactoryDecorator` | Transparent wrapping of `ExecutorService` and `ThreadFactory` |
| Template method pattern | `CorrelationCallable`, `CorrelationRunnable` | Abstract base classes with `doCall()`/`doRun()` hook methods |
| HTTP header propagation | `LogContextConstants.CORRELATION_ID_HEADER = "CORRELATION-ID"` | Constant only — actual filter/interceptor code lives in consumer services |
| JMS header propagation | `LogContextConstants.JMS_CORRELATION_ID_HEADER = "APP_CorrelationID"` | Constant only — actual message listener code lives in consumer services |

**Notable absence:** No support for reactive streams (Project Reactor `Context`, RxJava `Hooks`), no OpenTelemetry `Context` propagation, no Spring `TaskDecorator`. This limits applicability in reactive/WebFlux services without additional integration work.

## Strategic Status

**Status: Active, stable, strategically important but in need of modernisation.**

- The library is actively maintained (version `2.0.1`, Java 21, weekly Dependabot, CodeQL scanning).
- It is strategically critical — removing it without a replacement would break the audit trail across the entire platform.
- The core logic is correct and battle-tested (originated 2016, in active use).
- Modernisation gaps relative to Gen-3 / cloud-native expectations:
  - No OpenTelemetry trace/span context integration (the industry standard for distributed tracing).
  - No Spring Boot autoconfiguration module.
  - No reactive (non-blocking) propagation support.
  - The `invokeAll`/`invokeAny` gap is a known defect that should be addressed.

## Migration Blockers

| Blocker | Severity | Description |
|---|---|---|
| Hardcoded MDC key `"correlationId"` | Medium | Changing the key name requires coordinated update across all consuming services and their log parsing rules. |
| Hardcoded header names | Medium | `CORRELATION-ID` (HTTP) and `APP_CorrelationID` (JMS) are compile-time constants; renaming requires a new major version and consumer migration. |
| No OpenTelemetry integration | High (for Gen-3) | Gen-3 cloud-native services are expected to use OTel W3C TraceContext (`traceparent` header). The current library uses a proprietary header (`CORRELATION-ID`) that is not OTel-compatible. A bridge or replacement is required for Gen-3 services. |
| No reactive support | High (for reactive services) | MDC is thread-local; in Project Reactor / WebFlux the reactive `Context` must be used instead. This library cannot propagate IDs in reactive pipelines without changes. |
| Parent BOM coupling | Low-Medium | The library depends on `prepaid-parent` for all dependency versions. Upgrading to a Gen-3 Spring Boot parent would require decoupling from this BOM. |
| Tests skipped in CI | Low | No automated regression safety net; migration changes cannot be validated automatically without fixing the CI pipeline. |
