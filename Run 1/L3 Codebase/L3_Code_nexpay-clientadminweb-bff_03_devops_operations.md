# nexpay-clientadminweb-bff — DevOps & Operations View

## 1. Repository and Build Structure

The repository uses a standard Maven multi-module layout:

```
nexpay-clientadminweb/               (root POM — aggregator)
├── nexpay-clientadminweb-api/       (OpenAPI-generated server stubs)
├── nexpay-clientadminweb-boot/      (Spring Boot executable module — Dockerfile here)
├── nexpay-clientadminweb-client/
│   ├── nexpay-clientadminweb-claimcode-client-api/  (generated claim-code client)
│   └── nexpay-clientadminweb-config-client-api/     (generated config-svc client)
└── nexpay-clientadminweb-impl/      (business logic, filters, rest clients)
```

**Java version**: 25 (JEP-444 virtual threads enabled via `spring.threads.virtual.enabled: true`).

**Parent POM**: `com.onbe.nexpay:nexpay-parent:0.2.8-SNAPSHOT` — this is the Onbe enterprise parent BOM, providing dependency version management across all NexPay services.

**Maven wrapper**: `.mvn/wrapper/maven-wrapper.properties` pins the Maven version for reproducible builds. The `.mvn/wrapper/settings.xml` configures the internal Nexus/Artifactory mirror for dependency resolution.

## 2. Container and Docker

**Dockerfile** (`nexpay-clientadminweb-boot/Dockerfile`):

```dockerfile
FROM bellsoft/liberica-openjre-alpine:25
RUN apk update && apk add --no-cache jq curl bash
WORKDIR /app
EXPOSE 8080
CMD ["sh", "-c", "java $JAVA_TOOL_OPTIONS -jar ./${JAR_NAME}"]
```

Key observations:
- Base image: `bellsoft/liberica-openjre-alpine:25` — a lightweight JRE-only Alpine image. The use of JRE (not JDK) in production is a security best practice.
- `--enable-native-access=ALL-UNNAMED` is set via `JAVA_TOOL_OPTIONS` to suppress Netty warnings. This is a known pattern but does grant native library access to all unnamed modules. Monitor future Netty releases for a cleaner fix.
- `jq`, `curl`, `bash` are installed (`apk add`), which increases the image attack surface. These are likely needed for health-check scripts or entrypoint logic. A hardened production image should remove `bash` and `curl` unless required.
- No non-root user is declared in the Dockerfile. The container runs as root by default, violating PCI DSS Requirement 2.2 (system hardening). A `USER` directive should be added.

**Heap**: `-Xms512m` is set but no `-Xmx` cap. Under memory pressure, the container can exhaust the Container Apps memory limit (0.5Gi in QA, `qa.tfvars` line 203), triggering OOMKilled restarts. Add `-Xmx400m` or tune with `-XX:MaxRAMPercentage=75`.

## 3. CI/CD Pipeline

### 3.1 GitHub Actions Workflows

| Workflow | Trigger | Purpose |
|---|---|---|
| `deployment.yml` | PR open/sync, push to `main` | Build, test, publish to ACR, deploy to ACA |
| `app-config.yml` | Separate trigger | Push app-config settings to Azure App Configuration |
| `codeql.yml` | Push/PR | GitHub CodeQL SAST scanning |
| `redeploy.yml` | Manual dispatch | Re-deploy without a code change |
| `dependabot.yml` | Scheduled | Dependency vulnerability scanning |

### 3.2 Deployment Workflow Detail (`deployment.yml`)

The build delegates entirely to the shared reusable workflow at `OnbeEast/nexpay-iac/.github/workflows/java-build-deploy-aca.yml@main`. Key parameters:

- `APP_NAME: ca-nexpay-clientadminweb-bff` — the Azure Container App name.
- `PUBLISH_TO_APIM: true`, `EXTERNAL_APIM: true` — after a successful deploy, the service's OpenAPI spec (`./nexpay-clientadminweb-api/target/openapi.yml`) is published to the External APIM instance so that the client admin SPA can discover and call the API.
- `API_SUFFIX: api/nexpay-clientadminweb` — the APIM route prefix.
- `CODEQL_QUALITY: true` — CodeQL analysis runs as part of the build gate; failing analysis blocks deployment.
- `TARGET_ROOT: ./nexpay-clientadminweb-boot` — Maven build targets this module for the artifact JAR.
- `MAVEN_ARGS: '-q'` — quiet Maven output. Consider removing `-q` in QA to surface compilation warnings.

### 3.3 Container Registry

Images are pushed to `acraz1clusterqass.azurecr.io` (defined in `qa.tfvars` line 12). The Container Apps managed identity is granted `AcrPull` role (`container-apps/main.tf` lines 29–35), so no static registry credentials are injected into containers.

## 4. Environment Configuration

Configuration is delivered at runtime through two layers:

1. **Azure App Configuration** (`appcg-nexpay-qa.azconfig.io`) — keys prefixed `nexpay-clientadminweb-bff/` with label `qa`. This includes Redis host/port and downstream service URLs. Enabled in the `qa` Spring profile (`application-qa.yaml` lines 15–24).
2. **Azure Key Vault** — secrets referenced via App Configuration Key Vault references (pattern `@Microsoft.KeyVault(SecretUri=...)`). The Redis primary key and JWT secret are stored here.

Environment variable `AZURE_CLIENT_ID` must be injected into the container at deploy time to enable the Managed Identity credential (`application-qa.yaml` line 31).

## 5. Observability

### 5.1 Health Endpoints

```
GET :8081/actuator/health      — liveness/readiness (show-details: always)
GET :8081/actuator/info        — version metadata
GET :8081/actuator/metrics     — Micrometer metrics
GET :8081/actuator/prometheus  — Prometheus scrape endpoint
GET :8081/actuator/startup     — startup probe
GET :8081/actuator/env         — environment dump  ← HIGH RISK (see below)
```

Management port `8081` is separate from the application port `8080`. However, the `env` endpoint is included in `exposure.include` and can expose resolved configuration values including secrets that are not Key Vault references. This must be removed or restricted to an internal-only ingress rule.

### 5.2 Distributed Tracing

OpenTelemetry traces and metrics are exported via gRPC to `${OTEL_EXPORTER_OTLP_ENDPOINT}` (Dynatrace endpoint injected at runtime). Trace sampling probability is not configured in this BFF's YAML — it inherits the platform default. The `otel-grpc` runtime dependency (`pom.xml` line 44) provides the gRPC transport.

### 5.3 Logging

Logging level for `com.onbe.nexpay` is `INFO` in QA (`application-qa.yaml` line 50). Root logger is `WARN`. Logback configuration is inherited from the parent/boot. No structured logging format is explicitly configured here (unlike `nexpay-config-svc` which uses Logstash JSON format) — this is a gap for log aggregation consistency.

## 6. Scaling Configuration (QA)

From `qa.tfvars` lines 198–210:
- Min replicas: 1, Max replicas: 3
- CPU: 0.25 vCPU, Memory: 0.5Gi
- Workload profile: `Consumption`

The Consumption profile is pay-per-use with cold-start latency up to ~3–5 seconds. For a BFF serving an interactive admin portal this is acceptable in QA but should be reviewed for production where warm instances (`Dedicated` workload profile) are more appropriate.

## 7. Operational Runbook Notes

- **Zero-downtime re-deploy**: The Container App revision mode is `Single` (`container-apps/main.tf` line 67), meaning new revisions replace old ones. Combine with the `redeploy.yml` workflow for fast rollback.
- **Secret rotation**: Secrets flow from GitHub Environment secrets → Azure Key Vault (via `sync-secrets-to-kv.yml`) → App Configuration Key Vault reference → container env var at startup. Redis key rotation requires an App Configuration sentinel bump to trigger a refresh.
- **Rolling restart**: The `redeploy.yml` workflow triggers a re-deploy without code change, useful for picking up refreshed Key Vault secrets.
