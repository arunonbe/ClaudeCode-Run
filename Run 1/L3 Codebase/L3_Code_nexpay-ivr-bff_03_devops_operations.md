# nexpay-ivr-bff — DevOps / Operations View

## Build System

- **Build tool**: Maven (Maven Wrapper `mvnw`)
- **Java version**: **25** (early-access/preview — `java.version = 25`)
- **JDK distribution**: BellSoft Liberica (`FROM bellsoft/liberica-openjre-alpine:25` in Dockerfile)
- **Parent POM**: `com.onbe.nexpay:nexpay-parent:0.2.8-SNAPSHOT`
- **Multi-module structure**:
  - Root: `com.onbe.nexpay:nexpay-ivr:0.0.1-SNAPSHOT`
  - `nexpay-ivr-api` — request/response model classes (Jakarta validation)
  - `nexpay-ivr-boot` — Spring Boot application, Dockerfile
  - `nexpay-ivr-client` — (client module; content not fully scanned)
  - `nexpay-ivr-impl` — controllers, config, filter, health indicator
- **Key library dependencies**:
  - `nimbus-jose-jwt:10.9` — JWT parsing (declared in root POM)
  - `com.onbe.otel:otel-grpc:1.0.0-SNAPSHOT` — internal OTel gRPC library (SNAPSHOT)
  - Redis Jedis (from parent)
  - `spring-cloud-azure-appconfiguration-config-web` — Azure App Config
- **Failsafe plugin**: Configured in `nexpay-ivr-boot/pom.xml` — integration tests enabled
- **Maven config file**: `.mvn/maven.config`

## Deployment

- **Platform**: Azure Container Apps (ACA)
- **App name in ACA**: `ca-nexpay-ivr-bff`
- **APIM**: **External APIM only** (`INTERNAL_APIM: false`, `EXTERNAL_APIM: true`, `PUBLISH_TO_APIM: true`)
- **CI/CD target**: `OnbeEast/nexpay-iac/.github/workflows/java-build-deploy-aca.yml@main`
- **Container image base**: `bellsoft/liberica-openjre-alpine:25`
- **Port**: 8080 (application), 8081 (management/actuator)
- **Docker build**: Copies fat JAR; runs via `CMD ["sh", "-c", "java $JAVA_TOOL_OPTIONS -jar ./${JAR_NAME}"]`
- **JVM options**: `-Xms512m --enable-native-access=ALL-UNNAMED`
- **Local dev Docker Compose**: `docker-compose.yml` and `compose-integrated.yml` present
- **Virtual threads**: `spring.threads.virtual.enabled: true` — Project Loom enabled

## Config Management

- **Profile activation**: `ENVIRONMENT` environment variable (`local`, `docker`, `qa`)
- **Azure App Configuration**: QA profile uses `https://appcg-nexpay-qa.azconfig.io`; keys filtered `nexpay-ivr-bff/qa`
- **Azure Key Vault**: Referenced via `spring-cloud-azure-appconfiguration-config-web`
- **Managed Identity**: `credential.managed-identity-enabled: true`, `client-id: ${AZURE_CLIENT_ID}`
- **Redis config**: `redis.host`, `redis.port`, `redis.password`, `redis.ssl` (SSL true in QA) from Azure App Configuration
- **Auth service URL**: `AUTH_SERVICE_URL` environment variable (default: `http://localhost:8085`)
- **OTel endpoint**: `OTEL_EXPORTER_OTLP_ENDPOINT` environment variable (QA only)
- **Azure App Config endpoint**: `AZURE_APP_CONFIG_ENDPOINT` environment variable

## Observability

- **Logging**: Root level `WARN`; `com.onbe.nexpay: INFO` in QA. Structured logging not explicitly configured (no `ecs` format seen — differs from claim-code-svc)
- **Tracing**: OpenTelemetry OTLP gRPC (`com.onbe.otel:otel-grpc:1.0.0-SNAPSHOT`) — custom internal OTel library; traces to `${OTEL_EXPORTER_OTLP_ENDPOINT}` in QA
- **Metrics**: Micrometer OTLP metrics with gRPC transport in QA
- **Audit**: `AuditFilter` propagates actor identity (`actor.id`, `source`, `reason`) in OTel baggage for all non-actuator requests
- **Health**: Actuator probes on port 8081; `startup.access: read-only` (vs `UNRESTRICTED` in claim-code-svc)
- **OpenAPI / Swagger**: Enabled in `local` profile only; disabled in QA/production

## Infrastructure Dependencies

| Dependency | Purpose | Config |
|---|---|---|
| Azure Container Apps | Compute platform | Deployed by nexpay-iac |
| Azure Container Registry | Container images | Built and pushed by nexpay-iac |
| Azure App Configuration (`appcg-nexpay-qa.azconfig.io`) | Runtime config | Managed Identity auth |
| Azure Key Vault | Secrets (Redis credentials, downstream URLs) | Via App Config references |
| Azure Cache for Redis | Caching (affiliate, content data) | SSL, port 6380 in QA |
| `nexpay-auth-svc` | Auth service | `AUTH_SERVICE_URL` env var |
| External APIM | API gateway | Publishes OpenAPI spec; external callers enter here |
| `otel-grpc` (OTel collector) | Telemetry | `OTEL_EXPORTER_OTLP_ENDPOINT` |

## Operational Risks

1. **Java 25 (non-LTS / early-access)**: Same risk as `nexpay-claim-code-svc` — production stability concern.
2. **`nexpay-parent:0.2.8-SNAPSHOT` and `otel-grpc:1.0.0-SNAPSHOT`**: Two SNAPSHOT dependencies make builds non-reproducible.
3. **External APIM exposure with stub implementation**: The controller returns hardcoded data. If deployed to production, real IVR callers will receive fake customer data.
4. **No container scan**: `.github/containerscan/README.md` is present but no `allowedlist.yaml` — container scanning is not running for this service.
5. **Redis SSL port**: Default config uses port 6379 (non-SSL). Azure Cache for Redis TLS requires port 6380; QA config only sets `ssl: true` but does not override the port — the SSL connection may fail unless the port is also overridden via App Configuration.
6. **`DummyController` in production code**: `nexpay-ivr-impl/.../dummy/DummyController.java` — a dummy controller is in the main source tree, not in test. It will be registered in the application context and exposed at runtime.
7. **Virtual threads + `testOnBorrow: true` in Jedis**: With virtual threads, blocking on Redis borrow could create scheduling contention. Jedis is blocking/synchronous; consider using Lettuce (reactive Redis client) instead.

## CI/CD

| Workflow | File | Trigger | Action |
|---|---|---|---|
| `deployment.yml` | `.github/workflows/deployment.yml` | push to `main`, PR (opened/synced/labeled) | Build + deploy via nexpay-iac; publishes OpenAPI to external APIM |
| `redeploy.yml` | `.github/workflows/redeploy.yml` | `workflow_dispatch` | Redeploy without rebuild |
| `app-config.yml` | `.github/workflows/app-config.yml` | `app-config/**` changes | Push config to Azure App Configuration |
| `codeql.yml` | `.github/workflows/codeql.yml` | Schedule + `workflow_dispatch` | Java SAST |
| Dependabot | `.github/dependabot.yml` | Automated | Dependency update PRs |
