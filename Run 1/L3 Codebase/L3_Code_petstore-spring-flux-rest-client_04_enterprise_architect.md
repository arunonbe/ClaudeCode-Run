# Enterprise Architect Report — petstore-spring-flux-rest-client

## Platform Generation

**Gen-3 (NexPay/Onbe) — reference WebFlux client implementation.** Unambiguously Gen-3: Java 21, Spring WebFlux (`WebClient`), Reactor retry patterns, Micrometer observation, OpenAPI client code generation, virtual threads, Testcontainers, WireMock, and `onbe-spring-boot-parent:0.0.22-SNAPSHOT`.

## Role in Platform Architecture

This repository demonstrates the client-side half of the Gen-3 HTTP integration pattern. In production, every Onbe Gen-3 microservice that calls an external or internal API is expected to use a `WebClient`-based integration following this reference. The repository serves as:

1. A consumed library — other services import `petstore-spring-flux-rest-client-api` to get generated client stubs
2. A reference implementation — engineers copy patterns from `WebClientCustomizer`, `AppConfig`, and `WebClientConfigProperties`
3. A test harness — `PetStoreWireMockDSLTests` and `PetStoreAcrImageTestContainerTests` demonstrate how to write integration tests for WebClient-based services

The relationship between this repo and the server repo creates the complete Gen-3 HTTP client-server pattern:

```
[petstore-spring-flux-rest-client] (WebClient consumer)
    --> [HTTP/HTTPS] --> [petstore-spring-flux-rest-server] (WebFlux producer)
    
Both publish via:
[GitHub Packages (Maven)] <-- used by other Onbe services
```

## Integration Patterns

- **WebFlux WebClient (non-blocking):** The primary HTTP client technology for reactive Gen-3 services. Unlike `RestClient` (used in MVC services), `WebClient` is fully non-blocking and integrates with Project Reactor's reactive streams.
- **ExchangeFilterFunction (cross-cutting concerns):** `retryFilter` is applied as a `WebClient.Builder` exchange filter — the reactive equivalent of a servlet filter or RestClient interceptor. Patterns for logging, authentication header injection, correlation ID propagation, and retry all follow this pattern.
- **OpenAPI client generation:** The `-api` module uses `openapi-generator-maven-plugin` (configured in parent) to generate reactive `DefaultApi` client stubs from the Petstore OpenAPI spec, enabling type-safe API invocation.
- **ACR Testcontainers:** `PetStoreAcrImageTestContainerTests` pulls the petstore server image from Azure Container Registry for black-box integration testing — demonstrates how to write end-to-end integration tests against real service images.
- **WireMock contract testing:** `PetStoreWireMockDSLTests` demonstrates consumer-side WireMock stubs for unit testing the client without a live server.
- **Pact (consumer side):** The test resources and structure suggest consumer-driven contract testing (the petstore server's `deployment.yml` references `petstoreflux-api` as the Pact pacticipant).

## External Dependencies

| Dependency | Version | Purpose |
|---|---|---|
| Spring WebFlux | 3.4.3 | Reactive HTTP client (WebClient) |
| Reactor Core | Via Spring Boot BOM | Reactive streams runtime |
| OpenAPI Generator | 7.11.0 (from parent) | Client stub generation |
| Micrometer Observation | Via Spring Boot BOM | HTTP client metrics and tracing |
| WireMock | 3.12.0 (from parent) | Contract test mock server |
| Testcontainers | 1.20.5 (from parent) | ACR image integration testing |
| onbe-spring-boot-starter | 0.0.22-SNAPSHOT | Onbe framework defaults |
| Dapr SDK | 1.13.3 (from parent) | Secrets (test only) |

## Comparison: WebFlux Client vs. MVC RestClient

This repo uses `WebClient` (WebFlux, reactive) while `petstore-spring-mvc-rest-client` uses `RestClient` (Spring MVC, blocking with virtual threads). The choice between them:

| Criterion | WebClient (this repo) | RestClient (MVC repo) |
|---|---|---|
| Thread model | Non-blocking reactive | Blocking (virtual threads) |
| Use case | Reactive WebFlux services | Imperative MVC services |
| Retry pattern | `ExchangeFilterFunction` | `ClientHttpRequestInterceptor` |
| Observation | `ObservationRegistry` on builder | `ObservationRegistry` on builder |
| Complexity | Higher (reactive operators) | Lower (familiar synchronous code) |

## Strategic Status

**Active reference implementation, companion to `petstore-spring-flux-rest-server`.** Both should be maintained together as the canonical Gen-3 WebFlux client-server pair. The critical retry filter bug (see 05_solution_architect.md) must be fixed before any production service copies this pattern. Once corrected, this serves as the authoritative reference for Onbe teams building reactive API clients.
