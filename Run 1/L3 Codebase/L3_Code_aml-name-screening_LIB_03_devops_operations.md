# aml-name-screening_LIB — DevOps & Operations View

## Build & Packaging

- **Build tool**: Apache Maven. Maven Wrapper present (`.mvn/wrapper/`), pinned to Maven **3.9.1** (`maven-wrapper.properties` line 17).
- **Java target**: Source and target compiled at **Java 1.6** (`pom.xml` lines 65–66). This is a severely outdated Java version (EOL since 2013). The wrapper JDK version is not pinned separately.
- **Artifact coordinates**: `groupId=NameScreening`, `artifactId=NameScreening`, `version=1.0.0-SNAPSHOT` (`pom.xml` lines 3–5). The `-SNAPSHOT` suffix indicates this has never been released to a stable version.
- **Packaging**: `maven-assembly-plugin` with `jar-with-dependencies` descriptor (`pom.xml` lines 70–85). Produces a fat JAR: `NameScreening-1.0.0-SNAPSHOT-jar-with-dependencies.jar`. The assembly goal is `attached` (deprecated), which attaches the fat JAR as a secondary artifact.
- **No test phase**: There are no test sources, no JUnit dependency, and no test execution configured. Maven `test` phase will execute with zero tests.
- **Artifact repository**: `.mvn/wrapper/settings.xml` references two artifact repositories:
  - `https://d-na-stk01.nam.wirecard.sys:8081/nexus/...` — a legacy Wirecard-era internal Nexus (hostname suggests decommissioned infrastructure).
  - `https://maven.pkg.github.com/onbe/onbe_maven_releases` — GitHub Packages (Onbe org).
  - Central Maven via `https://repo1.maven.org/maven2`.

## Deployment

- **Deployment model**: Command-line batch JAR. No container, no application server, no service wrapper.
- **Invocation**:
  ```
  java -jar NameScreening-1.0.0-SNAPSHOT-jar-with-dependencies.jar <inputFileName> USERNAME=<user> PASSWORD=<pass>
  ```
- **Configuration file dependency**: `applicationContext.xml` (bundled in JAR classpath) hardcodes a properties file path: `C:\c-base\config\namescreening\NameScreening.properties` (`applicationContext.xml` line 20). A commented-out `D:\` path variant also exists (line 21). This means the tool will only run on a Windows host where that exact directory and file exist. The `${inputfilepath}` property is consumed from that file.
- **Database host**: `ppamwdcpisql1b1.nam.nsroot.net:2431` (`applicationContext.xml` line 44) — a Citi/Wirecard-era internal hostname (`nsroot.net` is Citibank's internal DNS domain). A commented-out alternate `ppamwdcdifsql1.nam.nsroot.net:2232` also exists. These hostnames are unlikely to be reachable in the current Onbe environment.
- **No containerization**: No Dockerfile, no docker-compose, no Kubernetes manifests exist in the repository.
- **No service definition**: No systemd unit, Windows Service wrapper, or scheduler configuration (cron/Task Scheduler) is present. Scheduling is entirely external and undocumented.

## Configuration Management

| Configuration Item | Location | Type |
|-------------------|----------|------|
| DB JDBC URL | `applicationContext.xml` line 44 | Hardcoded |
| Properties file path | `applicationContext.xml` line 20 | Hardcoded absolute Windows path |
| `inputfilepath` | `NameScreening.properties` (external, not in repo) | Runtime property |
| DB username/password | CLI args at runtime | Plaintext command-line |
| Fallback credentials | `NameScreeningConstants.java` lines 25–26 | Hardcoded in source |
| Maven server passwords | `.mvn/wrapper/settings.xml` lines 38–51 | Plaintext in VCS |
| Log4j configuration | Not present in repo | Presumably external or absent |

- **No environment profiles**: There is no dev/test/prod profile separation in `applicationContext.xml` or Maven POM. The single hardcoded URL points to what appears to be a production Citi-era SQL Server.
- **No secrets management**: No integration with Vault, AWS Secrets Manager, Azure Key Vault, or any equivalent system.

## Observability

- **Logging framework**: Commons Logging over Log4j 1.2.15 (`pom.xml` lines 22–29, 42–45). Log4j 1.x reached EOL in 2015 and has multiple known critical CVEs (including CVE-2019-17571).
- **Log appender**: `biz.minaret.log4j:datedFileAppender:1.0.3` — a third-party dated rolling file appender. No log4j.properties or log4j.xml is present in the repository; the appender configuration must be supplied externally.
- **Log content**: INFO level logs the full SQL query string, row values, DDA numbers, and card IDs (NameScreeningDAO.java lines 86, 108–110). This is a PII / sensitive data logging concern.
- **Metrics**: None. No JMX, Micrometer, Prometheus, or any metrics instrumentation.
- **Alerting**: None. Job success/failure is communicated only via OS exit code (0/1).
- **Health checks**: None.
- **Tracing**: None.

## Infrastructure Dependencies

| Dependency | Version | Status / Risk |
|-----------|---------|--------------|
| Java JDK | 1.6 (compiled target) | Critical: EOL since 2013, numerous CVEs |
| Spring Framework | 2.5.6 | Critical: EOL, last release ~2010 |
| Log4j | 1.2.15 | Critical: EOL 2015, CVE-2019-17571 |
| Apache Commons DBCP | 1.2.2 | High: very old, superseded by DBCP2 |
| Apache Commons Pool | 1.2 | High: very old |
| Apache Commons Logging | 1.1.1 | Medium: old |
| Jakarta POI | 3.0.1 | High: very old HSSF-only build |
| jTDS JDBC | 1.2.2 | Medium: last release 2013, unmaintained |
| SQL Server | Ecountcore on `ppamwdcpisql1b1.nam.nsroot.net` | Unknown: Citi-era hostname, likely unreachable |
| Nexus artifact repo | `d-na-stk01.nam.wirecard.sys:8081` | Likely decommissioned (Wirecard hostname) |

## Operational Risks

1. **Hardcoded production host** — The JDBC URL points to a Citi/Wirecard-era SQL Server. If this host is still reachable it is a production system with no environment separation.
2. **No error recovery** — Any exception in a single row's processing is caught and logged, but the batch continues. If the DB connection fails mid-batch, subsequent rows silently produce empty results with "No Possible Outcomes" written to the XLS without any operator notification.
3. **File handle leak risk** — In `NameScreeningHelper.updateWorkbook`, `xlInputStream` is closed only inside the `if(null != result)` block (line 209). If `result` is null, the `FileInputStream` is never closed.
4. **Connection not pooled** — `NameScreeningDAO` uses `DriverManagerDataSource` (not a pooling datasource), and opens and closes a new JDBC connection for every single name row. For large input files this creates significant connection overhead.
5. **Single-threaded sequential processing** — All name rows are processed serially with no parallelism.
6. **Output file corruption risk** — The output XLS is opened for read and then overwritten in the same method. If the JVM crashes between the `FileInputStream` read and `FileOutputStream` write, the file is left truncated or empty.

## CI/CD

- **CodeQL analysis**: `.github/workflows/codeql.yml` runs CodeQL on a schedule (`cron: 18 3 * * 6`, Saturdays at 03:18 UTC) and on `workflow_dispatch`. It uses the reusable workflow `Onbe/om-ci-setup/.github/workflows/codeql-auto.yml@main` with a self-hosted Linux runner (`self-hosted, X64, Linux, ubuntu-docker`).
- **Dependabot**: `.github/dependabot.yml` configures weekly Maven dependency version checks.
- **No build CI pipeline**: There is no GitHub Actions workflow for compiling, testing, or publishing the artifact. CodeQL is the only automated pipeline step.
- **No deployment pipeline**: No workflow triggers a deploy, no environment promotion, no release tagging. The `1.0.0-SNAPSHOT` version has never been released.
- **No test gate**: No automated tests exist, so the CI cannot enforce quality before merge.
