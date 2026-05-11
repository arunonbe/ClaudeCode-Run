# Solution Architect View — nexpay-cardprocessor-svc

## Technical Architecture

`nexpay-cardprocessor-svc` follows a **clean hexagonal architecture** with strict separation between the API layer, domain/implementation layer, data layer, and processor adapters.

### Module Topology

```
nexpay-cardprocessor-api           ← OpenAPI contract (code-generated)
nexpay-cardprocessor-adapter-spi   ← Processor SPI interface (no framework deps)
nexpay-cardprocessor-data-entity   ← JPA entities + Flyway SQL migrations
nexpay-cardprocessor-data-repository ← Spring Data JPA repositories
nexpay-cardprocessor-impl          ← Core business logic
  ├── ScopeResolver                ← Maps scope → ProcessorConfig
  ├── CardProcessorService         ← Orchestrates create/activate/balance
  ├── JobService                   ← Async job management
  └── CardResolver                 ← Resolves Card by UUID
nexpay-cardprocessor-adapter-thredd ← Thredd REST/JWT adapter (SPI impl)
nexpay-cardprocessor-adapter-fis    ← FIS form-encoded + mTLS adapter (SPI impl)
nexpay-cardprocessor-boot           ← Spring Boot wiring, config, Dockerfile
```

## API Surface

See `docs/API_REQUEST_FLOW.md` for full payload reference.

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/v1/cards` | Bearer JWT + `X-Integration-Id` + `Idempotency-Key` | Synchronous card creation |
| GET | `/v1/cards/{cardId}/balance` | Bearer JWT | Card balance inquiry |
| POST | `/v1/jobs` | Bearer JWT + `X-Integration-Id` + `Idempotency-Key` | Async card creation |
| GET | `/v1/jobs/{jobId}` | Bearer JWT | Poll job status |
| POST | `/v1/cards/{cardId}/activate` | Bearer JWT | Card activation |

Service is internal (`INTERNAL_APIM: true`, `EXTERNAL_APIM: false`) — not exposed to enterprise clients directly. Accessible only within the NexPay ACA environment.

## Security Posture

### Authentication
- Bearer JWT validated via Spring Security (`nexpay-parent` configuration).
- `X-Integration-Id` header identifies the calling integration (Entra client ID or logical name).
- `Idempotency-Key` is a required request header — enforced at API contract level.

### Processor Credentials
- **Thredd**: OAuth2 client credentials flow (`clientId` + `clientSecret` from Key Vault). JWT token cached and refreshed automatically.
- **FIS**: Credentials embedded in every request payload (`UserId`, `Pwd`) — form-encoded. Sensitive fields are masked in logs (per `docs/API_REQUEST_FLOW.md`). FIS mTLS client certificate loaded from Base64 Key Vault secret as PKCS#12.

### Data Protection
- Masked PAN (`first 6 / Xs / last 4`) stored in `card.masked_pan` — PCI DSS Req 3.4 compliant.
- `processorMetadata` JSONB: For FIS, `FisCreateCardMetadata.cardNum` — **must be audited to confirm this is the masked PAN, not the raw card number returned from FIS API**.
- Azure AD passwordless auth for PostgreSQL — no database password in any configuration.
- Azure Key Vault for all processor secrets — correct pattern.

### Circuit Breaker (Resilience4j)

```yaml
failure-rate-threshold: 50
wait-duration-seconds: 30
sliding-window-size: 10
permitted-calls-in-half-open: 3
minimum-number-of-calls: 5
```

Applied to balance inquiry calls. If 50% of the last 10 calls fail, the circuit opens for 30 seconds. This prevents cascading failures when a processor balance endpoint is degraded. **Note**: No circuit breaker is visible on the card creation path (`POST /v1/cards`) — if Thredd or FIS is unavailable, card creation will fail directly without a circuit break.

### Balance Throttle

```yaml
nexpay.balance.throttle-seconds: 10
```

Balance inquiries are throttled per card (10-second minimum interval). This prevents abuse of the balance inquiry endpoint as a high-frequency polling mechanism against the card processor.

## Technical Debt

| Item | Severity | Description |
|---|---|---|
| Container runs as root | High | No USER instruction in Dockerfile |
| No explicit `-Xmx` | Medium | Container may OOM under load |
| SNAPSHOT versions in production | Medium | Both service and parent are SNAPSHOT versions |
| `processorMetadata` JSONB PAN risk | Critical | FIS `cardNum` in JSONB metadata — must verify it is the masked PAN |
| Container scan disabled | Medium | `CONTAINER_SCAN: false` in deployment workflow |
| No circuit breaker on card creation | Medium | If Thredd/FIS call fails, no circuit-break protection |
| FIS mTLS cert loaded from Base64 per call | Low | Performance concern if SSLContext is not cached |
| `nexpay-parent:0.2.8-SNAPSHOT` | Medium | Parent POM instability in production |

## Gen-3 Architecture Observations

This service represents the most architecturally complete Gen-3 service in the portfolio reviewed. Notable patterns to highlight:

1. **SPI pattern for processor extensibility**: Adding a new processor (Fiserv, Marqeta, etc.) requires only implementing the adapter SPI — no changes to the core service.
2. **Time-bounded scope routing via `ScopeMap`**: `effective_from`/`effective_to` dates on `ScopeMap` records enable scheduled processor migrations without code changes.
3. **Hibernate Envers**: Automatic revision history on `Card` entity provides PCI DSS Req 10 compliance out of the box.
4. **Flyway with `baseline-on-migrate`**: Correct for a new service being deployed to pre-existing databases. `ddl-auto: none` ensures Hibernate never modifies the schema.
5. **Structured logging (Logstash format)**: JSON-formatted logs for centralised aggregation — correct Gen-3 pattern.

## Code-Level Risks

1. **`processorMetadata` JSONB field** (`card.processor_metadata`): The FIS adapter stores raw processor response in this JSONB column via `FisCreateCardMetadata`. The `cardNum` field within this metadata must be verified to contain only the masked PAN. If the FIS API returns the full card number in `cardNum` and it is stored before masking, this constitutes a PCI DSS Req 3.4 violation. A code audit of `FisCreateCardAdapter` / `FisCreateCardMetadata` is required before the next QSA assessment.

2. **`atomicityMode: ISSUE_EVEN_IF_ACTIONS_FAIL` (default)**: Post-issue actions (activate, initial load) are not transactionally bound to card creation by default. A card can exist in the processor without being activated or loaded. The calling service (orchestrator) must handle this case in its compensation logic — compensation stubs are currently not implemented in `nexpay-recipientorchestrator-svc`.

3. **`processorCardId` stickiness**: The `processorCardId` field on `Card` is set at issuance and should never change. There is no database constraint enforcing this immutability. An UPDATE that accidentally overwrites `processorCardId` would sever the link between Onbe's record and the processor's card — an irreversible data integrity failure.

4. **UUID v7 for `Card.id`**: Time-ordered UUIDs (UUID v7) are used for the primary key, ensuring B-tree index efficiency as the table grows. This is a forward-looking design choice that reduces page splits during high-volume card issuance.
