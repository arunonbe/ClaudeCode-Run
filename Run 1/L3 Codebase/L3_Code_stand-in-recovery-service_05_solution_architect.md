# 05 Solution Architect — stand-in-recovery-service

## Technical Architecture
Spring Boot 3.5.5, Java 21, multi-module Maven project. The deployable module is `stir-main`, which hosts a Spring Boot application (`StandInRecoveryApplication`) with:
- `RecoveryServiceController` — REST controller at `/recovery/**`
- `RecoveryService` / `RecoverySessionService` — service layer
- Spring Data JPA repositories (5 SQL Server databases via `DataSourceConfig`)
- `AzureServiceBusConfig` — configures standard and session-aware Service Bus processors
- `SchedulingConfig` — periodic session guard scheduling
- Lombok for boilerplate reduction (`@Slf4j`, `@RequiredArgsConstructor`, `@Builder`)

Supporting modules:
- `stir-common` — shared model/entity definitions
- `stir-accountmanagementapi` — integration with AccountManagementAPI (SOAP/REST, bean config, security props)
- `stir-csapiv3` — integration with CSAPI v3
- `stir-debitapi` — integration with DebitAPI

## API Surface
Base path: `/recovery`

| Method | Path | Purpose | Status |
|---|---|---|---|
| GET | `/recovery/status?queueName=` | Queue/processor status | Deprecated (remove) |
| POST | `/recovery/process-one` | Manual single-message processing | Deprecated (remove) |
| POST | `/recovery/snapshot` | Take serial state snapshot | Deprecated (remove) |
| POST | `/recovery/async/start-processor` | Start standard processor | Deprecated (remove) |
| POST | `/recovery/async/stop-processor` | Stop standard processor | Deprecated (remove) |
| POST | `/recovery/async/start-session-processor` | Start session processor | Deprecated (remove) |
| POST | `/recovery/async/stop-session-processor` | Stop session processor | Deprecated (remove) |
| POST | `/recovery/sessions` | Start recovery session | Active |
| POST | `/recovery/sessions/end` | End active recovery session | Active |
| GET | `/recovery/sessions/active` | Get active session details | Active |
| GET | `/recovery/sessions/active/progress` | Get session progress | Active |
| POST | `/recovery/sessions/reset-upper-limits` | Reset SASI upper-limit serials | Active |
| GET | `/recovery/sessions/dda-card-serials` | Get card/DDA serial upper limits | Active |

Spring Boot Actuator exposed at configurable management path.

## Security Posture
- No Spring Security configuration visible in `stir-main`; all endpoints appear unauthenticated at the application layer — security likely enforced at Azure APIM level
- **High risk**: `POST /recovery/sessions/reset-upper-limits` directly modifies card/DDA serial state; if APIM is misconfigured or bypassed, unauthenticated access would be catastrophic
- APIM configured as external gateway (`EXTERNAL_APIM: true`) — the service is internet-facing via APIM; APIM policy must enforce authentication before requests reach the service
- Azure Key Vault integration for all credentials — correct approach
- On-prem SQL Server: `trustServerCertificate=true` (no certificate validation) — TLS present but MITM risk on Wirecard network
- Wirecard CA bundle included in Docker image — necessary for on-prem TLS but must be kept current
- `accountmanagementapi.security.service.visa.key` and `.sharedSecret` in Key Vault — Visa payment network credentials; rotation must be coordinated with network

## Technical Debt
| Item | Severity |
|---|---|
| 7 deprecated REST endpoints still present and accessible | High |
| No Spring Security on REST endpoints (relies entirely on APIM) | High |
| `trustServerCertificate=true` for on-prem SQL connections | High |
| No retry/circuit-breaker for AccountManagementAPI / DebitAPI calls | Medium |
| No explicit transaction boundary spanning Service Bus message ack + DB write (at-least-once semantics) | Medium |
| `UPDATE_DEPENDENCIES: false` — dependencies not auto-updated | Medium |
| Docker image built from source; no base image version pinning visible | Low |
| `.trivyignore` present — check that ignored CVEs are reviewed regularly | Low |

## Gen-3 Migration
Service is already Gen-3. Recommended improvements:
1. Remove all `@Deprecated(forRemoval=true)` endpoints in the next sprint
2. Implement Spring Security with OAuth2/OIDC (backed by Azure Entra ID) on all `/recovery` endpoints; remove reliance on APIM as sole auth layer
3. Migrate cbaseapp and ecountcore to Azure SQL to eliminate on-premises SQL Server dependency and `trustServerCertificate=true`
4. Implement resilience4j circuit-breaker on AccountManagementAPI / DebitAPI calls with dead-letter handling
5. Add OpenAPI/Swagger documentation via SpringDoc
6. Enable Pact provider verification (`VERIFY_PROVIDER_PACT: true`) once stable consumer contracts are published

## Code-Level Risks
- `startRecoverySession()` performs `recoveryService.stopMessageProcessor()` in a try/ignore block; if stop fails silently, both standard and session processors may be running concurrently — a dual-consumer scenario on a session-aware queue could produce out-of-order or duplicated message processing
- `endActiveRecoverySession()` calls `stopSessionProcessor()` but does not restart the normal processor; the service is left with no active message consumer after session end unless the operator manually starts it — potential operational gap
- `getActiveSessionProgress()` always returns `ResponseEntity.ok(progress)` even if no session is active; the `RecoverySessionService.getActiveSessionProgress()` must handle the null-session case gracefully to avoid NPE
- All `@Deprecated` endpoint handlers catch `Exception` broadly and return `500 INTERNAL_SERVER_ERROR` with the exception message in the body — exposes internal error details to callers; should be replaced with a structured error response
- `azure.servicebus.max-concurrent-sessions=75` is a high concurrency setting; if the underlying thread pool is insufficient, session processing will queue up and potentially starve; thread pool sizing should be validated
