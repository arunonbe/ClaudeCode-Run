# Data Architect Report — petstore-spring-mvc-rest-client

## Data Models

### Configuration Model
`RestClientConfigProperties` — a Java record (immutable):
```java
@ConfigurationProperties(prefix = "petstore.restclient")
public record RestClientConfigProperties(String baseUrl, Duration timeout) {}
```
Simple configuration DTO. No sensitive data.

### API Client Models (OpenAPI-generated, in `-api` module)
Generated from the Petstore OpenAPI specification — same `Pet` and `NewPet` models as the server and WebFlux client. No sensitive payment data fields.

### Test Data
- `src/test/resources/db/mssql/schema.sql` and `init.sql` — Test database schema for Testcontainers SQL Server. Petstore `pet` table only (id, name, tag).
- No Dapr secrets file in the MVC client (unlike the WebFlux client) — this client does not appear to use Dapr at the application level.
- `logback-spring-test.xml` and `log4j2-test.xml` — both logging framework test configurations, matching the dual-logging-backend testing approach in the WebFlux client.

## Sensitive Data Handling

### No Sensitive Domain Data
The Petstore domain contains no CHD, PII, or payment-sensitive data. The client models are DTOs for `Pet` CRUD operations.

### RestClient Observation and Sensitive Headers
`PetStoreRestClientCustomizer` registers `ObservationRegistry` with `RestClient.Builder`:
```java
builder.observationRegistry(this.observationRegistry);
```
Spring Boot 3.x `RestClient` with `ObservationRegistry` automatically creates HTTP client spans. By default, Spring does not filter sensitive headers from spans, meaning if an `Authorization` header, API key, or any header containing CHD-adjacent data is set as a `defaultHeader`, it may appear in distributed traces.

The current implementation sets no default headers via `PetStoreRestClientCustomizer.customize()` — only the `config.getDefaultHeaders()` from `RestClientConfiguration` (which defaults to `Accept: application/json`, `Content-Type: application/json`). No sensitive headers are added by default. However, teams extending this pattern to add authentication headers must configure `ObservationConvention` to exclude those headers.

### Jackson `failOnUnknownProperties=false`
`AppConfig.jacksonCustomizer()` disables the fail-on-unknown-properties behavior globally. While this improves forward compatibility with evolving APIs, it means that if a server response accidentally includes sensitive fields not in the generated model, they will be silently deserialized and ignored. This prevents exposure in the client's domain model but also prevents detection of data leakage.

## Data Flows

```
[Application code] --> [RestClient (injected)]
    --> [PetStoreRestClientCustomizer: ObservationRegistry + defaultHeaders]
        --> [InterceptingClientHttpRequestFactory]
            --> [RetryRateLimitRequestInterceptor (from onbe-spring-boot)]
                --> [SimpleClientHttpRequestFactory]
                    --> [HTTP: petstore.restclient.base-url]
                        --> [JSON response] --> [OpenAPI generated model]
                            --> [Caller]

[Test execution] --> [Testcontainers MS SQL Server]
    --> [JDBC test database operations] (schema.sql, init.sql)
```

## Encryption Status

- **HTTP transport:** Application configuration `petstore.restclient.base-url` is set to `http://localhost:8080/v2` in the dev profile — HTTP (not HTTPS). As with the WebFlux client, QA/stage/prod profiles have empty configurations with no base URL set. All production deployments must use `https://` base URLs.
- **`SimpleClientHttpRequestFactory`:** Does not configure TLS client certificates or custom SSL context. For mTLS authentication (required by some payment APIs), this factory would need to be replaced with one supporting custom SSLContext configuration.
- **Log4j2 file logging:** The `staging`/`prod` profile writes logs to `./logs/spring-boot-logger-log4j2.log` — a local file. If this service is containerized (ephemeral filesystem), log files written to a local path will be lost when the container restarts unless a persistent volume is mounted. For PCI DSS Req 10, log persistence must be ensured via a log forwarding mechanism (Filebeat, Fluent Bit, Azure Monitor agent).
- **No database connectivity:** Unlike the server, the MVC client has no R2DBC or JDBC production database. Only test databases via Testcontainers.

## PCI DSS Compliance Assessment

As a reference/demo application: no direct PCI DSS obligation.

As a template for production MVC payment API clients:
- Gap: `SimpleClientHttpRequestFactory` does not support connection pooling — production payment services need connection pooling for performance and timeout reliability.
- Gap: No TLS configuration shown — production services must configure `javax.net.ssl.SSLContext` for HTTPS client connections.
- Gap: Log file persistence in containers — local file appender is unsuitable for containerized deployments without a log forwarder.
- Gap: No mTLS client certificate configuration — required for integration with some payment network APIs.
- Gap: Log4j2 non-structured logging in `staging`/`prod` profile contradicts the Onbe framework standard of Logstash JSON format. Inconsistent log formatting breaks SIEM pipeline parsers.
- Recommendation: Follow up with Security team to confirm that `ObservationRegistry` span sanitization is adequate for the production payment API client patterns that inherit from this template.
