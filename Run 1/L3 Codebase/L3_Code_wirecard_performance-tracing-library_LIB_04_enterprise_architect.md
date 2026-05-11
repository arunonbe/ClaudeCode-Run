# Enterprise Architect — wirecard_performance-tracing-library_LIB

## Platform Generation
**Gen-2 (Wirecard/Northlane) — Shared Library**. Spring Boot 2.0.7 BOM, Java 8, Gradle, Nexus. Part of the cross-cutting observability layer for the Wirecard Gen-2 platform.

## Business Domain
**Platform Observability / Cross-Cutting Concerns** — This library is infrastructure-level tooling that supports performance monitoring across all Gen-2 services.

## Role in the Wirecard Platform
- Shared library consumed by any Gen-2 Spring Boot service via `@EnablePerformanceTracing`
- Referenced in README as being used by `com.wirecard.checkagent` (check-agent service) example trace
- Part of the observability stack alongside Logstash/ELK and SonarQube
- Provides a lightweight alternative to full distributed tracing frameworks (no Zipkin/Jaeger/OpenTelemetry)

## System Dependencies
None at runtime — the library has no external service dependencies. It relies only on:
- Spring AOP (spring-boot-starter-aop)
- SLF4J (consumer service's Logback configuration)

## Integration Patterns
- **AOP/annotation-driven**: Single `@EnablePerformanceTracing` annotation activates the capability
- **Configuration-driven**: `performance.tracing.*` properties customise behaviour without code changes
- **Observer pattern**: Pure side-effect tracing; does not modify intercepted method behaviour

## Strategic Status
- **Current**: Active shared library, version 1.6.0
- **Strategic fit**: The performance tracing capability it provides is a valid Gen-3 concern, but the implementation approach (custom AOP library) is superseded by industry standards
- **Gen-3 replacement**: OpenTelemetry Java agent or Micrometer Tracing with a vendor backend (Datadog, Azure Monitor, AWS X-Ray) would replace this library entirely, providing richer distributed tracing across service boundaries

## Migration Path to Gen-3
1. Replace `@EnablePerformanceTracing` consumers with OpenTelemetry Java agent (zero-code instrumentation) or Micrometer Tracing
2. Route traces to cloud-native APM (Datadog, Azure Application Insights, or AWS X-Ray)
3. No data migration required — library produces only logs
4. Migration is low-risk: existing logging continues until library is removed; new tracing runs in parallel
5. Consuming services will need `@EnablePerformanceTracing` annotation removal as part of Spring Boot 3 upgrade
