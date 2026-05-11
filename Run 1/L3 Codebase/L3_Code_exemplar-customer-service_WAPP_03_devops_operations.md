# DevOps / Operations View — exemplar-customer-service_WAPP

## Build
- **Build system**: Maven (multi-module POM, 8 modules).
- **Maven wrapper**: `mvnw` / `mvnw.cmd` present; settings.xml in `.mvn/wrapper/` references Onbe internal Nexus (`d-na-stk01.nam.wirecard.sys:8080`).
- **Java version**: 11 (set in parent POM `java.version` property).
- **Spring Boot**: 2.4.5 (parent POM).
- **Packaging**: `customer-service-rest-controller` module produces a Docker image; root POM packages `pom` type.

## Deployment
- **Container**: `customer-service-rest-controller/Dockerfile` — base image `mcr.microsoft.com/mssql/server:2017-CU20-ubuntu-16.04` (this is the SQL Server image, used for the DB sidecar, not the app). The app image is at `jrjdemo20210612.azurecr.io/customer-service`.
- **Azure Container Registry**: `jrjdemo20210612.azurecr.io`.
- **Kubernetes**: `deploy/customer-service.yaml` — Deployment (1 replica) + LoadBalancer Service on port 9500.
- **Dapr sidecar**: Enabled via pod annotations (`dapr.io/enabled: "true"`, app-id: `customer-service`, app-port: `9500`).
- **Docker Compose**: `docker-compose.yml` for local development — launches app container + Dapr sidecar.
- **Namespace**: Not specified in Kubernetes manifests (defaults to `default` namespace).

## Configuration Management
- **Application config**: `application.yml` in `customer-service-config/src/main/resources/` — committed with hardcoded credentials (see risks).
- **Spring Cloud Config**: Present as a dependency but `spring.cloud.config.enabled: false` in the committed config.
- **Azure App Configuration**: `AppConfigContext` class references App Configuration (likely Azure App Configuration SDK), but details are in the AppConfigContext class not directly readable from available source. This suggests runtime externalisation.
- **Truststore**: Injected via `global.datasource.truststore.*` properties (base64-encoded content, location, password).
- **Liquibase**: Schema managed at startup from `classpath:/db/changelog/db.changelog-master.xml`.

## Observability
- **Spring Boot Actuator**: Enabled, all endpoints exposed at `/monitoring/*`.
- **Health checks**: `/monitoring/health` with `show-details: ALWAYS`.
- **Circuit breaker health**: `management.health.circuitbreakers.enabled: true`.
- **Zipkin**: `deploy/zipkin.yaml` — Zipkin distributed tracing deployment included.
- **Dapr config**: `deploy/dapr-config.yaml` — Dapr configuration for tracing.
- **Logging**: Lombok `@Slf4j` used in service classes; no structured logging configuration visible.
- **Pact contract tests**: PactFlow broker at `https://northlane.pactflow.io/` for contract publishing.

## Infrastructure Dependencies
| Dependency | Type | Notes |
|-----------|------|-------|
| SQL Server / Azure SQL | Database | `exemplar-sqlserver.database.windows.net` or Docker container |
| Dapr runtime | Sidecar | Required for pub/sub (MQTT via `pubsub-mqtt.yaml`) |
| MQTT broker | Message broker | `customer-service-dapr-components/pubsub-mqtt.yaml` |
| Zipkin | Tracing | `deploy/zipkin.yaml` |
| Azure Container Registry | Image registry | `jrjdemo20210612.azurecr.io` |
| Nexus repository | Maven artifacts | `d-na-stk01.nam.wirecard.sys:8080` |
| PactFlow | Contract testing | `https://northlane.pactflow.io/` |

## Operational Risks
1. Spring Boot 2.4.5 is EOL — security patches are no longer available from the upstream project.
2. H2 console enabled in committed config — must be disabled before any production use.
3. Hardcoded credentials in `application.yml` will be baked into any Docker image built from this repo without config substitution.
4. Single replica in Kubernetes manifest — no high availability.
5. `imagePullPolicy: Always` without image digest pinning — susceptible to supply chain substitution.
6. No resource limits for the Dapr sidecar container in the Kubernetes manifest.

## CI/CD
- **GitHub Actions**: `.github/workflows/codeql.yml` — CodeQL security analysis on push.
- **Dependabot**: `.github/dependabot.yml` — automated dependency update PRs.
- No Jenkins pipeline or GitLab CI file present.
- No deployment pipeline (Helm charts, ArgoCD, or equivalent) observed in this repository.
- Maven distribution management points to Nexus snapshots/releases at `d-na-stk01.nam.wirecard.sys:8080`.
