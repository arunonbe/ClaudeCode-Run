# DevOps / Operations View — nexpay-order-orchestrator

## Build System

| Attribute | Value |
|-----------|-------|
| Build tool | Maven 4.0.0-rc-5 (enforced minimum) |
| Java version | 25 (enforced minimum via `maven-enforcer-plugin`) |
| Parent POM | `nexpay-parent 0.2.6-SNAPSHOT` |
| Submodules | `nexpay-order-orchestrator-boot`, `nexpay-order-orchestrator-api`, `nexpay-order-orchestrator-impl`, `nexpay-order-orchestrator-api-client`, `nexpay-order-orchestrator-service-bus` |
| Test framework | JUnit 5, WireMock 3.0.1, OkHttp MockWebServer 5.3.0, Testcontainers |
| Integration tests | Separated by `*IT.java` suffix; run via `maven-failsafe-plugin` |
| Code coverage | JaCoCo with aggregate report |

The `nexpay-order-orchestrator-api-client` sub-module exposes a generated REST client artifact that other NexPay services can include as a dependency, following the API-client library pattern used across the platform.

## Containerization

### Dockerfile (`nexpay-order-orchestrator-boot/Dockerfile`)

```dockerfile
FROM bellsoft/liberica-openjre-alpine:25
RUN apk update && apk add --no-cache jq curl bash
WORKDIR /app
ARG JAR_NAME=nexpay-order-orchestrator-boot.jar
ENV JAVA_TOOL_OPTIONS="-Xms512m -Dotel.java.global-autoconfigure.enabled=true"
EXPOSE 8080
CMD ["sh", "-c", "java $JAVA_TOOL_OPTIONS -jar ./${JAR_NAME}"]
```

Key observations:
- Base image is BellSoft Liberica JRE 25 on Alpine — good for image size.
- Container runs as `root` by default (no `USER` instruction). This is a security gap — the container should run as a non-root user.
- `JAVA_TOOL_OPTIONS` sets only a minimum heap (`-Xms512m`). No maximum heap (`-Xmx`) is set, meaning the JVM can consume all available container memory.
- OpenTelemetry auto-instrumentation is enabled at JVM startup via `-Dotel.java.global-autoconfigure.enabled=true`.
- `jq`, `curl`, and `bash` are installed — useful for liveness probes but increases the attack surface. These should be audited for necessity in production images.

### Docker Compose

`compose.yaml` provides a local development environment. `compose-all.yaml` includes additional dependent services. No production Docker Compose is used — production runs on Azure Container Apps.

## CI/CD Pipeline

### GitHub Actions — `.github/workflows/deployment.yml`

```yaml
on:
  pull_request:
    types: [opened, synchronize, labeled]
  push:
    branches: [main]
jobs:
  build-and-deploy:
    uses: OnbeEast/nexpay-iac/.github/workflows/java-build-deploy-aca.yml@main
    with:
      APP_NAME: ca-nexpay-order-orchestrator
      PUBLISH_TO_APIM: false
      INTERNAL_APIM: true
      EXTERNAL_APIM: false
      CONTAINER_SCAN: false   # Disabled — noted as frequently failing
```

The CI/CD delegates entirely to a reusable workflow in `nexpay-iac`. This centralises the build/push/deploy logic. **Container scanning is explicitly disabled** (`CONTAINER_SCAN: false`) with a comment saying it "frequently fails." This is a PCI DSS Requirement 6.3.3 gap — vulnerability scanning of container images must be operational. Disabling it means unpatched CVEs in the base image or application dependencies may go undetected.

### Code Quality — `.github/workflows/codeql.yml`

GitHub CodeQL is configured for static analysis. This provides SAST coverage as required by PCI DSS Requirement 6.2.4.

### Dependency Management — `.github/dependabot.yml`

Dependabot is configured for automated dependency update PRs. This helps maintain patching cadence but requires PR review discipline.

## Configuration Management

### Azure App Configuration

In QA and Production, all runtime configuration is sourced from Azure App Configuration using the managed identity credential. The bootstrap config (`bootstrap.yml`) references `${AZURE_APP_CONFIG_ENDPOINT}`. Key-filter `nexpay-order-orchestrator/{key}` with label `${spring.profiles.active}` scopes configuration to this service and environment.

Sensitive values (database passwords, API keys) are stored as Azure Key Vault references within App Configuration. The `keyvault-secret-provider.enabled: true` setting enables transparent secret resolution.

Refresh interval is `5m` by default, overridable via `AZURE_APP_CONFIG_REFRESH_INTERVAL` environment variable.

### App Config Migration Workflow

The repository includes `AZURE_APP_CONFIG_MIGRATION_6.0.0.md` and `app-config/qa/appsettings.json`, providing an IaC-adjacent record of configuration changes. The `app-config.yml` GitHub Actions workflow automates pushing `appsettings.json` to Azure App Configuration.

## Observability

### Logging

- Structured JSON logging via Logstash format (`logging.structured.format.file: logstash`) for log aggregation compatibility.
- Log level in default config is `DEBUG` for `com.onbe.nexpay` and Spring web components — this is appropriate for QA but should be reviewed for production to avoid PII leakage in logs.
- HTTP client wire-level logging is enabled at `DEBUG` (`org.apache.hc.client5.http.wire: DEBUG`) — this logs full request/response bodies including HTTP headers. The `sanitize-headers` list (`Authorization,X-API-Key,X-Auth-Token`) provides partial protection but body-level logging may expose claim code values.

### Metrics and Tracing

- Spring Actuator exposes `health`, `info`, `metrics`, `prometheus`, `startup` on port 8081.
- OpenTelemetry is fully configured for QA/Prod with OTLP export to `${OTEL_EXPORTER_OTLP_ENDPOINT}`. Both traces and metrics are exported.
- Liveness (`/actuator/health/liveness`) and readiness (`/actuator/health/readiness`) probes are enabled for Kubernetes/ACA health management.

## Operational Runbook Notes

### Health Check Endpoints

| Endpoint | Port | Purpose |
|----------|------|---------|
| `GET /actuator/health` | 8081 | Overall health |
| `GET /actuator/health/liveness` | 8081 | ACA liveness probe |
| `GET /actuator/health/readiness` | 8081 | ACA readiness probe |
| `GET /actuator/metrics` | 8081 | Micrometer metrics |
| `GET /actuator/prometheus` | 8081 | Prometheus scrape |

### Saga Stale State Risk

Failed sagas transition to `COMPENSATED` but compensation stubs currently take no live action. Operations teams should monitor for sagas stuck in `FAILED` or `COMPENSATED` states with an alert threshold, and have a runbook for manual review of the claim code against the card processor.

### Connection Pool Sizing

HTTP client connection pool (`nexpay.httpclient.connection-pool.max-total: 50`, `max-per-route: 20`) and timeout configuration (`connect-ms: 10000`, `response-ms: 30000`) are defined in `application.yaml` lines 74–91. The validation API has separate extended timeouts of 45 seconds to accommodate potentially slow screening responses.

### Redis (Service-Bus Module)

The service-bus sub-module requires a Redis instance for orchestration state. No TTL is configured in visible code — orphaned state from failed orchestrations will accumulate. A monitoring alert on Redis key count growth rate is recommended.
