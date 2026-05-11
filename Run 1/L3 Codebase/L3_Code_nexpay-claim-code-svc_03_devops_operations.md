# nexpay-claim-code-svc — DevOps / Operations View

## Build System

- **Build tool**: Maven (Maven Wrapper `mvnw`)
- **Java version**: **25** (early-access / preview — `java.version = 25`, `maven.compiler.source/target = 25`)
- **JDK distribution**: BellSoft Liberica (`FROM bellsoft/liberica-openjre-alpine:25` in Dockerfile)
- **Parent POM**: `com.onbe.nexpay:nexpay-parent:0.2.7-SNAPSHOT`
- **Multi-module structure**:
  - Root: `com.onbe.nexpay:nexpay-config:0.0.2-SNAPSHOT` (note artifact ID mismatch: POM says `nexpay-config`, service name is `nexpay-claim-code-svc`)
  - `nexpay-claimcode-api` — OpenAPI-generated API contract
  - `nexpay-claimcode-boot` — Spring Boot application, Dockerfile, integration tests
  - `nexpay-claimcode-data/nexpay-claimcode-data-entity` — JPA entities, Flyway migrations
  - `nexpay-claimcode-data/nexpay-claimcode-data-repository` — Spring Data repositories
  - `nexpay-claimcode-impl` — Business logic, controllers, mappers, health check
- **Maven config file**: `.mvn/maven.config` (not read; likely sets parent or profile)
- **Build args in CI**: `-q` (quiet mode)

## Deployment

- **Platform**: Azure Container Apps (ACA)
- **App name in ACA**: `ca-nexpay-claim-code-svc`
- **APIM**: Internal APIM only (`INTERNAL_APIM: true`, `EXTERNAL_APIM: false`, `PUBLISH_TO_APIM: false`)
- **CI/CD target**: `OnbeEast/nexpay-iac/.github/workflows/java-build-deploy-aca.yml@main`
- **Container image base**: `bellsoft/liberica-openjre-alpine:25`
- **Port**: 8080 (application), 8081 (management/actuator)
- **Docker build**: Multi-stage — copies fat JAR, runs as non-privileged process via `CMD ["sh", "-c", "java $JAVA_TOOL_OPTIONS -jar ./${JAR_NAME}"]`
- **JVM options**: `-Xms512m --enable-native-access=ALL-UNNAMED`
- **Compose for local dev**: `nexpay-claimcode-boot/compose.yaml` (likely starts SQL Server via Testcontainers or Docker Compose for local development)
- **Container scan**: Disabled (`CONTAINER_SCAN: false` — noted as "frequently fails")

## Config Management

- **Profile activation**: `ENVIRONMENT` environment variable selects Spring profile (`local`, `docker`, `qa`)
- **Azure App Configuration**: Used in `qa` profile; endpoint `https://appcg-nexpay-qa.azconfig.io`; keys filtered by `nexpay-claimcode-svc/` prefix + `qa` label
- **Azure Key Vault**: Referenced via `spring-cloud-azure-appconfiguration-config-web` — Key Vault secrets are resolved through Azure App Configuration key references
- **Managed Identity**: `credential.managed-identity-enabled: true`, `client-id: ${AZURE_CLIENT_ID}` — uses Azure Managed Identity in ACA
- **Datasource**: Connection string injected from Azure App Configuration → Key Vault at startup (not present in source)
- **Flyway**: Enabled in default/local/docker profiles; **disabled** in QA (`flyway.enabled: false`) because QA DB user lacks DDL permissions

## Observability

- **Logging**: ECS (Elastic Common Schema) structured JSON format (`logging.structured.format.console: ecs`) in default profile; file logging in QA (`/var/log/nexpay-paymentprocessor-svc.log`)
- **Tracing**: OpenTelemetry (`spring-boot-starter-opentelemetry`); OTLP gRPC export to `${OTEL_EXPORTER_OTLP_ENDPOINT}` in QA
- **Metrics**: Micrometer OTLP metrics export (`management.otlp.metrics.export`) with gRPC transport in QA; disabled in QA profile (pending proper collector setup)
- **Health checks**: Spring Boot Actuator health probes enabled (`/actuator/health/readiness`, `/actuator/health/liveness`) with details and components shown; startup probe unrestricted access
- **Exposed actuator endpoints**: `health`, `info`, `metrics`, `prometheus`, `startup`, `env`
- **Hibernate Envers audit**: Every entity change captured with actor ID from OTel baggage

## Infrastructure Dependencies

| Dependency | Purpose | Config |
|---|---|---|
| Azure SQL Server (`nexpay_claimable` DB) | Primary data store | Connection string from Key Vault via Azure App Config |
| Azure App Configuration (`appcg-nexpay-qa.azconfig.io`) | Runtime config store | Managed Identity auth |
| Azure Key Vault | Secret storage (DB connection strings) | Referenced via App Config key references |
| Azure Container Apps | Compute platform | Deployed by nexpay-iac workflow |
| Azure Container Registry | Container image store | Images built and pushed by nexpay-iac |
| Testcontainers (MSSQL) | Integration test DB | Used in `nexpay-claimcode-boot` test profile |

## Operational Risks

1. **Java 25 (preview)**: Java 25 is an early-access/non-LTS version. Using preview Java in production is not recommended. Java 21 is the current LTS; Java 25 is not yet released as a stable build (as of knowledge cutoff August 2025). This may create supply-chain and supportability risks.
2. **Container scan disabled**: `CONTAINER_SCAN: false` — container vulnerability scanning is not running in CI, creating a potential blind spot for CVEs in the base image or dependencies.
3. **Flyway disabled in QA**: Schema migrations do not run in QA; schema must be managed manually or via a separate migration job. This creates drift risk between dev/docker and QA schemas.
4. **OTLP metrics disabled in QA**: Metrics are not exported in QA (`management.otlp.metrics.export.enabled: false`); monitoring coverage gap.
5. **Artifact ID mismatch**: Root POM `artifactId` is `nexpay-config` but the service name is `nexpay-claim-code-svc` — potential confusion in dependency management and SBOM.
6. **`nexpay-parent` SNAPSHOT dependency**: Parent POM `0.2.7-SNAPSHOT` is a snapshot; snapshot dependencies in production builds can lead to non-reproducible builds.

## CI/CD

| Workflow | File | Trigger | Action |
|---|---|---|---|
| `deployment.yml` | `.github/workflows/deployment.yml` | push to `main`, PR (opened/synced/labeled), `workflow_dispatch` | Build + deploy to ACA via `nexpay-iac` workflow |
| `redeploy.yml` | `.github/workflows/redeploy.yml` | (assumed `workflow_dispatch`) | Redeploy without rebuild |
| `app-config.yml` | `.github/workflows/app-config.yml` | (assumed on `app-config/**` changes) | Push config to Azure App Configuration |
| `codeql.yml` | `.github/workflows/codeql.yml` | Schedule + `workflow_dispatch` | Java SAST |
| Dependabot | `.github/dependabot.yml` | Automated | Dependency update PRs |
| Container allowlist | `.github/containerscan/allowedlist.yaml` | Per container scan | CVE allow-list |
