# cicd-gala_SVC — DevOps & Operations View

## Build & Packaging

- **Build system**: Apache Maven 3.6.3, Java 8 (source/target `1.8` in root `pom.xml`).
- **Parent POM**: `com.citi.prepaid.service:service-parent:8` — an internal Northlane/ecount parent POM; not publicly available.
- **Multi-module structure**:
  | Module | Artifact | Type | Role |
  |---|---|---|---|
  | `banker-common` | `banker-common` | JAR | Shared DTOs, exceptions, API interface, client Spring config |
  | `banker-impl` | (implicit) | JAR | Core business logic, DAO implementations |
  | `banker-service` | WAR | Deployable WAR | Primary service WAR — Tomcat servlet container via Apache Axis |
  | `banker-service2` | WAR | Deployable WAR | Identical second WAR (duplicate of banker-service; likely for a second Tomcat instance) |
  | `banker-tester` | WAR | Test harness WAR | Web UI test tool; depends on `service-test-web` framework |
- **Artifact version**: `1.0.5-SNAPSHOT` (root pom.xml, line 14).
- **Maven wrapper**: `.mvn/wrapper/maven-wrapper.jar` present; `.mvn/wrapper/settings.xml` provides a custom settings file for the wrapper.
- **Build image**: `maven:3.6.3-jdk-8` Docker image used in CI.
- **CI build command**: `mvn $MAVEN_OPTIONS clean package` (build stage).
- **Maven settings injection**: When `USE_MVN_SETTINGS=true` in CI, a base64-encoded `MVN_SETTINGS` secret is decoded to `~/.m2/settings.xml` at build time — this is the mechanism for Nexus credentials.
- **Tests**: All tests are skipped in the current CI configuration:
  - `MAVEN_BUILD_OPTS: "-Dmaven.test.skip=true -Pno-it"`
  - `MAVEN_TEST_OPTS: "-Dmaven.test.skip=true -Pno-it"`
  - `MAVEN_DEPLOY_OPTS: "-Dmaven.test.skip=true -Pno-it"`
  - Unit test job `test-app-unit` is commented out entirely in `maven.gitlab-ci.yml`.

## Deployment

- **Target server**: Tomcat (Windows service named `Pipelab`, per `.gitlab-ci.yml` `SERVICE_NAME`).
- **Deploy mechanism**: Script `deployFromNexus.sh` downloads the WAR from Nexus and deploys to Windows hosts via Samba (`dperson/samba` Docker image). Credentials passed as `$GL_NAM_USER` / `$GL_NAM_PASSWORD` CI variables.
- **Environments**:
  | Environment | Hosts Variable | Notes |
  |---|---|---|
  | Dev | `DEV_SERVICE_HOSTS: d-na-app04` | Auto-deploy on master branch merge |
  | QA | `QA_SERVICE_HOSTS: q-na-app07` | Manual trigger on master or Release- branch |
- **Deployable artifacts**: `banker-service` WAR and `banker-service2` WAR (`PROJECT_ARTIFACT_PATH: banker-service banker-service2`).
- **Config deployment**: Separate `configTo:dev` pipeline stage deploys configuration files from a dedicated config repo (`CONFIG_REPO_DEV`) using `deployConfig.sh`.
- **Health check**: HTTP GET to `${PROJECT_SERVICE_PROTO}://${HOST}.nam.wirecard.sys:${PORT}/service/` (port 31337) expected to return HTTP 200. Runs after deploy in both `maven.gitlab-ci.yml` and `mavenNexus.gitlab-ci.yml`.
- **Rollback / restart**: Pipeline includes `rollback:dev`, `rollback:qa`, `restart:dev`, `restart:qa` stages, all manual triggers. The script body is currently a placeholder (`echo "Rolling back service ... TBD"`), meaning rollback is not yet automated.
- **Release process**: `mvn release:prepare release:perform` triggered on branches matching `Release-*`. Uses SSH key (`GL_PIPELINE_RELEASE_KEY`) and sets SCM committer identity to `gitlab@northlane.com`.

## Configuration Management

- **External configuration root**: `${CBASE_HOME_URL}/config/service/banker/` — a filesystem path on the target server.
  - `log4j.xml` — logging configuration, refreshed every 300,000 ms (5 min).
  - `banker.client.properties` — contains `banker.service.wsdl.url`, `banker.service.timeout`.
  - Spring property files provide: `agent`, `agent.banker`, `agent.gp`, `database.banker`, `database.user`, `preset.funds.config.ratio.percent`, `preset.funds.config.base.amount`, banker role names.
- **CI/CD secrets** (from `.gitlab-ci.yml` variable references):
  - `GL_PIPELINE_RELEASE_KEY` — SSH key for git tag push during release.
  - `GL_NAM_USER` / `GL_NAM_PASSWORD` — Windows SMB credentials for WAR copy to Tomcat.
  - `NORTHLANE_CI_RO_USER` / `NORTHLANE_CI_RO_PASS` — GitLab read-only credentials for cloning ci-scripts repo.
  - `MVN_SETTINGS` — base64-encoded Maven settings.xml (Nexus credentials).
- **Artifact repository**: Nexus at `http://d-na-stk01.nam.wirecard.sys:8080/nexus` (internal Wirecard/Northlane infrastructure).
  - Snapshots: `.../repositories/snapshots`
  - Releases: `.../repositories/releases`
- **Artifact info file**: `target/classes/artifactInfo.properties` (filtered at build time) records `artifactGroup`, `artifactId`, `artifactVersion`, `artifactPackaging`, `deploymentName`, `configurationFiles`.
- **Multi-WAR duplication**: `banker-service` and `banker-service2` share identical Spring XML configs and `web.xml`. The second WAR appears to exist for a second Tomcat instance/port with different configuration applied at the server level. No differentiation is present in source.

## Observability

- **Logging**: Apache Commons Logging (façade over Log4j). Log configuration loaded from external `log4j.xml` at `${CBASE_HOME_URL}/config/service/banker/`. The `banker-impl` test resources include `log4j.properties` for test execution.
- **Log levels**: All business-critical paths use `logger.isDebugEnabled()` guards before `logger.debug(...)`. Fatal errors use `logger.fatal(...)` in `SendApprovalNotification.execute()`.
- **Audit AOP**: `BankerAuditMethodInterceptor` (class `com.ecount.springutils.aop.AuditMethodInterceptor`) is applied via Spring AOP pointcut on all `BankerServiceManagerImpl` public methods and `PresetFundsConfig` methods. This intercepts every API call for audit trail. The actual implementation is in the external `springutils-generic` library (not in this repo).
- **Exception AOP**: `BankerExceptionMethodInterceptor` (class `com.ecount.service.banker.util.BankerMethodExceptionInterceptor`) wraps `BankerServiceManagerImpl` — likely for uniform exception logging/translation.
- **Health check endpoint**: HTTP GET `/service/` returns 200 if Tomcat/Axis is running. No application-level health check (e.g., DB connectivity probe) is evident.
- **No metrics or distributed tracing**: No Micrometer, Prometheus, OpenTelemetry, or similar instrumentation is present. Observability is entirely log-based.
- **`System.out.println` in production**: `SendApprovalNotification.java` line 274 writes to stdout unconditionally. In a Tomcat deployment this goes to `catalina.out`, polluting the container log.

## Infrastructure Dependencies

| Dependency | Type | Location / Reference |
|---|---|---|
| Tomcat (Windows) | App server | `d-na-app04` (dev), `q-na-app07` (QA); service name `Pipelab` |
| Nexus | Artifact repository | `http://d-na-stk01.nam.wirecard.sys:8080/nexus` |
| GitLab | Source / CI | `gitlab.com/northlane/...` |
| Banker DB (SQL Server) | Database | Resolved via Director; agent/db from config |
| User DB / cbaseapp (SQL Server) | Database | Resolved via Director; agent/db from config |
| Great Plains DB (SQL Server) | Finance ERP | Multiple instances, routed per program regex via `banker_program_datasource` |
| Director service registry | Connection factory | `DirectorConfiguredDBCPdatasourceCreator` — internal ecount service registry |
| cbase profile services | Profile/label lookup | `AppProfileProgramCurrencyClass`, `AppPromotionLabelProfileClass`, `LabelTypesClass` |
| cbase notification manager | Email delivery | `NotificationManagerImpl` (com.cbase.business.notification) |
| ECountCore system | Platform framework | `com.ecount.service.Core2` — `ecount-system` 1.0.7, `director-client` 1.0.11 |
| Apache Axis 1.4 | SOAP framework | Client and server; `axis:axis:1.4` |
| Spring Framework 2.0.8 | IoC/AOP/JDBC | `org.springframework:spring:2.0.8` |
| xPlatform 2.5.47 | Internal library | `com.ecount:xPlatform` — unknown; provided by ecount platform |
| springutils-generic 1.0.6 | Internal AOP utils | `com.ecount.springutils:springutils-generic` |
| Apache DBCP (via Director) | Connection pooling | Implicit through `DirectorConfiguredDBCPdatasourceCreator` |
| jtds 1.2 | SQL Server JDBC | `net.sourceforge.jtds:jtds:1.2` (test scope); `sqljdbc 1.2` for prod |
| ci-scripts repo | Deployment scripts | `gitlab.com/northlane/infrastructure/scripts/ci-scripts` |
| config repo (dev) | Configuration files | `gitlab.com/northlane/development/application-development/configuration/legacy/dev` |

## Operational Risks

1. **Tests entirely disabled in CI**: All three Maven phases (build, test, deploy) skip tests with `-Dmaven.test.skip=true`. Regressions will not be caught by the pipeline.
2. **Rollback not implemented**: `rollback:dev` and `rollback:qa` pipeline stages output placeholder text only. There is no automated rollback capability.
3. **Single-host deployment**: Dev deploys to a single host (`d-na-app04`); QA to a single host (`q-na-app07`). No load balancing or high-availability configuration is visible.
4. **Stale in-memory cache**: Four data structures loaded at startup are never refreshed except the finance datasource map (via `updateProgramExpressions*` API). Changes to authorization limits or promo exception programs require a service restart.
5. **SERIALIZABLE isolation contention**: Under load, all `BankerServiceManager` calls serialize against the banker DB. A single slow GP call (120-second timeout) blocks all concurrent requests.
6. **HTTP-only service**: Health check and SOAP traffic on port 31337 using plain HTTP. Man-in-the-middle risk for financial authorization messages.
7. **Nexus HTTP endpoint**: Artifact repository uses HTTP (`http://d-na-stk01...`), exposing artifacts and Maven credentials to interception.
8. **`banker-service` and `banker-service2` divergence risk**: Two identical WARs deployed; any out-of-sync deployment creates inconsistent service instances.

## CI/CD

### Pipeline (`.gitlab-ci.yml` → `scripts/mavenNexus.gitlab-ci.yml`)

```
Stages: build → test → release → publish → deploy → verify
```

| Stage | Job | Trigger | Notes |
|---|---|---|---|
| build | `build-app` | Any push to `/application/` path | `mvn clean package`; produces WARs + `artifactInfo.properties` |
| test | `test-app-it` | Only if `$MAVEN_TEST_OPTS` does not contain `Pno-it` | Currently never runs (variable has `-Pno-it`) |
| release | `release` | Branch matches `Release-*` | `mvn release:prepare release:perform`; SSH key required |
| publish | `mvndeploy` | master branch or (not Release-, not -refactoring) | `mvn deploy` to Nexus |
| deploy | `deploy:dev` | Auto on master | Downloads WAR from Nexus via `deployFromNexus.sh`; copies to Windows host |
| deploy | `deploy:qa` | Manual on master or Release- | Same as dev |
| deploy | `configTo:dev` | Auto on master | Clones config repo; runs `deployConfig.sh` |
| deploy | `restart:dev/qa` | Manual | Placeholder only |
| deploy | `rollback:dev/qa` | Manual | Placeholder only |
| verify | `healthcheck:dev` | Auto after deploy:dev | HTTP GET to `/service/` |
| verify | `healthcheck:qa` | Manual | HTTP GET to `/service/` |
| verify | `review:dev/qa` | Manual | Placeholder only |

### GitHub Actions (`.github/workflows/codeql.yml`)

- **CodeQL** analysis runs weekly (Fridays 20:05 UTC) and on `workflow_dispatch`.
- Uses Onbe's shared workflow: `Onbe/om-ci-setup/.github/workflows/codeql-auto.yml@main`.
- Runner: self-hosted, X64, Linux, Ubuntu Docker.

### Dependabot (`.github/dependabot.yml`)

- Weekly Maven dependency updates configured for the root `/` directory.
- Pull requests will be opened on GitHub automatically.

### Runner tag

All GitLab CI jobs use `nl-ntt` runner tag — an internal Northlane/Onbe runner pool.
