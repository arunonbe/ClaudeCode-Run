# DevOps & Operations — nexpay-recipient-profile-svc

## Build
- Build tool: Maven Wrapper with parent POM `com.onbe.nexpay:nexpay-parent:1.0.2`.
- Java version: 25.
- Multi-module Maven project:
  - `nexpay-recipient-profile-api` — OpenAPI-generated API interfaces.
  - `nexpay-recipient-profile-data-entity` — JPA entities + Flyway migrations.
  - `nexpay-recipient-profile-data-repository` — Spring Data repositories.
  - `nexpay-recipient-profile-impl` — Service and delegate implementations.
  - `nexpay-recipient-profile-boot` — Spring Boot application entry point.
- Maven config: `.mvn/maven.config` and internal settings.xml for Nexus/Artifactory resolution.

## Deployment
- Containerised: `nexpay-recipient-profile-boot/Dockerfile` uses `bellsoft/liberica-openjre-alpine:25`.
- JVM: `JAVA_TOOL_OPTIONS="-Xms512m"` — min heap only, no max.
- Exposes ports `8082` (app) and `8083` (management/actuator).
- Deployed to **Azure Container Apps** via GitHub Actions workflow `deployment.yml`.
- Target ACA app name: `ca-nexpay-recipient-profile-svc`.
- CI/CD workflow: `OnbeEast/nexpay-iac/.github/workflows/java-build-deploy-aca.yml@main`.

## Configuration Management
- Azure App Configuration (endpoint: `appcg-nexpay-qa.azconfig.io`) — key filter: `nexpay-recipient-profile-svc/`, label filter: `qa`.
- Azure Key Vault provider enabled — secrets injected via App Configuration Key Vault references.
- Feature flags enabled via Azure App Configuration.
- Profile activation: `ENVIRONMENT` env var (defaults to `local`).
- Active profiles: `local`, `docker`, `qa`, `prod`, `test`.
- `application-local.yaml` uses `optional:azureAppConfiguration` import for offline development.

## Observability
- Spring Boot Actuator: `health`, `info`, `metrics`, `prometheus`, `startup` on port 8083.
- Liveness and readiness probes enabled: `/actuator/health/liveness`, `/actuator/health/readiness`.
- Structured log format: Logstash JSON.
- OTLP tracing/metrics/logs exported to Dynatrace (`DYNATRACE_API_TOKEN` / `OTEL_EXPORTER_OTLP_ENDPOINT`) in qa/prod.
- OpenTelemetry Java global auto-configure enabled in qa/prod.
- HikariCP leak detection: 60 s threshold.

## Infrastructure Dependencies
| Dependency | Environment | Notes |
|-----------|-------------|-------|
| Azure PostgreSQL Flexible Server | qa, prod | Passwordless via Managed Identity |
| PostgreSQL 14+ (localhost or Docker) | local, docker | Password via env var |
| Azure App Configuration | local, qa, prod | Config and feature flags |
| Azure Key Vault | qa, prod | Secrets via App Config KV provider |
| Azure Container Apps | qa, prod | Deployment target |
| Dynatrace OTLP endpoint | qa, prod | Telemetry export |

## CI/CD
- `deployment.yml`: triggers on push to `main` and on PR (opened/sync/labeled); paths-ignore for config/wrapper changes.
- Delegates to `OnbeEast/nexpay-iac/.github/workflows/java-build-deploy-aca.yml@main`.
- `PUBLISH_TO_APIM: false`, `INTERNAL_APIM: true`, `EXTERNAL_APIM: false` — internal APIM registration only.
- `CONTAINER_SCAN: false` — container vulnerability scanning temporarily disabled.
- `redeploy.yml` and `app-config.yml` workflows present for config-only redeployment.
- CodeQL analysis on push/PR/schedule (Wednesday 08:23).
- Dependabot configured.
- `containerscan/allowedlist.yaml` present — suppressions for container scan findings.

## Operational Risks
- `CONTAINER_SCAN: false` — vulnerability scanning disabled; new image CVEs will not be caught in CI.
- No `-Xmx` JVM ceiling — OOM risk in constrained ACA containers.
- Swagger UI enabled in qa/prod — API is browsable without authentication if not behind APIM/gateway.
- `flyway.validate-on-migrate: false` in local/docker profile — migration validation skipped; schema drift possible in dev.
- Log level `com.zaxxer.hikari: TRACE` and `org.postgresql: TRACE` in qa/prod — verbose DB connection logging may expose connection metadata.
