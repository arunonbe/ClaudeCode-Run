# banker_API — DevOps & Operations View

## Build & Packaging

- **Build tool**: Apache Maven 3.x. Parent POM (`pom.xml`) declares Java 21 compiler target/source (`maven.compiler.target=21`, `maven.compiler.source=21`).
- **Parent POM**: `com.parents:prepaid-parent:6.0.13`. Internal Onbe/eCount parent that manages shared dependency versions.
- **Module structure**:
  - `banker-common` → JAR (DTOs, API interface, exceptions, client-side Spring XML)
  - `banker-impl` → JAR (business logic, DAO implementations)
  - `banker-service` → WAR (`banker-service.war`, the deployable artifact)
  - `banker-tester` → commented out in parent POM (`<!--<module>banker-tester</module>-->`)
- **Build command**: `mvn clean install -Dmaven.test.skip` (from README; tests are skipped in all CI configurations).
- **Version**: `4.0.4-SNAPSHOT` at time of analysis.
- **Key runtime JARs copied to Tomcat lib** (via `maven-dependency-plugin` in `banker-service/pom.xml`):
  - `commons-discovery:0.2`, `commons-logging:1.1.1` (Axis requirements)
  - `slf4j-api`, `log4j-api`, `log4j-core`
  - `mssql-jdbc:12.5.0.jre11-preview` (SQL Server JDBC driver)
  - `HikariCP:5.1.0` (connection pooling)
- **Maven settings**: `.mvn/wrapper/settings.xml` is passed via `-s ./.mvn/wrapper/settings.xml` in CI, providing access to internal artifact repositories.
- **Dependabot**: Weekly Maven dependency update PRs are configured (`.github/dependabot.yml`).

## Deployment

- **Container**: Docker image based on `bellsoft/liberica-openjre-alpine:21` (Alpine Linux, OpenJRE 21).
- **Application server**: Apache Tomcat 10.1.28, downloaded at image build time from the Apache archive (`Dockerfile` lines 7–12).
- **WAR deployment**: `banker-service.war` is copied to `/opt/tomcat/webapps/`.
- **Port**: Container exposes port 80 (HTTP only, no TLS at container level).
- **CBASE_HOME_URL**: Environment variable set to `file:///cbase` in the Dockerfile. At runtime this is overridden to point to a mounted config volume.
- **Config volume**: Docker Compose (`docker-compose.yaml`) mounts `${CONFIG_DIR}:/cbase/config`, making external configuration files (properties, log4j2.xml, certificates) available to the application.
- **JVM flags**: `--add-opens` flags set for `java.base` and `java.rmi` packages to allow reflective access needed by Axis/SOAP (`Dockerfile` line 25).
- **Target environment**: AKS (Azure Kubernetes Service). Deployment workflow references `Onbe/om-cd-setup` and `Onbe/om-ci-setup` shared workflow repos.
- **Legacy deployment** (from `.gitlab-ci.yml`): Previously deployed to Windows/Linux servers — `d-na-app03` (dev) and `q-na-app03`, `q-na-app04` (QA) — under Tomcat on port 9009. This is the legacy GitLab-era configuration.
- **Service name in legacy**: `Banker` (Windows service name), `banker-service` (WAR context path).

## Configuration Management

All runtime configuration is externalized via the `CBASE_HOME_URL` environment variable pointing to a mounted directory:

| File | Path | Purpose |
|---|---|---|
| `director-client.properties` | `${CBASE_HOME_URL}/config/director-client.properties` | Director service address (`director.address`) |
| `banker.properties` | `${CBASE_HOME_URL}/config/service/banker/banker.properties` | DB names (`database.banker`, `database.user`), agent IDs (`agent`, `agent.banker`, `agent.gp`), role strings, preset fund defaults (`preset.funds.config.ratio.percent`, `preset.funds.config.base.amount`) |
| `banker.client.properties` | `${CBASE_HOME_URL}/config/service/banker/banker.client.properties` | Client-side: WSDL URL (`banker.service.wsdl.url`), connection timeout (`banker.service.timeout`) |
| `log4j2.xml` | `${CBASE_HOME_URL}/config/service/banker/log4j2.xml` | Logging configuration; refresh interval 300,000 ms (5 minutes, set in `web.xml` line 21) |

Key properties inferred from Spring XML bean definitions:
- `agent` — Main eCountCore/cbaseapp agent name
- `agent.banker` — Banker DB agent name
- `agent.gp` — Great Plains DB agent name
- `database.banker` — Banker DB name
- `database.user` — User/cbaseapp DB name
- `banker.role.auth.force`, `banker.role.settle.force`, `banker.role.minimum.level`, `banker.role.update.financedatasources` — Role name strings injected into `BankerRoleSetting`
- `preset.funds.config.ratio.percent`, `preset.funds.config.base.amount` — Preset fund calculation defaults

No secrets or credentials appear in source code. Database credentials are managed by the Director service.

## Observability

- **Logging**: Log4j2 via SLF4J with Lombok `@Slf4j` annotations. Debug-level logs emit detailed DTO state (via XStream XML) on every action enter/exit. Error-level logs capture exceptions.
- **Log file**: Location is configured in `log4j2.xml` (external). Tomcat access logs are written to `/opt/tomcat/logs/localhost_access_log*.txt` in combined format (per `server.xml` valve configuration).
- **Health check endpoint**: `GET /hc` returns `"OK"` (HTTP 200) via `HealthCheck.java` (`com.onbe.banker.health.HealthCheck`). This is the Kubernetes liveness/readiness probe endpoint.
- **Metrics**: No metrics framework (Micrometer, Prometheus, etc.) is present in the codebase. There are no `@Timed` or `@Counted` annotations. Observability beyond logs is absent.
- **Tracing**: No distributed tracing (no OpenTelemetry, no Sleuth). Correlation IDs must be tracked externally or via log correlation.
- **AOP audit interceptor**: `BankerAuditMethodInterceptor` (`com.ecount.springutils.aop.AuditMethodInterceptor`) is applied to all `BankerServiceManagerImpl` and `PresetFundsConfig` methods via AOP pointcuts (`banker-core.xml` lines 48–58). The actual audit behavior is in the `springutils-generic` library (external).
- **AOP exception interceptor**: `BankerExceptionMethodInterceptor` (`com.ecount.service.banker.util.BankerMethodExceptionInterceptor`) wraps all `BankerServiceManagerImpl` methods for exception handling/logging.

## Infrastructure Dependencies

| Dependency | Type | Purpose | Criticality |
|---|---|---|---|
| Director service | Internal service discovery | Provides JDBC datasource references for all three DBs | Critical — no datasources without it |
| SQL Server (Banker DB) | Database | Reserved sources, preset configs, approval notifications, program datasource mappings | Critical |
| SQL Server (User DB / cbaseapp) | Database | User and role lookups | Critical — every auth call requires it |
| SQL Server (Great Plains) | Database (multiple instances, per-program routing) | All financial data (free funds, promotions, documents, payments) | Critical |
| eCountCore / xplatform | Internal platform library | Profile services (currency, locale, program/relationship managers), notification delivery (`NotificationManagerImpl`) | Required for approval notifications and currency multiplier |
| Apache Axis 1.4 | SOAP framework (Jakarta port) | SOAP service endpoint and client proxy | Critical — the entire API layer |
| Spring Framework | IoC / AOP / JDBC | Container, transaction management, stored procedure wrappers | Critical |
| Email / notification service | Via `NotificationManagerImpl` from eCountCore | Sends approval notification emails | Required for escalation flow |
| AKS / Kubernetes | Container orchestration | Runtime environment | Critical |
| `qa.nam.wirecard.sys` / `ppnaut.nam.wirecard.sys` | Legacy DNS entries | Wired directly in `docker-compose.yaml` `extra_hosts` | QA environment only |

## Operational Risks

1. **No automated test execution**: All CI/CD pipelines pass `-Dmaven.test.skip` (`.gitlab-ci.yml` and `github-package-publish.yml`). Test infrastructure exists (XML test context files in `banker-impl/src/test/resources`) but is never run in CI. Regressions are not caught automatically.

2. **Stale in-memory cache**: The maps loaded at startup (`outstandingPaymentsProgramPromoMap`, `userGroupCodeAuthorizationAmountLimitsMap`, `bankerDefaultPromoExceptionPrograms`) are never refreshed without a service restart. Changes to DB configuration take effect only after a pod restart or redeployment.

3. **Singleton state shared across threads**: `BankerServiceManagerImpl.getInstance()` returns a static singleton (`line 132–136`). Concurrent modifications to in-memory maps require `synchronized` methods. `PresetFundsConfig.findPresetFundsConfigDTO()` and `setPresetFundsConfig()` are synchronized but the lazy DB refresh path within a synchronized call could create a bottleneck.

4. **Axis 1.4 (2006 vintage)**: The WSDL was generated by "Apache Axis version: 1.4, Built on Apr 22, 2006" (as noted in `wsdl.xml` line 3). This is an extremely old SOAP framework. The Jakarta port (`jakarta-axis`) is being used to make it work with Jakarta EE 6.0, but Axis 1.4 is not maintained.

5. **Plain HTTP**: The service runs on port 80 without TLS at the application level. Financial transaction data traverses unencrypted unless AKS ingress/service mesh provides TLS. A misconfigured ingress could expose SOAP traffic in plaintext.

6. **120-second transaction timeout**: `banker-transaction.xml` sets `timeout="120"` on all banker transactions. Long-running GP queries (especially `banker_get_all_unsettled_funds` on large programs) could consume threads for up to 2 minutes.

7. **Docker image downloads Tomcat from Apache archive at build time**: `Dockerfile` line 8 fetches Tomcat 10.1.28 from `archive.apache.org` during `docker build`. Build failures occur if the archive URL is unreachable or the version is removed.

## CI/CD

### GitHub Actions Pipelines

| Workflow | File | Trigger | Action |
|---|---|---|---|
| Deploy | `.github/workflows/deployment.yml` | Push/PR to `main` | Calls `Onbe/om-ci-setup/.github/workflows/java-workflow.yml@main`; builds, optionally verifies Pact, publishes WSDL to APIM, deploys to AKS |
| Package Publish | `.github/workflows/github-package-publish.yml` | Push to `main`, PR to `main`, `workflow_dispatch` | Builds and publishes JARs to GitHub Packages |
| CodeQL | `.github/workflows/codeql.yml` | Weekly (Friday 17:53 UTC), `workflow_dispatch` | Static analysis via `Onbe/om-ci-setup/.github/workflows/codeql-auto.yml@main` |
| Redeploy QA | `.github/workflows/redeploy.yaml` | `workflow_dispatch` only | Redeploys `bankerapi` to QA AKS environment via `Onbe/om-cd-setup/.github/workflows/redeploy.yaml@main` |

### Key CI/CD Observations
- `PUBLISH_TO_APIM: true`, `INTERNAL_APIM: true`, `EXTERNAL_APIM: false` — The WSDL is published to an internal API management gateway on deploy.
- `BACKEND_SUFFIX: "/banker-service/Banker/bankerServiceAPI"` — This is the SOAP endpoint path registered in APIM.
- `EXCLUDE_STAGE: true` — Staging environment is skipped; code goes directly from QA to production.
- `USE_ROLLOUT_CONFIG: true` — Progressive rollout is configured in AKS.
- `VERIFY_PROVIDER_PACT: false` — Banker is a PACT provider for some consumers but provider PACT verification is disabled.
- All Maven builds use `-s ./.mvn/wrapper/settings.xml` to access internal artifact repositories.

### Legacy GitLab CI
`.gitlab-ci.yml` references a GitLab CI template (`northlane/development/...`) for the pre-GitHub migration pipeline targeting Windows servers. This file is present but no longer active.
