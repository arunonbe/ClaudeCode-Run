# Business Analyst Report — petstore-spring-flux-rest-client

## Business Purpose

`petstore-spring-flux-rest-client` is a Gen-3 reference implementation demonstrating how to build a reactive HTTP client application using Spring WebFlux (`WebClient`) that consumes a REST API described by an OpenAPI specification. It is the companion client to `petstore-spring-flux-rest-server`, and together they form a complete client-server reference pair for Onbe's Gen-3 WebFlux programming model.

Its primary value is as a template and learning artifact for Onbe engineering teams who need to build services that act as HTTP clients — calling external or internal APIs in a reactive, non-blocking manner. In a payments context, this pattern is used extensively for services that call card network APIs, banking APIs, merchant enrichment services, fraud detection APIs, and other downstream payment infrastructure.

## Capabilities

- **Reactive WebClient-based HTTP client:** Uses Spring `WebClient` (not `RestClient`) for fully non-blocking, reactive outbound HTTP calls — appropriate for WebFlux-based services.
- **OpenAPI-generated client code:** The `-api` module contains generated client interfaces from the Petstore OpenAPI specification. The `PetStoreClient` wraps the generated `DefaultApi` with a blocking facade (`.block()` calls), demonstrating how to expose a reactive client as a synchronous service layer.
- **Rate-limit retry handling:** `WebClientCustomizer` applies a retry `ExchangeFilterFunction` that retries on HTTP 429 (Too Many Requests) with a fixed 1-second delay, up to 3 attempts — the reactive WebClient analog of the MVC `RetryRateLimitRequestInterceptor`.
- **Micrometer observation integration:** `WebClientCustomizer` optionally wires `ObservationRegistry` into the `WebClient.Builder` for automatic HTTP client metric and trace instrumentation.
- **Testcontainers integration:** The boot module includes `PetStoreAcrImageTestContainerTests` and related test classes that pull actual container images from Azure Container Registry (ACR) for integration testing.
- **WireMock contract testing:** `PetStoreWireMockDSLTests` and `PetStoreWireMockTestContainerTests` demonstrate WireMock-based API contract testing patterns.
- **Postman integration:** `PostmanTestContainersTests` and the Postman `QA_LB.postman_environment.json` suggest Postman/Newman is used for API environment testing.

## Client/Cardholder Impact

As a reference implementation, there is no direct cardholder impact. The patterns demonstrated — reactive HTTP client with retry, OpenAPI-generated client, observation integration — are used in production payment services. Correct implementation of retry logic and error handling in these patterns directly affects the reliability of downstream payment API calls (card authorization, disbursement, balance inquiry).

## Business Rules in Code

- Rate-limit retry: Fixed 3 attempts with 1-second delay when HTTP 429 is received (`WebClientCustomizer.retryFilter(3)`).
- The `PetStoreClient` exposes a blocking API (`.block()`) over the reactive `DefaultApi`. This is a deliberate design choice for use cases where the consuming code is not reactive (e.g., a scheduled task or a REST controller on the MVC stack). The comment on the class makes this explicit ("Simple blocking PetStore client").
- `WebClientConfigProperties` (`petstore.webclient.base-url`, `petstore.webclient.timeout`) configures the WebClient base URL and timeout from application properties.

## Regulatory Obligations

As a reference/demo application with no production CHD: no direct PCI DSS, NACHA, or OFAC obligations. As a template for payment API client implementations:
- Retry logic must not retry on authentication failures (HTTP 401/403) — only on transient failures.
- HTTP client observation must not capture request/response bodies containing CHD in Micrometer trace spans.
- TLS/HTTPS must be enforced for all production API calls — the WebClient base URL must use `https://`.

## Key Business Risks

- The `retryFilter` in `WebClientCustomizer` throws `RuntimeException("Too Many Requests")` and then calls `retryWhen(Retry.fixedDelay(...)).then(Mono.just(clientResponse))`. This retry logic has a subtle bug: the `retryWhen` is applied to the `Mono.error(...)`, not to the original request. The original request is NOT retried — only the error signal is retried (which always produces another `RuntimeException`). In effect, this retry filter does not actually retry the HTTP request; it creates an infinite loop of errors until maxAttempts is exhausted, then throws. Teams adopting this pattern will have broken rate-limit retry behavior.
- The `PetStoreClient.findPets()` and other `.block()` calls — if this code is used from within a reactive WebFlux pipeline, the `.block()` will cause `IllegalStateException` at runtime (blocking call not allowed on reactive scheduler). This is the intended use case warning but may not be obvious to all consumers.
