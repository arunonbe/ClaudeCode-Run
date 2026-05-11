# Solution Architect Report — petstore-spring-mvc-rest-client

## API Surface

This is a client library, not a server. It consumes the Petstore REST API via a generated synchronous client. The library's public API is the generated client stubs in the `-api` module:

Generated synchronous client methods (blocking, not Mono/Flux):
- `Pet addPet(NewPet body)`
- `Pet findPetById(Long id)`
- `List<Pet> findPets(List<String> tags, Integer limit)`

The boot module runs as a Spring Boot application with the default Actuator configuration from `onbe-spring-boot-starter` (health endpoint at `/hc`).

## Security Posture

### Strengths
- CodeQL static analysis enabled (weekly + PR)
- Micrometer Observation for automatic HTTP client span recording
- `RetryRateLimitRequestInterceptor` from `onbe-spring-boot` — correct rate-limit retry implementation (unlike the WebFlux client's broken retry)
- Virtual threads enabled — safe blocking I/O without thread pool starvation
- Jackson `failOnUnknownProperties=false` — forward-compatible, resilient to API evolution
- `PetStoreRestClientCustomizer` implements Spring Boot's `RestClientCustomizer` — integrates correctly with auto-configuration

### High Finding 1 — `SimpleClientHttpRequestFactory` (Non-Pooled, Limited TLS)

**File:** `petstore-spring-mvc-rest-client-impl/src/main/java/com/onbe/app/AppConfig.java`, line 28
```java
SimpleClientHttpRequestFactory factory = new SimpleClientHttpRequestFactory();
factory.setConnectTimeout(config.getConnectTimeout());
factory.setReadTimeout(config.getReadTimeout());
```

`SimpleClientHttpRequestFactory` uses `java.net.HttpURLConnection` which:
1. **Has no connection pooling** — each request opens and closes a new TCP/TLS connection. In a payment service making hundreds of API calls (batch disbursement, bulk authorization), this creates severe overhead and may exhaust ephemeral ports.
2. **Has limited TLS configuration** — cannot configure custom `SSLContext`, trust stores, or client certificates without system-level JVM properties. mTLS authentication (required by some payment network APIs) cannot be configured per-factory.
3. **Supports HTTP/1.1 only** — no HTTP/2 support.

`onbe-spring-boot`'s `WebAutoConfiguration` correctly uses `JdkClientHttpRequestFactory` (based on Java `java.net.http.HttpClient`) which supports connection pooling, HTTP/2, custom `SSLContext`, and works well with virtual threads. This reference application should use the same factory for consistency.

**Recommended fix:**
```java
var httpClient = HttpClient.newBuilder()
    .connectTimeout(config.getConnectTimeout())
    .executor(taskExecutor)
    .build();
var factory = new JdkClientHttpRequestFactory(httpClient);
factory.setReadTimeout(config.getReadTimeout());
```

### High Finding 2 — Log4j2 Configuration Overrides Framework Logstash JSON Standard

**File:** `petstore-spring-mvc-rest-client-boot/src/main/resources/log4j2-spring.xml`

The presence of a `log4j2-spring.xml` in the classpath causes Spring Boot to use this configuration file instead of the structured logging configuration defined in `onbe-spring-default.yaml` (Logstash JSON format). The `staging`/`prod` profile in `log4j2-spring.xml` uses:
- Console pattern: `%d %p %C{1.} [%t] %m%n` — non-JSON, non-Logstash format
- Rolling file: Local filesystem at `./logs/spring-boot-logger-log4j2.log` — unsuitable for containerized deployment

**Impact:** In a containerized Gen-3 service, this log configuration:
1. Produces non-structured logs that break SIEM/Logstash parsing pipelines (PCI DSS Req 10 compliance gap)
2. Writes logs to a local file that is lost when the container restarts (unless a persistent volume is mounted)
3. Contradicts the `onbe-spring-default.yaml` logging standard, causing inconsistency across the Gen-3 fleet

**Remediation:** Remove `log4j2-spring.xml` and rely on the `onbe-spring-boot-starter-logback` or `onbe-spring-boot-starter-log4j2` starters with Logstash JSON configuration. If Log4j2 is required, configure it to use the Logstash layout (`com.fasterxml.jackson.dataformat:jackson-dataformat-yaml` and Log4j2 JSON layout).

### Medium Finding 3 — Duplicate RestClient Configuration via Two Beans

**File:** `petstore-spring-mvc-rest-client-impl/src/main/java/com/onbe/app/AppConfig.java`, lines 36–40 and `PetStoreRestClientCustomizer.java`

`AppConfig` defines both:
1. A `ClientHttpRequestFactory` bean (with interceptors applied manually)
2. A `RestClient petstoreRestClient` bean built from `RestClient.Builder` + the factory

`PetStoreRestClientCustomizer` also applies the `requestFactory` and `defaultHeaders` to the builder.

If both `AppConfig.petstoreRestClient()` and `PetStoreRestClientCustomizer` are active simultaneously, the `RestClient.Builder` will have the factory set twice (once by the customizer, once directly in `AppConfig`). This creates unclear configuration precedence and potential duplication of interceptors. Teams inheriting this pattern may configure conflicting request factories.

**Remediation:** Consolidate to either the `RestClientCustomizer` pattern (auto-configuration-friendly) or the explicit bean pattern, not both.

### Medium Finding 4 — No Dapr Secrets Integration

The MVC client has no Dapr secrets configuration. If a team uses this as a template for a production service that needs to authenticate to the target API (e.g., OAuth 2.0 Bearer token, API key), there is no reference for how to securely load those credentials. Teams may resort to hardcoding credentials in `application.yaml`.

**Remediation:** Add a commented-out Dapr secrets configuration example in `application.yaml` with a note directing teams to the `petstore-spring-flux-rest-server` for a complete Dapr integration example.

## Technical Debt

- `SimpleClientHttpRequestFactory` — should be replaced with `JdkClientHttpRequestFactory` (Critical for production use)
- `log4j2-spring.xml` — conflicts with framework logging standard (High)
- No Dapr integration shown — missing a key Gen-3 pattern
- Empty QA/stage/prod profile configurations in `application.yaml` — same gap as the WebFlux client
- `pig.template` at repo root — same as other repos in the fleet
- `compose.yaml` present but no Dockerfile — inconsistency with the server reference which has both

## Recommendations

1. Replace `SimpleClientHttpRequestFactory` with `JdkClientHttpRequestFactory` for connection pooling and TLS configurability.
2. Remove `log4j2-spring.xml` and use the `onbe-spring-boot-starter` logging standard (Logstash JSON via Logback or Log4j2 starter).
3. Add QA/stage/prod `petstore.restclient.base-url` placeholder configurations with `https://` prefix.
4. Consolidate the `RestClient` configuration to use exclusively the `RestClientCustomizer` pattern (remove the `petstoreRestClient` bean from `AppConfig`).
5. Add a commented Dapr secrets configuration example to guide teams adding API authentication credentials.
6. Consider adding a Dockerfile to make this a complete deployable reference, consistent with the server reference.
