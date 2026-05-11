# Data Architect View — nexpay-order-orchestrator

## Data Architecture Summary

The nexpay-order-orchestrator uses two distinct persistence strategies across its two sub-modules: a relational PostgreSQL database with Flyway migrations for the HTTP-saga module, and a Redis cache for transient orchestration state in the legacy service-bus module.

## Relational Model (HTTP-Saga Module)

### Database

PostgreSQL (Azure Flexible Server in QA/Prod, local PostgreSQL for development). The service connects with Azure AD passwordless authentication via Azure Identity JDBC plugin (`azure.passwordless-enabled: true` in QA profile, `nexpay-recipientorchestrator-svc/nexpay-recipientorchestrator-boot/src/main/resources/application.yaml` line 321). Connection pooling is handled by HikariCP.

### Schema (Flyway Migrations)

**V1__initial_schema.sql** — creates three core tables:

```
saga (
    id              UUID PK DEFAULT gen_random_uuid(),
    correlation_id  UUID NOT NULL UNIQUE,     -- external idempotency anchor
    current_state   VARCHAR(30) NOT NULL,     -- enum: INITIATED…COMPLETED|FAILED|COMPENSATED
    claim_code      VARCHAR(100),
    error_message   TEXT,
    card_id         VARCHAR (added in V3),
    created_at      TIMESTAMPTZ,
    updated_at      TIMESTAMPTZ
)

saga_step (
    id              UUID PK,
    saga_id         UUID FK → saga.id,
    state           VARCHAR(30),              -- each state transition is a row
    error_message   TEXT,
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ
)

outbox_event (
    id              UUID PK,
    saga_id         UUID FK → saga.id,
    event_type      VARCHAR(50),             -- "SAGA_COMPLETION"
    payload         JSONB,
    published       BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ,
    published_at    TIMESTAMPTZ
)
```

**V2** renames the `CLAIMCODEVALIDATED` state to `CLAIMCODE_VALIDATED` and removes a deprecated `completed_at` column.

**V3** adds a `card_id VARCHAR` column to the `saga` table to persist the card identifier returned by the card processor.

### Key Data Design Observations

**Correlation ID** (`saga.correlation_id`) is the only uniqueness anchor at the saga level. However, no unique constraint on `claim_code` means that multiple sagas can exist for a single claim code. The `getSagaByClaimCode()` method performs an advisory lookup (`findFirstByClaimCodeOrderByCreatedAtDesc`) but does not prevent concurrent creation of duplicate sagas. This is a concurrency gap for idempotency.

**Outbox Pattern** — `outbox_event` with a `published BOOLEAN` column follows the Transactional Outbox pattern. The payload is stored as `JSONB`. However, the current `writeCompletionEvent()` implementation in `SagaService.java` (lines 282–289) writes a bare string `{"sagaId":"…","event":"COMPLETION"}` rather than a properly typed event envelope. No publisher/relay process is visible in this repository — it presumably exists in a separate infrastructure component.

**Audit Trail** — every state transition writes a `saga_step` row with a timestamp. This provides a complete audit trail of saga lifecycle, which is important for Reg E evidence of disbursement processing.

**No Envers on Saga** — the saga table does not use Hibernate Envers. Changes to the saga entity are tracked only via the `saga_step` table, not via the full column-level audit that Envers provides on the recipient profile service.

## Redis State (Service-Bus Module)

The `CardCreationOrchestrationService` in the service-bus sub-module uses Redis as an ephemeral state store keyed by `transactionId`. The `OrchestrationState` object includes:
- `ddaAccountNumber` and `routingNumber` — sensitive ACH routing data stored in Redis in plaintext.
- `cardholderName` — PII stored transiently in Redis.

The Redis configuration is in `RedisConfig.java`. The QA profile enables TLS on the Redis connection (`ssl.enabled: true`, `nexpay-recipientweb-bff/nexpay-recipientweb-boot/src/main/resources/application-qa.yaml` line 38) but the service-bus module's own Redis config needs independent verification. Redis TTL policy for orphaned orchestration states is not visible in the repository.

## Data Flow Diagram (Conceptual)

```
BFF → POST /process-claim-code
         │
         ▼
    saga (PostgreSQL)      ← created at INITIATED
         │
    saga_step              ← one row per state transition
         │
    outbox_event           ← one row at COMPLETED
         │
    [Publisher TBD]        ← reads published=FALSE, emits to downstream
         │
    MPA / CSA / Reporting
```

## Sensitive Data Handling

| Data Element | Location | Encrypted? | Notes |
|---|---|---|---|
| `claim_code` | `saga` table | No | Claim codes are short-lived bearer tokens — storage should be reviewed |
| `card_id` | `saga` table | No | This is a processor-assigned token, not a PAN — acceptable |
| `error_message` | `saga` table | No | May contain claim-code values in error text — review logging |
| DDA-derived program ID | In-memory only | N/A | Not persisted; extracted at `OrchestrationService.java:155` |
| `ddaAccountNumber` / `routingNumber` | Redis (service-bus module) | TLS only | ACH sensitive data — should not persist beyond transaction TTL |

## Data Retention

No data retention policy is implemented in the code. The `saga`, `saga_step`, and `outbox_event` tables grow without bound. For PCI DSS and GDPR/CCPA compliance, a retention policy must be defined and automated. Particularly, `claim_code` values (which may serve as bearers of payment entitlement) should be removed or tokenized after the saga reaches a terminal state.

## Integration Data Contracts

The orchestrator publishes and consumes via:
- **Inbound REST**: OpenAPI-generated delegate `ProcessClaimCodeApiDelegateImpl` (HTTP POST)
- **Outbound REST**: HTTP clients to claim-code-svc, recipient-screening-api, recipient-profile-svc, cardprocessor-svc, ACL — all generated from OpenAPI specs
- **Outbound async**: `outbox_event` table (Transactional Outbox — not Kafka/Service Bus directly from this service)

## Schema Migration Risk

Flyway is configured with `clean-disabled: true` in QA/Prod (`application.yaml` line 19). The `out-of-order: false` setting enforces strict migration ordering. V2 and V3 are non-destructive ALTER TABLE operations. Future migrations adding new `SagaState` enum values will require both a Java enum change and a Flyway migration to widen the VARCHAR column if the value exceeds 30 characters.
