# api-security_SVC — DevOps & Operations View

## Build & Packaging

- **Build system**: Apache Maven, multi-module POM. Root artifact: `com.citi.prepaid.security:api-security:3.0.1` (`pom.xml`).
- **Java version**: Source and target set to Java 21 (`<maven.compiler.source>21</maven.compiler.source>`, root `pom.xml` line 31-32).
- **Maven wrapper**: `.mvn/wrapper/maven-wrapper.properties` present; custom `settings.xml` at `.mvn/wrapper/settings.xml` supplies corporate artifact repository credentials.
- **Modules**:
  - `api-security-lib` — packaged as JAR (`api-security-lib-3.0.1.jar`). Shared library consumed by all platform APIs.
  - `api-security-web` — packaged as WAR (`api-security-administration.war`). Administration UI deployed to Tomcat. `finalName` is `api-security-administration`.
- **Transitive dependency control**: `maven-enforcer-plugin` with `banTransitiveDependencies` rule active in both modules. Allowed exceptions explicitly listed (XStream, Spring, Log4j2 starter).
- **Test execution**: Tests are skipped in all CI pipelines (`-Dmaven.test.skip=true` in `.gitlab-ci.yml`, `-Dmaven.test.skip` in `github-package-publish.yml`). This means no automated test gate on deployments.

---

## Deployment

### Legacy (GitLab / on-premises Tomcat)
- **CI template**: `northlane/development/application-development/configuration/ci-templates/mavenMulti.gitlab-ci.yml`
- **Artefact**: `api-security-web` WAR deployed as `api-security-administration` under the `ServiceTester` Windows service.
- **Dev hosts**: `d-na-app01` on port `9507` (HTTPS).
- **QA hosts**: `q-na-app03`, `q-na-app04` on port `9507` (HTTPS).
- **Deployment protocol**: HTTPS (`SHARED_SERVICE_PROTO: https`).
- **Health check URI**: `/` at `SHARED_SERVICE_PORT`.

### Current (GitHub Actions / Onbe platform)
- **Workflow**: `.github/workflows/deployment.yml`, delegates to `Onbe/om-ci-setup/.github/workflows/java-workflow.yml@main`.
- **Triggers**: Push or PR to `master` or `feature/java-21-upgrade`.
- **APIM publishing**: `PUBLISH_TO_APIM: true`, `EXTERNAL_APIM: true` — WSDL/API descriptor is published to external APIM on every deployment.
- **Pact contract verification**: `VERIFY_PROVIDER_PACT: false` — provider contract verification is disabled.
- **Target root**: `./api-security_SVC-war`.
- **Backend path**: `/services/api-security_SVC`.
- **Dependency auto-update**: `UPDATE_DEPENDENCIES: true`, `UPDATE_PARENT_VERSION: true`.

### Package publish
- `.github/workflows/github-package-publish.yml` — publishes `api-security-lib` JAR to GitHub Packages on push to `main`. Supports manual dispatch with version override, dry-run, and auto-increment flags.

---

## Configuration Management

| Property | Source | Default / Notes |
|---|---|---|
| `api.security.entity.dao.timeout` | `default.database.properties` | `120` (seconds) |
| `api.security.entity.identification.dao.timeout` | `default.database.properties` | `120` (seconds) — note: a bug exists in `appCtx-APISecurityDAO.xml` line 24: timeout is `${api.security.entity.identification.dao.timeout}1000`, i.e. literal `1000` is appended, making the timeout `1201000` seconds |
| `api.security.host.dao.timeout` | `default.database.properties` | `120` (seconds) |
| `api.security.startup.registration` | `config.properties` | `NONE` (valid values: `NONE`, `REGISTER`, `UNREGISTER`) |
| `api.security.startup.registration.label` | Referenced in `appCtx-JMX-context.xml`; not set in `config.properties` | Must be supplied per deployment |
| `context.name` | `config.properties` | `api-security-administration` |
| `context.displayName` | `config.properties` | `API Security Administration` |
| `service.cbaseapp.database.default.timeout` | `config.properties` | `600` (seconds) |
| `CBASE_HOME_URL` | `config.properties` | `file:///d:/c-base` — hardcoded Windows path, a dev-environment artefact that must be overridden in all higher environments |
| `com.sun.management.jmxremote.port` | JVM system property | Required for distributed cache registration; no default; service silently skips JMX registration if absent |
| DataSource | JNDI: `jdbc/CbaseappDataSource` | Configured at Tomcat server level; not in application config |
| Spring context override | `systemPropertiesModeName: SYSTEM_PROPERTIES_MODE_OVERRIDE` | JVM system properties override `config.properties` values, allowing environment-specific injection |

---

## Observability

- **Logging framework**: SLF4J with Log4j2 backend (`log4j2-test.xml` present in test resources; production appenders not in source).
- **Audit log categories**: Dedicated logger per `AuditType`:
  - `security.api.audit.ACCESS_REQUESTED`
  - `security.api.audit.ENTITY_IDENTIFIED`
  - `security.api.audit.ACCESS_GRANTED`
  - `security.api.audit.ACCESS_DENIED`
- **Operational log statements**:
  - Cache load duration: `CacheEntityManager.load` logs duration at DEBUG.
  - JMX reload: `CacheJMXLoader.reload` logs at DEBUG; connection errors at WARN.
  - Host registration/unregistration: INFO and WARN.
  - Duplicate IP/certificate on load: WARN.
  - X-Forwarded-For header value: logged at INFO level on every request (`AuthenticationCheckFilter` line 45) — high-volume noise in production.
- **JMX MBean**: `prepaid:name=APISecurityManager` (registered in `appCtx-JMX-context.xml`). Exposes: `reload()`, `getLastUpdated()`, `getRegisterdDomains()`, `getEntityNames()`, `getEntityIdentifications(entityName)`, `getEntityDomains(entityName)`, `testAccess(...)`, `register()`, `unregister()`.
- **Health check**: No dedicated health check endpoint. Ops teams rely on Tomcat `/` response and JMX `getLastUpdated()` to assess node health.
- **Metrics**: No metrics instrumentation (no Micrometer, no Prometheus endpoint). Cache hit/miss rates, authorisation grant/deny ratios, and request latency are not tracked programmatically.
- **Log scanner tool**: `api-security-log-scanner` (`SecurityEvent.cs`, `SecurityEventParser.cs`) is a C# console application that parses structured audit log lines into CSV output. It is a developer/operations tool, not a deployed component. It parses fields: Date, IP, SubjectDN, IssuerDN, SerialNumber, Entity, API, METHOD, PROGRAM, Access, Reason, GRID.

---

## Infrastructure Dependencies

| Dependency | Type | Details |
|---|---|---|
| SQL Server `cbaseapp` | Required | JNDI DataSource. All entity, domain, IP, certificate, and host data. |
| Tomcat 8.5.x | Required | WAR deployment target. Windows service named `ServiceTester`. |
| JMX RMI port | Required for distributed cache | `com.sun.management.jmxremote.port` system property. Each node registers itself; no port is mandated — ops must configure. |
| `com.citi.prepaid.spring-dbctx` | Internal library | `spring-dbctx-container` (runtime) and `spring-dbctx-mock` (test). Provides the `CbaseappDataSource` Spring bean wiring. Version `2.0.1`. |
| `com.citi.prepaid.springutils:springutils-generic` | Internal library | Version `3.0.2`. Used in `api-security-web` for the `StaticContext`/`StaticMethodLoader` admin UI framework (`com.ecount.service.tester`). |
| `com.thoughtworks.xstream:xstream` | Third-party | Version `1.4.20`. Used for XML serialisation of admin request/response objects. Three CVEs suppressed in `allowedlist.yaml`: CVE-2018-1000632, CVE-2020-10683, CVE-2024-22259. |
| `com.microsoft.sqlserver:mssql-jdbc` | Third-party | Provided scope (supplied by Tomcat). |
| `jakarta.servlet-api` | Third-party | Provided scope. Jakarta EE 9+ namespace. |
| Spring Framework | Third-party | `spring-context`, `spring-jdbc`. Version managed by parent POM `prepaid-parent:6.0.12`. |

---

## Operational Risks

1. **DAO timeout bug**: `appCtx-APISecurityDAO.xml` line 24 sets the entity identification DAO timeout to `${api.security.entity.identification.dao.timeout}1000`, meaning the literal string `1000` is concatenated to the property value. With `default.database.properties` setting `120`, the effective timeout becomes `1201000` seconds (~14 days), effectively disabled. This means hanging database queries on that DAO will never time out.
2. **Test skipping**: All CI pipelines skip tests. Regressions in security logic will not be caught until runtime.
3. **Manual cache reload required**: There is no automatic TTL-based cache expiry. If an access record is modified in the database (e.g., an entity's access is revoked), runtime nodes continue to grant access until a human operator initiates a cache reload. No alerting exists for cache staleness.
4. **JMX is unauthenticated**: Any host with network access to the JMX port can reload the cache, alter domain registrations, or simulate access decisions. No JMX authentication environment is configured.
5. **`CBASE_HOME_URL` hardcoded**: `file:///d:/c-base` in `config.properties` is a developer laptop path. If not overridden in production, the application may fail to locate required resources.
6. **Single shared DataSource**: All modules share the single `CbaseappDataSource`. A connection pool exhaustion or database outage takes down both the admin UI and the runtime security validation for all platform APIs simultaneously.
7. **Windows-only operational tooling**: `api-security-certificate-reader` (WinForms, `System.Deployment.Application`) and `api-security-log-scanner` are Windows-only tools. They depend on the now-deprecated ClickOnce deployment API and have no automated build or test pipelines.
8. **INFO-level X-Forwarded-For logging**: Every inbound request logs the `X-Forwarded-For` header value at INFO level (`AuthenticationCheckFilter` line 45). At high request volumes this generates significant log noise and may expose client IP data in log aggregation systems with insufficient access controls.

---

## CI/CD

| Pipeline | Platform | Trigger | Key Actions |
|---|---|---|---|
| `deployment.yml` | GitHub Actions | Push/PR to `master`, `feature/java-21-upgrade` | Maven build, publish WAR to APIM (external), auto-update dependencies and parent POM version |
| `github-package-publish.yml` | GitHub Actions | Push to `main`; manual dispatch | Publish JAR to GitHub Packages; supports dry-run, version override |
| `codeql.yml` | GitHub Actions | Push/PR to `master`/`feature/java-21-upgrade`; weekly schedule (Fri 22:19) | CodeQL static analysis on Java source |
| `dependabot.yml` | GitHub Dependabot | Weekly | Automated Maven dependency version PRs |
| `.gitlab-ci.yml` | GitLab CI | (Legacy) | Maven build, deploy WAR to on-premises Tomcat on `d-na-app01` (dev) and `q-na-app03/04` (QA) |

Observations:
- Two parallel CI systems (GitHub Actions and GitLab) with overlapping responsibilities. The GitLab pipeline targets different branches (`master`) and different deployment hosts, indicating a migration in progress.
- `master` and `main` branch names both appear — the GitHub Actions deployment workflow targets `master` while the package publish targets `main`. This inconsistency may cause missed deployments or duplicate releases.
- No integration, contract, or performance test stage in any pipeline.
- Container scanning allowlist (`allowedlist.yaml`) suppresses three XStream CVEs globally; this requires documented risk acceptance.
