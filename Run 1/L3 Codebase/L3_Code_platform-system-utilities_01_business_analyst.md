# Business Analyst — platform-system-utilities

## Business Purpose
A Maven monorepo that delivers shared, cross-cutting platform utilities consumed by Onbe's backend services. It is not a deployable service; it publishes reusable Java libraries to GitHub Packages. The current production-ready modules address two universal concerns for a PCI DSS Level 1 payments platform: **idempotent payment operations** and **compliant database audit trails**.

## Capabilities

| Capability | Module | Summary |
|---|---|---|
| Idempotency enforcement | `platform-idempotency-core` | Annotation-driven (`@Idempotent`) AOP aspect that intercepts Spring-managed methods and guarantees exactly-once execution semantics across concurrent or duplicate HTTP/messaging requests |
| Distributed locking | `platform-idempotency-redis` | Redis SETNX-backed lock with configurable TTL (default 30 s) to prevent concurrent processing of the same idempotency key |
| Payload hash verification | `platform-idempotency-core` | SHA-256 fingerprints request bodies and rejects duplicate requests that arrive with the same key but a different payload (HTTP 409) |
| Dependency BOM | `platform-dependencies-bom` | Centralises approved dependency versions (Lombok, JUnit 5, Mockito, AssertJ) for all platform modules |
| Database audit trail | `platform-envers-db-audit` | Hibernate Envers custom revision entity (`revinfo` table) capturing actor ID, source service, change reason, and W3C trace ID from OpenTelemetry Baggage |

## Key Business Entities

| Entity | Location | Description |
|---|---|---|
| `IdempotencyKey` | `core.domain.IdempotencyKey` | Compound key: `{keyPrefix}:{service}:{endpoint}:{clientUUID}` — three Redis key patterns derived from this |
| `IdempotencyResult` | `core.domain.IdempotencyResult` | Cached outcome: HTTP status code, serialised JSON body, timestamp; 5xx responses are never cached |
| `CustomRevisionEntity` | `envers.audit.CustomRevisionEntity` | Audit revision row: revision number, timestamp, actor ID (≤100 chars), source service, reason (≤500 chars), trace ID (32-char hex) |

## Business Rules

1. If no idempotency key is present (header, method parameter, or OTel Baggage), the request proceeds without enforcement — fail-open by design.
2. A duplicate request with the same key and matching payload hash returns the cached response immediately (HTTP 200/original status) without re-executing business logic.
3. A duplicate request with the same key but a different payload is rejected with HTTP 409 (`IdempotencyPayloadMismatchException`).
4. A concurrent request that finds an existing lock is rejected with HTTP 409 (`IdempotencyLockConflictException`).
5. Results with HTTP status ≥ 500 are never cached (`isCacheable()` returns false for statusCode ≥ 500).
6. Redis failures are fail-open by default (`failOpenOnRedisError = true`); this can be set to strict (`false`) per consumer.
7. Audit revisions capture the OTel actor ID and trace ID only when a valid OTel context is active; absent context is silently tolerated.

## Key Flows

### Idempotency Enforcement Flow
```
Inbound Request
  --> @Idempotent AOP aspect
      1. Resolve idempotency key (parameter → HTTP header → OTel Baggage)
      2. Build IdempotencyKey{keyPrefix, service, endpoint, value}
      3. Serialise first non-scalar argument as request body
      --> IdempotencyService.execute()
          a. store.findResult(key) -- cache hit? → validate hash → return cached response
          b. store.acquireLock(key, 30s TTL) -- lock conflict? → 409
          c. Post-lock double-check: store.findResult(key) again
          d. store.findRequestHash / store.saveRequestHash -- mismatch? → 409
          e. Execute delegate (actual business method)
          f. store.saveResult(key, result, 24h TTL) if isCacheable()
          g. store.releaseLock(key)
```

### Audit Trail Flow
```
JPA entity change
  --> Hibernate Envers intercept
      --> CustomRevisionListener.newRevision()
          a. Extract actor.id from OTel Baggage
          b. Extract source from OTel Baggage
          c. Extract reason from OTel Baggage
          d. Extract traceId from OTel Span
          --> Persist to revinfo table (rev, revtstmp, actor_id, source, reason, trace_id)
```

## Compliance Relevance

| Standard | Relevance |
|---|---|
| PCI DSS v4.0.1 (Req 10) | `platform-envers-db-audit` provides immutable audit logs of data changes with actor and trace correlation, directly supporting audit trail requirements |
| PCI DSS v4.0.1 (Req 6) | SHA-256 payload hashing and SETNX locking reduce replay-attack and duplicate-mutation risk in payment APIs |
| SOC 1 / SOC 2 | Audit revision entity supports change-management and non-repudiation controls |
| NACHA / Reg E | Idempotency prevents duplicate ACH/payment submissions |

## Business Risks

| Risk | Severity | Notes |
|---|---|---|
| Fail-open Redis behaviour | High | If Redis is unavailable, idempotency is entirely bypassed — duplicate payments may be processed |
| 24-hour result cache TTL is fixed in code | Medium | `DEFAULT_TTL` is hardcoded in `IdempotencyService`; the `IdempotencyProperties.ttl` field exists but is not wired to the service |
| No audit trail for idempotency cache misses/hits | Low | Micrometer counters are emitted but there is no durable per-request audit log of idempotency decisions |
| Absent OTel context silently produces null actor in revinfo | Medium | A revision row without actor_id weakens non-repudiation for PCI DSS Req 10 |
