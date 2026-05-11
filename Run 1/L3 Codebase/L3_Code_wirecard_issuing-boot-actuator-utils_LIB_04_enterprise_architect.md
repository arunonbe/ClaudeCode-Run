# Enterprise Architect Report — wirecard_issuing-boot-actuator-utils_LIB

## Platform Generation

**Gen-2 (Wirecard/Northlane) with Gen-3 build pipeline.** The library's business origin is Wirecard issuing (Gen-2), as evidenced by:
- Package name: `com.wirecard.issuing.opensource.actuator.utils`.
- Version naming: `issuing-boot-actuator-utils`.
- Consumed by Gen-2 services: sg-bank-agent, NAM bank agent, wire transfer agent, etc.

However, the build pipeline has been migrated to GitHub Actions with Java 21 and GitHub Packages, reflecting Gen-3 infrastructure practices. The library bridges Gen-2 business logic with Gen-3 build infrastructure.

## Integration Patterns

- **Library dependency pattern**: Consumed as a Maven JAR dependency by all Wirecard issuing microservices that expose a Spring Boot Actuator health endpoint.
- **Spring Boot Actuator extension**: Implements `StatusAggregator` and `StdSerializer<Health>` interfaces — standard Spring Boot extension points.
- **Monitoring integration**: The custom health format is designed for consumption by the Wirecard internal monitoring system (likely Nagios, Zabbix, or a custom poller based on the `overall_status_ok` boolean field pattern).

## External Dependencies

- `spring-boot-actuator` (version from parent BOM).
- `spring-webmvc`, `spring-core` (version from parent BOM).
- `jackson-databind`, `jackson-core` (version from parent BOM).
- `com.parents:prepaid-parent:6.0.12` — the Onbe shared parent POM governing all dependency versions.
- GitHub Packages (`onbe/onbe_maven_releases`) — artifact publication.

## Position in the Broader Platform

This library is a **cross-cutting infrastructure concern** for all Gen-2 issuing microservices. Any service that uses Spring Boot Actuator and inherits from `prepaid-parent` is expected to include this library to produce the standard Wirecard health response format. It is a governance-level artefact for operational monitoring consistency.

In the Gen-3 migration context, the library has been updated to Java 21 and republished with GitHub Actions, suggesting it is intended to remain relevant through the Gen-2 to Gen-3 transition. However, Gen-3 services using Micrometer/OpenTelemetry may not need this custom actuator format if monitoring is migrated to Azure Monitor or Prometheus.

## Migration Blockers

- If Gen-3 services adopt OpenTelemetry for health and observability, this library becomes unnecessary. The `overall_status_ok` / `reply_host` / `cached_ts` format would be replaced by standard Prometheus metrics or Azure Monitor custom metrics.
- The `CustomHealthAggregator` logic (critical vs. non-critical indicator differentiation) would need to be replicated in whatever health aggregation approach Gen-3 adopts.

## Strategic Status

**Maintenance mode — targeted for replacement in Gen-3.** The library provides value in the Gen-2 environment by standardizing health endpoint format. For Gen-3, the recommendation is to adopt OpenTelemetry health probes and Azure Monitor integration rather than continuing to maintain a custom actuator serializer. The bug in `getAggregateStatus()` (see Solution Architect report) should be fixed in the next release regardless, as it affects all consuming services' health rollup logic.
