# Enterprise Architect Report — petstore-spring-mvc-rest-client

## Platform Generation

**Gen-3 (NexPay/Onbe) — reference Spring MVC client implementation.** While the application pattern is imperative (blocking + virtual threads) rather than reactive, it is fully Gen-3 in its dependencies: Java 21, Spring Boot 3.4.3, `onbe-spring-boot-parent:0.0.22-SNAPSHOT`, Spring `RestClient` (Spring Boot 3.2+ API), Micrometer Observation, OpenAPI Generator 7.11.0, and virtual threads. This is the recommended path for Gen-2 teams migrating to Gen-3 who are not yet adopting the reactive programming model.

## Role in Platform Architecture

This repository occupies the "imperative Gen-3 client" niche — complementary to the "reactive Gen-3 client" (`petstore-spring-flux-rest-client`). Together, they cover the two canonical HTTP client patterns for Gen-3:

| Pattern | Repository | HTTP Client | Thread Model |
|---|---|---|---|
| Reactive (WebFlux) | petstore-spring-flux-rest-client | `WebClient` | Non-blocking reactor threads |
| Imperative (MVC) | petstore-spring-mvc-rest-client | `RestClient` | Blocking + virtual threads |

The MVC pattern is strategically important for Onbe's Gen-2 → Gen-3 migration path:
- Gen-2 services built on Spring Boot 2.x with `RestTemplate` can migrate to `RestClient` (same mental model, blocking I/O) without adopting reactive programming
- Virtual threads provide the concurrency benefits (previously requiring reactive programming) with the simplicity of blocking code
- This pattern reduces migration risk for teams unfamiliar with reactive programming

## Integration Patterns

- **RestClient (Spring Boot 3.2+ imperative HTTP client):** Replaces `RestTemplate` as the standard blocking HTTP client. Shares the same builder, customizer, and interceptor patterns as `RestTemplate` but with a modern fluent API.
- **`ClientHttpRequestInterceptor` (cross-cutting concerns):** `RetryRateLimitRequestInterceptor` from `onbe-spring-boot` applies retry and header defaults via Spring's request interceptor pattern — the MVC equivalent of WebFlux's `ExchangeFilterFunction`.
- **OpenAPI client generation (synchronous):** Unlike the WebFlux client which generates reactive (`Mono`/`Flux`) stubs, the MVC client generates blocking client interfaces. The `openapi-generator-maven-plugin` configuration in the parent POM generates reactive code by default (`<reactive>true</reactive>`) — the MVC client module's API pom must override this to `<reactive>false</reactive>` for synchronous generation.
- **`RestClientCustomizer`:** `PetStoreRestClientCustomizer` implements `RestClientCustomizer` (Spring Boot's auto-configuration hook), which is the correct integration point for customizing the auto-configured `RestClient.Builder`. This is the MVC equivalent of `WebClientCustomizer`.
- **Micrometer Observation:** Same pattern as the WebFlux client — `ObservationRegistry` wired into the builder for automatic HTTP client instrumentation.

## External Dependencies

| Dependency | Version | Purpose |
|---|---|---|
| Spring MVC | 3.4.3 | Imperative HTTP server (Tomcat) |
| Spring RestClient | 3.4.3 | Blocking HTTP client |
| OpenAPI Generator | 7.11.0 (from parent) | Synchronous client stub generation |
| Micrometer Observation | Via Spring Boot BOM | HTTP client metrics and tracing |
| Log4j2 | Via Spring Boot BOM | Async structured logging |
| LMAX Disruptor | 3.4.4 (from parent) | Async log queue for Log4j2 |
| onbe-spring-boot-starter | 0.0.22-SNAPSHOT | Onbe framework defaults |
| `SimpleClientHttpRequestFactory` | Spring core | Basic HTTP connection factory |

## Key Architecture Differences vs. WebFlux Client

The most significant architectural difference is the HTTP client factory:
- **WebFlux client:** Uses Reactor Netty's `ClientHttpConnector` (non-blocking event loop, connection pooling, HTTP/2 support)
- **MVC client:** Uses `SimpleClientHttpRequestFactory` (blocking `HttpURLConnection`, no pooling, HTTP/1.1 only)

For production payment API clients, the MVC reference should be updated to use `JdkClientHttpRequestFactory` (Java 11+ `HttpClient`) as the factory, which provides connection pooling and TLS customization while remaining blocking-compatible with virtual threads. This is the pattern used in `onbe-spring-boot`'s `WebAutoConfiguration`.

## Strategic Status

**Active reference implementation for the Gen-2 → Gen-3 migration path.** This repository is strategically important for Onbe's migration journey. Teams migrating Spring Boot 2.x `RestTemplate`-based clients to Gen-3 should use this as their target reference. The repository should be maintained alongside the reactive client reference to provide both migration paths.

Key improvement needed before this can be fully endorsed as the canonical MVC reference: replace `SimpleClientHttpRequestFactory` with `JdkClientHttpRequestFactory` (consistent with `onbe-spring-boot`'s `WebAutoConfiguration`), add Dapr secrets integration to demonstrate the Gen-3 secrets pattern, and resolve the Log4j2/Logstash logging conflict.
