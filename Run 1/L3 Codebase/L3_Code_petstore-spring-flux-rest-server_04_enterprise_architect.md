# Enterprise Architect Report — petstore-spring-flux-rest-server

## Platform Generation

**Gen-3 (NexPay/Onbe) — reference implementation.** This is unambiguously Gen-3:
- Java 21
- Spring Boot 3.4.3 / Spring WebFlux (reactive)
- R2DBC (non-blocking database access)
- Dapr sidecar for secrets and messaging
- Azure App Configuration for feature flags and runtime config
- OpenAPI-generated API layer (delegate pattern)
- Containerized on BellSoft Liberica JRE 21 / Alpine
- Azure APIM publication
- GitHub Actions CI/CD with Pact contract testing

## Integration Patterns

- **API-First (OpenAPI):** API contract defined via central `openapi-doc` repository (`petstore/v2/petstore-expanded-openapi.yaml`), downloaded at build time, and code-generated into the `-api` module. All production Onbe Gen-3 services are expected to follow this pattern.
- **Delegate Pattern (OpenAPI Generator):** The generated code produces a `DefaultApi` interface and a `DefaultApiDelegate` interface. `PetStoreControllerDelegate` implements the delegate, keeping business logic separate from the generated routing layer. This is Onbe's canonical API implementation pattern.
- **Dapr Secrets (Sidecar):** Dapr sidecar injects secrets at startup via `DaprSecretsConfiguration`. In Kubernetes production, the Dapr sidecar is injected via the Dapr control plane.
- **Azure App Configuration / Feature Flags:** `AppConfigurationRefresh` polled on a scheduled interval (`PetStoreConfig.init()`), enabling runtime feature flag changes without redeployment.
- **Reactive Stack (Project Reactor):** All controller methods return `Mono<T>` or `Flux<T>`. R2DBC repository uses reactive streams. BlockHound verification ensures no blocking calls on Reactor schedulers.
- **Pact Contract Testing:** Consumer-driven contracts (`PACT_PACTICIPANT: petstoreflux-api`) — the server validates that its API responses match the expectations of registered consumers.
- **Internal APIM only:** The service is published to the internal Azure API Management instance, not the external gateway. This indicates it is an internal OnePlatform microservice, not a client-facing API.
- **Distributed Tracing (Brave/Zipkin):** `Tracer` (Brave) is injected into `PetStoreConfig`, enabling distributed trace context propagation through the reactive pipeline.

## External Dependencies

| Dependency | Version | Purpose |
|---|---|---|
| Spring Boot WebFlux | 3.4.3 | Reactive HTTP server |
| R2DBC MSSQL | 12.8.1 | Reactive SQL Server connectivity |
| Dapr SDK | 1.13.3 | Secrets, messaging abstraction |
| Spring Cloud Azure App Config | 5.20.0 | Feature flags, runtime config |
| Brave (Tracer) | Via Spring Cloud Sleuth/Micrometer | Distributed tracing |
| MapStruct | 1.6.3 | Entity-to-model mapping |
| Resilience4j | 2.3.0 | Retry (via Spring Retry @Retryable) |
| BellSoft Liberica JRE 21 Alpine | :21 (floating) | Container base image |
| onbe-spring-boot-starter | 0.0.22-SNAPSHOT | Onbe framework |
| Azure App Configuration | Feature Flags extension | Runtime feature toggles |

## Position in Broader Platform

```
[External client / Internal consumer (via APIM)]
    --> [Azure API Management (Internal)]
        --> [petstore-spring-flux-rest-server (AKS pod)]
            --> [Dapr sidecar] --> [Azure Key Vault]
            --> [Azure App Configuration] (feature flags)
            --> [SQL Server (petstore database)] (R2DBC)
            --> [petstore-spring-flux-rest-client] (consumer, contract test partner)
```

This service demonstrates the full Gen-3 integration topology in a deployable form. Its value is architectural demonstration, not business functionality.

## Migration Considerations

This service is entirely Gen-3 and has no Gen-1/Gen-2 migration debt. It exists to help Gen-1/Gen-2 teams understand what their target state looks like after migration. Teams migrating from Gen-1/Gen-2 should use this as:
- Reference for Spring WebFlux reactive API structure
- Reference for Dapr secrets integration
- Reference for Azure App Configuration feature flags
- Reference for GitHub Actions CI/CD pipeline structure
- Reference for Dockerfile and containerization patterns

## Strategic Status

**Active, strategic reference application.** This repository is more valuable as documentation and a template than as a production service. It should be maintained at the current version of `onbe-spring-boot-starter` and updated with each significant framework release to remain a valid reference. It should be treated as a "living documentation" artifact:
- Code should be clean, commented, and pedagogically clear
- Anti-patterns (double retry, commented-out production code) should be removed or clearly marked as demonstration artifacts
- Security posture should be exemplary — it is the template that production services copy from
