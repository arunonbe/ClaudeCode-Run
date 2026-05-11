# citi-direct-file-process_LIB — DevOps & Operations View

## Build & Packaging

- **Build tool**: Apache Maven. Maven Wrapper is present (`.mvn/wrapper/`), pinned to Maven 3.9.1 (`maven-wrapper.properties` line 17).
- **Artifact**: `CitiDirectFile-1.0.1.jar` (`pom.xml` lines 4-6). The `maven-jar-plugin` is configured to embed `com.ecount.one.etl.reports.CitiDirectFileProcess` as the `Main-Class` in `MANIFEST.MF` (lines 78-87).
- **Fat-jar support**: `maven-assembly-plugin` with `jar-with-dependencies` descriptor is declared (lines 90-96), enabling production of a self-contained executable JAR. This is the likely deployed artifact.
- **Java version**: Not explicitly declared in `pom.xml`; no `maven-compiler-plugin` configuration or `<java.version>` property. The build will use whatever JDK is on the CI runner's PATH.
- **No test sources**: The only test dependency is `junit:3.8.1` (line 12) at test scope. No test source files exist under `src/test/`. Coverage is zero.
- **Spring version**: `spring:1.2.7` — this is Spring Framework 1.x from approximately 2006, well beyond end-of-life.

## Deployment

- **Execution model**: Command-line Java application. Deployed as a JAR and invoked via a scheduler (likely a cron job or Windows Task Scheduler based on the `d:/c-base/...` path in `etlContext.properties`).
- **Runtime arguments**: `args[0]` = base output file path including filename (e.g., `d:/c-base/runtime/citidirectfile/citidirect.txt`). The process appends `_yyyyMMddkkmmss` before the `.txt` extension (`CitiDirectFileProcess.java` lines 143-147).
- **Exit codes**:
  - `0` = success
  - `1` = missing argument, Spring context error, or unhandled `Throwable`
  - `-1` = output path null or file open failure
- **Log file location**: Controlled by system property `log.file` set to `args[0] + ".log"` (line 136); the Log4j `RollingFileAppender` writes to `citidirect.log` (hardcoded in `log4j.properties` line 9) — there is a mismatch: the system property sets `log.file` but Log4j is configured with a literal path, not a reference to `${log.file}`. The system-property-based log path has no effect at runtime.
- **Classpath resources required at runtime**:
  - `etlContext.xml` (loaded via `ClassPathXmlApplicationContext`)
  - `etlContext.properties` (referenced inside `etlContext.xml`)
  - `log4j.properties`
  - `newAccountFileTemplate.xml` and `newAccountFileTemplate.xsd` (loaded from `CitiDirectFilePath` directory, NOT from classpath — `CitiDirectAccountFile.java` line 129-130)
- **Director service dependency**: The process requires network access to the Director HTTP endpoint to obtain a database connection pool. If the Director service is unavailable, the process fails at startup.

## Configuration Management

| Property | File | Value (checked in) | Risk |
|---|---|---|---|
| `director.address` | `etlContext.properties` | `http://ecappdev/service/dispatch.asp` | Dev/test endpoint hardcoded; must be overridden for production |
| `agent` | `etlContext.properties` | `B2CTEST` | Test agent hardcoded; production deployment requires override |
| `database` | `etlContext.properties` | `EcountCore` | Likely correct for production but no environment separation |
| `CitiDirectFilePath` | `etlContext.properties` | `d:/c-base/runtime/citidirectfile/` | Windows path hardcoded; incompatible with Linux deployment |

Configuration is loaded from classpath at startup via Spring `PropertyPlaceholderConfigurer` (`etlContext.xml` lines 5-10). There is no environment-variable or external-config-file override mechanism; changing configuration requires replacing the JAR's embedded `etlContext.properties` or providing a different classpath entry at runtime.

No secrets management (Vault, AWS Secrets Manager, etc.) is used. All configuration is plaintext in `.properties` files committed to the repository.

## Observability

- **Logging framework**: Log4j 1.2.15 (EOL). Two appenders: `ConsoleAppender` (stdout) and `RollingFileAppender` (`citidirect.log`, max 100 KB, 1 backup).
- **Log levels used**: `INFO` for normal milestones (`>> Started`, `>> Initialized`, `>> Done`), `ERROR` for exceptions, `DEBUG` for agent name. No `WARN` usage observed.
- **Log gaps**:
  - The `log.file` system property is set but never referenced in `log4j.properties`; the log file location is hardcoded to `citidirect.log` relative to the working directory.
  - No structured logging; all messages are free-text strings.
  - No correlation ID, job ID, or run ID in any log message.
  - No metrics or counters emitted (e.g., to Prometheus, Splunk, Datadog).
- **Health checks**: None. No liveness probe, heartbeat, or status endpoint exists.
- **Alerting**: None built into this library. Any alerting must be configured externally (e.g., monitoring the process exit code).

## Infrastructure Dependencies

| Dependency | Details | Risk |
|---|---|---|
| Director service | `http://ecappdev/service/dispatch.asp` | Single point of failure; plain HTTP; dev URL hardcoded |
| SQL Server (EcountCore) | jTDS JDBC driver 1.2.2 | jTDS is no longer maintained; SQL Server 2019+ may require Microsoft JDBC driver |
| Filesystem path | `d:/c-base/runtime/citidirectfile/` | Windows path; process must run on Windows or path must be reconfigured |
| JDK | Unspecified version | No JDK pinning; behaviour may vary by environment |
| `newAccountFileTemplate.xml` | Must exist at `CitiDirectFilePath` at runtime | Not bundled in JAR; deployment process must place it correctly |

## Operational Risks

1. **Test credentials in committed config** — `agent=B2CTEST` and `director.address=http://ecappdev/service/dispatch.asp` are committed. Accidental production deployment with this config would generate a CitiDirect file from test data.
2. **No idempotency / duplicate prevention** — if the process is run twice for the same day (e.g., after a failure), it will produce a second output file. There is no deduplication guard; Citibank could receive duplicate payment instructions.
3. **`System.exit()` anti-pattern** — five uses of `System.exit()` prevent calling code from handling errors gracefully and prevent the process from being embedded in a container or orchestration framework.
4. **Log file location mismatch** — the `log.file` system property set in `main()` is ignored by Log4j; the log always writes to a relative-path `citidirect.log`, which could overwrite or co-mingle logs from concurrent runs if deployed in a shared working directory.
5. **Log rotation too aggressive** — 100 KB + 1 backup means a maximum of ~200 KB of history. A single large run could exhaust the log before completion.
6. **File not cleaned up on failure** — if the process fails mid-write, a partial output file remains at the output path with no `.failed` or `.tmp` extension to mark it as incomplete.

## CI/CD

- **Workflow**: GitHub Actions. Two workflows present:
  - **CodeQL** (`.github/workflows/codeql.yml`): Runs on `workflow_dispatch` and weekly on Fridays at 00:39 UTC. Uses the shared `Onbe/om-ci-setup/.github/workflows/codeql-auto.yml@main` reusable workflow on a self-hosted Linux x64 Ubuntu Docker runner. Secrets are inherited.
  - **Dependabot** (`.github/dependabot.yml`): Configured for `maven` ecosystem, weekly updates from the root directory.
- **Missing pipeline stages**:
  - No build/compile step in CI (no `mvn package` or `mvn verify` workflow).
  - No test execution step (no unit tests exist).
  - No artifact publication (no Maven deploy or GitHub Packages push).
  - No deployment pipeline of any kind.
- The only automated CI activity is static security scanning (CodeQL) and dependency version updates (Dependabot). There is no build, test, or publish pipeline.
