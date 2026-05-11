# 03 DevOps / Operations — stand-in-recovery-service

## Build
- **Tool**: Maven Wrapper (`mvnw`); multi-module project
- **Parent**: `spring-boot-starter-parent:3.5.5`
- **Java**: 21
- **Modules**: `stir-common`, `stir-accountmanagementapi`, `stir-csapiv3`, `stir-debitapi`, `stir-main`
- **Build target**: `stir-main` (per `TARGET_ROOT: './stir-main'` in deployment workflow)
- Tests skipped in deployment pipeline (`-DskipTests`)
- Spring Boot fat JAR

## Deployment
- GitHub Actions workflow (`.github/workflows/deployment.yml`) delegates to Onbe centralised CI/CD template (`Onbe/om-ci-setup/.github/workflows/java-workflow.yml@main`)
- `APP_NAME: SasiRecoveryService` (Pascal-case, required by CI template)
- Deployed to Azure (APIM external publishing enabled: `PUBLISH_TO_APIM: true`, `EXTERNAL_APIM: true`)
- Staging environment included (`EXCLUDE_STAGE: false`)
- No-downtime switchover documented in `docs/no-downtime-switching-dda-card-allocators.md` and `docs/SASI-to-Legacy No-Downtime Switchover.pdf`
- Containerised: `Dockerfile` and `docker-compose.yaml` present
- Custom CA certificate for Wirecard internal PKI bundled in `bindings/ca-certificates/nam.wirecard.sys.crt`
- Trivy container security scan configured (`.trivyignore`)
- Redeploy workflow available (`.github/workflows/redeploy.yaml`)
- App-config workflow (`.github/workflows/app-config.yml`) for configuration updates

## Config Management
- Environment-specific config in `app-config/{qa,staging,prod}/appsettings.json`
- Secrets via Azure Key Vault references (`key_vault_references` block in appsettings)
- Maven wrapper settings at `.mvn/wrapper/settings.xml`
- Azure Service Bus properties: `azure.servicebus.connection-string`, `azure.servicebus.max-concurrent-sessions`
- STIR tuning parameters: `stir.session.guard.interval-ms`, `stir.snapshot.buffer`, `stir.snapshot.safety-margin`
- Director address and ecount service URLs per environment

## Observability
- Spring Boot Actuator present (management endpoint path configurable via `management.endpoints.web.base-path`)
- Structured logging via SLF4J / Logback (Spring Boot 3 default)
- `@Slf4j` (Lombok) used throughout controllers and services
- Azure Service Bus queue runtime properties accessible via `ServiceBusAdministrationClient` (used in deprecated status endpoint)
- No explicit Prometheus/Grafana or Azure Monitor configuration visible in source; expected to be configured at the infrastructure layer

## Infrastructure Dependencies
| Dependency | Environment |
|---|---|
| Azure SQL Database (`sql-az1-cluster-qa-ss` / prod equivalent) | Cloud |
| SQL Server on-premises (`u-lis-db01/02.nam.wirecard.sys:2231`) | On-prem (Wirecard network) |
| Azure Service Bus (session-enabled queue) | Cloud |
| Azure Key Vault (secrets) | Cloud |
| Azure API Management (APIM) | Cloud |
| Wirecard internal CA (`nam.wirecard.sys`) | On-prem PKI |
| `accountmanagementapi-impl:3.1.7` | Internal Maven registry |
| `debitapi-impl:3.1.4` | Internal Maven registry |
| `csapiv3:3.1.13` | Internal Maven registry |
| `job-common/impl:4.0.1` | Internal Maven registry |

## Operational Risks
- **Critical**: Crash or unhandled exception during an active recovery session leaves card/DDA serial state in an indeterminate position; no automated rollback mechanism observed — manual intervention required
- **High**: `trustServerCertificate=true` for on-premises SQL Server connections — man-in-the-middle risk on the Wirecard network
- **High**: Max concurrent Azure Service Bus sessions set to 75 (`azure.servicebus.max-concurrent-sessions=75`) — must be sized appropriately for peak recovery message volume; under-provisioning causes session backlog
- **Medium**: All operational REST endpoints in `RecoveryServiceController` are marked `@Deprecated(forRemoval = true, since = "1.0.0")` except session lifecycle endpoints — unclear if deprecated endpoints are still reachable in production
- **Medium**: `stir-main` Spring Boot app; no circuit-breaker or retry configuration visible for AccountManagementAPI / DebitAPI calls during recovery replay

## CI/CD
- GitHub Actions (`deployment.yml`): push to `main` triggers build and deploy; PR to `main` triggers build only
- Pact contract testing: `PACT_PACTICIPANT: stand-in-recovery-service`, `VERIFY_PROVIDER_PACT: false` (consumer only)
- Copilot instructions file present (`.github/copilot-instructions.md`) — indicates active AI-assisted development
- Dependency updates: `UPDATE_DEPENDENCIES: false`, `UPDATE_PARENT_VERSION: false` — must be manually managed
