# Enterprise Architect Report — onbe-spring-boot-parent_PARENT

## Platform Generation

**Gen-3 (NexPay/Onbe) — foundational governance layer.** This POM is the topmost artifact in the Gen-3 dependency hierarchy. It inherits from `spring-boot-starter-parent:3.4.3` and defines the version governance for the entire Gen-3 microservices estate. It has no Gen-1 or Gen-2 artifacts in scope.

## Role in Platform Architecture

This POM establishes the platform "contract" — the agreed-upon versions of all third-party components that Gen-3 services may use. It is equivalent to an enterprise architecture standards document expressed as executable code. Changes to this POM are, in effect, changes to platform-wide technology standards.

The hierarchy is:
```
spring-boot-starter-parent:3.4.3 (Spring/VMware/Broadcom)
    └── onbe-spring-boot-parent:0.0.22-SNAPSHOT (this repo)
            └── onbe-spring-boot:0.0.22-SNAPSHOT (framework library)
                    └── [Individual Onbe Gen-3 microservices]
```

## Technology Stack Decisions

The parent POM canonically establishes Onbe's Gen-3 technology choices:

### Application Platform
- Spring Boot 3.4.x as the application runtime framework
- Spring Cloud Azure 5.20.x as the Azure integration layer
- Kotlin 2.1 as the primary language for framework code, with Java 21 for service implementation

### Reactive Stack
- Spring WebFlux + Project Reactor for reactive HTTP services
- R2DBC (SQL Server driver) for reactive database access
- Kotlin Reactor extensions (`reactor-kotlin-extensions`) for idiomatic Kotlin reactive code

### Event-Driven Architecture
- Dapr as the messaging/state/secrets abstraction layer
- Spring Cloud Stream with Dapr binder for message-driven services
- Apache Avro (1.12.0) for event schema definition and serialization
- Debezium (3.0.7) for SQL Server CDC-based event sourcing

### API Architecture
- API-first development with OpenAPI Generator (7.11.0) and SpringDoc
- Azure API Management integration (controlled by CI pipeline)
- Pact contract testing support (referenced in petstore deployment pipeline)

### Observability Stack
- Micrometer metrics → Prometheus
- OpenTelemetry distributed tracing (alpha instrumentation)
- Logstash JSON structured logging

### Data Storage
- Microsoft SQL Server (primary transactional store, R2DBC and JDBC)
- Redis via Lettuce (cache and rate limiting)
- Azure Blob Storage (via Spring Cloud Azure)

### Security
- Dapr + Azure Key Vault for secrets management
- MSAL4J + Azure Identity for managed identity / OAuth 2.0
- OWASP Encoder (1.3.1) for output encoding
- Resilience4j for circuit breakers and rate limiting

## Integration Patterns

- **Sidecar pattern (Dapr):** Every Gen-3 service runs with a Dapr sidecar injected by Kubernetes/AKS. The sidecar handles secrets, pub/sub, state, and observability.
- **API-first (OpenAPI):** All HTTP APIs are defined via OpenAPI specifications stored in the centralized `openapi-doc` repository and downloaded during builds.
- **Spring Modulith / jMolecules:** These dependencies indicate Onbe is evaluating modular design patterns for some services, potentially as a structured alternative to microservices sprawl.
- **Feature flags (Azure App Configuration):** Runtime feature flag evaluation via the Spring Cloud Azure App Configuration integration.
- **CDC (Debezium):** SQL Server CDC connector for event-driven patterns — applicable to payment ledger or card state change events.

## Migration Blockers (Gen-1/Gen-2 → Gen-3)

For services migrating to Gen-3, the parent POM itself is not a blocker — it is a target state. The blockers are:
1. Java version upgrade (Gen-1: ≤8, Gen-2: ≤11 → Gen-3: 21) — major migration
2. Reactive programming model adoption (blocking JDBC → R2DBC, Tomcat → Netty)
3. Struts/Axis/XML-RPC → Spring WebFlux/RestClient
4. Gen-1/Gen-2 secrets management → Dapr secret store
5. Monolithic deployment → containerized AKS deployment

## Strategic Status

**Strategic, actively governed, high criticality.** This is the single most impactful repository in the Gen-3 platform estate from a governance perspective. Any organization-wide technology decisions (e.g., Spring Boot upgrade, library security response, license compliance change) are implemented here first and propagate to all Gen-3 services.

**Governance recommendation:** This POM should have a formal release process with change advisory board review, integration testing against a representative set of Gen-3 service consumers before publication, and semantic versioning with a clear deprecation policy. The current SNAPSHOT release model is appropriate for development but should transition to a release version for production service consumption.
