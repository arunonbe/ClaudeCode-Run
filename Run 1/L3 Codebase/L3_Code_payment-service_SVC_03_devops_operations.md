# DevOps & Operations — payment-service_SVC

## Build
- **Build tool**: Apache Maven multi-module (parent `com.parents:prepaid-parent:6.0.13`).
- **Java**: 21 (`maven.compiler.source/target=21`).
- **Modules**: `payment-client`, `Payment-Common`, `Payment-Service`, `Payment-War`.
- **Artifact**: WAR (`payment-service-webapp.war`), deployed to Tomcat 10.1.28.
- **Wrapper**: `mvnw` / `mvnw.cmd` present.
- **CI/CD**: `.gitlab-ci.yml` present — includes `northlane/development/application-development/configuration/ci-templates:maven.gitlab-ci.yml`.
- **Tests skipped**: All Maven phases (`build`, `test`, `deploy`) set `MAVEN_TEST_OPTS: "-Dmaven.test.skip=true"`.

## Deployment
- **Dockerfile** (`Payment-War/Dockerfile`): Base `bellsoft/liberica-openjre-alpine:21`; downloads and configures Apache Tomcat 10.1.28 at build time via `curl https://archive.apache.org/dist/tomcat/tomcat-10/v10.1.28/...`; copies WAR as `service.war`; imports QA cert into JVM trust store; exposes port 80.
- **Environment variable**: `CBASE_HOME_URL=file:///cbase` — path from which Tomcat reads `log4j2.xml` and potentially property files.
- **Docker Compose**: `Payment-War/docker-compose.yaml` present.
- **GitLab CI targets**: Dev hosts `d-na-app03`; QA hosts `q-na-app03`, `q-na-app04`.
- **Service deployment**: The service name `Payment` and path `Payment-War` map to a named Windows service and Tomcat instance (per `SERVICE_NAME` and `DEV_SERVICE_HOSTS` variables) — suggests on-premises Windows deployment alongside containerized deployment.
- **Server port**: 9208 (dev and QA).
- **Health check path**: `/service/dispatch.asp` (XMLRPC servlet URL).

## Configuration Management
- Spring XML context files loaded from classpath: `DataSources.xml`, `PropertyPlaceHolder.xml`, `ExternalServicesContext.xml`, `appCtx-PaymentService.xml`, `EPaymentXMLRPC.xml`.
- `PropertyPlaceHolder.xml` uses Spring's `PropertyPlaceholderConfigurer`; properties injected from filesystem at `${CBASE_HOME_URL}/config/service/payment/`.
- No Azure Key Vault or Dapr integration — configuration management is filesystem/environment-variable based (legacy Gen-1 pattern).
- QA cert bundled in Docker image (`config/certfile_qa.crt`); production cert management not visible in source.

## Observability
- **Logging**: Log4j2; configuration loaded from `${CBASE_HOME_URL}/config/service/payment/log4j2.xml` at runtime (external to WAR). Log4j2 refresh interval: 300 seconds (5 minutes).
- **Health check**: HTTP GET to `/hc` via Spring MVC `DispatcherServlet`; `HealthCheck.java` class in `com.ecount.one.health` package.
- **No Micrometer/Actuator**: No Spring Boot Actuator — this is a WAR-deployed Spring MVC application, not Spring Boot.
- **No distributed tracing**: No OpenTelemetry or other tracing instrumentation.
- **Thread-local logger**: Unusual `ThreadLocal<Logger>` in `PaymentServiceImpl` — not standard SLF4J/Log4j2 usage.

## Infrastructure Dependencies
| Dependency | Details |
|-----------|---------|
| Apache Tomcat 10.1.28 | Servlet container; downloaded at Docker build time |
| SQL Server `cbaseapp` | Primary DB; JDBC via xplatform data source config |
| director-service (XMLRPC) | ecount backend dispatcher |
| member XMLRPC client | Member management |
| device XMLRPC client | Device management |
| transfer XMLRPC client | Transfer operations |
| profile client | Profile service |
| notification service | Email notifications via `NotificationManagerImpl` |
| `affiliateLocaleSkinHelper` / `AffiliateMapSkin` | Affiliate-based skin/locale resolution for email links |
| External files at `CBASE_HOME_URL` | Log4j2 config, property files |

## Operational Risks
- **Tomcat downloaded at build time**: `curl https://archive.apache.org/dist/tomcat/...` in Dockerfile — network dependency during build; archive.apache.org availability is not guaranteed; no hash/checksum verification in Dockerfile.
- **`certfile_qa.crt` in Docker image**: QA certificate embedded at build time — must not be used in production images; separate production Dockerfile or build arg should be used.
- **Tests skipped in all CI phases**: No automated test execution means regressions are not caught in CI.
- **External log4j2 config**: Log4j2 configuration read from `${CBASE_HOME_URL}/config/` — if that path is unavailable at startup, logging will fail to initialize properly.
- **JVM opens flags**: `--add-opens java.base/java.lang=ALL-UNNAMED` etc. in `JAVA_OPTS` — required for Tomcat 10 / Jakarta EE compatibility but suppresses module encapsulation checks.
- **On-premises Windows deployment** implied by `SERVICE_NAME` and `*_SERVICE_HOSTS` variables — dual deployment target (Windows and Docker) increases operational complexity.

## CI/CD
- `.gitlab-ci.yml` delegates to shared `maven.gitlab-ci.yml` pipeline template.
- Pipeline stages: build, test (skipped), deploy to dev/QA Windows hosts.
- Variables: `SERVICE_NAME=Payment`, `PROJECT_ARTIFACT_PATH=Payment-War`, `PROJECT_SERVICE_DEV_PORT=9208`, `QA_SERVICE_HOSTS=q-na-app03 q-na-app04`.
- Tests are explicitly skipped in build, test, and deploy phases.
