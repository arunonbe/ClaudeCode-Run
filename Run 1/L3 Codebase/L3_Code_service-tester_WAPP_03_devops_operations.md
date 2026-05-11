# service-tester_WAPP — DevOps / Operations View

## Build System
- Maven multi-module project (parent + `service-test-common`, `service-test-web`, `service-test-web-admin`).
- Java 8 (`maven.compiler.source=1.8`, `maven.compiler.target=1.8`).
- Parent: `com.citi.prepaid.service:service-parent:8`.
- Version: `2.0.2-SNAPSHOT`.
- Build tool: `maven-release-plugin` 3.0.0-M1, `maven-compiler-plugin` 3.8.1.
- Distribution: WebDAV to Nexus (`d-na-stk01.nam.wirecard.sys:8080`).
- `service-test-console` module exists as a JAR-based console client (not a web module).

## CI/CD Pipelines
| Pipeline | System | Trigger | Purpose |
|---|---|---|---|
| `.gitlab-ci.yml` | GitLab | Push/MR | Maven build, deploy to dev/QA Tomcat |
| `codeql.yml` (GitHub) | GitHub Actions | Weekly; workflow_dispatch | CodeQL SAST |
| Dependabot | GitHub | Weekly | Maven dependency updates |

### GitLab CI Details
- Uses shared template `northlane/development/.../ci-templates/mavenMulti.gitlab-ci.yml`.
- Deploy target: Windows Tomcat service named `ServiceTester` on hosts:
  - DEV: `d-na-app01` port 9507
  - QA: `q-na-app03`, `q-na-app04` port 9507
- Tests skipped in all phases (`-Dmaven.test.skip=true`).
- Deploys artefact: `service-test-web-admin`.

## Config Management
- `service.tester.smtp.host=mail.ecount.com` — hardcoded SMTP host (legacy Ecount).
- `service.tester.smtp.from=servicetester@ecount.com` — legacy sender address.
- Database connection via JNDI `jdbc/ServiceTesterDataSource` — configured in Tomcat context.
- `resources-filtered/artifactInfo.properties` uses Maven resource filtering for build metadata.

## Observability
- Apache Commons Logging in `JdbcUserDao` and `JarLoader`.
- `log4j.properties` in console and swing modules — Log4j 1.x configuration.
- Log4j 1.2.17 declared in dependency management — **Log4j 1.x is EOL since 2015 and has known CVEs**.
- No metrics, no distributed tracing, no health endpoints.

## Infrastructure Dependencies
| Dependency | Notes |
|---|---|
| Tomcat 8.5 (Windows service) | Deployment target; server names d-na-app01, q-na-app03/04 |
| SQL Server (JNDI `jdbc/ServiceTesterDataSource`) | User and access database |
| SMTP `mail.ecount.com` | Email notifications (legacy Ecount host) |
| Nexus `d-na-stk01.nam.wirecard.sys:8080` | Artefact repository |
| GitLab `gitlab.com/northlane/...` | SCM and CI/CD platform |
| `com.citi.prepaid.service:service-parent:8` | Parent POM |

## Operational Risks
- **Log4j 1.2.17**: EOL, multiple CVEs (CVE-2019-17571, socket server deserialization). Must be upgraded to Log4j 2.x or SLF4J/Logback.
- Runtime JAR loading (`JarLoader`) — JARs added to Tomcat's `WebappClassLoader` at runtime. If the JAR source directory is writable, this is a code injection vector.
- Tests always skipped — no regression gate.
- Deployment to Windows Tomcat services — no containerisation, no blue/green, no rollback automation.
- SMTP host `mail.ecount.com` — if this domain is decommissioned, email notifications will fail silently.
- Distribution URL uses HTTP (not HTTPS): `http://d-na-stk01.nam.wirecard.sys:8080/nexus/...`.
