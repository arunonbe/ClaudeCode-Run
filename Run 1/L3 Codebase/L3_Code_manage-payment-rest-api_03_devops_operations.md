# DevOps / Operations View — manage-payment-rest-api

## Build System

| Attribute | Value |
|---|---|
| Build tool | Maven 3.x (mvnw wrapper) |
| Java | 21 |
| Spring Boot | 3.4.5 |
| Packaging | Executable JAR (Spring Boot repackage) |
| Test frameworks | JUnit 5, Spock 2.4 (Groovy 4.0), Spring Boot Test |
| Integration tests | Maven Failsafe plugin (`*IntegrationSpec`) |
| Code generation | SpringDoc OpenAPI Maven plugin (generates `openapi.yaml` at integration-test phase) |

### Build Phases

1. `mvn clean verify` — runs unit tests (Spock `*Spec`) + integration tests (`*IntegrationSpec` via Failsafe)
2. Integration tests start a `mock` profile Spring Boot instance: `-Dspring.profiles.active=mock`
3. SpringDoc plugin generates `openapi.yaml` from the running application at `http://localhost:8080/v3/api-docs`
4. `openapi.yaml` is published to APIM as part of the CI/CD pipeline

## Containerisation

**Dockerfile** (`bellsoft/liberica-openjre-alpine:21`):
- Runs as an **implicit root user** (no `USER` instruction) — security risk for a PCI DSS payment API
- Memory: `-Xms512m -Xmx2048m` via `JAVA_TOOL_OPTIONS`
- Ports: 80 (app), 9090 (actuator), 9091, 50505
- Startup: `source startup.sh; java $JAVA_TOOL_OPTIONS -jar application.jar`
- QA AD certificate imported into JVM truststore (`nam-ad-dc1-ca.crt`)
- `startup.sh` is sourced before JVM launch — its content is not in the repository; it likely injects environment variables

**`docker-compose.yml`** provides a local development environment with mock services.

## CI/CD Pipeline

### Primary Pipeline (`deployment.yml`)

Delegates to `om-ci-setup/.github/workflows/java-workflow.yml@main`:
```yaml
APP_NAME: ManagePaymentAPI
PUBLISH_TO_APIM: true
EXTERNAL_APIM: true
java-runner: "['ubuntu-latest']"   # GitHub-hosted runner (not self-hosted)
API_SUFFIX: managepayments
```

The shared workflow (`java-build-deploy-aca.yml` in `nexpay-iac`) performs:
1. `mvn clean verify` — build and test
2. CodeQL security scan (Java/Kotlin)
3. Docker image build and push to ACR (`acraz1clusterqass.azurecr.io`)
4. Deploy to Azure Container Apps (`ca-ManagePaymentAPI-qa` and `-prod`) via `azure/container-apps-deploy-action@v1`
5. Publish OpenAPI spec to Azure APIM (`apim-az1-cluster-{env}-ss`) as an **external API** (`EXTERNAL_APIM: true`)

**Deployment targets**: `qa` and `prod` environments, run in sequence with max-parallel: 1 via matrix strategy.

**Trigger**: Push to `main` branch deploys to both QA and prod. PRs trigger build-and-test only.

### Supplemental Pipelines

| Workflow | Purpose |
|---|---|
| `redeploy.yaml` | Redeploy existing image without rebuild (environment variable updates, config changes) |
| `codeql.yml` | Weekly CodeQL scan |

## Configuration Management

### Profile-Based Configuration

| Profile | Database hosts | Director/banker | Notes |
|---|---|---|---|
| `dev`/`local` | `u-lis-db01.nam.wirecard.sys:2231` (UAT) | `uat.nam.wirecard.sys` | Default active profile |
| `prod` | `p-lis-db01/02/03.nam.wirecard.sys:2231` | `prod.nam.wirecard.sys` | Production DB servers |
| `mock` | Not connected | Mock implementations | Integration test profile |

### Secrets Injection

- Database credentials: `${MANAGEPAYMENTAPI_CBASEAPPDB_USERNAME}` / `${..._PASSWORD}` — injected as environment variables in Container Apps (from Azure Key Vault via App Configuration).
- Redis password: `${RECIPIENTWEB_REDIS_PASSWORD}`
- End-client OAuth: `${ENDCLIENT_OAUTH_CLIENT_ID}`, `${ENDCLIENT_OAUTH_CLIENT_SECRET}`

**Critical finding from 02_data_architect.md**: `dapr-components/dapr-secrets.json` contains development secrets committed to the repository. This is a PCI DSS Req 3.3 / Req 8 violation that must be remediated.

### `trustServerCertificate=true`

All four SQL Server JDBC URLs have `trustServerCertificate=true`, which disables TLS certificate validation for database connections. This creates a MITM risk on the network path between the service and SQL Server. This should be replaced with explicit certificate validation (import the SQL Server certificate into the JVM truststore and remove `trustServerCertificate=true`).

## Observability

### Health Endpoints (Actuator)

| Endpoint | URL |
|---|---|
| Health | `GET /hc` (mapped from `/actuator/health`) |
| Health liveness | `GET /actuator/health/liveness` |
| Health readiness | `GET /actuator/health/readiness` |
| Health DB probes | DB health included (`show-details: always`) |
| RPC connection health | Director service at `https://uat.nam.wirecard.sys:8080/service/dispatch.asp` |

**Security concern**: `show-details: always` exposes database connection health details including connection pool status in the health endpoint response. This should be `show-details: when-authorized` in production.

### Logging (Logbook)

Zalando Logbook logs all HTTP requests/responses on `/v1/accounts/**` paths with JSON body field masking for `ssn`, `cardNumber`, `cvv`. Log level for logbook is `TRACE` in default profile — this will produce very high log volume in production and may create latency. Log level should be `INFO` or `WARN` in production.

### OpenTelemetry

No OpenTelemetry configuration is visible in the application YAML files (unlike NexPay Gen-3 services). This service does not appear to have OTLP/Dynatrace integration. Observability relies on Logbook HTTP logs and Spring Boot Actuator metrics (Prometheus endpoint exposure not configured).

## Operational Risk Register

| Risk | Severity | Detail |
|---|---|---|
| Container runs as root | High | No USER instruction in Dockerfile |
| `trustServerCertificate=true` on all DBs | High | SQL Server MITM risk; PCI DSS Req 4 |
| `dapr-secrets.json` with Visa keys in repo | Critical | Already noted in 02; must rotate credentials immediately |
| `show-details: always` on health endpoint | Medium | Exposes internal connectivity details to unauthenticated callers |
| Logbook TRACE logging in production | Medium | High-volume HTTP logging including sensitive field values near payment data paths |
| No OTel / distributed tracing | Medium | No end-to-end trace correlation across services |
| Single QA/prod deployment (no staging) | Medium | Changes go directly from QA to prod via the matrix strategy |
