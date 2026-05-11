# DevOps & Operations — nexpay-recipientweb-bff

## Build
- Build tool: Maven Wrapper; parent POM `com.onbe.nexpay:nexpay-parent:0.2.8-SNAPSHOT`.
- Java version: 25.
- Multi-module Maven project:
  - `nexpay-recipientweb-api` — OpenAPI-generated API interfaces.
  - `nexpay-recipientweb-client` — downstream service client sub-modules:
    - `nexpay-recipientweb-claimcode-client-api`
    - `nexpay-recipientweb-config-client-api`
    - `nexpay-recipientweb-country-state-list`
    - `nexpay-recipientweb-recipientorchestrator-client-api`
  - `nexpay-recipientweb-impl` — Business logic and service implementations.
  - `nexpay-recipientweb-boot` — Spring Boot application entry point.
- `nimbus-jose-jwt:10.9` for JWE operations.

## Deployment
- Containerised: `nexpay-recipientweb-boot/Dockerfile` (uses `bellsoft/liberica-openjre-alpine:25`).
- Deployed to **Azure Container Apps** via `deployment.yml`.
- Target ACA app name: `ca-nexpay-recipientweb-bff`.
- CI/CD: `OnbeEast/nexpay-iac/.github/workflows/java-build-deploy-aca.yml@main`.
- `PUBLISH_TO_APIM: true`, `EXTERNAL_APIM: true` — published to external-facing APIM.

## Configuration Management
- Profiles: `local`, `docker`, `qa` (from `application-*.yaml` files and `app-config/qa/appsettings.json`).
- Azure App Configuration used in non-default profiles.
- `jwt.secret-token` sourced from Key Vault — must be exactly 32 bytes.
- `AUTH_SERVICE_URL`, `CONFIG_SERVICE_URL`, `RECIPIENT_ORCHESTRATOR_SERVICE_URL` — service URLs via environment variables.
- Redis: `host`/`port` configurable per profile; default `localhost:6379`.
- `mobileApp.ddaEncrypt` property controls DDA encryption toggle in `JweHelper`.

## Observability
- Spring Boot Actuator on port 8081: `health`, `info`, `metrics`, `prometheus`, `startup`, `env`.
- Liveness/readiness probes: `/actuator/health/liveness`, `/actuator/health/readiness`.
- `AuditFilter`: extracts actor identity from `X-Actor-Id` header or JWT claims; propagates to OTEL baggage with `actor.id`, `source`, `reason`, optional `Idempotency-Key`.
- OTEL integration: `otel-grpc` library for gRPC-based OTEL export (version `1.0.0-SNAPSHOT`).
- Swagger UI disabled by default (`springdoc.api-docs.enabled: false`); enabled per specific profiles.

## Infrastructure Dependencies
| Dependency | Environment | Notes |
|-----------|-------------|-------|
| Redis | All | Affiliate cache; Lettuce pool max-active 10 |
| nexpay-auth-svc | All | Username availability check |
| nexpay-config-svc (nexpay-claim-code-svc) | All | Claim code validation and program config |
| nexpay-recipientorchestrator-svc | All | Claim code processing / saga |
| Azure App Configuration | non-local | Config and feature flags |
| Azure Key Vault | non-local | JWT secret, service credentials |
| Azure Container Apps | qa, prod | Deployment target |

## CI/CD
- `deployment.yml`: triggers on push to `main` and PR events; ignores `app-config/**` and CI wrapper files.
- `redeploy.yml`: manual redeploy workflow.
- `app-config.yml`: config-only update workflow.
- CodeQL analysis scheduled Wednesday.
- Container scan configuration present (`.github/containerscan/README.md`).
- `app-config/qa/appsettings.json` stores environment-specific settings in-repo.

## Mock Infrastructure (local dev)
- `nexpay-recipientweb-boot/mocks/` — WireMock stubs for:
  - `nexpay-claimcode-wiremock` — get-claimable, validate-codes, get-recipient-registration.
  - `nexpay-config-wiremock` — get-modality-detail, get-program-countries, get-registration-settings.
  - `nexpay-recipientorchestrator-wiremock` — post-process-claimcode.
- `compose-integrated.yml` and `docker-compose.yml` for local full-stack startup.

## Operational Risks
- `otel-grpc:1.0.0-SNAPSHOT` dependency — SNAPSHOT in production build pipeline is unstable.
- Redis is a single point of failure for all affiliate lookups — no fallback or circuit breaker observed for affiliate cache miss.
- `EXTERNAL_APIM: true` — publicly exposed API; JWT secret rotation and APIM throttling policies are critical.
- No explicit timeout on Redis operations observed in application YAML beyond Lettuce pool config.
- Multiple `// TODO` in `ClaimableChoiceApiDelegateImpl` indicate incomplete implementation paths.
