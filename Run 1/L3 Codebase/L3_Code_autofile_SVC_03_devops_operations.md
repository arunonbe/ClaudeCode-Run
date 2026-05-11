# autofile_SVC — DevOps & Operations View

## Build & Packaging

- **Build tool**: Apache Maven 3 (wrapper present at `.mvn/wrapper/maven-wrapper.properties`)
- **Java version**: Java 21 (compiler source/target in root `pom.xml`; runtime: `bellsoft/liberica-openjre-alpine:21`)
- **Parent POM**: `com.parents:prepaid-parent:6.0.13`
- **Project version**: `3.0.3`
- **Artifact ID**: `com.ecount.service.autofile:autofile:3.0.3`
- **Module structure**: Three Maven modules:
  - `autofile-common` → JAR (public API, DTOs, proxy)
  - `autofile-impl` → JAR (business logic, DAO, domain)
  - `autofile-service` → WAR (servlet, health endpoint, Tomcat config)
- **WAR name**: `autofile-service.war` (set via `<finalName>`)
- **Additional build output**: `maven-dependency-plugin` copies Tomcat-lib JARs into `target/tomcat-lib/` during the `package` phase:
  - `commons-discovery:0.2`, `commons-logging:1.1.1`, `slf4j-api`, `log4j-api`, `log4j-core`
  - `com.microsoft.sqlserver:mssql-jdbc:12.5.0.jre11-preview`
  - `com.zaxxer:HikariCP:5.1.0`
- **Test execution**: All build commands use `-Dmaven.test.skip`. No test sources or test infrastructure are present in the repo.
- **Enforcer plugin**: `maven-enforcer-plugin` with `banTransitiveDependencies` is active in all three modules, preventing unintended transitive dependency additions.

## Deployment

### Container
- **Base image**: `bellsoft/liberica-openjre-alpine:21`
- **Dockerfile**: `autofile-service/Dockerfile`
- **App server**: Apache Tomcat 10.1.28 (downloaded at build time from `archive.apache.org`)
- **Port exposed**: 80 (container) — mapped to host port 9305 in `docker-compose.yaml`
- **WAR deployment**: `target/autofile-service.war` → `/opt/tomcat/webapps/autofile-service.war`
- **Config injection**: `config/server.xml` is copied into `/opt/tomcat/conf/`
- **Certificate**: `config/certfile_qa.crt` imported into JVM truststore (`changeit` password — standard default)
- **JVM flags** (`JAVA_OPTS`): multiple `--add-opens` for `java.base` and `java.rmi` packages (required by Axis SOAP and legacy serialization)
- **Config directory**: mounted from `${CONFIG_DIR}` host path to `/cbase/config` inside container. Log4j2 config path: `${env:CBASE_HOME_URL}/config/service/autofile/log4j2.xml`

### Kubernetes / AKS
- **Target environment**: QA AKS (`application-name: "autofilesvc"` in `redeploy.yaml`)
- **CI/CD pipelines** use centralized reusable workflows from `Onbe/om-ci-setup` and `Onbe/om-cd-setup` GitHub orgs
- **APIM publishing**: `deployment.yml` sets `PUBLISH_TO_APIM: true` (publishes WSDL), `INTERNAL_APIM: false`, `EXTERNAL_APIM: false`

### Docker Compose (local/QA)
```yaml
ports: "9305:80"
env_file: ./.env
volumes: ${CONFIG_DIR}:/cbase/config
extra_hosts:
  - "qa.nam.wirecard.sys:10.91.22.253"
  - "ppnaut.nam.wirecard.sys:10.91.22.254"
```
The `extra_hosts` entries reference legacy Wirecard/ecount hostnames — these hardcoded IPs are a legacy dependency.

## Configuration Management

All runtime configuration is injected externally. The codebase references these categories of properties (resolved at Tomcat startup via `EnvironmentPropertySource`):

| Property Key | Purpose | Config File |
|---|---|---|
| `${agent}` | Workflow engine agent identifier | External (env/config) |
| `${System_Auto_Auth}` | System user ID for automatic authorization and `InsufficientFundsRetryScheduler` | External |
| `${System_Run}` | System user ID for processing error retry | External |
| `${banker.force.authorize.userid}` | Force-authorize user ID when Banker label is OFF | External |
| `${feature.simulate.insufficient.funds}` | Feature flag: simulate insufficient funds (non-prod only) | External |
| `${insufficientFunds.retryFireTimes}` | Scheduler fire times, e.g. `"09:00,13:00,17:00"` | External |
| `${insufficientFunds.testingMode}` | Boolean: enable 15-min test firing | External |
| `${genericschedulercallback.service.url}` | Callback URL for scheduler retries | External |
| `${loading.*}`, `${bankerUnavailable.*}`, `${fundsUnavailable.*}`, etc. | Retry properties (maxRetryAttempts, firstRetryInterval, retryInterval) | External |
| DB stored proc names | All 11 stored proc SQL values in `autofile-datasource.properties` | Bundled in WAR |
| `${CBASEAPP_JDBC_URL}`, `${JOBSVC_JDBC_URL}` | Database connection URLs | Environment variables |
| `${AUTOFILESVC_*_PASSWORD/USERNAME}` | Database credentials | Environment variables / secrets |
| `${CBASE_HOME_URL}` | Root config directory URL | Environment variable (set to `file:///cbase`) |

The stored procedure names are the only configuration bundled inside the WAR (`autofile-impl/src/main/resources/autofile-datasource.properties`). All other configuration is externalized to the mounted `/cbase/config` volume.

## Observability

### Logging
- **Framework**: Log4j2 (API + core + 1.2 bridge + Jakarta web integration declared in `autofile-service/pom.xml`)
- **Logging style**: Mix of `@Slf4j` (Lombok) and `ThreadLocal<Logger>` pattern (legacy code in `AutofileServiceProxy`, `AutofileInputValidator`)
- **Log4j2 config**: External file at `${env:CBASE_HOME_URL}/config/service/autofile/log4j2.xml` — not bundled in the WAR, must be present in the mounted config volume
- **Audit markers**: `InsufficientFundsRetryScheduler` and `ProgramJobOrderHelper` write structured `AUDIT |` prefixed log lines for key business events (workflow started, skipped for manual auth, etc.)
- **No structured logging**: Log messages are plain string concatenation; no JSON/MDC-based structured logging is implemented

### Health Check
- **Endpoint**: `GET /hc` → returns `"OK"` (HTTP 200)
- **Implementation**: `com.onbe.autofile.health.HealthCheck` (Spring MVC `@RestController`, mapped via `AutoFile` DispatcherServlet)
- **Depth**: Shallow — returns OK unconditionally. Does not check database connectivity, downstream service availability, or scheduler health.

### Metrics
No metrics instrumentation is present. No Micrometer, Prometheus, or similar is configured.

### Distributed Tracing
No tracing (e.g., OpenTelemetry, Zipkin) is configured.

### Access Logging
Tomcat `AccessLogValve` is configured in `server.xml`: logs to `logs/localhost_access_log*.txt` in combined format.

## Infrastructure Dependencies

| Dependency | Type | Protocol | Notes |
|---|---|---|---|
| JobSvc SQL Server | Database | JDBC/mssql | Primary state store; JNDI `jdbc/JobSvcDataSource` |
| CbaseApp SQL Server | Database | JDBC/mssql | User/member data; JNDI `jdbc/CbaseappDataSource` |
| Banker Service | RPC | Apache Axis (SOAP) | `BankerServiceAPI` via `com.ecount.service.banker:banker-common:4.0.3` |
| Scheduler Service | RPC | Spring Remoting (HTTP Invoker) | `scheduler-common:3.0.1` |
| Job Scheduler Service | RPC | Spring Remoting (HTTP Invoker) | `jobscheduler-common:3.0.0` |
| Job Service | RPC | cbase platform RPC | `com.cbase.business.jobsvc.*` classes from `xplatform:6.5.8` |
| Repository Service | RPC | cbase platform RPC | `com.cbase.business.repository.*` classes from `xplatform:6.5.8` |
| Profile Service | RPC | cbase platform RPC | `com.cbase.business.profile.*` classes from `xplatform:6.5.8` |
| Workflow Engine | RPC | cbase platform RPC | `com.cbase.business.workflow.WorkflowManager` from `xplatform:6.5.8` |
| GitHub Packages | Artifact registry | HTTPS | Maven settings from `.mvn/wrapper/settings.xml` |
| AKS (Azure Kubernetes) | Container runtime | — | QA deployment target |

Legacy Wirecard DNS entries (`qa.nam.wirecard.sys`, `ppnaut.nam.wirecard.sys`) are hardcoded in `docker-compose.yaml`, indicating unresolved dependency on legacy infrastructure for local/QA runs.

## Operational Risks

1. **Hard-coded legacy Wirecard hostnames** — `docker-compose.yaml` contains `extra_hosts` entries pointing to `10.91.22.253` and `10.91.22.254`. If these IPs are unavailable, local/QA startup will fail for any downstream service resolution that depends on them.
2. **Tomcat downloaded at Docker build time** — the `Dockerfile` executes `curl -O https://archive.apache.org/dist/tomcat/...` at image build time. If the archive URL is unreachable (network issue, EOL removal), builds fail. No pre-baked base image is used.
3. **No database health in /hc endpoint** — the `HealthCheck.health()` method returns `"OK"` unconditionally. AKS liveness/readiness probes will report the service as healthy even when both SQL Server connections are broken.
4. **WorkflowCache loaded at startup** — `WorkflowCache` loads the full workflow process/step/state-machine metadata from the Workflow Engine RPC at bean initialization (`init` via constructor). If the Workflow Engine is unavailable at startup, the cache silently catches `ReturnStatus` and continues with an empty cache. Subsequent workflow executions will fail at runtime rather than failing fast at startup.
5. **No retry on JVM/Tomcat crash** — `InsufficientFundsRetryScheduler` is an in-JVM daemon thread. A JVM crash or Tomcat restart loses all scheduled timer state. The scheduler restarts correctly on pod restart due to Spring `init-method="start"`, but any in-progress retry window is aborted without compensation.
6. **simulateInsufficientFunds flag** — `feature.simulate.insufficient.funds` defaults to `false` per `domain-helpers.xml` Spring wiring but depends on correct external configuration. No environment-type guard (e.g., check for `SPRING_PROFILES_ACTIVE=production`) prevents accidental enablement.
7. **Trivy allowlist has 6 CVE exceptions** — `.trivyignore` / `allowedlist.yaml` explicitly suppresses: CVE-2018-1000632, CVE-2020-10683, CVE-2024-22262, CVE-2024-38816, CVE-2024-47072, CVE-2024-52316. These should be periodically reviewed for severity re-classification.

## CI/CD

### Pipelines (GitHub Actions)

| Workflow | Trigger | Action |
|---|---|---|
| `deployment.yml` | Push to `main`, PR to `main` | Calls `Onbe/om-ci-setup/.github/workflows/java-workflow.yml@main` — builds, tests, deploys to AKS |
| `github-package-publish.yml` | Push to `main`, PR to `main`, manual dispatch | Calls `Onbe/om-ci-setup/.github/workflows/java-package-publish.yml@main` — publishes JARs to GitHub Packages |
| `redeploy.yaml` | Manual dispatch only | Calls `Onbe/om-cd-setup/.github/workflows/redeploy.yaml@main` — redeploys to QA AKS |
| `codeql.yml` | Weekly schedule (Friday 17:53 UTC), manual dispatch | Calls `Onbe/om-ci-setup/.github/workflows/codeql-auto.yml@main` — static analysis |
| `vm-deployment.yml` | Separate pipeline (not inspected in detail) | Likely VM-based deployment |

### Key CI Settings
- `MAVEN_ARGS: ' -s ./.mvn/wrapper/settings.xml -Dmaven.test.skip '` — tests are always skipped in CI
- `EXCLUDE_STAGE: true` — no staging environment promotion
- `UPDATE_DEPENDENCIES: true`, `UPDATE_PARENT_VERSION: true` — automated dependency version bumping is enabled
- `PACT_PACTICIPANT: autofile-svc`, `VERIFY_PROVIDER_PACT: false` — Pact contract testing is registered but provider verification is not enabled
- `PUBLISH_TO_APIM: true` — WSDL is published to APIM on every main-branch push
- `.gitlab-ci.yml` is also present — indicates historical GitLab CI usage or dual-SCM transition
