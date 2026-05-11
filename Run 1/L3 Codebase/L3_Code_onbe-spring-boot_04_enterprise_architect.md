# Enterprise Architect Report — onbe-spring-boot

## Platform Generation

**Gen-3 (NexPay/Onbe).** This library is unambiguously Gen-3: it targets Java 21, Spring Boot 3.4.x, Spring Framework 6.2.x, Kotlin 2.1, reactive R2DBC, Azure Dapr integration, and Azure App Configuration. It has no dependency on Gen-1 (Struts, Axis, XML-RPC) or Gen-2 (Spring Boot ≤2.5, Wirecard/Northlane patterns). It is the foundational SDK for all new Onbe microservices.

## Integration Patterns

- **Dapr (Distributed Application Runtime):** Used as a secrets abstraction layer and as a potential messaging binder (`spring-cloud-stream-binder-dapr` managed in parent POM). Dapr provides a portable API over Azure Key Vault, Redis, Azure Service Bus, etc. This is Onbe's primary sidecar pattern for Gen-3 services.
- **Azure App Configuration / Feature Flags:** `AppConfigurationRefresh` is referenced in petstore server config (built on this framework), indicating Azure App Configuration is the feature flag and runtime config store for Gen-3 services.
- **OpenAPI / API-First:** The parent POM includes the `openapi-generator-maven-plugin` (v7.11.0) configured for Spring WebFlux delegate pattern, SpringDoc OpenAPI (v2.8.5), and APIM publication. All Gen-3 APIs are expected to be specification-first.
- **Spring Cloud Azure:** `spring-cloud-azure` (v5.20.0) provides identity, storage, and service bus integration. `azure-identity` supports managed identity authentication.
- **Reactive Stack (Project Reactor):** WebFlux, R2DBC, Reactor context propagation, BlockHound integration. All new Onbe services are expected to be non-blocking reactive.
- **Observability Pipeline:** Micrometer → Prometheus → Grafana. Distributed tracing via Zipkin/OpenTelemetry. Structured logs → Logstash → centralized SIEM.
- **Debezium CDC:** Managed in parent POM (SQL Server connector), indicating CDC-based event sourcing patterns are planned or in use for some Gen-3 services.
- **Spring Modulith / jMolecules:** Dependencies managed in parent POM, indicating Onbe is evaluating modular monolith and domain-driven design patterns as architectural alternatives to pure microservices.

## External Dependencies

| Dependency | Version | Purpose |
|---|---|---|
| Spring Boot | 3.4.3 | Core framework |
| Kotlin | 2.1.10 | Primary language for framework code |
| Dapr SDK | 1.13.3 | Secrets, pub/sub, state management |
| Spring Cloud Azure | 5.20.0 | Azure Key Vault, Service Bus, App Config |
| Resilience4j | 2.3.0 | Circuit breaker, retry, rate limiting |
| R2DBC (MSSQL) | 12.8.1.jre11 | Reactive SQL Server connectivity |
| Debezium | 3.0.7.Final | Change data capture (SQL Server) |
| OpenAPI Generator | 7.11.0 | API-first code generation |
| CycloneDX Maven Plugin | 2.9.1 | SBOM generation |
| OpenTelemetry | 2.13.1-alpha | Distributed tracing instrumentation |

## Position in Broader Platform

`onbe-spring-boot` occupies the foundational layer of the Gen-3 platform stack:

```
[Azure Infrastructure]
    |
[Azure APIM / App Gateway]
    |
[Gen-3 Microservices (consuming onbe-spring-boot)]
    |
[onbe-spring-boot framework layer]
    |
[onbe-spring-boot-parent (BOM / version management)]
    |
[Spring Boot 3.4.x + Spring Cloud Azure 5.x]
```

Every Gen-3 service that imports `onbe-spring-boot-starter` inherits: Dapr secrets, REST client standards, reactive patterns, structured logging, and Actuator observability. The framework is the primary enforcement mechanism for Onbe's engineering standards across the Gen-3 estate.

## Migration Blockers

- None from Gen-1/Gen-2 to Gen-3: this library does not need to migrate; it is a greenfield Gen-3 artifact.
- For Gen-1/Gen-2 services migrating to Gen-3: the primary migration blockers are Java version upgrade (from ≤8 to 21), blocking I/O to reactive I/O migration, and replacement of Struts/Axis/XML-RPC with Spring WebFlux/RestClient.
- The `spring-boot-thin-layout` dependency (v1.0.31.RELEASE) in the Azure Functions profile is a Spring experimental artifact that may not track with Spring Boot 3.x upgrades.

## Strategic Status

**Active, strategic, core platform asset.** This library is in active development (SNAPSHOT versioning, frequent Spring Boot version bumps per the README changelog). It represents Onbe's strategic commitment to Gen-3 Java/Kotlin/Azure microservices. All new Onbe services should depend on this framework. It should be subject to Onbe's highest levels of code review, security scanning, and release governance given its blast radius across the entire Gen-3 estate.
