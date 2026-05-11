# DevOps & Operations — oneplatform-rest_API

## Build
- **Build tool**: Apache Maven (parent `onbe-spring-boot-parent:0.0.15`).
- **Java**: 21 (`maven.compiler.source/target=21`).
- **Artifact**: Executable JAR (`oneplatform-rest-api-5.8.0.jar`).
- **Wrapper**: `mvnw` / `mvnw.cmd` present.
- **OpenAPI spec**: `springdoc-openapi-maven-plugin` generates `v3/api-docs` during integration-test phase (runs embedded Spring Boot on port 8081 with `mock` profile).
- **Enforcer**: `maven-enforcer-plugin` bans `log4j:log4j` transitive dependency; enforces no duplicate POM dependencies; allows SNAPSHOT for internal artifacts.
- **Tests**: Integration tests wired to run against embedded Spring Boot; requires mock profile startup. Unit tests via JUnit 5 / Mockito.

## Deployment
- **Dockerfile** (`Dockerfile`): Base image `bellsoft/liberica-openjre-alpine:21`. Port 80 exposed. JVM options: `-Xms512m -Xmx2048m`.
- **Docker Compose**: `docker-compose.yml`, `docker-compose-dev.yml`, `docker-compose-dev-min.yml` — multi-container local dev setup.
- **Dapr**: `dapr-components/` and `dapr-configuration/` directories present — Dapr sidecar required at runtime for PayPal, push provisioning, OTP, and GeoIP service invocations.
- **Spring profiles**: `dev`, `qa`, `staging`, `prod`, `mock`.
- **Integration directory**: `integration/` folder present but contents not read; likely integration test configs.

## Configuration Management
- Profile YAML files (`application-{profile}.yaml`) for all environments.
- `bootstrap.yaml` for Spring Cloud Azure App Configuration bootstrapping.
- Dapr secret store (`services-secret-store`) and config store (`local-config-store`) inject secrets at runtime via Dapr components.
- Key Vault secrets referenced as `${mypaymentvaultapi-*}` property placeholders — resolved via Dapr or Spring Cloud Azure Key Vault depending on profile.
- **Findings**: `application.yaml` contains hardcoded Azure App Config connection string with embedded secret (line 12), Redis cache key (line 218), CBTS credentials (lines 168-169), Western Union static key (line 126-127).

## Observability
- **Spring Boot Actuator**: Configured at `management.endpoints.web.exposure.include: 'health,info'`; health endpoint mapped to `/hc`.
- **Health checks**: DB health probe enabled; liveness/readiness probes enabled; RPC connection health indicator (`RpcConnectionHealthIndicator`) for director-service.
- **Logging**: Log4j2 (`log4j2-spring.xml`); SLF4J bridging via `log4j-jcl`. Structured JSON logging implied by log4j2 config (not read in detail).
- **Metrics**: Micrometer with Spring Boot Actuator (actuator starter dependency present).
- **Tracing**: No OpenTelemetry or distributed tracing dependency observed in this repo.

## Infrastructure Dependencies
| Dependency | Details |
|-----------|---------|
| SQL Server (cbaseapp) | HikariCP; `q-lis-db01` / `P-LIS-DB03`; TLS 1.2 |
| SQL Server (EcountCore) | HikariCP; `q-lis-db02` / `P-LIS-DB02`; TLS 1.2 |
| SQL Server (jobsvc) | HikariCP; `q-lis-db01` / `P-LIS-DB01`; TLS 1.2 |
| Azure Redis Cache | Jedis 5.2.0; TLS; password from Dapr/Key Vault |
| Azure App Configuration | Feature flags; connection string in config |
| Dapr sidecar | Service invocation (PayPal, OTP, GeoIP, push provisioning); pub/sub outbox |
| director-service (XMLRPC) | ecount backend RPC; `https://qa.nam.wirecard.sys:8080/service/dispatch.asp` |
| CBTS | Cross-border transfer HTTP; `http://q-na-app08.nam.wirecard.sys:9443/` |
| BioCatch API | External behavioral scoring; `https://api-osiristest.us.v2.customers.biocatch.com` |
| Google reCAPTCHA Enterprise | External CAPTCHA; `https://recaptchaenterprise.googleapis.com` |
| PayPal OAuth | `https://www.paypal.com/connect` (prod); sandbox in dev |
| Western Union | Certificate-based integration (`citi.crt` bundled) |
| xSSO | SSO token decryption service |

## Operational Risks
- **Dapr dependency**: All PayPal, OTP, GeoIP, and push provisioning flows fail if Dapr sidecar is unavailable — single point of failure.
- **Three SQL Server connections**: Health check on all three at startup; a single DB being unreachable will fail readiness probe.
- **RPC health indicator**: Points to director-service; if director-service is down, health check may report unhealthy.
- **External API timeouts**: BioCatch and reCAPTCHA are called synchronously; slow external responses will increase API latency.
- **CBTS retry**: 3 retries at 1-second intervals — aggressive retry may amplify load on CBTS during incidents.
- **SNAPSHOT dependency**: `onbe-cloud-starter:2.0.0-SNAPSHOT` — SNAPSHOT dependencies introduce build non-reproducibility.

## CI/CD
- No CI/CD pipeline definition file found in this repository root (no `.gitlab-ci.yml`, `Jenkinsfile`, or `.github/workflows/`).
- `pig.template` present (likely a Gitlab pipeline templating artifact — content not read).
