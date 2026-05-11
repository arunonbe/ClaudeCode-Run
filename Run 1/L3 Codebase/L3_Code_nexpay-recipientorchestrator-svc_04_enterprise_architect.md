# Enterprise Architect View — nexpay-recipientorchestrator-svc

## Position in the NexPay Gen-3 Architecture

The nexpay-recipientorchestrator-svc is the **payee-side orchestration layer**, coordinating the sequence of actions needed to onboard a recipient and deliver their payment. It sits between the Recipient Web BFF (which handles the payee's browser interaction) and the downstream platform services (claim code, screening, profile, card processor, legacy ACL).

```
Payee Browser
    │
    ▼
nexpay-recipientweb-bff
    │ POST /process-claim-code
    ▼
nexpay-recipientorchestrator-svc  ← THIS SERVICE
    │
    ├── nexpay-claim-code-svc (validation)
    ├── recipient-screening-api (OFAC/sanctions)
    ├── nexpay-recipient-profile-svc (identity)
    ├── nexpay-cardprocessor-svc (payment instrument)
    ├── legacy ACL (write-back)
    └── outbox_event → [MPA / CSA / Reporting]
```

## Architectural Overlap with nexpay-order-orchestrator

A critical architectural observation is that `nexpay-recipientorchestrator-svc` and `nexpay-order-orchestrator` implement nearly identical saga logic:
- Same step sequence (validate → screen → recipient → card → ACL → outbox)
- Same `SagaService`, `SagaState`, `SagaStateTransitions` pattern
- Same `OrchestrationService.processClaimCodeSaga()` implementation
- Same PostgreSQL schema (saga, saga_step, outbox_event)

This suggests either:
1. Both services were created from the same template and serve different triggers (BFF-initiated vs. system-initiated).
2. One service is intended to supersede the other but both are in development simultaneously.
3. The services target different payment rails (recipient web portal vs. batch/system orders).

The enterprise architecture must clarify the boundary: which service owns which disbursement trigger, and what prevents both being called for the same claim code. Without this clarification, the risk of double payment is elevated.

## OFAC Screening Integration

This service implements the OFAC screening enforcement gate for payee-initiated claims. The flow is:

1. `RecipientScreeningServiceClient.submitScreeningRequest(recipient, claimCode, sagaId)` is called in parallel with claim code validation.
2. The result `RecipientScreeningResult.cleared()` is evaluated.
3. If `!screening.cleared()`, an `IllegalStateException` is thrown, triggering saga failure and compensation.

This means an OFAC hit on a recipient will:
- Fail the saga at the screening step.
- Not issue a payment instrument.
- Record the failure in `saga.error_message` and `saga_step.error_message`.
- NOT currently notify the payee of the specific reason for rejection (the BFF receives a 500-level error response).

**Enterprise concern**: OFAC screening results must be handled with extreme care. The reason for a screening failure must not be disclosed to the recipient (potential tipping-off violation under AML regulations). The error handling should provide a generic "unable to process" response to the payee while routing the specific screening result to Compliance teams via the outbox event or a dedicated compliance notification.

## Service Client Module

The `-client` submodule (`nexpay-recipientorchestrator-client`) publishes an OpenAPI-generated client library. The BFF (`nexpay-recipientweb-bff`) includes this client library as a dependency (`nexpay-recipientweb-recipientorchestrator-client-api`), enabling type-safe HTTP calls from the BFF to this service. This is the standard pattern across the NexPay platform.

## Integration Model

| Consumer | How | API |
|---|---|---|
| `nexpay-recipientweb-bff` | REST (generated client) | `POST /api/v1/claim-codes/{code}/process` |
| MPA / CSA / Reporting | Outbox event (async) | `outbox_event.payload` |

## Enterprise Risk Register

| Risk | Severity | Notes |
|---|---|---|
| Architectural overlap with nexpay-order-orchestrator | High | Potential double-payment; requires boundary clarification |
| Compensation stubs not implemented | Critical | Card issued without reversal capability on failure |
| OFAC rejection not handled with compliance-grade response | High | Tipping-off risk; Compliance notification gap |
| Swagger UI enabled in production | High | API surface exposed; `try-it-out` enabled |
| No saga claim-code uniqueness constraint | High | Duplicate saga creation risk |
| Outbox event payload is raw string concatenation | Medium | Structural risk; replace with typed JSON serialisation |

## Compliance Architecture

### PCI DSS

- Claim codes are stored in `saga.claim_code` (plaintext). Claim codes function as payment bearer tokens. Their plaintext storage may constitute storage of Sensitive Authentication Data depending on programme configuration. Legal and Compliance should assess.
- The card ID (`card_id`) stored on the saga is the processor's token — not a PAN — and is not subject to PAN storage restrictions.
- The service is within the CDE (Cardholder Data Environment) boundary to the extent that it handles claim codes and coordinates card issuance.

### GDPR/CCPA

- Recipient PII (name, address, phone) flows through this service's API layer but is not persisted. Data lineage should be documented to confirm no local PII retention.
- The `error_message` fields in saga and saga_step may contain fragments of recipient-identifying information if errors occur during the recipient creation step. These must be included in data retention and deletion policies.

### NACHA / Reg E

- Each completed saga represents a completed electronic fund transfer. The saga record and step history are the primary evidence.
- Failed/compensated sagas where a card was issued but the ACL write-back failed require manual reconciliation — this is a Reg E disclosure risk if the payee received a card but the system doesn't record the transfer as complete.
