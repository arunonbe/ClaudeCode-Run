# Business Analysis — nexpay-recipientweb-bff

## Business Purpose
The Backend for Frontend (BFF) that drives the NexPay recipient-facing web application. It mediates between the React/OnePlatform UI and the NexPay Gen-3 backend microservices, orchestrating the claimable-choice payment collection flow: claim code validation, program onload, recipient registration, and post-registration session token creation. It replaces legacy OnePlatform REST API controllers for the NexPay Gen-3 recipient web experience.

## Capabilities
- Validate a single claim code (maps to legacy `ClaimableChoiceService#validateCCClaimCode`).
- Validate multiple claim codes in one call.
- Claimable Choice FTU (First Time Use) onload: parallel fetch of program configuration and claim code validation results; apply payment-amount minimum thresholds per modality.
- Populate contact info: decrypt incoming JWE card token, re-encrypt into a registration-scoped token, parallel-fetch program registration settings and recipient contact details.
- Submit CC registration: decrypt card token, build orchestrator request, call `nexpay-recipientorchestrator-svc`, return encrypted post-registration session token.
- Check username availability via `nexpay-auth-svc`.
- Provide state/country list (bundled static data via `CountryStateServiceImpl`).
- BFF wraps all successful responses as Base64-encoded JSON inside a `ModelApiResponse` envelope, matching the legacy OnePlatform encoding contract.
- Redis-backed affiliate cache lookup (`AffiliateService`) to resolve `customUrl` → affiliate record.

## Key Entities
| Entity | Source | Description |
|--------|--------|-------------|
| `ClaimablePaymentDetail` | nexpay-claim-code-svc | Payment record associated with a claim code |
| `AffiliateResponse` | Redis cache | Affiliate/program identity for URL routing |
| `ProgramDetail` | nexpay-config-svc | Program modalities, thresholds, countries |
| `ProgramRegistrationSettings` | nexpay-config-svc | Fields to display/require during registration |
| `RecipientRegistrationDetail` | nexpay-claim-code-svc | Pre-populated recipient contact data |
| `ProcessClaimCodeResponse` | nexpay-recipientorchestrator-svc | Saga ID, status, card ID after claim processing |
| Card Token (JWE) | Internal | Encrypted session state passed between UI and BFF |

## Business Rules
- Affiliate validation: the DDA field of the payment must match the affiliate derived from the `customUrl` — mismatch triggers a 400-equivalent `IllegalArgumentException`.
- DDA-to-affiliateId derivation: `affiliateId = "1" + dda.substring(0, 8)`.
- ProgramId derivation from affiliateId: `programId = affiliateId.substring(1)`.
- Claimable error codes: `Already_Claimed`, `Expired`, `invalid_status_code` derived from payment status.
- Modality suppression: `selectionOpt{Virtual,PrepaidCard,Check,ACH}` flags are set to `false` if payment amount does not exceed the program's minimum threshold for that modality.
- `cardToken` JWE uses `dir`/`A256GCM` algorithm with a 32-byte symmetric key configured as `jwt.secret-token`.
- Registration T&C, OTP, MFA, and username-exists checks have `// TODO` markers — not yet implemented.

## Data Flow
1. UI submits `customUrl` + `claimCode` (or multi-code list) to BFF.
2. BFF validates affiliate from Redis cache.
3. BFF calls `nexpay-claim-code-svc` to fetch/validate payment details.
4. BFF calls `nexpay-config-svc` for program details (parallel where possible using virtual threads).
5. BFF constructs a JWE card token and returns Base64-encoded JSON response.
6. On registration submission: BFF calls `nexpay-recipientorchestrator-svc` to process the claim, receives card ID, issues post-registration JWE token.

## Compliance Relevance
- JWE card token carries `memberId`, `affiliateId`, and `claimCode` — sensitive identity data in transit; protected by A256GCM encryption.
- `password` field included in JWE registration token (`encryptValidUserRegistrationClaim`) — credential material in token; key management is critical.
- Base64-encoded response payload: data is not encrypted, only encoded — UI must treat it as plaintext.
- No explicit PAN or SAD in the BFF — payment amounts and claim codes are handled but not card numbers.
- Affiliate validation prevents cross-program claim code use — a fraud-prevention control.

## Risks
- Multiple `// TODO` comments indicate incomplete flows: T&C check, OTP/MFA, username-exists check, DOB/SSN sourcing — production readiness incomplete.
- The `password` field is encrypted inside the JWE registration token; if the JWE key is compromised, stored credentials are exposed.
- `jwt.secret-token` must be exactly 32 bytes — misconfiguration causes startup failure (`IllegalArgumentException`).
- Redis cache is the source of truth for affiliate lookups — Redis unavailability blocks all claim code flows.
- Parallel async flows using `CompletableFuture` with virtual thread executor — exception propagation path must be carefully monitored.
