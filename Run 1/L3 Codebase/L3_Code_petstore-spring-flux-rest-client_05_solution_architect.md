# Solution Architect Report — petstore-spring-flux-rest-client

## API Surface

This is a client library, not a server. It consumes the Petstore REST API. The public API surface exposed by the library is:

**`PetStoreClient`** (blocking facade over reactive client):
```java
Pet addPet(NewPet newPet)
Pet findPetById(Long id)
List<Pet> findPets(List<String> tags, Integer limit)
```

**`DefaultApi`** (reactive generated client, from `-api` module):
```java
Mono<Pet> addPet(NewPet body)
Mono<Pet> findPetById(Long id)
Flux<Pet> findPets(List<String> tags, Integer limit)
```

The boot module exposes Spring Boot Actuator endpoints (`/hc` for health) if `spring-boot-actuator` is on the classpath.

## Security Posture

### Strengths
- CodeQL static analysis enabled (weekly + PR)
- Micrometer Observation integration for automatic HTTP client span recording
- WireMock contract testing for consumer-side API contract validation
- Virtual threads enabled (`spring.threads.virtual.enabled: true`)
- No hardcoded credentials in source files

### Critical Finding 1 — Broken Rate-Limit Retry Logic

**File:** `petstore-spring-flux-rest-client-impl/src/main/java/com/onbe/app/WebClientCustomizer.java`, lines 37–46

```java
private static ExchangeFilterFunction retryFilter(int maxAttempts) {
    return ExchangeFilterFunction.ofResponseProcessor(clientResponse -> {
        if (clientResponse.statusCode().value() == 429) {
            return Mono.error(new RuntimeException("Too Many Requests"))
                .retryWhen(Retry.fixedDelay(maxAttempts, Duration.ofSeconds(1)))
                .then(Mono.just(clientResponse));
        }
        return Mono.just(clientResponse);
    });
}
```

**Analysis:** This retry logic is fundamentally broken. `Mono.error(new RuntimeException("Too Many Requests"))` creates a new `Mono` that immediately emits an error. `retryWhen(Retry.fixedDelay(maxAttempts, Duration.ofSeconds(1)))` is applied to **this error Mono** — not to the original HTTP request. Each retry attempt re-executes `Mono.error(...)` which always fails immediately. After `maxAttempts` failures, the `RuntimeException` propagates. The original HTTP request is **never retried**. The `.then(Mono.just(clientResponse))` is unreachable dead code.

**Correct implementation** should use a request-level retry, e.g., by throwing a retryable exception and using `retryWhen` at the `WebClient.retrieve()` level, or using a `retryWhen` on the actual exchange.

**Impact:** Any production payment API client that copies this pattern and encounters HTTP 429 rate limiting will not retry the request — it will immediately throw a `RuntimeException` after retryWhen exhaust the error signal. This could cause cascading failures during rate-limited operations (mass disbursement, settlement, card authorization bursts).

**PCI DSS mapping:** Req 6.2 (secure development), Req 12.3.4 (review of software components).

### High Finding 2 — `PetStoreClient.block()` Anti-pattern Without Warning

**File:** `petstore-spring-flux-rest-client-impl/src/main/java/com/onbe/petstore/client/PetStoreClient.java`, lines 18–33

All three public methods call `.block()` on the reactive publisher:
```java
return api.addPet(newPet).block();
return api.findPetById(id).block();
return api.findPets(tags, limit).collectList().block();
```

While the class Javadoc says "Simple blocking PetStore client," there is no `@Deprecated` annotation, no `@Beta` annotation, and no explicit warning that this must not be called from a reactive scheduler thread. Any reactive WebFlux service that injects `PetStoreClient` and calls it will get an `IllegalStateException: block()/blockFirst()/blockLast() are blocking, which is not supported in thread reactor-http-nio-X` at runtime. BlockHound would also detect this.

**Remediation:** Either remove the blocking facade entirely (encourage use of `DefaultApi` directly) or add a clear `@Deprecated` annotation with a migration note, and add a Javadoc example showing how to invoke from a reactive pipeline.

### Medium Finding 3 — Empty QA/Stage/Prod Profile Configurations

**File:** `petstore-spring-flux-rest-client-boot/src/main/resources/application.yaml`, lines 32–44

```yaml
---
spring:
  config:
    activate:
      on-profile: qa
---
spring:
  config:
    activate:
      on-profile: stage
---
spring:
  config:
    activate:
      on-profile: prod
```

No `petstore.webclient.base-url` is configured for QA, stage, or prod. If a team deploys this client in any non-dev environment without adding the base URL, the WebClient will have no target URL and all API calls will fail with a configuration error. This is a missing production-readiness concern.

**Remediation:** Add commented-out placeholder base URL configurations with an explicit note that `https://` is required.

### Medium Finding 4 — Micrometer Observation Without Sensitive Header Exclusion

**File:** `petstore-spring-flux-rest-client-impl/src/main/java/com/onbe/app/WebClientCustomizer.java`, line 33
```java
builder.observationRegistry(this.observationRegistry);
```
`ObservationRegistry` is wired without configuring `WebClientObservationConvention` to exclude sensitive headers (e.g., `Authorization`, `X-API-Key`, `X-Card-Number`) from trace span attributes. In a production payment API client, authorization headers and any CHD-adjacent URL parameters would be captured in distributed traces if not explicitly excluded.

**Remediation:** Configure `WebClientObservationConvention` with `SensitiveRequestHeadersFilter` or equivalent, and document which headers are excluded in the reference implementation.

## Technical Debt

- `WebClientConfigProperties` is in `petstore-spring-flux-rest-client-impl` but the actual WebClient configuration (`AppConfig.java`) is also in the same module — the separation is minimal and could be collapsed.
- `pig.template` at repo root (package-info generator template) — same as in the server repo.
- The `petstore.properties` test resource file suggests another configuration mechanism being tested alongside YAML — should be consolidated.
- `postman-qa-lb-run.sh` script in the boot module — if this script contains hardcoded URLs or credentials, it should be reviewed. The path is `petstore-spring-flux-rest-client-boot/scripts/postman-qa-lb-run.sh`.

## Recommendations

1. **Critical:** Fix `retryFilter` — implement actual request-level retry using `WebClient.retrieve()` with a retry operator, not a response processor retrying an error signal.
2. Remove or clearly deprecate `PetStoreClient` blocking facade; document that `DefaultApi` is the preferred reactive client interface.
3. Add QA/stage/prod `petstore.webclient.base-url` configurations with `https://` placeholders.
4. Configure `WebClientObservationConvention` to exclude sensitive headers from trace spans.
5. Review `postman-qa-lb-run.sh` for hardcoded credentials or environment-specific values that should be externalized.
