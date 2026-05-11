# cicd-testlib_LIB — Enterprise Architect View

## Platform Generation (Gen-1/Gen-2/Gen-3)

**Classification: Gen-1 / Legacy**

Evidence:
- Parent POM `com.citi.prepaid:module-parent:7` indicates Citi/prepaid estate origin — the earliest identifiable platform generation.
- Group ID `com.ecount.opensource` and SCM URL `gitlab.com/northlane/development/application-development/libraries/cicd-testlib.git` confirm the library transitioned through the ecount → Northlane lineage before reaching Onbe.
- Java 8 compilation target (source/target = 8 in `pom.xml` lines 74–75).
- Dependencies (SLF4J 1.7.7 from 2014, Log4j2 2.1 from 2014, TestNG 6.8.21) are vintage 2014–2015 vintages.
- Version remains `1.0.0-SNAPSHOT` — no formal release has been cut, suggesting the library has been maintained informally.
- The original developer attribution (`Created by fabio.oliveira on 25.06.2016` in `CorrelationExecutorServiceDecorator.java` line 18 and `CorrelationThreadFactoryDecorator.java` line 6) dates active development to 2016.

No Gen-2 or Gen-3 framework patterns (Spring Boot auto-configuration, reactive programming, cloud-native observability) are present.

## Business Domain

**Cross-cutting infrastructure concern — Observability / Distributed Tracing**

This library does not belong to a single business domain. It is a horizontal platform utility that supports all domains (payments, disbursements, prepaid card management, incentives) by enabling log correlation across threads and services. In domain terms, it is part of the **Platform Services** layer, specifically the **Logging & Observability** sub-domain.

## Role in Platform

`cicd-testlib` is a **shared library** (JAR dependency) consumed by application services at compile time. Its role in the broader platform architecture is:

1. **Log correlation infrastructure**: Enables end-to-end tracing of business transactions (e.g., a disbursement request) across service boundaries and thread pools by propagating a UUID-based correlation ID.
2. **Naming convention enforcer**: Defines the canonical constant names for the correlation ID across three transport protocols (HTTP, JMS, MDC) via `LogContextConstants`. This makes it a de-facto platform standard for log key naming.
3. **Thread-safety wrapper**: Provides decorator patterns (`CorrelationExecutorServiceDecorator`, `CorrelationThreadFactoryDecorator`) that any service using Java thread pools must adopt to preserve log correlation.

**Consumers**: Any service in the ecount/Northlane/Onbe application estate that uses `ExecutorService`, JMS consumers, or HTTP filters for correlation ID propagation.

## Dependencies

### Upstream (what this library depends on)
| Artefact | Version | Risk |
|---|---|---|
| `com.citi.prepaid:module-parent:7` | 7 | Parent POM from legacy Citi/prepaid estate; ownership and maintenance status unknown |
| `org.slf4j:slf4j-api` | 1.7.7 | Outdated; should be 2.0.x for modern compatibility |
| `org.apache.logging.log4j:*` | 2.1 (test) | Critically outdated; Log4Shell vulnerable |
| `org.testng:testng` | 6.8.21 (test) | Outdated; current is 7.x |

### Downstream (what depends on this library)
Not determinable from this repository alone. Consuming services would declare `com.ecount.opensource:cicd-testlib` as a Maven dependency. A search of other platform repositories for this artifact ID would identify all consumers.

### External Services
- GitLab (`gitlab.com/northlane/...`) — SCM origin
- GitHub (`github.com/Onbe/om-ci-setup`, `maven.pkg.github.com/onbe/onbe_maven_releases`) — current CI and artefact registry
- Wirecard internal Nexus (`d-na-stk01.nam.wirecard.sys:8081`) — legacy artefact registry, likely unreachable

## Integration Patterns

| Pattern | Implementation |
|---|---|
| **Decorator** | `CorrelationExecutorServiceDecorator` wraps `ExecutorService`; `CorrelationThreadFactoryDecorator` wraps `ThreadFactory` |
| **Template Method** | `CorrelationCallable.doCall()` and `CorrelationRunnable.doRun()` define the extension point; lifecycle (ID setup/teardown) is fixed in the base class |
| **Thread-Local Context** | SLF4J MDC stores correlation ID per-thread; `CorrelationIDContext` is a static facade over the MDC |
| **Constant Registry** | `LogContextConstants` acts as a shared vocabulary for key names across transports |
| **Shared Library / JAR** | Distributed as a Maven JAR dependency; no service mesh, no API, no HTTP endpoint |

No event-driven, reactive, or REST integration patterns are used within this library itself.

## Strategic Status

**Status: Maintenance-only / Migration Candidate**

- The library provides a useful capability (correlation ID propagation) but is implemented with 2014–2016 era technology.
- The industry-standard replacement is **OpenTelemetry** (OTEL), which provides standardised distributed tracing, context propagation across threads and network boundaries, and integration with modern observability platforms (Jaeger, Zipkin, Grafana Tempo, AWS X-Ray).
- Spring Boot 3.x (Micrometer Tracing + OTEL) provides built-in correlation ID propagation that supersedes all functionality in this library.
- The library should be retained only as long as consuming services have not migrated to Spring Boot 3.x / OTEL. Once all consumers are on the modern stack, this library can be deprecated.

## Migration Blockers

| Blocker | Detail | Migration Path |
|---|---|---|
| Unknown consumer surface | Cannot determine how many services declare `com.ecount.opensource:cicd-testlib` as a dependency without scanning all platform repos | Scan all `pom.xml` files across the estate; build a dependency graph |
| `LogContextConstants` key names embedded in logging configs | Consuming services may have `log4j2.xml` / `logback.xml` / Splunk/ELK parsers hardcoded to `correlationId` and `APP_CorrelationID` | Align OTEL trace ID MDC key name with existing key or update all log parsers |
| JMS header name convention | `APP_CorrelationID` used as JMS header; migrating to OTEL W3C TraceContext (traceparent/tracestate) requires updating all JMS producers and consumers | Phased migration with dual-write period |
| Java 8 compilation target | Restricts adoption of newer Java language features or APIs; OTEL Java agent requires Java 8+ so this is not a hard blocker, but upgrading to Java 11 or 17 is a prerequisite for full Gen-3 migration | Update POM `<source>` / `<target>` to 17 as part of parent POM upgrade |
| `SNAPSHOT` version | Consuming services pinned to `1.0.0-SNAPSHOT` cannot get a stable, reproducible build | Cut a release version before deprecating SNAPSHOT |
