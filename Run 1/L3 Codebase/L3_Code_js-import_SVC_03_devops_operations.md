# DevOps and Operations View — js-import_SVC

## Build System

`js-import_SVC` is a Maven WAR project (artifact `jsimport`, packaging `war`, final name `jsvalidator`). It inherits from `service-parent` POM (`com.citi.prepaid.service:service-parent:8`). Key build properties:

- Java 1.8 (source and target) — `pom.xml` lines 38–40
- Maven Wrapper (`mvnw` / `mvnw.cmd`) bundled under `.mvn/wrapper/`
- Custom Nexus repository for dependency resolution (internal Onbe/Wirecard Nexus at `d-na-stk01.nam.wirecard.sys:8080/nexus`)
- Spring 2.0.4 (legacy Spring Framework, not Spring Boot)

Build commands:
```sh
./mvnw clean package -Dmaven.test.skip=true
```

The WAR is deployed to Apache Tomcat (`servers-8.5.5.7`) as the `JSValidator` Windows service.

## CI/CD Pipeline

CI/CD is managed via GitLab CI (`.gitlab-ci.yml`). The pipeline inherits from a shared template:
```yaml
include:
  - project: 'northlane/development/application-development/configuration/ci-templates'
    ref: 'refactor'
    file: 'maven.gitlab-ci.yml'
```

Key pipeline variables:
| Variable | Value |
|---|---|
| `SERVICE_NAME` | JSValidator |
| `PROJECT_ARTIFACT_PATH` | `.` (root) |
| `PROJECT_SERVICE_PROTO` | `http` |
| `PROJECT_SERVICE_DEV_PORT` | `8480` |
| `PROJECT_SERVICE_QA_PORT` | `8480` |
| `PROJECT_SERVICE_URI` | `/jsvalidator` |
| `DEV_SERVICE_HOSTS` | `d-na-app04` |
| `QA_SERVICE_HOSTS` | `q-na-app09` |
| `MAVEN_BUILD_OPTS` | `-Dmaven.test.skip=true -Pno-it` |

Tests are **skipped in all pipeline phases** (`-Dmaven.test.skip=true`). This is a significant quality gap — no automated test validation occurs during CI.

GitHub Actions also includes a CodeQL workflow (`.github/workflows/codeql.yml`) and Dependabot configuration (`.github/dependabot.yml`), suggesting dual-hosting on GitHub and GitLab.

## Deployment Architecture

The service runs as a Tomcat-hosted WAR application on Windows servers:
- **Dev**: `d-na-app04` (Windows host)
- **QA**: `q-na-app09` (Windows host)
- Port: `8480` (non-standard; not behind a load balancer based on available config)
- Health check endpoint: `http://{host}:8480/jsvalidator`
- No containerisation (no Dockerfile present)
- No Kubernetes manifests present

The JNDI data source `java:comp/env/jdbc/JobSvcDataSource` is expected to be configured in Tomcat's `context.xml`, not in application config — this creates an environment dependency that must be separately managed per Tomcat instance.

Application configuration is read from:
- `D:/c-base/config/service/jobservice/JSImporter/service.properties` (environment-specific chars, environment name, Redis URL)
- JNDI for database connection

This path (`D:/c-base/...`) is a Windows filesystem path, confirming the on-premise Windows deployment model.

## Dependency Management

Key runtime dependencies and their risk profiles:

| Dependency | Version | Risk |
|---|---|---|
| `log4j:log4j` | 1.2.17 (provided) | EOL; CVE-2019-17571 (CVSS 9.8 socket-server deserialization) |
| `net.sourceforge.jtds:jtds` | 1.2.2 | Legacy JDBC driver; no vendor support |
| `commons-dbcp:commons-dbcp` | 1.2.2 | Legacy connection pool; superseded by DBCP2 |
| `commons-collections` | 3.2 | CVE-2015-6420 (CVSS 7.5 deserialization) — version 3.2 without patch |
| `spring:spring` | 2.0.4 | Very old Spring Framework; numerous historical CVEs |
| `com.fasterxml.jackson.core` | 2.15.2 | Relatively current |
| `xPlatformLibrary` | 1.0.15 | Internal library; version currency unknown |

The dependency set is severely outdated. Dependabot alerts should be reviewed immediately.

## Operational Monitoring

- **Health endpoint**: `GET /jsvalidator` (basic HTTP 200)
- **DB health**: `DBConnectionTestDAO` bean performs a test SQL query; failure returns an error response via `JobValidatorServlet`
- **Logging**: Uses Log4j 1.x (provided by container). Log output location and rotation are Tomcat-managed.
- **No APM integration** apparent from config files
- **No distributed tracing** (no correlation ID injection)

## Operational Procedures

The GitLab CI pipeline manages start/stop of the Windows service `JSValidator` during deployments via the shared `maven.gitlab-ci.yml` template. Manual operations require RDP access to `d-na-app04` / `q-na-app09`.

Key operational concerns:
1. **Forced run mode override** (`UpdateJobFileForcedRunModeDAO`) must be access-controlled — it can bypass normal batch/realtime routing.
2. **File reprocessing** — there is no built-in retry mechanism; operations staff must manually resubmit or modify `job_file` table rows.
3. **ID sequence exhaustion** — if `IDGeneratorImpl` sequences are exhausted, imports fail silently. Monitoring of `GetIDSequenceDAO` outcomes is necessary.
4. **Redis cache availability** — `service.properties` provides a Redis URL; if Redis is unavailable at startup, `JSContext` initialization may fail, preventing the Servlet from loading.

## Environment Configuration Risk

The hard-coded path `D:/c-base/config/...` in `jobsvc_import.xml` (line 35) means the service is tightly coupled to a specific Windows filesystem layout. This makes containerisation, cloud migration, or disaster recovery to a different path extremely difficult without code changes.
