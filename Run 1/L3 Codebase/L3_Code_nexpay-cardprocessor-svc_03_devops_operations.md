# DevOps / Operations View — nexpay-cardprocessor-svc

## Build System

| Attribute | Value |
|---|---|
| Build tool | Maven 4 (mvnw wrapper, POM 4.1.0 format) |
| Java | 25 |
| Spring Boot | via `nexpay-parent:0.2.8-SNAPSHOT` |
| Version | `0.0.3-SNAPSHOT` |
| Packaging | Executable JAR (`nexpay-cardprocessor-boot.jar`) |
| Modules | `-adapter-fis`, `-adapter-spi`, `-adapter-thredd`, `-api`, `-boot`, `-data-entity`, `-data-repository`, `-impl` |
| Test containers | Not visible in root pom.xml (may be in nexpay-parent) |

### Module Build Order

```
nexpay-cardprocessor-adapter-spi   ← SPI interfaces (no deps)
nexpay-cardprocessor-api           ← OpenAPI-generated API contracts
nexpay-cardprocessor-data-entity   ← JPA entities + Flyway migrations
nexpay-cardprocessor-data-repository ← Spring Data repositories
nexpay-cardprocessor-impl          ← Business logic (depends on above)
nexpay-cardprocessor-adapter-thredd ← Thredd REST adapter (implements SPI)
nexpay-cardprocessor-adapter-fis   ← FIS form-encoded adapter (implements SPI)
nexpay-cardprocessor-boot          ← Spring Boot assembly + configuration
```

## Containerisation

**Dockerfile** (`nexpay-cardprocessor-boot/Dockerfile`):
```dockerfile
FROM bellsoft/liberica-openjre-alpine:25
ENV JAVA_TOOL_OPTIONS="-Xms512m -Dotel.java.global-autoconfigure.enabled=true"
EXPOSE 8080
CMD ["sh", "-c", "java $JAVA_TOOL_OPTIONS -jar ./${JAR_NAME}"]
```

- **Base image**: BellSoft Liberica JRE 25 on Alpine
- **No USER instruction**: Container runs as root — security risk
- **No explicit max heap**: Only `-Xms512m` (initial heap) specified; no `-Xmx` — container memory could be exhausted under load
- **OTel autoconfigure**: `-Dotel.java.global-autoconfigure.enabled=true` in default `JAVA_TOOL_OPTIONS`
- **`.dockerignore`** present in the boot module — excludes unnecessary build artifacts from the image

**`docker-compose.yml`** (root level) provides local development with a PostgreSQL container.

## CI/CD Pipeline

### Primary Pipeline (`nexpay-cardprocessor-svc/.github/workflows/deployment.yml`)

Delegates to `OnbeEast/nexpay-iac/.github/workflows/java-build-deploy-aca.yml@main`:
```yaml
APP_NAME: ca-nexpay-card-proc-svc
PUBLISH_TO_APIM: false
INTERNAL_APIM: true
EXTERNAL_APIM: false
TARGET_ROOT: ./nexpay-cardprocessor-boot
CONTAINER_SCAN: false       # temporarily disabled
```

**Pipeline flow** (from `java-build-deploy-aca.yml`):
1. Java version auto-detected from `pom.xml` (`maven.compiler.target = 25`)
2. `mvn clean verify` — build + test
3. CodeQL security scan (`security-extended` + `security-and-quality`)
4. Docker build and push to `acraz1clusterqass.azurecr.io`
5. Deploy to ACA `ca-nexpay-card-proc-svc-qa` and `-prod` via `azure/container-apps-deploy-action@v1`
6. Environment variables injected: `ENVIRONMENT`, `APP_NAME`, `AZURE_CLIENT_ID`, `AZURE_APP_CONFIG_ENDPOINT`
7. OpenAPI spec NOT published to APIM (`PUBLISH_TO_APIM: false`) — internal service only

**Trigger**: Push to `main` branch deploys to both QA and prod (sequential, max-parallel: 1).

**Coverage gate**: JaCoCo coverage report published to PRs with minimum thresholds (80% overall, 60% changed files).

### Additional Workflows

| Workflow | Purpose |
|---|---|
| `app-config.yml` | Update Azure App Configuration values without full redeploy |
| `codeql.yml` | Weekly CodeQL scan |
| `temp-deployment.yml` | Temporary/experimental deployment workflow |

## Configuration Management

### Azure App Configuration (QA/Prod)

The service uses Azure App Configuration (`appcg-nexpay-qa.azconfig.io`) with Key Vault secret references:
```yaml
selects:
  - key-filter: "nexpay-cardprocessor-svc/"
    label-filter: "qa"
trim-key-prefix: "nexpay-cardprocessor-svc/"
```

Keys stored in App Config (from `app-config/qa/appsettings.json`):
- `spring.datasource.url` → Key Vault ref: `card-proc-svc-pg-connection-string`
- `processor.fis.uatusername` → Key Vault ref: `fis-uat-username`
- `processor.fis.uatpassword` → Key Vault ref: `fis-uat-password`
- `processor.fis.uatcertificate` → Key Vault ref: `fis-cert-base64`
- `processor.thredd.uatclientid` → Key Vault ref: `thredd-uat-clientid`
- `processor.thredd.uatclientsecret` → Key Vault ref: `thredd-uat-clientsecret`

All processor credentials are stored in Azure Key Vault, not in the repository. This is the correct pattern.

### Database Authentication

QA/Prod: Azure AD passwordless via Managed Identity:
```yaml
datasource:
  username: msi-nexpay-${ENVIRONMENT}
  azure:
    passwordless-enabled: true
```
Azure AD authentication plugin: `com.azure.identity.extensions.jdbc.postgresql.AzurePostgresqlAuthenticationPlugin`.

## Observability

### OpenTelemetry (QA/Prod)

Full OTLP/HTTP export to Dynatrace:
- Traces: `${OTEL_EXPORTER_OTLP_ENDPOINT}/v1/traces`
- Logs: `${OTEL_EXPORTER_OTLP_ENDPOINT}/v1/logs`
- Metrics: `${OTEL_EXPORTER_OTLP_ENDPOINT}/v1/metrics`
- Auth header: `${DT_OTLP_AUTH_HEADER}` (injected at Container App runtime)

**Note**: In default profile, OTel is enabled via `JAVA_TOOL_OPTIONS` global autoconfigure but `DT_OTLP_AUTH_HEADER` defaults are not set — OTel export will fail silently without the env var.

### Health Endpoints

| Endpoint | Port | Notes |
|---|---|---|
| `/actuator/health` | 8081 | Show details + components |
| `/actuator/health/liveness` | 8081 | Liveness probe |
| `/actuator/health/readiness` | 8081 | Readiness probe |
| `/actuator/startup` | 8081 | **UNRESTRICTED access in default profile** |
| `/actuator/env` | 8081 | **NONE access in QA/Prod** (correctly locked down) |

**Finding**: The `startup` endpoint is `UNRESTRICTED` in the default profile but `NONE` in QA. This is the correct state — QA correctly disables the startup endpoint. The default profile concern is acceptable since it only affects local development.

### Logging

- Default: All application loggers at `ERROR`, HikariCP at `TRACE` — high connection pool noise in default profile.
- QA/Prod: Application at `INFO`, Hibernate SQL at `DEBUG`, structured JSON (Logstash format) — correct for centralised log aggregation.

## Operational Risk Register

| Risk | Severity | Detail |
|---|---|---|
| Container runs as root | High | No USER instruction in Dockerfile |
| No `-Xmx` in Dockerfile | Medium | No max heap; container may OOM under load |
| Container scan disabled | Medium | `CONTAINER_SCAN: false` — Trivy not running; known CVEs may exist in base image |
| `0.0.3-SNAPSHOT` version | Medium | SNAPSHOT in production pipeline — not a release artifact |
| `nexpay-parent:0.2.8-SNAPSHOT` | Medium | Parent POM also SNAPSHOT — version instability |
| `DYNATRACE_API_TOKEN` not in Key Vault | Medium | Injected only as TF_VAR at deploy time; may be in Terraform state file |
| `startup` endpoint `UNRESTRICTED` in default | Low | Only affects local development; correctly locked in QA/Prod |
| FIS mTLS cert loaded per-request | Low | Base64 PKCS#12 decoded per-request may be performance-intensive; verify caching |
