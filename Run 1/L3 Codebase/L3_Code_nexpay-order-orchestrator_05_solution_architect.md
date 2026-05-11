# Solution Architect View — nexpay-order-orchestrator

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Language | Java 25 |
| Framework | Spring Boot 4.0.5 / Spring MVC |
| Concurrency | Java 25 virtual threads (Project Loom) |
| Persistence | PostgreSQL (JPA/Hibernate) + Flyway migrations |
| Async persistence | Redis (service-bus module, Lettuce client) |
| Messaging | Azure Service Bus, Azure Event Hub (service-bus module) |
| API | OpenAPI 3.0 code generation (openapi-generator-maven-plugin 7.21.0) |
| Object mapping | MapStruct 1.6.3 |
| HTTP clients | Spring RestClient with Apache HttpClient 5 |
| Observability | OpenTelemetry auto-instrumentation + OTLP export |
| Security | Spring Security (JWT/OAuth2 via Azure APIM) |
| Config | Azure App Configuration + Azure Key Vault |
| Testing | JUnit 5, WireMock, OkHttp MockWebServer, Testcontainers |

## Module Structure

```
nexpay-order-orchestrator/
├── nexpay-order-orchestrator-api/        # OpenAPI spec → generated Spring interfaces
├── nexpay-order-orchestrator-api-client/ # OpenAPI spec → generated Java client (consumed by other services)
├── nexpay-order-orchestrator-impl/       # Business logic: OrchestrationService, SagaService, filters
├── nexpay-order-orchestrator-boot/       # Spring Boot application, config, security, Dockerfile
└── nexpay-order-orchestrator-service-bus/ # Reactive event-driven orchestration (legacy ACH rail)
```

## Core Implementation Patterns

### Step Executor Pattern

`StepExecutor` (in the `orchestration` package of `-impl`) is a static utility that launches a list of `Supplier<T>` lambdas in parallel on a provided `TaskExecutor`, collects results into `StepResult<T>` records, and blocks via `CompletableFuture.allOf().join()`. Exceptions are captured per-step rather than propagated immediately, enabling partial success handling (e.g., advancing saga state for the claim-code validation independently of the screening result).

### Saga State Machine

`SagaStateTransitions` defines:
- `STEP_ORDER`: ordered list of states representing the happy-path progression
- `ALLOWED`: map of from-state → set of valid next-states

Calling `SagaStateTransitions.validate(from, to)` throws `IllegalStateException` on an invalid transition. This is called within `SagaService.advanceSaga()` before any database write, making the state machine enforced at the service layer, not only at the application layer.

### Actor ID Security Filter

`ActorIdSecurityFilter.java` (in `-impl`) runs at filter order 1 and propagates an `actor.id` into OpenTelemetry baggage from three sources in priority order: existing baggage > `X-Actor-Id` header > authenticated principal name. This enables end-to-end actor attribution in distributed traces without requiring every downstream service to re-extract the actor from the JWT.

### Outbox Pattern

`SagaService.writeCompletionEvent()` writes a single `outbox_event` row within the same database transaction as the final saga state update. This guarantees that the completion event is only written if the transaction commits — a classic Transactional Outbox implementation. However, the payload is a raw string rather than a typed event object (line 287): `"{\"sagaId\":\"" + sagaId + "\",\"event\":\"COMPLETION\"}"`. This should be replaced with a proper Jackson-serialized event envelope to support versioning and structured consumers.

## Security Architecture

### Authentication and Authorization

The service is deployed behind Azure APIM (`INTERNAL_APIM: true`). APIM enforces JWT validation before requests reach the container. Spring Security is configured in the boot module. The `ActorIdSecurityFilter` observes the authenticated principal for observability purposes.

### Secret Management

All secrets are stored in Azure Key Vault and referenced via Azure App Configuration's Key Vault provider. The managed identity credential (`managed-identity-enabled: true` in QA/Prod) means no service principal credentials are in the codebase.

### Header Sanitization

HTTP client headers `Authorization`, `X-API-Key`, and `X-Auth-Token` are excluded from HTTP wire logging (configured at `application.yaml` lines 80–81). This prevents credential leakage in log sinks.

## Critical Security Findings

### Finding 1: Compensation Logic is Stubbed

**File**: `SagaService.java`, lines 226–255  
**Risk**: If a card is issued (Step 3 succeeds) and then the ACL write-back (Step 4) fails, `compensateCardIssuance()` logs a warning but does not call the card processor to cancel the card. This means a payee could receive a funded card without the ACL knowing the claim is complete. For ACH/push-to-card rails where real money moves, this becomes a regulatory and financial risk.  
**Recommendation**: Implement `compensateCardIssuance()` to call `CardProcessorServiceClient.cancelCard()` before production go-live.

### Finding 2: No Saga-Level Idempotency Key

**File**: `V1__initial_schema.sql` (saga table), `SagaService.java` line 41  
**Risk**: Two concurrent HTTP requests with the same claim code can both successfully call `startSaga()` and create two sagas, potentially issuing two payment instruments for one claim code.  
**Recommendation**: Add a unique index on `saga.claim_code` with a mechanism to return the existing saga ID on duplicate, or enforce idempotency at the API gateway level with a client-supplied idempotency key stored in a Redis dedup cache.

### Finding 3: DEBUG Logging in Default Profile Includes HTTP Wire Data

**File**: `application.yaml`, lines 56–58  
**Risk**: `org.apache.hc.client5.http.wire: DEBUG` logs full HTTP request and response bodies for all outbound calls. In the default (local) profile this includes claim codes, validation results, and recipient data returned from screening. If this log level propagates to QA/Prod by accident, sensitive data will appear in the log aggregation system.  
**Recommendation**: Set wire logging to `WARN` in the default profile and only enable `DEBUG` via a feature flag or environment override.

### Finding 4: Container Runs as Root

**File**: `nexpay-order-orchestrator-boot/Dockerfile`  
**Risk**: No `USER` instruction means the JVM process runs as UID 0. If an attacker achieves remote code execution, they have root access within the container.  
**Recommendation**: Add `RUN adduser -D -u 1001 nexpay` and `USER nexpay` before the `CMD` instruction.

### Finding 5: Container Scanning Disabled

**File**: `.github/workflows/deployment.yml`, line 33  
**Risk**: `CONTAINER_SCAN: false` means container image vulnerabilities are not detected. This is a gap against PCI DSS Requirement 6.3.3 (protect all system components from malicious software).  
**Recommendation**: Fix the underlying container scanning configuration rather than disabling it. Use the `allowedlist.yaml` file in `.github/containerscan/` to accept known false positives.

## Performance Considerations

### Virtual Threads

Spring Boot 4 with Java 25 virtual threads allows each incoming HTTP request to block on I/O without consuming an OS thread. Given that the saga involves 5+ sequential and parallel HTTP calls totalling up to 45 seconds, virtual threads are the right choice — they enable high concurrent saga processing without reactive complexity.

### Connection Pool Sizing

The HTTP client pool (`max-total: 50`, `max-per-route: 20`) is sized for moderate concurrency. Under load, 50 total connections across all downstream services may become a bottleneck if saga volume grows. The per-route limit of 20 is the binding constraint for any single downstream service.

### Database Connection Pool

HikariCP defaults from the parent POM. QA/Prod uses `DB_POOL_MAX_SIZE:20` and `DB_POOL_MIN_IDLE:5`. For a synchronous, virtual-thread based service where each saga makes 3–4 database writes, 20 connections should handle approximately 20 concurrent saga completions at any instant. Monitor `hikaricp_connections_pending` metric for pool exhaustion.
