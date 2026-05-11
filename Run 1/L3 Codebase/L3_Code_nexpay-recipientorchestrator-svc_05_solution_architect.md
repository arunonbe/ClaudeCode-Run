# Solution Architect View — nexpay-recipientorchestrator-svc

## Technical Architecture

`nexpay-recipientorchestrator-svc` shares the same multi-module hexagonal architecture pattern as `nexpay-cardprocessor-svc`, confirming a common NexPay Gen-3 template.

### Module Topology

```
nexpay-recipientorchestrator-api          ← OpenAPI contract (code-generated)
nexpay-recipientorchestrator-client/      ← Published client libraries
  ├── -cardprocessor-client-api           ← Client for nexpay-cardprocessor-svc
  ├── -claimcode-client-api               ← Client for nexpay-claim-code-svc
  └── -screening-client-api               ← Client for recipient-screening-api
nexpay-recipientorchestrator-data-entity  ← JPA entities (saga, saga_step, outbox_event) + Flyway
nexpay-recipientorchestrator-data-repository ← Spring Data repositories
nexpay-recipientorchestrator-impl         ← Saga orchestration logic
  ├── OrchestrationService                ← processClaimCodeSaga()
  ├── SagaService                         ← State machine + DB operations
  └── SagaStateTransitions                ← Valid state transition rules
nexpay-recipientorchestrator-boot         ← Spring Boot assembly + configuration + Dockerfile
```

## API Surface

| Method | Path | Description | Called By |
|---|---|---|---|
| POST | `/api/v1/claim-codes/{claimCode}/process` | Process a claim code — initiate the full recipient onboarding and card issuance saga | `nexpay-recipientweb-bff` |

A single endpoint drives the entire saga. The endpoint is synchronous from the BFF's perspective — the BFF waits for the saga to complete (or fail) before returning to the payee.

### Client Modules Published

The `-client` submodule publishes three OpenAPI-generated client libraries:
- `nexpay-recipientorchestrator-cardprocessor-client-api` — used internally to call `nexpay-cardprocessor-svc`
- `nexpay-recipientorchestrator-claimcode-client-api` — used internally to call `nexpay-claim-code-svc`
- `nexpay-recipientorchestrator-screening-client-api` — used internally to call `recipient-screening-api`

`nexpay-recipientweb-bff` consumes the main orchestrator client generated from the `-api` module.

## Security Posture

### Authentication
- Bearer JWT validated via Spring Security (via `nexpay-parent`).
- No fine-grained RBAC visible in the reviewed code — authentication is all-or-nothing for the single endpoint.

### Claim Code Sensitivity
- Claim codes are stored plaintext in `saga.claim_code`. Claim codes function as single-use payment bearer tokens — if intercepted and reused before saga completion, they could be exploited to initiate duplicate payments.
- **Recommendation**: Hash claim codes at rest using a one-way function (SHA-256). Store only the hash; compare hashes at validation time. The claim code service performs the actual validation via remote call so the raw value is not needed locally after the saga starts.

### OFAC Screening Enforcement Gate
- `RecipientScreeningServiceClient.submitScreeningRequest()` is called in parallel with claim code validation (Step 1).
- Failure throws `IllegalStateException` → saga transitions to `FAILED`.
- No payment instrument is issued to an OFAC-hit recipient.
- **Gap**: The error response surfaced to the BFF (and thus the payee) must be a generic "unable to process" message to avoid AML tipping-off concerns. The current `IllegalStateException` propagation path should be verified to confirm it produces a compliant error message.

### Swagger UI in All Environments (Including Production)

The QA and Prod profiles both have `swagger-ui.enabled: true` and `try-it-out-enabled: true`. This is a **production security concern** shared across NexPay services. The Swagger UI allows interactive API calls to `POST /api/v1/claim-codes/{code}/process` from any browser, potentially enabling:
- Saga creation for arbitrary claim codes by authenticated users
- API reconnaissance

**Recommendation**: Set `swagger-ui.enabled: false` and `api-docs.enabled: false` in the `qa` and `prod` profiles. Retain only for `local` and `docker` profiles.

## Technical Debt

| Item | Severity | Description |
|---|---|---|
| Compensation logic is stubbed | Critical | `compensate()` methods log a warning but take no action. Card issued + ACL write-back failure = orphaned card. |
| No claim code uniqueness constraint | High | `saga.claim_code` has no UNIQUE constraint — multiple sagas can process the same claim code concurrently (double-payment risk) |
| Claim code stored in plaintext | High | Payment bearer token stored unprotected in `saga.claim_code` |
| Swagger UI enabled in production | High | Interactive API explorer exposed in prod |
| No deployment pipeline | High | Only `codeql.yml` present — no `deployment.yml`. Service deployment is opaque. |
| Outbox event as string concatenation | Medium | `"{\"sagaId\":\"" + sagaId + "\",...}"` — replace with Jackson serialisation |
| `completed_at` not populated in saga_step | Medium | Step completion time not recorded — audit trail incomplete |
| OFAC rejection generic error not verified | High | `IllegalStateException` on screening failure may surface processor-specific messages to the payee |
| `saga.error_message` may contain claim code | Medium | Error during saga processing may embed claim code in error message |
| Base logging level `ERROR` in default profile | Medium | `WARN` would be safer; silent failures on misconfigured profile activation |
| No data retention policy | Medium | Saga records grow indefinitely; GDPR deletion obligation unaddressed |
| `0.0.1-SNAPSHOT` version | Medium | SNAPSHOT in production pipeline |

## Saga Compensation Design Gap (Critical)

The compensation logic in `OrchestrationService` is explicitly stubbed:

```java
// Compensation stub — no live rollback action
log.warn("Compensation not implemented: card issued but ACL update failed. Manual reconciliation required.");
```

This means in the following failure scenario:
1. Claim code validated ✓
2. Screening cleared ✓
3. Recipient created ✓
4. **Card issued ✓** (card exists at processor)
5. ACL write-back fails ✗ → saga → FAILED → compensation called → **STUB — no action**

Result: A prepaid card exists at the processor (Thredd/FIS), and the ACL (legacy system) does not know the claim is complete. The payee may receive a card that cannot be activated in the legacy system, or the claim code may remain "open" and be reusable.

**Resolution required before production go-live**: Implement `compensate()` to call `nexpay-cardprocessor-svc` to deactivate or cancel the issued card, and ensure the ACL state is corrected via the claim code service.

## Architectural Overlap with nexpay-order-orchestrator

As documented in `04_enterprise_architect.md`, this service implements nearly identical saga logic to `nexpay-order-orchestrator`. The solution architect should determine:

1. Are both services intended to coexist permanently (different triggers: BFF-initiated vs. system-initiated)?
2. Should the saga implementation be extracted to a shared library (`nexpay-saga-common`) consumed by both?
3. Is there a risk of both orchestrators being called for the same claim code due to a triggering ambiguity?

Until this is resolved, the `saga.correlation_id` UNIQUE constraint provides the primary deduplication defence — but only if both orchestrators use the same `correlation_id` for the same payment event.

## Gen-3 Architecture Assessment

This service follows all correct Gen-3 patterns:
- PostgreSQL + Flyway + Spring Data JPA
- Azure AD passwordless auth
- Testcontainers for integration tests
- Virtual threads (Project Loom, Java 25)
- OpenAPI-generated client modules
- OTel instrumentation
- Transactional Outbox for downstream event delivery

The two critical gaps preventing production readiness:
1. Compensation not implemented
2. No deployment pipeline defined in the repository
