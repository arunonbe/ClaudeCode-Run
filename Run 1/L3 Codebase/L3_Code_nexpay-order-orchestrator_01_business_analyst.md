# Business Analyst View — nexpay-order-orchestrator

## Service Identity

| Attribute | Value |
|-----------|-------|
| Artifact ID | `nexpay-order-orchestrator` |
| Parent POM | `nexpay-parent 0.2.6-SNAPSHOT` |
| Spring Boot | 4.0.5 |
| Java | 25 |
| Runtime port | 8080 (app) / 8081 (actuator) |
| Deploy target | Azure Container App `ca-nexpay-order-orchestrator` |

## Business Purpose

The nexpay-order-orchestrator is the central fulfillment engine for NexPay Gen-3 disbursements. Its single business responsibility is to take a validated disbursement order — represented by a claim code that a payee has presented — and drive that order to completion by coordinating every downstream service required to release funds to the payee.

The service exists because disbursement fulfillment is inherently multi-step and multi-party. Releasing a payment requires: verifying the claim code is genuine and has not expired, screening the payee against OFAC and other sanctions lists, creating or updating the payee's identity record, issuing the chosen payment instrument (virtual prepaid card in the current implementation), writing back a "completed" status to the ACL (Access Control Layer) legacy system, and emitting a completion event for downstream consumers such as MPA (Member Portal Application), CSA (Customer Service Application), and Reporting.

If any single step fails, the funds must not be disbursed and any partial work must be reversed. The orchestrator implements this using the Saga choreography-as-orchestration pattern.

## Business Capabilities

### Claim-Code Processing (Happy Path)

The primary business flow is the `processClaimCode` Saga, implemented in `OrchestrationService.java`. The saga proceeds through five numbered steps:

1. **Validation (parallel)**: The claim code is validated against the nexpay-claim-code-svc and the payee identity is screened via recipient-screening-api simultaneously. Both calls run in parallel using Java 25 virtual threads via `StepExecutor`. Partial state is persisted immediately: the saga advances to `CLAIMCODE_VALIDATED` when claim validation passes and independently to `SCREENING_CLEARED` when the screening clears. This means that even if only one sub-task succeeds before a restart, progress is not lost.

2. **Recipient creation**: The recipient (payee) profile is created or updated in nexpay-recipient-profile-svc. The saga advances to `RECIPIENT_CREATED`.

3. **Issuance**: A virtual prepaid card is created by nexpay-cardprocessor-svc using the validated payment amount (in minor currency units, extracted from the claim-code validation response) and a program ID derived from the first 8 characters of the DDA field. The saga advances to `CARD_ISSUED`.

4. **ACL write-back**: The claim status is updated to `COMPLETED` in the legacy ACL system. The saga advances to `CLAIM_UPDATED`.

5. **Post-processing**: A `SAGA_COMPLETION` outbox event is written. The saga advances through `EVENT_EMITTED` to `COMPLETED`. Downstream consumers poll or subscribe to outbox events to trigger their own workflows.

### Compensation (Unhappy Path)

If any step throws an exception, `failSaga()` is called, which transitions the saga to `FAILED` and runs `compensate()`. Compensation walks the `STEP_ORDER` list in reverse and calls a stub method for each completed step (`compensateRecipientCreation`, `compensateCardIssuance`, etc.). As of the current codebase, all compensation stubs log a warning but take no live action — this is a known gap requiring completion before production go-live with real financial instruments. See `SagaService.java` lines 213–255.

### Retry

A saga in `FAILED` or `COMPENSATED` state can be retried by calling `retrySaga()`, which creates a brand-new saga for the same claim code. This supports ops team manual recovery workflows.

### Legacy Service-Bus Orchestration

The `nexpay-order-orchestrator-service-bus` sub-module contains an earlier, event-driven orchestration design using Azure Service Bus and Azure Event Hub, with Redis-backed state (`CardCreationOrchestrationService.java`). This module handles a different flow: card creation via DDA account provisioning (used for ACH/push-to-card disbursements). The two orchestration patterns (HTTP saga vs. reactive service-bus saga) coexist in the repository, targeting different payment rails.

## User-Facing Impact

End-users (payees) interact with this service indirectly through the nexpay-recipientweb-bff. When a payee submits their registration on the Claimable Choice web portal, the BFF calls this orchestrator's `POST /api/v1/claim-codes/{claimCode}/process` endpoint. The payee's experience depends entirely on this service completing or cleanly failing within the 45-second response timeout configured in `application.yaml` (line 87).

## Regulatory Obligations

- **Reg E (Electronic Fund Transfer Act)**: Every disbursement this service processes constitutes an electronic fund transfer. The saga audit trail (step table, outbox event) is the primary evidence of whether funds were transferred and when.
- **OFAC / Sanctions**: Screening happens in Step 1 via the `RecipientScreeningServiceClient`. The orchestrator enforces a hard stop if `screening.cleared()` returns false.
- **PCI DSS**: The orchestrator does not store card numbers or CVV. It receives a `cardId` (token) from the card processor and stores only that in the saga entity. The card data environment boundary is maintained.
- **AML**: Velocity and amount controls are the responsibility of `nexpay-ordervalidator-svc`. The orchestrator relies on the claim-code validation to have applied those controls before a claim code is presented.

## Key Business Risks

1. **Compensation stubs are not implemented**: If a card is issued and then the ACL write-back fails, the issued card is not automatically cancelled. This creates a double-payment risk unless compensating logic is completed.
2. **No idempotency key on the HTTP endpoint**: A payee or the BFF retrying the HTTP call can initiate a second saga for the same claim code. The `saga` table has no unique constraint on `claim_code`. Duplicate saga detection is limited to `getSagaByClaimCode()`, which is advisory only.
3. **Program ID extraction from DDA**: The program ID is derived by taking the first 8 characters of the DDA string at `OrchestrationService.java` line 155. If upstream systems change the DDA format, program routing breaks silently.
