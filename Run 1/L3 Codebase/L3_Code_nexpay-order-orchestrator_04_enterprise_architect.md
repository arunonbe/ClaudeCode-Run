# Enterprise Architect View — nexpay-order-orchestrator

## Position in the NexPay Gen-3 Architecture

The nexpay-order-orchestrator occupies the **fulfillment orchestration layer** of the NexPay Gen-3 disbursement platform. It is the authoritative coordinator for claim-code-based disbursements and sits at the intersection of the recipient-facing portal, the identity and screening infrastructure, the payment instrument provisioning layer, and the legacy ACL system.

```
┌─────────────────────────────────────────────────────────────────────┐
│  External (Payee-Facing)                                             │
│  nexpay-recipientweb-bff  →  POST /api/v1/claim-codes/{cc}/process  │
└──────────────────────────────────┬──────────────────────────────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │  nexpay-order-orchestrator   │  ← THIS SERVICE
                    │  (Saga Orchestrator)         │
                    └──┬───────┬────────┬──────┬──┘
                       │       │        │      │
              claim-   │  screening     │   card-
              code-svc │  -api    recip-│   processor-
                       │        ient-  │   svc
                       │        profile│
                       │        -svc   │
                       │               │
                    legacy-ACL   outbox-event
                    (write-back) (→ MPA/CSA/Reporting)
```

## Architecture Style

The orchestrator implements the **Orchestration Saga** pattern (as opposed to choreography). A single service (`OrchestrationService.java`) holds all step sequencing knowledge. This is an intentional design choice that simplifies observability and debugging: all orchestration logic is in one place, and the saga state machine provides a complete audit trail.

The service uses **Spring MVC (blocking)** with **Java 25 virtual threads** (`spring.threads.virtual.enabled: true`). This gives synchronous, readable code semantics while achieving high concurrency through virtual thread scheduling — avoiding the complexity of reactive (WebFlux) code that would otherwise be needed for the same level of I/O concurrency.

## Dual-Module Architecture

The repository contains two distinct orchestration designs:

| Module | Pattern | Persistence | Transport | Status |
|--------|---------|-------------|-----------|--------|
| `nexpay-order-orchestrator-impl` + `-boot` | HTTP Saga (step-based) | PostgreSQL + Outbox | REST in/out | Active (claim-code flow) |
| `nexpay-order-orchestrator-service-bus` | Reactive event-driven | Redis (transient) | Azure Service Bus + Event Hub | Legacy/ACH rail |

This dual design reflects an in-progress architectural migration from an event-driven, service-bus-based orchestration to a synchronous HTTP-saga model. The coexistence of two orchestration patterns within the same deployable creates conceptual complexity. The enterprise architecture recommendation is to establish a clear decommission timeline for the service-bus module once the HTTP-saga module covers all payment rails.

## Downstream Service Dependencies

| Dependency | Purpose | Timeout | Blocking? |
|---|---|---|---|
| `nexpay-claim-code-svc` | Claim validation | 15s connect / 45s read | Yes (Step 1 parallel) |
| `recipient-screening-api` | OFAC/sanctions screening | 15s connect / 45s read | Yes (Step 1 parallel) |
| `nexpay-recipient-profile-svc` | Payee identity CRUD | 5s connect / 10s read | Yes (Step 2) |
| `nexpay-cardprocessor-svc` | Payment instrument issuance | 5s connect / 30s read | Yes (Step 3) |
| Legacy ACL | Claim status write-back | Not explicitly set | Yes (Step 4) |

The 45-second read timeout for the validation API is the constraining factor for the overall saga response time. If the BFF has a shorter timeout, timeouts will surface as errors upstream before the service has a chance to complete.

## Saga State Machine as Enterprise Contract

The `SagaState` enum and `SagaStateTransitions` class define the formal state machine. Every allowed transition is explicitly declared. Invalid transitions throw an exception. This makes the saga state machine a machine-readable enterprise contract that governs exactly how a disbursement can proceed or fail. Future payment rails (ACH, push-to-card, check) should be added as additional steps or alternative saga flows, not by bypassing the state machine.

## API Surface

The service exposes:
- `POST /api/v1/claim-codes/{claimCode}/process` — initiates a new claim-processing saga
- `GET /api/v1/sagas/{sagaId}` — retrieves saga state (for ops / BFF polling)
- `POST /api/v1/sagas/{sagaId}/compensate` — triggers manual compensation
- `POST /api/v1/sagas/{sagaId}/retry` — creates a retry saga

The `INTERNAL_APIM: true` deployment flag in the CI workflow means the API is published to Azure APIM for internal service-to-service consumption only. It is not directly reachable from the public internet.

## Integration with nexpay-parent

All dependency versions and build plugins are inherited from `nexpay-parent`. The orchestrator overrides `jackson-datatype-jsr310.version` to `2.18.3` to resolve a Jackson 2.x/3.x compatibility issue with OpenAPI-generated client code under Spring Boot 4 (which defaults to Jackson 3.x). This is a known cross-cutting concern for all OpenAPI-generated clients in the NexPay platform.

## Enterprise Risk Register

| Risk | Severity | Mitigation Status |
|---|---|---|
| Compensation stubs are no-ops — card/recipient not reversed on failure | Critical | Not mitigated — stubs only log |
| No claim-code uniqueness constraint on saga table | High | Advisory lookup only |
| 45-second validation timeout may exceed BFF client timeout | Medium | Needs end-to-end timeout alignment |
| Service-bus module Redis state has no TTL — potential data accumulation | Medium | Not mitigated |
| Container runs as root | Medium | No `USER` instruction in Dockerfile |
| Container scanning disabled in CI | High | `CONTAINER_SCAN: false` — PCI DSS gap |

## NIST CSF 2.0 Alignment

| Function | Control | Status |
|---|---|---|
| Identify | Asset inventory via SBOM | Dependabot active; no explicit SBOM generation in pipeline |
| Protect | Secrets in Key Vault | Yes — managed identity + KV references |
| Protect | Network isolation | INTERNAL_APIM only — not public |
| Detect | SAST (CodeQL) | Active |
| Detect | DAST / container scanning | Container scan disabled |
| Respond | Saga compensation | Partial — stubs not implemented |
| Recover | Saga retry mechanism | Implemented |
