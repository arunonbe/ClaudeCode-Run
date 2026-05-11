# DevOps & Operations Report — nexpay-auth-svc

## 1. Build Configuration

`nexpay-auth-svc` is a Maven multi-module project inheriting from `com.onbe.nexpay:nexpay-parent:0.2.8-SNAPSHOT`. The root `pom.xml` targets:
- `java.version: 25` (line 27) — Java 25 (the cutting-edge JDK at time of development)
- Maven 4.x model (`modelVersion: 4.1.0` in `pom.xml` line 2)

The three-module structure:
- `nexpay-auth-api` — OpenAPI code generation (downloads OpenAPI spec and generates Java interfaces)
- `nexpay-auth-boot` — Spring Boot application entry point, `application.yaml`, Dockerfile
- `nexpay-auth-impl` — Business logic, Graph API client, delegate implementations

**Maven config** (`.mvn/maven.config`): Controls project-level Maven options applied to all commands.

## 2. Container Configuration

**Dockerfile** (`nexpay-auth-boot/Dockerfile`):
- Base image: `bellsoft/liberica-openjre-alpine:25` — Java 25 BellSoft Liberica Alpine, consistent with Gen-3 service standard.
- No `HEALTHCHECK` instruction — health is managed by ACA/Kubernetes probes via the Spring Actuator endpoints.
- Standard Spring Boot fat-JAR execution pattern.
- `EXPOSE 8080` — application port.
- Management port 8081 (configured in `application.yaml` line 40) is not exposed in the Dockerfile, meaning Actuator endpoints are only accessible internally within the container network.

**`docker-compose.yml`** (root): Local development environment. No database service is included (consistent with the current stateless architecture where no local DB is used).

## 3. CI/CD Pipeline

**`.github/workflows/deployment.yml`**:
```yaml
uses: OnbeEast/nexpay-iac/.github/workflows/java-build-deploy-aca.yml@main
with:
  APP_NAME: ca-auth-svc
  PUBLISH_TO_APIM: false
  INTERNAL_APIM: true
  EXTERNAL_APIM: false
  MAVEN_ARGS: '-q '
  TARGET_ROOT: ./nexpay-auth-boot
```

Key observations:
- **Reusable workflow**: `java-build-deploy-aca.yml@main` — standardized Gen-3 NexPay CI/CD pipeline.
- **Internal APIM only** (`INTERNAL_APIM: true`, `EXTERNAL_APIM: false`): The auth service is exposed only on the internal API Management gateway. It is not directly accessible from the internet. MPV and other callers access it through the internal network.
- **No APIM publish** (`PUBLISH_TO_APIM: false`): The OpenAPI spec is not published to the API gateway catalog. This should likely be `true` to enable service discovery.
- **ACA deployment**: `ca-auth-svc` is an Azure Container App name following the `ca-*-svc` naming convention.
- **Quiet Maven** (`-q`): Minimal build output, reduces log noise.

**`.github/workflows/redeploy.yml`**: Allows manual re-deployment of an existing image without a code change.
**`.github/workflows/app-config.yml`**: Syncs `app-config/` directory changes to Azure App Configuration, enabling configuration changes without a full rebuild.
**`.github/workflows/codeql.yml`**: CodeQL static analysis on Java source.

## 4. Application Configuration

**`application.yaml`** profiles:
- `default` / non-local: Production-ready — logging at ERROR, Azure App Configuration enabled, health details `when_authorized`
- `local`: Development — logging at DEBUG, Swagger UI enabled, health details `always`, Azure App Configuration disabled
- `docker`: Container local dev — same as local but with less verbose logging

Azure App Configuration integration (`spring.config.import: optional:azureAppConfiguration`) is the primary configuration source for non-local environments. The `optional:` prefix means startup does not fail if Azure App Configuration is unreachable, which is a resilience trade-off.

## 5. Observability

- **Actuator endpoints** exposed: `health`, `info`, `metrics`, `prometheus`, `startup` (non-local: line 44-45); `env` added in local profile (line 93-94).
- **Liveness and readiness probes**: Enabled (`management.health.livenessstate.enabled: true`, `management.health.readinessstate.enabled: true`) — required for proper ACA lifecycle management.
- **Prometheus metrics**: Enabled (`management.defaults.metrics.export.enabled: true`) — supports Azure Monitor scraping or a Prometheus deployment.
- **Structured logging**: `logging.structured.format.file: logstash` (line 77) — JSON-structured log output for production, enabling log aggregation in Azure Monitor / ELK.
- **Azure Identity debug logging**: `com.azure.identity: DEBUG` (line 71) — helps diagnose Managed Identity and Key Vault authentication issues. This should be reviewed for production (DEBUG logging for Azure identity can expose token exchange details in logs).

## 6. Virtual Threads

`spring.threads.virtual.enabled: true` (lines 9-10 of `application.yaml`) enables Project Loom virtual threads for all Spring Web/MVC request handling. Combined with Java 25, this provides high-throughput, low-latency request processing with minimal thread pool configuration overhead. The `ReentrantLock` in `EntraGraphTokenProvider` is safe with virtual threads (unlike `synchronized` blocks, which can pin carrier threads under Project Loom in some JVM versions; however, `ReentrantLock` does not pin).

## 7. Operational Risks

1. **SNAPSHOT parent dependency**: `nexpay-parent:0.2.8-SNAPSHOT` (root `pom.xml` line 13) — SNAPSHOT dependencies introduce non-deterministic builds. Production deployments should use a release version.
2. **Java 25**: Java 25 is not yet GA at the time of this analysis (Java 24 is the latest GA, Java 25 is early-access). Deploying on an early-access JDK increases operational risk (potential JVM bugs, unsupported production fixes).
3. **`optional:azureAppConfiguration`**: If Azure App Configuration is unavailable and the `optional:` prefix causes silent degradation, the service may start with incomplete configuration, leading to runtime failures on first use rather than a clean startup failure.
4. **`com.azure.identity: DEBUG` logging in production**: Verbose Azure identity logs may expose token exchange metadata in production log streams.
