# workbench_WAPP — DevOps / Operations View

## Build
- **Build tool**: Maven (with Maven Wrapper `mvnw`/`mvnw.cmd`)
- **Java version**: Java 8 (`maven.compiler.source=1.8`, `maven.compiler.target=1.8`)
- **Packaging**: WAR file, `finalName=ROOT` (deploys as root context on Tomcat)
- **Parent POM**: `com.citi.prepaid.web:webapp-parent:10.0.0`
- **Build profiles**: Not visible in root pom; CI skips tests with `-Dmaven.test.skip=true -Pno-it`
- **Maven settings**: `.mvn/wrapper/settings.xml` — likely points to internal Nexus/Artifactory

## Deployment
- **CI/CD**: GitLab CI (`.gitlab-ci.yml`) — includes a shared template from `northlane/development/application-development/configuration/ci-templates` project (`refactor` branch)
- **GitHub Actions**: CodeQL analysis and Dependabot config present (`.github/dependabot.yml`, `.github/workflows/codeql.yml`)
- **Deployment target**: Windows Tomcat servers
  - Dev: `d-na-app02` (port 8081)
  - QA: `q-na-app05` (port 8090)
  - UAT/Prod: referenced in pom URL as `d/q/u/p-na-app0(1/5/5/7).nam.wirecard.sys:8090`
- **Service name**: `Workbench1` (Windows service, matches folder name in Tomcat `servers-8.5.5.7`)
- **Protocol**: HTTPS (infrastructure level), application uses HTTP connector
- **Health check URI**: `/` (root)
- **Deployment method**: Maven deploy → artifact to repo → GitLab CI stops/starts Windows service

## Configuration Management
- **Override properties**: `application.properties` references an external override file at `d:/c-base/config/workbench/application.properties` — environment-specific config is provided by server-local file, not injected via CI/CD secrets
- **JobScheduler URL**: Injected via `${jobscheduler.service.url}` property resolved at runtime from override properties file
- **JNDI datasource**: `CbaseappDataSource` resolved via JNDI (`java:comp/env/jdbc/CbaseappDataSource`) — connection pool configured in Tomcat server.xml (not in this repo)
- **No containerization**: No Dockerfile present; runs on bare-metal/VM Tomcat

## Observability
- **Logging**: Log4j 1.2.17 (`log4j.version=1.2.17`) via `Log.config` and `workbench-SystemLog.config`
- **Log4j 1.x is EOL** and contains known CVEs (CVE-2019-17571, others); this is a critical security risk
- **Request log**: Jetty NCSA-format request log configured for local development (not production logging)
- **No APM or distributed tracing** configuration visible in this repository
- **No health-check endpoint** defined in the application; GitLab CI uses `/` URI as health probe

## Infrastructure Dependencies
| Dependency | Type | Details |
|-----------|------|---------|
| SQL Server (CbaseappDataSource) | RDBMS | Primary database, JNDI lookup |
| SQL Server (JobSvcDataSource) | RDBMS | Job service and symbol data |
| JobSchedulerService | HTTP Invoker | Remote Spring HTTP Invoker endpoint |
| xSecurity service | Internal library | Authentication/authorization |
| xAffiliateService | Internal library | Affiliate management |
| xPlatform | Internal library | Core platform services |
| brandedCurrency service | Internal library | Branded currency management |
| symbol-svc | Internal library | Symbol/currency management |
| banker-common | Internal library | Banker operations |
| autofile-common | Internal library | Autofile processing |
| Tomcat 8.5.5.7 | Application server | Windows-hosted |

## Operational Risks
1. **Log4j 1.2.17 (EOL)**: Known vulnerabilities; deserialization risk via SocketAppender (CVE-2019-17571)
2. **No container image**: Manual Tomcat deployment increases drift risk between environments
3. **External properties file** (`d:/c-base/config/...`) is on the application server filesystem — no secrets management; credentials in plaintext on disk
4. **Single-instance deployment**: No evidence of load-balanced or clustered deployment; single point of failure
5. **Tests skipped in CI**: `-Dmaven.test.skip=true` in all CI stages; regression risk
6. **`ehcache`** in-memory caching without visible TTL/eviction config may cause stale configuration to be served after database updates

## CI/CD Pipeline
```
GitLab CI (gitlab-ci.yml)
  → Includes ci-templates/maven.gitlab-ci.yml@refactor
  → Build stage: mvn clean install (tests skipped)
  → Deploy to dev (d-na-app02:8081): stop Windows service → deploy WAR → start service
  → Deploy to QA (q-na-app05:8090): stop Windows service → deploy WAR → start service
  → Health check: HTTPS GET to /

GitHub Actions (supplemental)
  → CodeQL security scanning on push/PR
  → Dependabot for dependency updates
```
