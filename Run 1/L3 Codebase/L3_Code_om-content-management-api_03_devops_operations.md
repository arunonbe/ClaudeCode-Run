# DevOps & Operations — om-content-management-api

## Build
- Build tool: Maven Wrapper; parent POM `org.springframework.boot:spring-boot-starter-parent:3.5.9`.
- Java version: **21** (LTS — unlike the NexPay Gen-3 services which use Java 25).
- Single Maven module.
- Spring Cloud Azure: `5.23.0`.
- JaCoCo 0.8.14 (coverage report only; no threshold enforcement in pom).
- Produces fat JAR via Spring Boot Maven Plugin.

## Deployment
- Containerised: `Dockerfile` present (content not read; deployment follows Azure Container Apps pattern per CI/CD workflow).
- Deployed to AKS or ACA via `Onbe/om-ci-setup/.github/workflows/java-workflow.yml@feature/IN-9108-inverse-aks`.
- Target application name: `OmContentManagementApi`.
- CI/CD workflow on feature branch of `om-ci-setup` (`feature/IN-9108-inverse-aks`) — NOT pinned to `main`; indicates active development/migration.
- `INVERSE_DEPLOY_ORDER: true` — non-standard deployment ordering.
- `EXCLUDE_STAGE: false` — staging environment included in pipeline.

## Configuration Management
- Profiles: `dev`, `qa`, `staging`, `prod` (from `application-*.yaml` files).
- Azure App Configuration: `spring-cloud-azure-starter-appconfiguration-config` — config imported at startup.
- Secrets via Key Vault (blob connection string, GitHub token).
- `app-config/qa/appsettings.json`, `app-config/prod/appsettings.json`, `app-config/stage/appsettings.json` — environment-specific settings committed to repo.
- `spring.autoconfigure.exclude: AzureStorageBlobAutoConfiguration` in default profile — blob client manually initialised via `@PostConstruct`.
- `rediscache-admin-service-url` hardcoded in `application.yaml` — staging URL present in default config; should be profile-specific.

## Observability
- Spring Boot Actuator: `health`, `info` at `/hc` (not `/actuator/health`).
- Health endpoint shows details always.
- No OTEL / distributed tracing configured in application YAML.
- No structured log format configured — default Spring Boot logging.
- `LogSanitizer.java` — sanitises values for log output.

## Infrastructure Dependencies
| Dependency | Environment | Notes |
|-----------|-------------|-------|
| Azure Blob Storage | qa, staging, prod | Connection string from Key Vault |
| GitHub API (`api.github.com`) | All non-dev | GitHub PAT from Key Vault |
| Azure App Configuration | All | Config and feature flags |
| Azure Key Vault | All | Secrets |
| Redis Cache Admin Service | Referenced in default YAML | URL: `was-az1-recipientcacheadminapp-stage-ss.azurewebsites.net` |

## CI/CD
- `deployment.yml`: triggers on push to `main` and PR events; `INVERSE_DEPLOY_ORDER: true`.
- `app-config.yml`: separate config-only update workflow.
- `PUBLISH_TO_APIM: true`, `INTERNAL_APIM: true`, `EXTERNAL_APIM: false` — internal APIM only.
- `CONTAINER_SCAN: false` — container scan disabled.
- Pact consumer contract test: `PACT_PACTICIPANT: om-content-management-api`, `VERIFY_PROVIDER_PACT: false`.
- CodeQL analysis on push/PR/schedule.
- Deployment workflow uses `feature/` branch of `om-ci-setup` — not stable `main` branch.

## Operational Risks
- CI/CD uses a `feature/` branch of `om-ci-setup` — pipeline stability risk; must be merged to `main` before production.
- `CONTAINER_SCAN: false` — image vulnerability scanning disabled.
- `rediscache-admin-service-url` staging URL hardcoded in default `application.yaml` — wrong endpoint may be called if profile is not overriding it.
- No structured logging — logs harder to parse and search in production.
- No OTEL tracing — no distributed trace correlation for upstream request chains.
- `@PostConstruct` Azure Blob client initialisation throws `IllegalStateException` on startup if connection string is blank — service will fail to start if App Config is unavailable.
- 20 MB max file upload — may cause memory pressure under load in a constrained container.
