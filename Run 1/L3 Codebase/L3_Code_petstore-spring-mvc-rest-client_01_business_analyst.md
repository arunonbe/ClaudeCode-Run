# Business Analyst Report — petstore-spring-mvc-rest-client

## Business Purpose

`petstore-spring-mvc-rest-client` is a Gen-3 reference implementation demonstrating how to build a Spring MVC (imperative/blocking) HTTP client application using Spring's `RestClient` that consumes a REST API described by an OpenAPI specification. It is the Spring MVC counterpart to `petstore-spring-flux-rest-client` (which uses reactive `WebClient`), and provides the canonical template for Onbe engineering teams building imperative HTTP client services on Spring Boot 3.4.x with Java 21 virtual threads.

In Onbe's payment processing context, many services use imperative (non-reactive) Spring MVC patterns — particularly older Gen-2 services being migrated to Gen-3, background batch services, and administrative microservices that don't require the complexity of reactive programming. This reference application shows these teams how to correctly configure a `RestClient` with proper timeout management, retry logic, Micrometer observation integration, and OpenAPI-generated client stubs.

## Capabilities

- **RestClient-based HTTP client (blocking + virtual threads):** Uses Spring `RestClient` (Spring Boot 3.2+ replacement for `RestTemplate`) for outbound HTTP calls. Virtual threads are enabled (`spring.threads.virtual.enabled: true`), making blocking calls on virtual threads efficient for high-concurrency scenarios.
- **OpenAPI-generated client code:** The `-api` module contains generated synchronous client interfaces from the Petstore OpenAPI specification. Unlike the WebFlux client, the generated stubs here return plain objects (not `Mono`/`Flux`), appropriate for Spring MVC consumers.
- **RetryRateLimitRequestInterceptor (from onbe-spring-boot):** `AppConfig` applies the `RetryRateLimitRequestInterceptor` from the `onbe-spring-boot` framework as a `ClientHttpRequestInterceptor`, using `SimpleClientHttpRequestFactory` for basic HTTP connections.
- **Micrometer observation integration:** `PetStoreRestClientCustomizer` registers the `ObservationRegistry` with the `RestClient.Builder` for automatic HTTP client metric and trace instrumentation.
- **Log4j2 structured logging:** The boot module includes a `log4j2-spring.xml` configuration that uses async loggers for improved logging throughput, with rolling file appender for `staging`/`prod` profiles.
- **Jackson customization:** `jacksonCustomizer()` disables `failOnUnknownProperties`, making the client resilient to API changes that add new fields — a good defensive client configuration.

## Client/Cardholder Impact

As a reference/demo application with no production cardholder data: no direct impact. As a template for Gen-3 MVC HTTP client services, the patterns here directly inform how production payment API client services are built. Correct timeout configuration, retry logic, and error handling in these patterns affect the reliability of integrations with card networks, banking APIs, and payment gateways.

## Business Rules in Code

- HTTP connection timeout: Configured via `onbe.rest.client.connectTimeout` (default 10s from `onbe-spring-boot` `RestClientConfiguration`).
- HTTP read timeout: Configured via `onbe.rest.client.readTimeout` (default 10s from `RestClientConfiguration`).
- `AppConfig` uses `SimpleClientHttpRequestFactory` for connection management, which is the simplest (non-pooled) HTTP client factory in Spring. For production payment services with high throughput, a pooled HTTP client (Apache HttpComponents or JDK's `HttpClient`) should be used instead.
- Jackson `failOnUnknownProperties=false` — client will not fail if the server returns additional JSON fields not in the generated model — forward-compatible deserialization.
- `petstore.restclient.base-url` and `petstore.restclient.timeout` are the client-specific configuration properties, separate from the framework-level `onbe.rest.client.*`.

## Regulatory Obligations

As a reference/demo application: no direct regulatory obligations. As a template for production payment API clients:
- Retry logic must not retry on authentication failures (HTTP 401/403).
- All production API connections must use HTTPS (TLS).
- HTTP client observation must not capture Authorization headers or CHD in Micrometer trace spans.
- Connection timeouts must be set appropriately to prevent thread exhaustion under slow API responses.

## Key Business Risks

- `SimpleClientHttpRequestFactory` is non-pooled — each HTTP request opens and closes a new TCP connection. Under high throughput (e.g., batch disbursement with thousands of API calls), this creates significant overhead. Teams using this as a production template without changing the HTTP client factory will encounter performance issues.
- The `log4j2-spring.xml` for `staging`/`prod` profiles uses a non-structured (pattern-based) log format rather than Logstash JSON. This contradicts the `onbe-spring-default.yaml` from the `onbe-spring-boot` framework which mandates Logstash JSON. There is a configuration conflict that teams adopting this template should resolve in favor of the framework default.
