# Enterprise Architecture — nexpay-recipientweb-bff

## Platform Generation
**Gen-3 (NexPay)** — BFF layer of the NexPay Gen-3 recipient web platform.

## Business Domain
Recipient Payment Claim / Disbursement UX. This BFF mediates between the recipient-facing web UI (OnePlatform React frontend) and the Gen-3 backend microservices for the claimable-choice payment collection flow.

## Role in the Platform
| Attribute | Value |
|-----------|-------|
| Type | Backend for Frontend (BFF) |
| Deployed in production | Yes (Azure Container Apps) |
| API exposure | External APIM (EXTERNAL_APIM: true) |
| Replaces | Legacy OnePlatform REST API controllers for claimable-choice flow |

## Dependencies
### Upstream (callers)
- **OnePlatform React UI / Recipient Web Application** — the primary consumer.
- External API clients via Azure APIM.

### Downstream (services called)
| Service | Purpose |
|---------|---------|
| `nexpay-auth-svc` | Username availability check |
| `nexpay-claim-code-svc` | Claim code validation, recipient registration details |
| `nexpay-config-svc` | Program detail, registration settings, program countries |
| `nexpay-recipientorchestrator-svc` | Claim code processing orchestration (saga) |
| Redis (affiliate cache) | Affiliate/program lookup by custom URL |

## Integration Patterns
- **Backend for Frontend** — aggregates calls to multiple downstream services into a single UI-optimised response.
- **JWE-based stateless session** — card token carries session state between UI calls without server-side session storage.
- **Async parallel fanout** — `CompletableFuture` with virtual thread executor for concurrent downstream calls (claim validation + program detail in `claimableChoiceFTUOnload`; registration settings + recipient detail in `populateContactInfo`).
- **Affiliate-domain validation** — cross-program payment claim prevention via DDA-to-affiliateId matching.
- **Base64-encoded response envelope** — `ModelApiResponse` with `successResponse` as Base64 JSON preserves compatibility with legacy OnePlatform UI contract.
- **Redis affiliate cache** — populated by an Azure Function triggered by affiliate database changes (see `onbeeast-architecture-models` C4 container diagram).

## Strategic Status
- **Active Gen-3 development** — `0.0.1-SNAPSHOT`, NexPay parent `0.2.8-SNAPSHOT`.
- This service is the Gen-3 replacement for the OnePlatform BFF (Oneplatform API in the C4 container model).
- Multiple `// TODO` markers indicate the legacy OnePlatform flows are being migrated incrementally — not all flows are complete.
- The C4 component diagram in `onbeeast-architecture-models` documents the target state: Card Activation, Dashboard, Generic, Login, Registration, and Transaction controllers.

## Migration Blockers
- Incomplete flows: T&C acceptance check, OTP/MFA, `userNameExists` check sourced from auth service, DOB/SSN sourcing for registration (`toRegistrationDetails` TODOs in `ClaimableChoiceApiDelegateImpl`).
- `otel-grpc:1.0.0-SNAPSHOT` must be replaced with a stable release.
- Legacy `encryptValidUserRegistrationClaim` includes `password` in the JWE payload — this must be reviewed for compliance before production promotion.
- Redis dependency for affiliate lookup: Redis availability SLA must match or exceed BFF availability SLA.
