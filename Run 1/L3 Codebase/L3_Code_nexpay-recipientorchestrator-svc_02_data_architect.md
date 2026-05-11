# Data Architect View — nexpay-recipientorchestrator-svc

## Data Architecture Summary

The nexpay-recipientorchestrator-svc uses a **relational PostgreSQL database** with JPA/Hibernate and Flyway schema management. The data model is purpose-built for saga orchestration: it records saga lifecycle state, step-level audit trail, and outbox events. The service does not store recipient PII directly — that responsibility belongs to `nexpay-recipient-profile-svc`.

## Database Configuration

| Attribute | Value |
|---|---|
| Database type | PostgreSQL |
| ORM | Hibernate 6 (via Spring Boot 4 JPA) |
| Schema management | Flyway |
| Connection pooling | HikariCP |
| Prod authentication | Azure AD passwordless (Managed Identity) |
| DDL auto | `validate` (Hibernate validates schema against JPA entities; does not alter) |

The `ddl-auto: validate` setting is production-safe — Hibernate will fail on startup if the database schema does not match the JPA entity mappings. This catches migration failures before the service accepts traffic.

## Schema Design

### Table: `saga`

```sql
saga (
    id              UUID PK DEFAULT gen_random_uuid(),
    correlation_id  UUID NOT NULL UNIQUE,
    current_state   VARCHAR(30) NOT NULL,
    claim_code      VARCHAR(100),
    error_message   TEXT,
    card_id         VARCHAR,      -- added in V3
    created_at      TIMESTAMPTZ NOT NULL,
    updated_at      TIMESTAMPTZ NOT NULL
)
```

**Indexes**: `idx_saga_current_state`, `idx_saga_correlation_id`, `idx_saga_claim_code_created_at`

**Design observations**:
- `correlation_id` has a UNIQUE constraint — this is the external idempotency anchor. However, `claim_code` does not have a unique constraint. Multiple sagas can exist for the same claim code.
- `card_id` is added in V3 migration and stored as `VARCHAR` (no length limit specified in V3). The card processor's ID format should inform an appropriate length constraint.
- `error_message` as `TEXT` may contain claim code values if the error occurs during validation — these should be considered sensitive.

### Table: `saga_step`

```sql
saga_step (
    id              UUID PK,
    saga_id         UUID FK → saga.id,
    state           VARCHAR(30),
    error_message   TEXT,
    started_at      TIMESTAMPTZ DEFAULT now(),
    completed_at    TIMESTAMPTZ
)
```

Each state transition produces one row. This provides a complete, immutable audit trail of saga progression. For a saga that completes successfully (INITIATED → … → COMPLETED), approximately 8 rows are written. For a failed saga, additional FAILED and COMPENSATED rows are appended. The `completed_at` column is nullable — it appears `started_at` is always set but `completed_at` may not be explicitly populated in the current implementation (not visible in `SagaService.java`'s `recordStep` method).

### Table: `outbox_event`

```sql
outbox_event (
    id              UUID PK,
    saga_id         UUID FK → saga.id,
    event_type      VARCHAR(50),
    payload         JSONB,
    published       BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT now(),
    published_at    TIMESTAMPTZ
)
```

The Transactional Outbox pattern. `published: false` rows are the pending delivery queue for downstream consumers. The `payload` is JSONB — suitable for structured querying but the current `SagaService.writeCompletionEvent()` writes a raw string rather than leveraging JSONB structure:
```java
event.setPayload("{\"sagaId\":\"" + sagaId + "\",\"event\":\"COMPLETION\"}");
```
This string concatenation should be replaced with Jackson serialisation to a typed event object. String-built JSON is prone to injection if saga IDs contain unexpected characters (though UUIDs are safe here).

## Flyway Migration History

| Migration | Description |
|---|---|
| `V1__initial_schema.sql` | Creates `saga`, `saga_step`, `outbox_event` tables with indexes |
| `V2__remove_completed_at_and_update_claimcodevalidated_state.sql` | Removes `completed_at` from saga, renames state enum value |
| `V3__alter_state_column_sizes_and_add_card_to_saga.sql` | Adds `card_id` column, widens state VARCHAR columns |

All migrations are non-destructive in the current set. The `clean-disabled: true` setting in QA/Prod prevents accidental `flyway clean` operations.

## Data Flow

```
BFF HTTP Request (RecipientRegistrationDetail)
    │
    ▼
ProcessClaimCodeApiDelegateImpl.processClaimCode()
    │
    ├── SagaService.startSaga(claimCode)
    │       → INSERT INTO saga (current_state='INITIATED', correlation_id=new_uuid, claim_code=...)
    │       → INSERT INTO saga_step (state='INITIATED')
    │
    ├── [Step 1] ClaimCodeServiceClient.validateClaimCode()   [no DB write if remote call]
    │           RecipientScreeningServiceClient.screenRecipient()  [no DB write]
    │       → SagaService.advanceSaga(CLAIMCODE_VALIDATED)
    │           → UPDATE saga SET current_state='CLAIMCODE_VALIDATED'
    │           → INSERT INTO saga_step (state='CLAIMCODE_VALIDATED')
    │       → SagaService.advanceSaga(SCREENING_CLEARED)
    │           → UPDATE saga, INSERT saga_step
    │
    ├── [Step 2] RecipientProfileServiceClient.createOrUpdateRecipient()  [no local DB write]
    │       → advanceSaga(RECIPIENT_CREATED) → UPDATE/INSERT
    │
    ├── [Step 3] CardProcessorServiceClient.createCardAtProcessor()  [no local DB write]
    │       → SagaService.updateCardResult(cardId) → UPDATE saga SET card_id=...
    │       → advanceSaga(CARD_ISSUED) → UPDATE/INSERT
    │
    ├── [Step 4] AclApiClient.updateClaimStatus()  [no local DB write]
    │       → advanceSaga(CLAIM_UPDATED) → UPDATE/INSERT
    │
    └── [Step 5] SagaService.writeCompletionEvent()
            → INSERT INTO outbox_event (published=false, payload=...)
            → advanceSaga(EVENT_EMITTED) → UPDATE/INSERT
            → advanceSaga(COMPLETED) → UPDATE/INSERT
```

## Sensitive Data Handling

| Data | Stored? | Where | Protection |
|---|---|---|---|
| Claim code | Yes | `saga.claim_code` | In plaintext — short-lived bearer; consider hashing at rest |
| Card ID (processor token) | Yes | `saga.card_id` | Processor-assigned token, not PAN |
| Error messages | Yes | `saga.error_message`, `saga_step.error_message` | May contain claim code values; review |
| Recipient PII | No | Not stored locally; passed through to profile-svc | — |
| Payment amount | No | Not stored in this service | Sourced at runtime from claim-code-svc |

## Data Retention Consideration

The saga tables will grow indefinitely without a retention policy. For GDPR/CCPA compliance and database hygiene, a retention strategy should archive or delete terminal-state sagas (COMPLETED, COMPENSATED) after a retention window (e.g., 7 years for financial records, then anonymise or delete). The claim code value in `saga.claim_code` represents a reference to a payment entitlement — once the saga is completed and the payment delivered, retaining the claim code has no operational value and increases the data surface area for potential exposure.
