# Business Analyst View — nexpay-recipientorchestrator-svc

## Service Identity

| Attribute | Value |
|-----------|-------|
| Artifact ID | `nexpay-recipientorchestrator-svc` |
| Spring Boot | 4.0.5 (via nexpay-parent) |
| Java | 25 |
| Runtime port | 8080 (app) / 8081 (actuator) |
| Database | PostgreSQL (Azure Flexible Server in QA/Prod) |
| Swagger UI | Enabled in local/docker/QA/Prod (all environments) |

## Business Purpose

The nexpay-recipientorchestrator-svc is the **recipient onboarding and payment delivery orchestrator**. It coordinates the sequence of steps required to onboard a payee (recipient) and deliver a payment to them. In the NexPay Gen-3 architecture, it plays a role analogous to the nexpay-order-orchestrator but focused specifically on the recipient journey — identity, eligibility, screening, and payment instrument delivery — rather than the broader order lifecycle.

In the Gen-3 disbursement flow, this service is the authoritative coordinator called by the Recipient Web BFF when a payee selects their payment method and submits their registration. The BFF delegates the entire registration and payment delivery workflow to this service.

## Business Capabilities

### Claim Code Processing Saga

The core capability is `processClaimCodeSaga()`, implemented in `OrchestrationService.java`. This saga orchestrates:

1. **Validation (parallel)**: Validates the claim code and performs recipient screening simultaneously.
   - `ClaimCodeServiceClient.validateClaimCode(claimCode)` — confirms the claim code is genuine, unexpired, and carries a valid payment.
   - `RecipientScreeningServiceClient.submitScreeningRequest(recipient, claimCode, sagaId)` — submits the recipient's identity for OFAC/sanctions screening.

2. **Recipient Creation**: Creates or updates the recipient's profile in `nexpay-recipient-profile-svc`.

3. **Card Issuance**: Issues a virtual prepaid card via `nexpay-cardprocessor-svc` using the validated payment amount and program ID.

4. **ACL Write-back**: Updates the claim status in the legacy ACL system to `COMPLETED`.

5. **Post-processing**: Writes a completion event to the outbox for downstream consumers.

Note: The `nexpay-recipientorchestrator-svc` and `nexpay-order-orchestrator` appear to implement very similar (possibly identical) saga logic. This warrants clarification of the architectural boundary between the two services — they may target different disbursement triggers (recipient-initiated via BFF vs. system-initiated order processing).

### OFAC Screening — This Service's Role

This service is where OFAC screening occurs for the **recipient-triggered** disbursement flow. The `RecipientScreeningServiceClient.submitScreeningRequest()` call in Step 1 submits the recipient's identity to the screening service. If `screening.cleared()` returns false, the saga throws an `IllegalStateException` and the disbursement is stopped. This is the OFAC enforcement gate for payee-initiated claims.

### Saga State Machine

The saga progresses through the following states:
`INITIATED → CLAIMCODE_VALIDATED → SCREENING_CLEARED → RECIPIENT_CREATED → CARD_ISSUED → CLAIM_UPDATED → EVENT_EMITTED → COMPLETED`

Terminal failure state: `FAILED → COMPENSATED`

States are persisted to the `saga` table in PostgreSQL with individual step records in `saga_step`.

## Business Process Integration

### Entry Point

The service exposes a REST API (`ProcessClaimCodeApiDelegateImpl`) called by `nexpay-recipientweb-bff`. When a payee completes their registration form and selects a payment method, the BFF calls `POST /api/v1/claim-codes/{claimCode}/process` on this service.

### Exit Points

On successful completion, the service:
1. Returns a response to the BFF containing `sagaId` and `cardId`.
2. Writes a `SAGA_COMPLETION` outbox event consumed by MPA (Member Portal), CSA (Customer Service), and Reporting.
3. The BFF uses the returned `cardId` to encrypt a post-registration session token for the payee.

## Regulatory Obligations

- **OFAC/Sanctions (31 CFR Part 501)**: OFAC screening is performed in Step 1. The saga cannot progress to payment instrument issuance without `screening.cleared() == true`.
- **Reg E**: Each successful saga completion represents a completed electronic fund transfer. The saga audit trail (steps, outbox event) is the primary transaction record.
- **PCI DSS**: The service does not store card numbers. The `card_id` stored on the saga entity is the card processor's token, not a PAN. The service handles claim codes (payment entitlement tokens) — these should be treated as sensitive if they can be used to fraudulently initiate payments.
- **GDPR/CCPA**: Recipient PII (name, address, email, phone) flows through this service as part of the `RecipientRegistrationDetail` object. This data is passed to recipient-profile-svc for storage and to the card processor for issuance. Data minimisation should be verified — does the card processor need all recipient fields?

## Key Business Risks

1. **Compensation stubs not implemented**: Similar to the order orchestrator, compensation logic is stubbed (logs warning, no live action). If card issuance succeeds but ACL write-back fails, the card exists without the ACL knowing the claim is complete.
2. **No deduplication on claim code**: A payee or a network retry could create two sagas for the same claim code, leading to two payment instruments being issued.
3. **Card processor receives recipient PII**: The `createCardAtProcessor()` call passes `RecipientRegistrationDetail` (name, address) to the card processor. This PII transfer must be governed by a data processing agreement.
