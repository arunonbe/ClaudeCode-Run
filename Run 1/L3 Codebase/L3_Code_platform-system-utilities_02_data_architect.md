# Data Architect — platform-system-utilities

## Data Stores

| Store | Type | Purpose | Module |
|---|---|---|---|
| Redis | In-memory KV store | Idempotency lock, result cache, request-hash cache | `platform-idempotency-redis` |
| Relational DB (consumer-owned) | RDBMS (JPA/Envers) | Audit revision table (`revinfo`) | `platform-envers-db-audit` |

## Schema / Key Patterns

### Redis Key Namespaces (platform-idempotency-redis)

All keys follow the pattern `{keyPrefix}:{type}:{service}:{endpoint}:{clientUUID}` where `keyPrefix` defaults to `idem`.

| Pattern | Purpose | TTL |
|---|---|---|
| `idem:lock:{service}:{endpoint}:{uuid}` | Distributed mutex — value is `"1"` | 30 s (configurable via `lockTtl`) |
| `idem:result:{service}:{endpoint}:{uuid}` | Serialised `IdempotencyResult` JSON | 24 h (configurable via `ttl`) |
| `idem:request-hash:{service}:{endpoint}:{uuid}` | SHA-256 hex of request body | 24 h (configurable via `ttl`) |

### Relational Table — `revinfo` (platform-envers-db-audit)

| Column | Type | Source | Max Length |
|---|---|---|---|
| `rev` | INT (auto-generated PK) | Hibernate sequence | — |
| `revtstmp` | BIGINT (epoch ms) | Hibernate | — |
| `actor_id` | VARCHAR(100) | OTel Baggage `actor.id` | 100 |
| `source` | VARCHAR(100) | OTel Baggage `source` | 100 |
| `reason` | VARCHAR(500) | OTel Baggage `reason` | 500 |
| `trace_id` | VARCHAR(32) | OTel Span context | 32 |

Consumer services define their own audited entity tables; Envers appends `_AUD` shadow tables. This library only defines the `revinfo` table structure.

## Sensitive Data

| Data Class | Location | Notes |
|---|---|---|
| Request body payloads | Redis `idem:result:*` keys | Cached as serialised JSON for up to 24 hours — may contain PII or payment data depending on the calling service |
| SHA-256 body fingerprint | Redis `idem:request-hash:*` keys | Hash only; not reversible, not sensitive in isolation |
| Actor identity | `revinfo.actor_id` | User/system ID of change author — classify per consumer's data sensitivity |
| OTel trace ID | `revinfo.trace_id` | Operational metadata; low sensitivity |

## Encryption

| Layer | Mechanism | Status |
|---|---|---|
| Redis transport | Depends on consumer Redis configuration (TLS) | Not configured within this library |
| Redis at-rest encryption | Depends on hosting infrastructure | Not configured within this library |
| Request body in Redis | Plaintext JSON — no application-level encryption | Gap for PCI DSS if payment fields are included in cached bodies |
| `revinfo` table | Depends on consumer DB encryption | Not configured within this library |

## Data Flow

```
Consumer HTTP Request
  --> IdempotencyAspect serialises request body (ObjectMapper.writeValueAsString)
  --> RedisIdempotencyStore writes:
        idem:lock:*         (string "1", 30 s TTL)
        idem:request-hash:* (SHA-256 hex, 24 h TTL)
        idem:result:*       (serialised JSON, 24 h TTL)
  --> On cache hit: reads idem:result:* back and deserialises
  --> JPA entity change triggers Envers --> CustomRevisionListener
        reads OTel Baggage (actor.id, source, reason)
        reads OTel Span (traceId)
        writes revinfo row via JPA
```

## Data Quality and Retention

| Concern | Detail |
|---|---|
| TTL consistency | Result and request-hash TTLs should be equal; currently both default to 24 h in code. If a result expires before its hash, a second request would be treated as a miss but the hash mismatch check would still trigger |
| Redis eviction policy | Not controlled by this library; if Redis uses `allkeys-lru`, idempotency keys may be evicted early under memory pressure |
| `revinfo` retention | Not defined in this library; consumer services must establish their own retention policies for compliance |
| Null actor in revinfo | Actor ID is nullable — absent OTel context produces a `NULL` `actor_id`; this weakens audit completeness |

## Compliance Gaps

| Gap | Standard | Impact |
|---|---|---|
| Request bodies cached in Redis as plaintext | PCI DSS Req 3.5 | If a cached response contains CHD/SAD fields, they must be encrypted at rest in Redis |
| No application-level encryption of Redis values | PCI DSS Req 3.5 | Library does not encrypt cached results; consumer is responsible |
| Redis ACL / access control not specified | PCI DSS Req 7 | Least-privilege access to Redis key namespaces not enforced at library level |
| `actor_id` nullable in revinfo | PCI DSS Req 10.2 | NULL actor weakens who-did-what audit trail |
| No data retention policy | PCI DSS Req 10.7 / GLBA | Library does not enforce minimum or maximum retention on `revinfo` or Redis |
