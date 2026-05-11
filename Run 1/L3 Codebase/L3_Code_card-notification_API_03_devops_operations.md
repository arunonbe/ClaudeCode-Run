# card-notification_API — DevOps & Operations View

## Build & Packaging

- **Build tool**: Maven 3.9.1 (Maven Wrapper via `.mvn/wrapper/maven-wrapper.properties`)
- **Packaging**: WAR (`<packaging>war</packaging>` in `pom.xml` line 12)
- **Artifact ID**: `cardnotification` (`pom.xml` line 11)
- **Final artifact name**: `cardnotification.war` (`<finalName>cardnotification</finalName>` in `pom.xml` line 162)
- **Version**: `2.0.0-SNAPSHOT`
- **Java source/target**: 1.8 (Java 8), set in `pom.xml` lines 41–42
- **Parent POM**: `com.ecount:ecount-parent:6` — an internal parent POM not in this repository
- **Artifact repository**: Internal Nexus at `d-na-stk01.nam.wirecard.sys:8080`
  - Release: `http://d-na-stk01.nam.wirecard.sys:8080/nexus/content/repositories/releases`
  - Snapshot: `http://d-na-stk01.nam.wirecard.sys:8080/nexus/content/repositories/snapshots`
  - Transport: WebDAV via `wagon-webdav-jackrabbit` extension
- **Tests are skipped in all CI phases**: All three GitLab CI Maven option variables are `"-Dmaven.test.skip=true"` (`.gitlab-ci.yml` lines 15–17)

### Key Dependencies
| Dependency | Version | Notes |
|---|---|---|
| Spring Framework | 2.5.4 | Core DI, AOP, JDBC, Hibernate integration |
| Apache Axis | 1.4 (Apr 2006) | SOAP/JAX-RPC runtime — end-of-life |
| EHCache | 1.3.0 | In-process caching with disk overflow |
| JUnit | 3.8.1 | Very old test framework |
| spring-mock | 2.0.4 | Integration test support |
| log4j | 1.2.17 | End-of-life logging framework (CVE-2019-17571) |
| commons-lang | 2.2 | Apache Commons utilities |
| xPlatform | 3.0.4 | Internal eCount platform library |
| xAffiliateService | 1.0.9 | Internal affiliate/program service |
| xSearch-client | 2013.2.1-SNAPSHOT | Internal member search client — SNAPSHOT dependency |
| aspectjweaver | 1.5.3 | AOP weaving |
| jsonevent-layout | 1.7 | JSON log formatting (Logstash) |

## Deployment

- **Runtime container**: Apache Tomcat (referenced as `tomcat/servers-8.5.5.7` in `.gitlab-ci.yml` line 7 SERVICE_NAME comment)
- **Windows service name**: `CardNotificationSMSPull` (`.gitlab-ci.yml` line 7)
- **Deployment context**: `/cardnotification` — WAR is deployed as `cardnotification.war`
- **Health check URI**: `/cardnotification/Cardnotification/CardnotificationService` on port 9324 (`.gitlab-ci.yml` lines 10–13)
- **Dev hosts**: `d-na-app02`
- **QA hosts**: `q-na-app01`, `q-na-app02`
- **Port**: 9324 for both dev and QA
- **CI pipeline**: Delegates to shared template `northlane/development/application-development/configuration/ci-templates/maven.gitlab-ci.yml` on master branch
- **External config location**: `${CBASE_HOME_URL}/config/CardNotification/` — must contain:
  - `CardNotification.properties` (agent, database name, transaction source types)
  - `director-client.properties` (director service address)
  - `log4j.xml` (log configuration, path hardcoded to `d:/c-base/config/CardNotification/log4j.xml` in `web.xml` line 19 — Windows path)

## Configuration Management

All runtime configuration is externalized via Spring `PropertyPlaceholderConfigurer` (`applicationContext.xml` lines 9–18). The following properties are required at startup:

| Property Key | Bean/Usage |
|---|---|
| `${cardnotification.agent}` | Agent identifier for eCount core, xSearch, and datasource lookup |
| `${cardnotification.cbaseapp.database}` | Database name passed to `DirectorConfiguredDBCPdatasourceCreator` |
| `${director.address}` | URL of the Director service (used for datasource and xSearch client) |
| `${cardnotification.lasttransactionsourcetypes}` | Pipe-delimited list of activity/source types for TRANSACTION filter |

Properties are sourced from files on the filesystem at `${CBASE_HOME_URL}/config/`. This is an environment variable that must be set in the JVM startup environment.

**Log4j config**: Hardcoded path `d:/c-base/config/CardNotification/log4j.xml` in `web.xml` line 19. This is Windows-specific and will fail on Linux unless the path is mapped.

**No container-managed secrets management**: No Vault, AWS SSM, or Kubernetes secrets integration. Secrets are in filesystem-based properties files.

## Observability

### Logging
- **Framework**: Log4j 1.2.17 with JSON event layout support (`jsonevent-layout 1.7`, `json-smart 1.1.1`) suggesting Logstash/ELK integration
- **Log statements**:
  - `JaxRpcCardNotificationService.java` (lines 40–58): Logs BEGIN/END of every call including mobile number and action type, with duration in ms
  - `CardNotificationServiceImpl.java`: Info logs for xSearch calls and member counts; error logs for all failure paths
  - `CardNotificationLogInsertDAO.java`: Debug logs for stored proc output
- **PII in logs**: Mobile phone number is logged at INFO level on every request (line 42 of `JaxRpcCardNotificationService`)

### Metrics
- No APM agent, Micrometer, Prometheus, or health check endpoint is present in the repository
- Duration logging is manual (start/end timestamps in `JaxRpcCardNotificationService`)

### Audit Trail
- AOP interceptor `CardNotificationLoggingInterceptor` writes every successful response to `sms_cardnotification_log` via `dbo.sms_cardnotification_log_insert` stored procedure. Logged fields: programId, mobile_phone, msg_category (always "PULL"), msg_type, create_date.

### Health Check
- The health check URI in `.gitlab-ci.yml` (`/cardnotification/Cardnotification/CardnotificationService`) implies a Tomcat context liveness check only — no dedicated `/health` or `/actuator` endpoint exists.

## Infrastructure Dependencies

| Dependency | Type | Discovery Mechanism |
|---|---|---|
| Director Service | HTTP/internal service registry | `${director.address}` property |
| xSearch-xmlrpc | Internal RPC service | Resolved via Director at runtime |
| SQL Server (CbaseApp DB) | Relational database | Connection provisioned by `DirectorConfiguredDBCPdatasourceCreator` via Director |
| SQL Server (EcountCore DB) | Relational database | Accessed via eCount platform `EDevice`/`EMember` objects |
| Apache Tomcat 8.5.5.7 | Servlet container | Deployment target |
| Internal Nexus repository | Maven artifact repository | `d-na-stk01.nam.wirecard.sys:8080` |
| GitLab CI | CI/CD | `gitlab.com/northlane/...` |
| GitHub Actions (CodeQL) | SAST scanning | `.github/workflows/codeql.yml` |

**All infrastructure references are internal hostnames** (wirecard.sys domain). This service cannot build or deploy outside the Wirecard/Northlane internal network without reconfiguration.

## Operational Risks

1. **Log4j 1.2.17 EOL with known CVE**: log4j 1.x reached end-of-life in August 2015 and has CVE-2019-17571 (socket server deserialization RCE). This dependency should be treated as a critical vulnerability.
2. **Apache Axis 1.4 EOL (2006)**: The SOAP runtime has not received security patches in nearly 20 years. It handles all inbound SOAP parsing and is a primary attack surface.
3. **Windows-hardcoded log path**: `d:/c-base/config/CardNotification/log4j.xml` in `web.xml` will silently fail or use default logging on non-Windows or non-standard deployments.
4. **Tests unconditionally skipped**: All CI phases have `maven.test.skip=true`. No automated quality gate exists.
5. **SNAPSHOT production dependency**: `xSearch-client:2013.2.1-SNAPSHOT` is a mutable SNAPSHOT artifact. Production builds using SNAPSHOTs are non-reproducible.
6. **Single Nexus point of failure**: All internal dependencies resolve from one Nexus instance. If `d-na-stk01.nam.wirecard.sys` is unreachable, the build fails.
7. **EHCache disk overflow to temp directory**: If `java.io.tmpdir` is on a small or shared partition, disk overflow could cause OOM or cross-process data exposure.

## CI/CD

### GitLab CI (`.gitlab-ci.yml`)
- Delegates entirely to a shared Maven CI template hosted at `northlane/development/application-development/configuration/ci-templates` on master
- Variables defined:
  - `SERVICE_NAME`: `CardNotificationSMSPull`
  - `PROJECT_ARTIFACT_PATH`: `.` (root)
  - `PROJECT_SERVICE_PROTO`: `http` (not https)
  - Ports: 9324 (dev and QA)
  - `DEV_SERVICE_HOSTS`: `d-na-app02`
  - `QA_SERVICE_HOSTS`: `q-na-app01 q-na-app02`
- **All test phases skip tests** — no test execution in the pipeline

### GitHub Actions (`.github/workflows/codeql.yml`)
- Runs CodeQL static analysis on a weekly schedule (Thursdays at 14:10 UTC) and on manual dispatch
- Uses shared workflow `Onbe/om-ci-setup/.github/workflows/codeql-auto.yml@main`
- Java runner: self-hosted Linux/Ubuntu Docker (`['self-hosted', 'X64', 'Linux', 'ubuntu-docker']`)

### Dependabot (`.github/dependabot.yml`)
- Weekly automated dependency version checks for Maven ecosystem at root directory
- Will generate PRs for outdated Maven dependencies

### No Production deployment pipeline is visible in this repository
- No staging or production environment variables or host lists are defined in `.gitlab-ci.yml`
- Production deployment appears to be a manual or out-of-band process
