# customer-service-rest-api — DevOps / Operations View

## Build System
- **Maven** with Spring Boot parent `3.4.10`; Java 21.
- `pom.xml` final artifact name: `customer-service-rest-api` (fat JAR via `spring-boot-maven-plugin`).
- OpenAPI Generator 7.12.0 generates controller interfaces, models, and `ApiUtil.java` from `openapi.yml` into `target/generated-sources`.
- Swagger Codegen 3.0.68 converts `openapi.yml` to `target/openapi.json`.
- MapStruct 1.6.3 + Lombok 1.18 for mapper and boilerplate generation.
- Maven Enforcer: requires Java 1.21+, Maven 3.0+; no SNAPSHOTs except for internal `com.ecount*`, `com.citi.prepaid*`, `com.wirecard*`, `com.onbe*` groups.

## Container
- `Dockerfile`: base image `bellsoft/liberica-openjre-alpine:21`.
- Exposes ports `80` (server), `9090` (actuator), `9091`, `50505`.
- JVM flags: `-Xms512m -Xmx2048m` via `JAVA_TOOL_OPTIONS`.
- `startup.sh` sourced before JVM launch (content not present in repo — injected at runtime).
- Internal AD CA certificate imported at image build time (`nam-ad-dc1-ca.crt`).

## CI/CD Pipeline
- GitHub Actions workflow: `.github/workflows/deployment.yml`
- Triggers: push to `main` or `bugfix/EPTD-3459-request-logging`; PR open/sync/label.
- Reusable workflow: `Onbe/om-ci-setup/.github/workflows/java-workflow.yml@main`.
- Key parameters:
  - `APP_NAME: CustomerServiceAPI`
  - `PUBLISH_TO_APIM: true`, `EXTERNAL_APIM: true` — OpenAPI spec published to external APIM.
  - `MAVEN_ARGS: -s ./.mvn/wrapper/settings.xml -U -Daether.connector.https.securityMode=insecure -Dmaven.test.skip` — **tests skipped in CI**.
  - `API_SUFFIX: managepayments/customerservice`.
- Additional workflows: `codeql.yml` (CodeQL SAST), `redeploy.yaml` (on-demand redeploy).
- Dependabot: `dependabot.yml` configured for automated dependency updates.
- Container scan allowlist: `.github/containerscan/allowedlist.yaml`.
- CODEOWNERS: `.github/CODEOWNERS`.

## Configuration
All runtime configuration via environment variables:
| Variable | Purpose |
|---|---|
| `SERVER_PORT` | HTTP port (default 8080) |
| `ACTUATOR_PORT` | Management port (default 9090) |
| `ECOUNT_AGENT` | eCount agent identifier |
| `ECOUNT_CONFIG_SERVICE_URL` | eCount config service boot address |
| `ECOUNT_ORDER_SERVICE_URL` | eCount order service URL |
| `CUSTOMERSERVICE_CBASEAPPDB_URL` | cbaseapp DB JDBC URL |
| `CUSTOMERSERVICEAPI_CBASAPPDB_USERNAME/PASSWORD` | cbaseapp DB credentials |
| `CUSTOMERSERVICE_JOBSVCDB_URL` | jobsvc DB JDBC URL |
| `CUSTOMERSERVICEAPI_JOBSVCDB_USERNAME/PASSWORD` | jobsvc DB credentials |
| `ECOUNT_CORE_BASE_URL` | ECountCore REST base URL |
| `CMS_MEMBER_ID` | AccountManagementAPI member ID |
| `CMS_OP_LOGIN_URL` | CMS operation login URL |
| `FISERV_DR_PROGRAMS` | Fiserv DR program codes |
| `CONNECTION_TIMEOUT`, `IDLE_TIMEOUT`, `MAX_LIFE_TIME`, `MAX_POOL_SIZE` | HikariCP tuning |

Dapr secret store configured (`dapr-components/`): `dapr-secrets.json` present for local dev, `local-secret-store.yaml`, `secret-store-config.yml`.

## Observability
- Spring Actuator endpoints exposed: `health` (mapped to `/hc`), `metrics`, `info`, `prometheus`.
- OpenTelemetry: `opentelemetry-spring-boot-starter` (version 2.15.0-alpha) + `opentelemetry-api-incubator`.
- Log4j2 (`spring-boot-starter-log4j2`); `log4j2-spring.xml` in resources.
- Prometheus metrics tag: `app_name=customer-service`.
- Health probes: liveness and readiness enabled for Kubernetes.
- DB health check enabled (`management.health.db.enabled: true`).

## Risks
- `MAVEN_ARGS` includes `-Daether.connector.https.securityMode=insecure` — TLS verification disabled during Maven dependency resolution in CI.
- Tests are explicitly skipped in CI (`-Dmaven.test.skip`); no automated regression gate before deployment.
- `startup.sh` is not in the repository — content unknown; failure in startup script would prevent the container from launching with no visibility from the Dockerfile alone.
- OpenTelemetry instrumentation is `alpha` (2.15.0-alpha) — API stability not guaranteed.
- HikariCP `min-idle=10` equals `max-pool-size=10`; pool never shrinks — may hold excess DB connections during low-traffic periods.
