# Business Analyst View — petstore-spring-mvc-rest-server

## Business Purpose

petstore-spring-mvc-rest-server is an internal reference/exemplar application used by Onbe's engineering organization to demonstrate Gen-3 platform architecture patterns. It implements the classic OpenAPI Petstore specification as a concrete, runnable example of how new microservices should be built using Onbe's `onbe-spring-boot-starter`, Azure infrastructure (Key Vault, Service Bus, App Config, Redis), and Spring Boot 3 / Java 21.

This is not a production payments service — it handles no real cardholder data, no financial transactions, and no regulatory obligations. Its purpose is to provide a canonical working template that development teams can use as a starting point for new services.

## Capabilities Provided

The petstore API demonstrates the following platform capabilities in a safe, non-sensitive context:

- **REST API design**: OpenAPI-spec-driven code generation; controller implements `DefaultApi` generated interface
- **Azure Key Vault integration**: secrets (`mypaymentvaultapi-cbaseappdb-username`, `mysecret`) loaded via Spring Cloud Azure Key Vault property source
- **Azure App Configuration**: feature flag management (`FeatureManager` for `petstore.streaming` flag)
- **Async processing**: `CompletableFuture`-based async request handling with Spring's `AsyncTaskExecutor`
- **Resilience patterns**: Resilience4j circuit breaker, rate limiter, and time limiter annotations on API operations
- **Retry logic**: Spring Retry with backoff on transient database exceptions
- **Redis caching**: Spring Cache backed by Redis (Lettuce client); 2-hour TTL
- **Leader election**: Redis-based distributed leader election for singleton scheduled tasks
- **Event messaging**: Apache Avro-serialized events published to Azure Service Bus (production) or RabbitMQ (local/dev) via Spring Cloud Stream
- **Change Data Capture (CDC)**: `CDCConfig` class demonstrates event-driven data change propagation
- **QueryDSL**: type-safe database queries alongside plain JDBC alternative implementation
- **SQL Server connectivity**: HikariCP connection pool to SQL Server; Dapr sidecar secret injection demonstrated
- **ArchUnit tests**: enforces architectural rules (Spring layer rules, modularity rules) as automated tests
- **Spring Modulith**: module structure verification tests

## Client/Cardholder Impact

None — this is an internal exemplar. Its only "clients" are Onbe engineers using it as a reference. The petstore domain (pets, owners) is synthetic and non-sensitive.

## Business Rules Found in Code

- Rate limiter configured to 1 request per minute per instance (extremely restrictive — this is a demonstration value, not a production SLA)
- Circuit breaker opens at 50% failure rate
- Time limiter set to 30-second timeout for list operations
- Feature flags (via Azure App Config) control streaming behavior at runtime without redeployment — this pattern is prescribed for use in production services
- Secrets must never be logged; `KeyVaultConfigProperties.toString()` masks secret values using `com.onbe.text.TextUtils.mask()` — this masking pattern is prescribed for all services
- Event publishing failures do not fail the API call (fire-and-forget pattern with error logging) — teams should evaluate whether this is appropriate for financial events in production services

## Regulatory Obligations

None applicable to this exemplar. However, the patterns demonstrated here carry regulatory implications when adopted in production:

- Key Vault secret loading pattern must be used for all credentials in production (PCI DSS Requirement 8.6.2)
- Event masking pattern (masking in `toString()`) must be applied to any PII or SAD fields in production service logs
- Rate limiting and circuit breaker patterns support availability and DDoS resilience obligations

## Key Business Risks Found in Code

- **`encrypt: false` in datasource config**: `application.yaml` sets `encrypt=false` on the SQL Server connection, disabling TLS encryption on the database connection. This is acceptable in the local dev profile but must be overridden to `encrypt=true` in all production configurations. **This pattern must not be copied to production services without correction.**
- **`trustServerCertificate: true`**: Also set in the local profile config — disables certificate validation. Must not appear in production configurations.
- **`debug: true`** in the local Spring profile: Enables verbose Spring framework debug logging. Must not be enabled in production as it may log sensitive request/response data.
- **SNAPSHOT version**: `petstore-spring-mvc-rest-server-boot` is `0.0.1-SNAPSHOT` — consistent with its exemplar status; must not be deployed to production environments.
- **Dapr secrets**: `application.yaml` references `SPRING_R2DBC_USERNAME` and `MERCHANTENRICHMENT_TRIPLE_APITOKEN` via Dapr secret store. The `MERCHANTENRICHMENT_TRIPLE_APITOKEN` name suggests integration with a merchant enrichment API; teams adopting this pattern must ensure the real token is properly secured.
