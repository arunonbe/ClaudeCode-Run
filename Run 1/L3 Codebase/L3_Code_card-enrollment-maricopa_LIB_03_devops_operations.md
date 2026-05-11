# card-enrollment-maricopa_LIB — DevOps & Operations View

## Build & Packaging

- **Build tool**: Apache Maven, with Maven Wrapper (`mvnw` / `mvnw.cmd`) pinned to Maven **3.9.1** (`.mvn/wrapper/maven-wrapper.properties` line 17).
- **Packaging**: JAR (`<packaging>jar</packaging>` in `pom.xml` line 15).
- **Artifact coordinates**: `com.citi.process:card-enrollment:1.0` (`pom.xml` lines 12–14).
- **Java version**: Not explicitly specified in `pom.xml`. The parent POM (`com.parents:service-parent:9.0.0`) likely sets the compiler level, but it is not readable from this repository.
- **Parent POM**: Inherits from `com.parents:service-parent:9.0.0` (`pom.xml` lines 4–8). This parent is resolved from the Nexus/GitHub packages repositories configured in `settings.xml` — dependency on an internal artifact repo.
- **Artifact repository**: Maven settings in `.mvn/wrapper/settings.xml` reference two artifact sources:
  - Legacy Wirecard Nexus: `https://d-na-stk01.nam.wirecard.sys:8081/nexus/content/groups/public/` (lines 13, 92, 120)
  - GitHub Packages: `https://maven.pkg.github.com/onbe/onbe_maven_releases` (line 111)
  - Active profile is `nexus` (line 142), meaning builds attempt the Wirecard Nexus host first.
- **No test sources**: There is no `src/test/` directory or any test class in the repository. The only test dependency (`junit:junit:3.8.1`) is declared in `pom.xml` lines 53–57 but unused.
- **Version pinned at 1.0**: No SNAPSHOT designation; this is a fixed-version artifact. No versioning strategy is evident.

## Deployment

- **Deployment type**: This is a standalone batch JAR, not a web application or microservice. It is executed directly on a host machine using `java -jar` (or equivalent classpath invocation).
- **Runtime environment assumption**: The main class (`EnrollmentProcessMain`) hardcodes the following filesystem paths, which must exist on the target host:
  - `D:\c-base\config\processes\cardenrollment\cardenrollment.properties` (appContext.xml line 8)
  - `D:\c-base\config\director-client.properties` (appContext.xml line 9)
  - `D:\c-base\config\processes\cardenrollment\log4j.xml` (EnrollmentProcessMain.java line 14)
- **Target OS**: Windows (hardcoded backslash `D:\` and forward-slash `D:/` paths in the config). The CodeQL workflow specifies a Linux runner (`ubuntu-docker`) but the application itself will fail on Linux due to the Windows drive-letter paths.
- **No containerization**: No Dockerfile, no docker-compose, no Kubernetes manifests are present.
- **No deployment scripts**: No shell scripts, Ansible playbooks, or Terraform configurations are present.
- **Trigger mechanism**: The batch job has no built-in scheduler. It must be triggered externally (e.g., Windows Task Scheduler, cron, or a job orchestrator calling the JAR directly).

## Configuration Management

- **Configuration strategy**: Entirely externalized to flat `.properties` files on the local filesystem. Spring's `PropertyPlaceholderConfigurer` bean (appContext.xml lines 4–13) loads two files at fixed absolute Windows paths.
- **Key configuration properties** (resolved at runtime from external files, not present in this repo):
  - `${director.address}` — hostname/port of the Director service
  - `${ecount.agent}` — agent identifier for the eCount platform
  - `${ecountcore.database}` — logical database name for eCount Core
- **No environment-specific profiles**: There is no Spring profile mechanism (no `@Profile`, no `-Dspring.profiles.active`). The same `appContext.xml` is used regardless of environment, relying entirely on the external properties files to differentiate environments.
- **Secrets in source control**: `.mvn/wrapper/settings.xml` contains plaintext usernames and passwords for Nexus and other servers (lines 33–50). This is a critical misconfiguration — see Data Architect findings.
- **Log4j configuration**: Also externalized to a hardcoded Windows path. Any change to logging behavior requires modifying a file on the production host, not a deployment.

## Observability

- **Logging framework**: Apache Log4j (classic, `org.apache.log4j`) loaded via a `DOMConfigurator` from a hardcoded XML file path (`EnrollmentProcessMain.java` lines 14, 84–85). The secondary import `org.apache.commons.logging.Log` is also present in `EnrollmentHelper.java` line 9 but the logger is instantiated at line 36 and never actually used in the file's methods (the `logger` field is declared but no log statements appear in the active code paths of `EnrollmentHelper`).
- **Log levels used**: DEBUG, INFO, ERROR in `EnrollmentProcessMain.java`.
  - Batch start/end timestamps logged at INFO.
  - Each account ID logged at INFO before and after processing.
  - Errors per account logged at ERROR with stack trace (via `logger.error(e.getStackTrace())`, line 59 — note: this logs the array object's `toString()`, not the full stack trace text, which is a logging bug).
- **No metrics**: No Micrometer, no JMX, no Prometheus instrumentation.
- **No distributed tracing**: No trace IDs, correlation IDs, or MDC context.
- **No alerting integration**: No webhook, email, or PagerDuty/OpsGenie integration. Failures are log-only.
- **No health checks**: Not applicable for a batch JAR, but no summary/report output (e.g., counts of successes vs. failures) is produced at the end of a run.

## Infrastructure Dependencies

| Dependency | Type | Reference | Notes |
|---|---|---|---|
| eCount Core Database | RDBMS (vendor DB) | `appContext.xml` `EcountCoreDataSource` bean | Accessed via DBCP connection pool, configured by Director |
| Director Service | Internal Onbe/eCount service | `appContext.xml` `directorDataSourcesFactory` — `${director.address}` | Provides DataSource factory; single point of failure |
| eCount xPlatform / Core2 libraries | Internal JAR dependencies | `pom.xml` lines 37–51 — `com.ecount:xPlatform:2.5.45`, `com.ecount.service.Core2.director:director-client:1.0.11`, `com.ecount.service.Core2:ecount-system:1.0.10` | Resolved from Nexus/GitHub Packages |
| Legacy Wirecard Nexus (`d-na-stk01.nam.wirecard.sys`) | Artifact repository | `settings.xml` lines 13, 92, 120 | This hostname references the Wirecard-era infrastructure. If this host is decommissioned, builds will fail |
| Host filesystem (Windows) | Local disk | `D:\c-base\config\...` paths | All configuration and logging assumes a specific Windows host directory structure |
| Spring Framework 2.5.4 | Library | `pom.xml` line 27–29 | Severely end-of-life (2008); no security patches available |

## Operational Risks

1. **Wirecard Nexus dependency**: The `settings.xml` active profile (`nexus`) resolves artifacts from `d-na-stk01.nam.wirecard.sys:8081` first. If this host is gone or unreachable, Maven builds fail and the JAR cannot be rebuilt.
2. **No retry logic despite declared constant**: `DEFAULT_RETRY_COUNT = 3` is defined in `EnrollmentHelper.java` line 37 but is never used. A transient API failure causes silent per-account loss with no retry.
3. **No run summary or alerting**: An operator has no automated way to know if a batch run processed 0 accounts (empty result set) vs. 1,000 accounts, or how many failed.
4. **Hardcoded Windows paths prevent portability**: Deployment to Linux (as suggested by the CodeQL workflow's Ubuntu runner) will fail at runtime due to `D:\` paths.
5. **Log4j version**: The classic Log4j 1.x library (`org.apache.log4j`) is end-of-life and has known vulnerabilities (though the specific CVE-2021-44228 Log4Shell affects Log4j 2.x, Log4j 1.x has its own separate CVEs including deserialization issues).
6. **Spring 2.5.4 (2008 EOL)**: Using a framework version from 2008 means no security patches and no support for modern Java versions.
7. **Duplicate processing risk**: No mechanism to mark accounts as "in progress" before the batch completes, creating a window for concurrent or re-run double-issuance.

## CI/CD

- **GitHub Actions — CodeQL**: `.github/workflows/codeql.yml` defines a SAST scan:
  - Trigger: `workflow_dispatch` (manual) and weekly schedule (Thursday at 21:05 UTC via `cron: 5 21 * * 4`)
  - Reuses Onbe's shared workflow: `Onbe/om-ci-setup/.github/workflows/codeql-auto.yml@main`
  - Runner: self-hosted Linux Docker (`['self-hosted', 'X64', 'Linux', 'ubuntu-docker']`)
  - Inherits all secrets from the calling repository
- **Dependabot**: `.github/dependabot.yml` configures weekly Maven dependency version checks on the root `pom.xml` (lines 5–10).
- **No build pipeline**: There is no `build.yml`, `deploy.yml`, or any CI workflow that compiles, tests, or publishes the artifact. The CodeQL scan is the only automated workflow. There is no automated deployment pipeline.
- **No test stage**: The lack of any test classes means even a CI build pipeline would have no tests to run.
