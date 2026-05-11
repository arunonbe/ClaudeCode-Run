# accept-prechecks_API — DevOps & Operations View

## Build & Packaging

- **Build tool**: Apache Maven with Maven Wrapper (`mvnw` / `mvnw.cmd`), Maven Wrapper version pinned in `.mvn/wrapper/maven-wrapper.properties`.
- **Parent POM**: `com.parents:prepaid-parent:6.0.13` — an internal Onbe/ecount parent POM not in this repository; sourced from a private Maven registry configured in `.mvn/wrapper/settings.xml`.
- **Java version**: 21 (`maven.compiler.source/target = 21`); runtime image `bellsoft/liberica-openjre-alpine:21`.
- **Spring Boot version**: `3.5.7` (root `pom.xml` line 35); Spring Cloud `2025.0.0`; Spring Cloud Azure `5.23.0`.
- **Module structure** (three Maven modules):
  - `accept-prechecks-ws` → JAR (business logic, SOAP service, validators)
  - `accept-prechecks-war` → WAR (legacy Tomcat deployment artifact, depends on ws JAR)
  - `accept-prechecks-boot` → Fat JAR / Spring Boot (modern container deployment, depends on ws JAR)
- **Final artifact name**: `acceptprechecks` (set via `<finalName>${deployment.name}</finalName>` in both war and boot POMs).
- **Test skip**: All CI/CD pipeline calls (`deployment.yml`, `github-package-publish.yml`, `.gitlab-ci.yml`) pass `-Dmaven.test.skip` or `MAVEN_TEST_OPTS="-Dmaven.test.skip=true"`. Tests are skipped in every automated pipeline run.
- **Dependency enforcement**: `maven-enforcer-plugin` with `requireReleaseDeps` at root level (no SNAPSHOTs allowed, except for intra-project modules). The boot module has `<fail>false</fail>` on the transitive-deps rule, effectively disabling it.
- **Code coverage**: JaCoCo `0.8.12` configured in ws and war modules. Coverage report upload to Codecov via `code_cov_build.yml`, but this workflow only runs on `main` / `feature/code-coverage` branches and uses the WAR module (legacy path).

## Deployment

### Container / Kubernetes (current path — `accept-prechecks-boot`)
- **Base image**: `bellsoft/liberica-openjre-alpine:21` (`Dockerfile` line 1).
- **Exposed ports**: 80 (HTTP), 9090, 9091, 50505 (`Dockerfile` line 5). Port 9090/9091 suggest Dynatrace agent ports.
- **Entry point**: `java -jar ./app.jar` with no JVM tuning flags (commented-out `JAVA_ARGS=-Xms512m -Xmx2048m`).
- **CA certificate injection**: `nam.wirecard.sys.crt` is copied into the Alpine OS trust store and the JVM cacerts (`Dockerfile` lines 18–25) using hardcoded storepass `changeit`.
- **Dynatrace**: Comment in Dockerfile states "injected when the pod is deployed to K8S" — no explicit configuration file.
- **Kubernetes deployment**: Via `Onbe/om-cd-setup` reusable workflow. Application name: `acceptprechecksapi`. Redeploy workflow (`redeploy.yaml`) targets `qa` environment only.
- **Context path**: Configurable via `SERVER_CONTEXT_PATH` env var (default `/`).
- **Docker Compose (local dev)**: `docker-compose.yaml` maps port `9302:80`, sets `SPRING_PROFILES_ACTIVE=local`.

### Legacy WAR / Tomcat (historical path — `accept-prechecks-war`)
- **Target servers (GitLab CI)**: `d-na-app02` (DEV), `q-na-app01`, `q-na-app02` (QA) — from `.gitlab-ci.yml`.
- **Service URI**: `/acceptprechecks/AcceptPrecheckService?wsdl`
- **Context**: Deployed under `/acceptprechecks` context path (`META-INF/context.xml`).
- **JNDI resource**: `jdbc/EcountCoreDataSource` linked via Tomcat `ResourceLink`.
- **Log4j2 config**: Loaded from `${env:CBASE_HOME_URL}/config/AcceptPrechecks/log4j2.xml` (environment-variable-based external config, `web.xml` line 17).
- **App config**: Loaded from `${CBASE_HOME_URL}/config/AcceptPrechecks/AcceptPrechecks.properties` (`applicationContext.xml` line 10).

## Configuration Management

- **Azure App Configuration**: Centralised configuration via `spring-cloud-azure-appconfiguration-config-web`. Key prefix: `acceptprechecksws/`, with label per active Spring profile. Refresh interval: `AZURE_APP_CONFIG_REFRESH_INTERVAL` (default 15 minutes, `bootstrap.yaml` line 9).
- **Azure Key Vault**: Secrets injected at startup via `spring-cloud-azure-starter-keyvault-secrets`.
- **Profile handling**:
  - `local` profile: uses `AZURE_APP_CONFIG_CONNECTION_STRING` (connection string auth, no managed identity).
  - Non-local: uses `AZURE_MANAGED_IDENTITY_CLIENT_ID` for all Azure auth.
- **App Config publishing**: Workflow `app-config.yml` publishes changes from the `app-config/` directory to Azure App Configuration under prefix `acceptprechecksws`, with label `staging`. Triggered on push to `main` or any `feature/**` branch.
- **Placeholder values in application.yml**: `url-from-app-config`, `username-from-app-config`, `password-from-app-config`, `from-app-config` are sentinel values indicating all runtime config comes from Azure App Config / Key Vault — nothing is environment-specific in the shipped JAR.
- **Axis configuration**: `server-config.wsdd` is resolved at startup via `System.setProperty("axis.ServerConfigFile", "server-config.wsdd")` and `axis.home` set to servlet context real path (`WebConfiguration.java` lines 104–107).

## Observability

- **Health check**: `GET /hc` returns `"OK"` (`HealthCheck.java`). Spring Boot Actuator also exposes `/actuator/health` and `/actuator/info` (`application.yml` lines 49–52).
- **Logging**: Log4j2 via `spring-boot-starter-log4j2`. Root level: ERROR; `com.ecount`, `com.onbe`, `com.citi` at DEBUG; Spring at ERROR. No structured/JSON logging configuration observed in this repository.
- **Performance timing**: `PerformanceFilter` is registered for `/AcceptPrecheckService` but the `doFilter` method only delegates to the chain — it performs no timing measurement (the `StopWatch` is in `AcceptPrecheckServiceImpl.acceptPrecheck()` at lines 55–73, logging elapsed time at INFO).
- **Dynatrace APM**: Injected by Kubernetes infrastructure, not by this application.
- **No distributed tracing**: No Sleuth, Zipkin, or OpenTelemetry dependency found.
- **No metrics endpoint beyond Actuator**: No Micrometer/Prometheus configuration found.

## Infrastructure Dependencies

| Dependency | Type | Address (UAT from .env_bkp) |
|---|---|---|
| ecount Core dispatch service | HTTP (xplatform) | `https://uat.nam.wirecard.sys:8080/service/dispatch.asp` |
| ecount Order service | HTTP | `https://uat.nam.wirecard.sys:9003/order/OrderService` |
| SQL Server — cbaseapp | JDBC (SQL Server) | `u-lis-db01.nam.wirecard.sys:2231;database=cbaseapp` |
| SQL Server — ecountcore | JDBC (SQL Server) | `u-lis-db02.nam.wirecard.sys:2231;database=ecountcore` |
| SQL Server — jobsvc | JDBC (SQL Server) | `u-lis-db01.nam.wirecard.sys:2231;database=jobsvc` |
| Azure App Configuration | HTTPS | `as-app-configuration.azconfig.io` (from .env_bkp) |
| Azure Key Vault | HTTPS | Endpoint injected via Managed Identity |
| Internal Maven registry | HTTPS | Configured in `.mvn/wrapper/settings.xml` |
| Onbe GitHub Actions reusable workflows | GitHub | `Onbe/om-ci-setup`, `Onbe/om-cd-setup` |

All database hosts use the legacy `nam.wirecard.sys` domain (Wirecard/Payscout heritage infrastructure).

## Operational Risks

1. **Tests always skipped**: Every pipeline configuration skips unit and integration tests. Regressions will not be caught in CI. The real test coverage path (`code_cov_build.yml`) is a separate opt-in workflow, not part of the main deployment gate.
2. **No JVM heap configuration**: `JAVA_ARGS` in Dockerfile is commented out. The container runs with default JVM ergonomics, which may be inappropriate for the container memory limit.
3. **storepass "changeit" in Dockerfile**: The JVM truststore password is the default `changeit`, hardcoded visibly in the Dockerfile (line 24). This is a low-severity but documented security antipattern.
4. **WAR module references preview JDBC driver**: `accept-prechecks-war/pom.xml` line 129 references `mssql-jdbc:12.5.0.jre11-preview` — a preview/pre-release driver version. The boot module correctly uses `12.8.2.jre11`.
5. **PerformanceFilter is a no-op**: The filter is registered and mapped to `/AcceptPrecheckService` but performs no useful work (no timing, no logging, no throttling). It exists as dead infrastructure code.
6. **`allow-circular-references: true`**: Enabled in `application.yml` line 26. This is a Spring Boot antipattern and may indicate wiring issues that should be resolved.
7. **`allow-bean-definition-overriding: true`**: Enabled in `application.yml` line 24. This can cause silent bean replacement, masking configuration errors.
8. **Axis `adminPassword` is "admin"**: `server-config.wsdd` line 6 sets `adminPassword` to `admin`. The `AdminService` has `enableRemoteAdmin=false`, which mitigates this, but the password is still exposed in configuration.
9. **`fail-fast: false` on Azure App Config**: Both `bootstrap.yaml` store configs use `fail-fast: false`, meaning the application will start even if Azure App Config is unreachable, with placeholder values.

## CI/CD

### GitHub Actions Pipelines

| Workflow File | Trigger | Purpose |
|---|---|---|
| `deployment.yml` | Push / PR to `main` | Main build and deploy; calls `Onbe/om-ci-setup/java-workflow.yml@main` |
| `app-config.yml` | Push to `main` or `feature/**` (changes in `app-config/`) | Publishes Azure App Config entries |
| `code_cov_build.yml` | Push to `main` / `feature/code-coverage`, manual | Build + integration tests (docker-compose) + JaCoCo + Codecov |
| `codeql.yml` | Weekly (Fri 17:53 UTC) + manual | SAST via CodeQL (`Onbe/om-ci-setup/codeql-auto.yml@main`) |
| `github-package-publish.yml` | Push to `main`, PR to `main`, manual | Publishes JAR to GitHub Packages |
| `redeploy.yaml` | Manual only | Redeploys `acceptprechecksapi` to QA AKS |

### Legacy GitLab CI
`.gitlab-ci.yml` includes `northlane/development/.../maven.gitlab-ci.yml` and defines DEV/QA Tomcat host targets. This appears to be the pre-Kubernetes deployment pipeline, still present in the repository. Tests are skipped (`-Dmaven.test.skip=true`).

### APIM Publishing
`deployment.yml` sets `PUBLISH_TO_APIM: true`, `EXTERNAL_APIM: true`, `INTERNAL_APIM: false`. The `wsdl.xml` at the repository root is published to the external Azure API Management gateway. Note: the root `wsdl.xml` is a generic placeholder (`targetNamespace="http://example.com/soap"` with `GenericOperation`) — it does not match the actual `AcceptPrecheckService.wsdl`. This means the APIM-published contract is incorrect.

### Pact Contract Testing
`deployment.yml` sets `PACT_PACTICIPANT: accept-prechecks-api` and `VERIFY_PROVIDER_PACT: false`. Consumer-driven contract testing is configured as a participant but provider verification is disabled.

### Dependabot
Weekly Maven dependency updates configured (`dependabot.yml`).
