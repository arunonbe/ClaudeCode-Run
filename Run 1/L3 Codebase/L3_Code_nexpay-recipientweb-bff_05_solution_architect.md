# Solution Architecture — nexpay-recipientweb-bff

## Technical Architecture
- **Framework**: Spring Boot (nexpay-parent:0.2.8-SNAPSHOT), Java 25.
- **Architecture style**: Multi-module Maven BFF; OpenAPI-first; delegate pattern.
- **Async**: `CompletableFuture` + `@Qualifier("virtualThreadExecutor")` Executor for parallel downstream calls.
- **JWE**: nimbus-jose-jwt 10.9; `DIR`/`A256GCM` symmetric encryption.
- **Redis**: Spring Data Redis, Lettuce connection pool.
- **Observability**: `AuditFilter` propagates `actor.id`, `source`, `reason`, `Idempotency-Key` as OTEL baggage.
- **OTEL**: `otel-grpc:1.0.0-SNAPSHOT` for gRPC telemetry export (SNAPSHOT version — stability risk).

## API Surface
| Method | Path | Description |
|--------|------|-------------|
| POST | `/claimable-choice/validate` | Validate single claim code |
| POST | `/claimable-choice/validate-multiple` | Validate multiple claim codes |
| POST | `/claimable-choice/ftu-onload` | FTU onload: program + claim code data |
| POST | `/claimable-choice/populate-contact-info` | Decrypt token, fetch registration info |
| POST | `/claimable-choice/submit-registration` | Submit CC registration |
| POST | `/registration/check-username` | Check username availability |
| GET | `/my-account/states` | Country/state list |
| GET | `/actuator/health` | Liveness/readiness probes |
| GET | `/actuator/metrics`, `/actuator/prometheus` | Metrics (port 8081) |

## Security Posture
- **JWE encryption**: `JweHelper.java:43-53` — 32-byte symmetric key (`A256GCM`) loaded at startup; key from `jwt.secret-token` property; if key length is not exactly 32 bytes, startup fails with `IllegalArgumentException`.
- **Password in JWE**: `JweHelper.java:122-139` — `encryptValidUserRegistrationClaim` places `cardNumber`, `userName`, and `password` into the JWE payload; these are protected by the symmetric key.
- **DDA in JWE**: `JweHelper.java:141-160` — `encryptDda` conditionally wraps DDA in JWE, toggled by `mobileApp.ddaEncrypt` property.
- **Actor audit**: `AuditFilter.java:50-111` — skips `/actuator` paths; reads `X-Actor-Id` header, then auth token claims, then falls back to `"undefined"`.
- **Log sanitisation**: `AuditFilter.java:203-215` — replaces non-printable/non-ASCII characters before logging.
- **Transport**: External APIM exposure — HTTPS enforced at APIM/ACA ingress level; no application-level TLS config.
- **Authentication**: Not enforced by this service directly — relies on APIM and/or upstream Spring Security (configuration not observed in this module).

## Technical Debt
- Multiple `// TODO` in `ClaimableChoiceApiDelegateImpl`:
  - Line 103: `configService.isClaimableChoiceEnabled(programId)` — hardcoded `true`.
  - Line 106: `userService.getUserFromMemberId(memberId)` — hardcoded `false` (registered flag).
  - Line 367-370: `checkTermsAndConditions`, `termsFileName`, `userNameExists` — hardcoded stubs.
  - Lines 652-655: `dob`, `socialSecurityNumber`, `whatsAppPhone`, `homeCountryCode` — not populated.
- `otel-grpc:1.0.0-SNAPSHOT` — SNAPSHOT dependency in production build.
- `JweHelper.java` has mixed indentation (spaces vs tabs from line 70 onward) — legacy code.
- `encryptValidUserRegistrationClaim` places `password` in JWE — plaintext password in token payload before encryption; must review if this matches the security model.
- `Base64Helper.encode()` produces non-signed, non-encrypted output — interceptable at transport layer if HTTPS fails.
- No retry or circuit-breaker on downstream REST clients (`RestClient` with `SimpleClientHttpRequestFactory`) — a slow downstream service will block the virtual thread.

## Code-Level Risks
| File | Line | Risk |
|------|------|------|
| `JweHelper.java` | 122-139 | `password` field placed into JWE registration token — credential material in encrypted payload; key compromise exposes passwords |
| `JweHelper.java` | 43 | `secret.getBytes(StandardCharsets.UTF_8)` — key length must be exactly 32 bytes; any misconfiguration causes hard startup failure |
| `ClaimableChoiceApiDelegateImpl.java` | 103-115 | Multiple hardcoded stubs (`claimableChoice=true`, `registered=false`, `mfaResponse=null`) — incomplete feature parity with legacy |
| `ClaimableChoiceApiDelegateImpl.java` | 555-561 | `deriveAffiliateId`: if DDA is null or < 8 chars, returns null and affiliate validation fails — no specific error code for short DDA |
| `RestClientConfig.java` | 119 | `SimpleClientHttpRequestFactory` used for all downstream calls — no connection pooling, no circuit breaker, no retry |
| `pom.xml` | 47 | `otel-grpc.version: 1.0.0-SNAPSHOT` — SNAPSHOT in production dependency chain |

## Gen-3 Migration Requirements
- Service is already Gen-3 native.
- Before production promotion: complete all `// TODO` stubs, replace `otel-grpc` SNAPSHOT, implement circuit breakers on downstream REST clients, review `password` in JWE design, disable Swagger UI in prod profile, verify APIM throttling and authentication policies.
