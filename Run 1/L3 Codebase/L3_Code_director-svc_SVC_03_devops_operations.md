# Director SVC — DevOps / Operations View

## 1. Build System

- **Build tool**: Apache Maven (wrapper `mvnw` / `mvnw.cmd`; Maven Wrapper properties at `.mvn/wrapper/maven-wrapper.properties`)
- **Java version**: 21 (compiler source/target in root `pom.xml:26-27`)
- **Parent POM**: `com.parents:prepaid-parent:6.0.12` (internal Onbe artifact, not in public Maven Central)
- **Module structure**:

| Module | Artifact ID | Packaging | Purpose |
|---|---|---|---|
| `Directory-Common` | `directory-common` | `jar` | Shared API: `IDirectoryService`, `GetOutput`, `ConfigException` |
| `Directory-Service` | `directory-service` | `jar` | Core implementations: `JNAWinUtil`, `DirectoryImpl`, `AzureDirectoryImpl`; migration utilities |
| `Directory-War` | `directory-war` | `war` | Tomcat WAR deployment: servlet config, `web.xml`, Spring MVC wiring, `PropertyConfig` |
| `Directory-SpringBootApp` | `directory-springbootapp` | `jar` (exec) | Spring Boot fat-jar for containerised/AKS deployment |

- **Artifact repository**: GitHub Packages (`https://maven.pkg.github.com/onbe/onbe_maven_releases`) — configured in `.mvn/wrapper/settings.xml`. Authentication via `GITHUB_TOKEN` environment variable.
- **Build command**: `mvn clean install -Dmaven.test.skip -s ./.mvn/wrapper/settings.xml`
- **Final WAR name**: `directory-webapp` (set via `<deployment.name>` property, `pom.xml:29`)
- **Final Spring Boot JAR name**: `directory-springbootapp-exec.jar` (exec classifier)
- **Enforcer plugin** is active on all modules: no snapshot dependencies (except whitelisted internal artifacts), and `banTransitiveDependencies` rules are applied per-module.

---

## 2. Deployment Models

### Legacy: Tomcat WAR (Gen-1, on-premises Windows)
- Deployed to Tomcat 10.x.x+ as `directory-webapp.war` under the `Directory-War` module.
- Tomcat `server.xml` (`Directory-War/config/server.xml`) configures:
  - Shutdown port `8005`
  - HTTP connector on port `80`, redirect port `8443`
  - No HTTPS connector defined (potential misconfiguration — TLS termination presumably at load balancer)
  - `autoDeploy="false"` on the Host — deployments are manual
- QA host identified in `.gitlab-ci.yml`: `q-na-app12`
- Dev host: `d-na-app01`
- Service health URI (from `.gitlab-ci.yml`): `http://host:8080/service/dispatch.asp`
- TLS certificate for QA: `Directory-War/config/certfile_qa.crt`
- Config file location driven by `CBASE_HOME_URL` environment variable: `${CBASE_HOME_URL}/config/service/directory/directory.properties` (`PropertyConfig.java:22`)
- Log4j2 config location: `${CBASE_HOME_URL}/config/service/directory/log4j2.xml` (`web.xml:13`)
- Legacy GitLab CI pipeline is defined in `.gitlab-ci.yml` (references Northlane/Wirecard-era CI templates)

### Current: Spring Boot Container / AKS (Gen-2)
- Container built from `Directory-SpringBootApp/Dockerfile`:
  - Base image: `bellsoft/liberica-openjre-alpine:21`
  - Exposes port `80`
  - JVM args: `-Xms512m -Xmx2048m`
  - Entry: `java -jar ./directory-springbootapp-exec.jar`
- Docker Compose (`docker-compose.yaml`) for local dev: maps host `8080` → container `80`, injects `SPRING_PROFILES_ACTIVE`, `AZURE_APP_CONFIG_CONNECTION_STRING`, and mounts `${CONFIG_DIR}` to `/cbase/config`
- QA AKS deployment via `redeploy.yaml` workflow: calls reusable workflow at `Onbe/om-cd-setup/.github/workflows/redeploy.yaml@main` with `application-name: "directorsvc"`, `environment: "qa"`
- XML-RPC servlet registered in `XmlrpcConfig.java` at `/service/dispatch.asp` (line 17)
- Health check endpoint: `GET /hc` → returns `"OK"` (`HealthCheck.java`); also Spring Actuator at `/hc` via `application.properties`
- Default server port: `${SERVER_PORT:8080}` from `application.properties`

---

## 3. Configuration Management

| Config Item | Source | Notes |
|---|---|---|
| Spring profile (`dev`/`qa`/`staging`/`prod`) | `SPRING_PROFILES_ACTIVE` env var | Controls which `AzureConfig` bean is created |
| Azure App Config connection string (dev) | `AZURE_APP_CONFIG_CONNECTION_STRING` env var | Secret — should be in vault, not docker-compose |
| Azure App Config endpoint (qa+) | `AZURE_APP_CONFIG_ENDPOINT` env var | |
| Azure Managed Identity client ID (qa+) | `AZURE_MANAGED_IDENTITY_CLIENT_ID` env var | |
| Tomcat config path (WAR) | `CBASE_HOME_URL` env var | Path prefix for `directory.properties` and `log4j2.xml` |
| Server port | `SERVER_PORT` env var (default 8080) | |
| Application config data | `app-config/qa/appsettings.json` | Published to Azure App Config via `app-config.yml` on push to `main` |

---

## 4. CI/CD Pipelines

### GitHub Actions (current)

| Workflow File | Trigger | Purpose |
|---|---|---|
| `.github/workflows/deployment.yml` | Push/PR to `main` | Build + deploy via reusable `Onbe/om-ci-setup/.github/workflows/java-workflow.yml@main`. Targets `Directory-SpringBootApp`, publishes backend URL `/dispatch.asp`, uses rollout config, skips container scan |
| `.github/workflows/github-package-publish.yml` | Push to `main`, workflow_dispatch | Publishes Maven artifacts to GitHub Packages via `java-package-publish.yml@main` |
| `.github/workflows/app-config.yml` | Push to `main` affecting `app-config/**` | Publishes `app-config/qa/appsettings.json` contents to Azure App Config with prefix `DirectorySVCAPI` |
| `.github/workflows/redeploy.yaml` | `workflow_dispatch` | Manually re-deploys `directorsvc` to QA AKS |
| `.github/workflows/codeql.yml` | Weekly schedule (Fri 17:53 UTC), workflow_dispatch | CodeQL security analysis |

### GitLab CI (legacy, still present)

`.gitlab-ci.yml` references `northlane/development/application-development/configuration/ci-templates/maven.gitlab-ci.yml` — a legacy Wirecard/Northlane-era template. Still lists dev and QA WAR deployment hosts (`d-na-app01`, `q-na-app12`). This file should be considered a deployment risk if both CI systems are active simultaneously.

### Dependency Updates
- `dependabot.yml` configured for weekly Maven dependency updates.
- `deployment.yml` sets `UPDATE_DEPENDENCIES: true` and `UPDATE_PARENT_VERSION: true` — the CI pipeline auto-updates parent POM version on deployment.

---

## 5. Observability

| Concern | Finding |
|---|---|
| **Logging framework** | Log4j2 (via `log4j-1.2-api` bridge for legacy `commons-logging` calls). Log config is external to the WAR (`${CBASE_HOME_URL}/config/service/directory/log4j2.xml`). For Spring Boot, `log4j2-test.xml` in test resources shows console-only appender. |
| **Log refresh interval** | 300,000 ms (5 minutes) — set in `web.xml:31` |
| **Health check** | `/hc` endpoint returns `"OK"` (HTTP 200). Spring Actuator exposes `health` and `info` endpoints at `/hc`. No liveness/readiness distinction evident. |
| **Metrics** | No metrics instrumentation found. Spring Actuator is included but only `health` and `info` are exposed (`application.properties:6`). No Micrometer or Prometheus endpoint. |
| **Tracing** | `GlobalRequestIDInterceptor` / `UUIDGlobalRequestIDGenerator` generates a UUID per request and writes it to the Log4j MDC (`Log4jMDCWriter`). App name set to `"directorsvc"`. No distributed tracing (no Zipkin/Jaeger). |
| **Structured logging** | `net.logstash.log4j:jsonevent-layout` is a dependency — JSON log output possible, but actual layout configuration depends on the external `log4j2.xml` not present in the repository. |
| **Alert on failure** | No alerting configuration found in this repository. |

### What Happens If Director Goes Down

Director going down causes a **cascading failure across the entire Gen-1/Gen-2 platform**:

1. Every service using `com.ecount.core.client.locator.DirectorServiceLocator` will fail to resolve service endpoints on next lookup.
2. Every service that dynamically constructs data sources from Director-returned connection strings (as described in `DataSources.xml` comments, line 12–18) will fail to create new DB connections.
3. Services that cache resolved values may continue to function until their cache expires or the process restarts. No cache mechanism is visible in the Director code itself; caching would have to be in the client-side `DirectorServiceLocator`.
4. Services using hard-coded fallback DataSources (as defined in `DataSources.xml` test fallback beans) may continue with stale connections. This fallback is only observed in test configuration.
5. The health check at `/hc` will stop responding, which should trigger AKS liveness probe restarts if configured.

**There is no evidence of HA, active-active clustering, or hot-standby for Director in this repository.**

---

## 6. Infrastructure Notes

- **QA hostnames** visible in `appsettings.json`: Q-LIS-DB01, Q-LIS-DB02, Q-LIS-DB03, Q-LIS-DB04 (SQL Server, port 2231), q-na-app09, q-na-app12, q-na-bat02 (all in `nam.wirecard.sys` domain — legacy Wirecard network naming).
- **Extra hosts** in `docker-compose.yaml`: `qa.nam.wirecard.sys:10.91.22.253` and `ppnaut.nam.wirecard.sys:10.91.22.254` — static `/etc/hosts` entries injected into the container, indicating the QA environment is not fully DNS-resolvable from the container network.
- **Tomcat libs copied at build time** (from `Directory-War/pom.xml` maven-dependency-plugin): `commons-logging`, `slf4j-api`, log4j2 jars, `mssql-jdbc:12.5.0.jre11-preview`, `HikariCP:5.1.0` — these are placed in `target/tomcat-lib/`, implying they need to be manually copied to `$CATALINA_HOME/lib`.

---

## 7. Operational Risks

| Risk | Severity | Detail |
|---|---|---|
| **No high availability / no clustering** | Critical | Director is a single point of failure for the entire platform. No load-balanced or replicated deployment configuration is present. |
| **Dual CI pipelines** | High | Both GitLab CI (legacy) and GitHub Actions are present. Simultaneous active pipelines could deploy conflicting versions to the same environment. |
| **Container scan disabled** | Medium | `deployment.yml:38`: `CONTAINER_SCAN: false` — container vulnerability scanning is disabled (`"frequently fails"`). Known CVEs in the allowedlist (`allowedlist.yaml`) include critical Spring and Jackson vulnerabilities. |
| **No HTTPS on Tomcat** | High | `server.xml` defines only HTTP on port 80 with a redirect port but no `<Connector>` on 8443. XML-RPC traffic carrying credential dictionaries travels over HTTP unless TLS is terminated at a load balancer. |
| **Log4j2 config external** | Medium | If the `CBASE_HOME_URL` directory is missing or `log4j2.xml` is absent, the WAR may fail to initialise logging or use unsafe defaults. |
| **`autoDeploy="false"` in Tomcat** | Low | Deployments require a manual file copy + restart sequence. No rolling restart is automated. |
| **Azure SDK version lag** | Medium | `azure-data-appconfiguration:1.3.0` and `azure-identity:1.5.3` were released in 2022; as of 2026, these are significantly outdated and may carry resolved CVEs. |
| **`reactor-core:3.5.0` / `reactor-netty:1.1.0`** | Medium | These exact versions are over 3 years old. `reactor-netty` 1.1.0 had known CVEs. |
| **`mssql-jdbc:12.5.0.jre11-preview`** | Medium | Preview classifier indicates an unofficial release. Should use a stable GA JDBC driver. |
