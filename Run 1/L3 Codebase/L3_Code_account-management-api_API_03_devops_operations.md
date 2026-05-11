# account-management-api_API — DevOps & Operations View

## Build & Packaging

- **Build tool**: Apache Maven with wrapper (`mvnw`); settings in `.mvn/wrapper/settings.xml`
- **Java version**: 21 (compiler source/target in root `pom.xml` lines 27–28); Java 8 build path still exists in the CI/CD pipeline as a selectable option (`cicd-deployment.yml` input `java_version`)
- **Spring Boot**: 3.5.7 (`spring-boot.version` in root `pom.xml`)
- **Spring Framework**: 6.2.11
- **Module structure** (Maven multi-module):
  - `accountmanagementapi-impl` — service logic, domain, helpers, DAOs
  - `accountmanagementapi-ws` — SOAP web service interface, request/response objects, handler
  - `accountmanagementapi-war` — legacy WAR packaging (web.xml, Spring XML contexts, Apache Axis)
  - `accountmanagementapi-boot` — Spring Boot executable JAR (`accountmanagementapiws.jar`)
  - `accountmanagementapi-sasi` — commented out in root `pom.xml` (module disabled)
- **Final artifact name**: `accountmanagementapiws` (set in `accountmanagementapi-boot/pom.xml` line 18 `deployment.name`)
- **Packaging**: Both WAR (legacy Tomcat deployment) and Spring Boot JAR (container/Kubernetes) are produced
- **Enforcer rules**: `requireReleaseDeps` — no SNAPSHOT dependencies allowed (excluding `${project.groupId}`); `banTransitiveDependencies` in boot module (fail=false)
- **BouncyCastle**: `bouncycastle.version=1.60` — an older version (2018); relevant for `JWEHelper` AES-GCM operations

## Deployment

### Container (Gen-3 path — Spring Boot JAR in Docker)
- Base image: `bellsoft/liberica-openjre-alpine:21` (Alpine-based, minimal JRE)
- Exposed ports: 80, 9090, 9091, 50505 (`Dockerfile` line 7)
- Wirecard CA certificate injected into OS trust store and JVM `cacerts` at image build time (`Dockerfile` lines 19–27); cert file: `accountmanagementapi-boot/bindings/ca-certificates/nam.wirecard.sys.crt`
- Dynatrace APM injected via Kubernetes pod spec annotation (no code changes required per `Dockerfile` comment line 29)
- `docker-compose.yaml`: local dev mapping port 9313→80, profile `local`, external network `my-network`

### VM/Tomcat (Gen-2 path — WAR deployment)
- Target path: `D:\c-base\opt\tomcat\servers\AccountManagement\webapps` (Windows VM)
- Service name: `Apache Tomcat - AccountManagement` (Java 21) or `Apache Tomcat 8.5 AccountManagement` (Java 8)
- QA servers: `q-app01.nam.wirecard.sys`, `q-app02.nam.wirecard.sys`
- Production servers: `p-app01.nam.wirecard.sys`, `p-app02.nam.wirecard.sys`
- Backup path: `D:\c-base\backup`
- Deployment user (QA): `NAM\qa_east_deploy`; (Prod): `NAM\prod_east_deploy`
- WSDL published to external API Management (`PUBLISH_TO_APIM: true`, `EXTERNAL_APIM: true` in `deployment.yml` line 29)
- API suffix for APIM: `account-management-api`; backend suffix: `/services/AccountManagementApiWebServices`

## Configuration Management

- **Azure App Configuration**: Primary external config source. Endpoint from `AZURE_APP_CONFIG_ENDPOINT` env var. Key-filter: `accountmanagementapiws/<key>` with label = active Spring profile. Refresh interval: 15 minutes (configurable via `AZURE_APP_CONFIG_REFRESH_INTERVAL`). Fail-fast disabled.
- **Azure Key Vault**: Secrets resolved via Managed Identity (`AZURE_MANAGED_IDENTITY_CLIENT_ID`). Used for database passwords, Visa shared secret, KYC client secret, etc.
- **Local development**: Uses `AZURE_APP_CONFIG_CONNECTION_STRING` (connection string auth, no Managed Identity)
- **Classpath config files** (loaded in `application.yml`): `director-client.yaml`, `ecount-config.yaml`, `accountmanagementapi.yaml`, `api-security.yaml`, `APIValidation.properties`, `artifactInfo.yaml`, `banker.client.yaml`, `database.default.yaml`, `payment.yaml`, `sasi-defaults.yaml`, `service.default.yaml`, `service.monitor.default.yaml`, `service.yaml`, `version.yaml`
- **`from-app-config` convention**: Approximately 20+ properties use this placeholder in committed YAML files, indicating they must be present in Azure App Config for the service to function.
- **Key runtime environment variables** (not present in repo, expected at runtime):
  - `AZURE_APP_CONFIG_ENDPOINT`
  - `AZURE_MANAGED_IDENTITY_CLIENT_ID`
  - `SERVER_PORT` (default: 80)
  - `SERVER_CONTEXT_PATH` (default: `/`)
  - `SPRING_PROFILES_ACTIVE`
  - `ENDCLIENT_SERVICE_URL`, `ENDCLIENT_OAUTH_TOKEN_URL`, `ENDCLIENT_OAUTH_CLIENT_ID`, `ENDCLIENT_OAUTH_CLIENT_SECRET`, `ENDCLIENT_OAUTH_SCOPE`

## Observability

- **Health endpoint**: `/hc` — custom `HealthCheck` `@RestController` (`accountmanagementapi-boot/src/main/java/.../health/HealthCheck.java`) using `MonitorTestExecutor` infrastructure. Returns `"OK"` or `"DOWN"` string. Also Spring Actuator endpoints `health` and `info` exposed at `/actuator/health` and `/actuator/info`.
- **Logging**: Log4j2 (`spring-boot-starter-log4j2`). Root level ERROR; `com.citi` and `com.onbe` at DEBUG; `com.azure.spring.cloud.appconfiguration` at DEBUG; `org.springframework.cloud.bootstrap` at DEBUG. In legacy WAR, log4j config path: `${env:CBASE_HOME_URL}/config/accountmanagementapi/log4j2.xml`.
- **Audit tracing**: `GlobalRequestIDInterceptor` wraps `AccountManagementHandler` via AOP proxy, generating request IDs from `RequestAwareGlobalRequestIDGenerator` (app name: `account.mngmt`). `AuditMethodInterceptor` wraps both `AccountManagementHandler` (with statistics) and `SecurityValidator`.
- **MDC**: `Log4jMDCWriter` writes request context data to MDC for log correlation.
- **Action result logging**: `logActionResults()` in `AccountManagementApiServiceImpl` logs all action names, statuses, and sys codes at INFO per request.
- **Dynatrace**: Injected at pod level (Kubernetes sidecar/init container pattern) — no code instrumentation required.
- **Code coverage**: JaCoCo with Codecov integration (`code_cov_build.yml`). Postman integration tests run in Docker Compose (`docker-compose-test.yaml`) during the code coverage workflow.

## Infrastructure Dependencies

| Dependency | Type | Config Key | Notes |
|---|---|---|---|
| Order Service | HTTP Invoker (Spring Remoting) | `service.order.service.base.url` | Core transaction processing; `SynchronousOrderProcessor` with configurable timeout (`accountmanagementapi.order.synchronous.processor.client.timeoutMillis`) |
| EcountCore Database | SQL Server JDBC | `spring.datasource.ecountcore.url` | Promotions, card details, claimable flags |
| CbaseApp Database | SQL Server JDBC | `spring.datasource.cbaseapp.url` | Cardholder profiles, affiliate presentation |
| JobSvc Database | SQL Server JDBC | `spring.datasource.jobsvc.url` | Job manager / UserMapping |
| Banker Service | HTTP Invoker | `banker.client.yaml` | Balance retrieval; app ID=6, user ID=0 |
| Director Client | HTTP | `director-client.yaml` | xplatform director; `director-client-version=2.0.1` |
| ecount Agent (xplatform) | TCP/custom | `ecount.agent`, `ecount.config.system.defaultSystem.bootAddress` | Core ecount platform connectivity |
| Redis Cache | HTTP (admin service URL) | `redis.cacheservice.url` | Caching; `redisURL` injected into `AccountManagementHandlerImpl` |
| Azure App Configuration | HTTPS | `AZURE_APP_CONFIG_ENDPOINT` | Runtime configuration |
| Azure Key Vault | HTTPS | (via Managed Identity) | Secret management |
| End Client Service | HTTPS REST | `ENDCLIENT_SERVICE_URL` | KYC relationship validation; OAuth client-credentials |
| Azure AD / MSAL4J | HTTPS | `ENDCLIENT_OAUTH_TOKEN_URL` | OAuth token endpoint for End Client service |
| KYC Portal | HTTPS | `kyc.portal.url` | KYC portal (referenced in config, not in reviewed Java code) |
| Recipient Screening | HTTP | `cms.op.url`, `cms.recipient.ve.url` | OFAC screening post account creation |
| SMTP (Order Service notification) | SMTP | `service.order.notification.smtp.host` | Email notifications for fund loads |
| Wirecard NAM CA | TLS trust | `nam.wirecard.sys.crt` | Legacy internal CA required for Order Service communication |

## Operational Risks

1. **Dual deployment modes**: Two parallel deployment paths (Spring Boot JAR to Kubernetes, WAR to Windows Tomcat VMs) increase operational complexity and create risk of configuration drift between environments.
2. **10-minute DB query timeout**: Default JDBC timeout is 600 seconds for all three databases. Under heavy load or lock contention, threads can be held for 10 minutes, risking thread pool exhaustion.
3. **`allow-circular-references: true`**: Required in `application.yml` line 37, suggesting unresolved circular dependencies between Spring beans. This can mask initialization issues and indicates incomplete Spring Boot migration.
4. **`allow-bean-definition-overriding: true`**: Line 36 allows JNDI-sourced beans (legacy) to be overridden by Boot-defined beans. If ordering changes, JNDI beans may shadow Boot beans silently.
5. **Wirecard legacy CA certificate**: The Wirecard-branded CA cert suggests connectivity to legacy Wirecard/NAM infrastructure. If this cert expires or the CA is decommissioned, all Order Service connections would fail.
6. **No liveness probe distinct from health**: `/hc` endpoint runs active dependency checks. If a downstream (e.g., database) becomes slow, the liveness probe may fail and cause unnecessary pod restarts.
7. **Secret key hardcoded as default**: `jwe.secretKey` default in committed YAML is a secret management risk if Azure App Config override is missing (e.g., cold-start failure or config service outage).

## CI/CD

Four GitHub Actions workflows are present:

| Workflow | File | Trigger | Purpose |
|---|---|---|---|
| Shared Services Deployment | `deployment.yml` | Push/PR to `main` | Builds, tests (skip by default), publishes to APIM; delegates to `Onbe/om-ci-setup` reusable workflow |
| CI/CD Deployment | `cicd-deployment.yml` | Manual (`workflow_dispatch`) | Build + deploy to QA, optional promote to Production; supports Java 8 or 21 selection |
| VM Deployment | `vm-deployment.yml` | (present in repo) | Deploys WAR to Windows VMs via shared workflow |
| App Config | `app-config.yml` | (present in repo) | Azure App Configuration related |
| GitHub Packages Publish | `github-package-publish.yml` | Push/PR to `main`, manual | Publishes artifacts to GitHub Packages via `Onbe/om-ci-setup` Java package publish workflow |
| CodeQL | `codeql.yml` | Push/PR to `main`, weekly schedule (Friday 22:19 UTC) | Static analysis via GitHub CodeQL |
| Code Coverage | `code_cov_build.yml` | Push to `main`/`feature/code-coverage`, PR | Builds, runs integration tests via Docker Compose, generates JaCoCo report, uploads to Codecov |
| Redeploy | `redeploy.yaml` | (present in repo) | Targeted redeployment |
| Dependabot | `dependabot.yml` | Scheduled | Dependency update PRs |

Key observations:
- Tests are skipped by default in `cicd-deployment.yml` (`SKIP_TESTS` default: `false` but set to `-Dmaven.test.skip` in `deployment.yml` MAVEN_ARGS)
- Container scanning allowlist exists at `.github/containerscan/allowedlist.yaml`
- `.trivyignore` file present — some CVEs are suppressed
- Reusable workflows delegated to `Onbe/om-ci-setup` organization repository (centrally managed CI/CD templates)
- PACT contract testing configured (`PACT_PACTICIPANT: account-management-api`); provider verification disabled (`VERIFY_PROVIDER_PACT: false`)
