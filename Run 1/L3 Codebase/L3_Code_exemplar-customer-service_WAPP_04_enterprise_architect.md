# Enterprise Architect View — exemplar-customer-service_WAPP

## Platform Generation
**Gen-3** — This is Onbe's reference architecture exemplar for cloud-native microservices. It demonstrates the target-state patterns: Spring Boot 2.x (on path to 3.x), Kubernetes, Dapr sidecar, Liquibase schema management, OpenAPI documentation, Pact contract testing, and Azure SQL with TLS-configurable data sources.

## Business Domain
**Reference Architecture / Platform Engineering** — Not a business domain service. This application exists to document and demonstrate correct architecture patterns for teams building new services. The customer entity is a synthetic placeholder; the real domain served is "how to build a service at Onbe."

## Role
- **Primary role**: Exemplar / template application for new service development.
- **Secondary role**: Demonstrates Dapr pub/sub integration, event publishing, and contract testing patterns.
- Acts as the authoritative example teams should follow for: multi-module Maven structure, Spring Boot configuration, TLS data source setup, Liquibase migrations, Kubernetes deployment manifests, Dapr sidecar configuration, Pact testing, and Cucumber acceptance testing.

## Dependencies
### Inbound (consumers)
- Development teams learning the reference architecture.
- CI/CD tooling that may fork this repo as a service template.

### Outbound (runtime)
| Dependency | Type |
|-----------|------|
| SQL Server / Azure SQL | Database |
| Dapr runtime (MQTT pub/sub) | Messaging infrastructure |
| Zipkin | Distributed tracing |
| PactFlow | Contract testing broker |
| Azure Container Registry | Image registry |
| Internal Nexus | Maven artifact resolution |

## Integration Patterns
- **Synchronous REST**: JSON and XML content-negotiated REST endpoints.
- **Asynchronous event publishing**: Dapr pub/sub for TheaterCreatedEvent (demonstrates event-driven pattern).
- **Contract testing**: Pact provider tests with PactFlow broker.
- **Schema management**: Liquibase changesets (code-first DB migration).
- **Service discovery**: Kubernetes Service (LoadBalancer type) for internal discovery.

## Strategic Status
**Active / Reference** — This is a living exemplar. It should be kept current with Onbe's evolving technology standards. It is not at risk of decommissioning; it is the target pattern.

Gaps vs Gen-3 ideal state:
- Spring Boot 2.4.5 should be upgraded to Spring Boot 3.x.
- Java 11 should be upgraded to Java 17 or 21 LTS.
- Hardcoded credentials must be replaced with Azure Key Vault / Azure App Configuration references before the exemplar is used as a production template.
- No Spring Security or API authentication implemented — exemplar is incomplete in security posture.
- Nexus URL references `d-na-stk01.nam.wirecard.sys` (Wirecard-era hostname) — should be updated to current Onbe artifact registry.

## Migration Blockers
- None for migration to Gen-3 — this IS the Gen-3 exemplar.
- Before copying as a production service template, resolve: credentials externalisation, Spring Boot version, Java version, and security layer.
