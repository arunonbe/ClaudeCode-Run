# cancel-transaction-process_LIB — DevOps & Operations View

## Build & Packaging

- **Build tool:** Apache Maven 3 (Maven Wrapper present; `mvnw` / `mvnw.cmd`)
- **Maven Wrapper target version:** 3.9.1 (`.mvn/wrapper/maven-wrapper.properties`)
- **Parent POM:** `com.citi.prepaid:prepaid-parent:3`
- **Artifact:** `com.citi.prepaid.processes.canceltransactionprocess:canceltransactionprocess:1.0.1-SNAPSHOT`
- **Packaging:** `jar` (standalone executable JAR via `maven-assembly-plugin`)
- **Assembly:** `jar-with-dependencies` descriptor produces a fat JAR (`canceltransactionprocess-jar-with-dependencies.jar`) alongside the thin JAR; `finalName` is `canceltransactionprocess`.
- **Main class declared in manifest:** `com.citi.prepaid.processes.canceltransactionprocess.CancelTransactionProcessMain`
- **Source JAR:** `maven-source-plugin:3.2.0` generates a `-sources.jar` on every build.
- **Release plugin:** `maven-release-plugin:3.0.0-M1` configured for SCM-based releases.
- **Tests are skipped in CI** across all phases:
  - `MAVEN_BUILD_OPTS: "-Dmaven.test.skip=true"`
  - `MAVEN_TEST_OPTS: "-Dmaven.test.skip=true"`
  - `MAVEN_DEPLOY_OPTS: "-Dmaven.test.skip=true -Dmaven.javadoc.skip=true"`
  (`.gitlab-ci.yml`)

The only test present (`AppTest.java`) is a JUnit 3 stub (`assertTrue(true)`) — no functional test coverage exists.

---

## Deployment

- **Deployment type:** Command-line batch process (not a web service or daemon).
- **Execution mechanism:** A `.bat` script (`scripts/canceltransactionprocess-abat.bat`) launches the fat JAR:
  ```bat
  java -jar canceltransactionprocess.jar -config "%CONFIG_FILE%" -log "%LOG4J_FILE%"
  ```
- **Configuration directory:** Resolved from the `CBASE_HOME_URL` environment variable at runtime:
  - Config XML: `$CBASE_HOME_URL/config/canceltransactionprocess/canceltransactionprocess.xml`
  - Log4j XML: `$CBASE_HOME_URL/config/canceltransactionprocess/log4j.xml`
  - Properties: `$CBASE_HOME_URL/config/canceltransactionprocess/canceltransactionprocess.properties`
- **Exit codes:**
  | Code | Meaning |
  |---|---|
  | 0 | Success |
  | 1 | Process exception (failed/incomplete tasks, unexpected errors) |
  | 2 | Database / data exception |
  | 3 | Other fatal exception |
  | 4 | Log4j initialisation failure |
- **Scheduling:** Not implemented in this library. The bat script (`-abat.bat`) naming convention suggests invocation by an external scheduler (likely a Windows Task Scheduler or equivalent platform job runner labelled "ABAT" — Automated Batch).
- **SCM:** GitLab (`gitlab.com/northlane/development/application-development/libraries/cancel-transaction-process`); repository has been migrated to the Onbe GitHub organisation (CodeQL workflow references `Onbe/om-ci-setup`).

---

## Configuration Management

All runtime configuration is externalised; no hardcoded values for environment-specific settings exist in the source code.

| Parameter | Source | Description |
|---|---|---|
| `agent` | `canceltransactionprocess.properties` | ecount agent identifier used for Core API calls and data source lookup |
| `memberId` | `canceltransactionprocess.properties` | ecount member ID |
| `director.address` | `canceltransactionprocess.properties` | ecount Director service address (provides DB connection strings) |
| `ecountcore.database` | `canceltransactionprocess.properties` | Logical name of the Core database in Director |
| `cbaseapp.database` | `canceltransactionprocess.properties` | Logical name of the CBase App database in Director |
| `CBASE_HOME_URL` | OS environment variable | Root path for all config and log files |

The properties file is resolved by `PropertyPlaceholderConfigurer` in `cancelTransactionProcessContext.xml` with `systemPropertiesModeName=SYSTEM_PROPERTIES_MODE_OVERRIDE`, meaning system properties take precedence over the properties file.

**The actual `canceltransactionprocess.properties` and `canceltransactionprocess.xml` (consumer config) are not in this repository** — they live in the deployed environment under `$CBASE_HOME_URL/config/`.

`ThreadPoolExecutor` (executor bean), `ProcessRunData` bean (with `cancelAge`, `fromCancelAge`, `maxTry`, `minSleepTime`, `maxSleepTime`, `limitTransactions`, `transactionTypes`) are expected to be defined in the consumer-supplied `canceltransactionprocess.xml`, not in the library's bundled `cancelTransactionProcessContext.xml`.

---

## Observability

- **Logging framework:** Apache Commons Logging (`commons-logging:1.1`) as the facade; Log4j as the backend, configured via an external `log4j.xml` loaded from `$CBASE_HOME_URL`.
- **Custom logging wrapper:** `FormatLog` / `FormatLogFactory` — a `MessageFormat`-based wrapper around `commons-logging.Log` for parameterised log messages.
- **Log4j MDC propagation:** `MDCWriter` (ecount Spring Utils AOP) writes `audit.global.request.id` (a UUID) to the Log4j MDC on each execution thread, enabling correlation of all log lines for a single process invocation.
- **Dated log file appender:** `biz.minaret.log4j:datedFileAppender:1.0.3` dependency — log rotation by date.
- **JMX monitoring:** `ControllerJMXExporter` exposes runtime metrics at JMX bean `prepaid:name=CancelProcess`:
  - `getTaskCount()`, `getFailedCount()`, `getIncompleteCount()`, `getFinishedCount()`, `getRetryCount()`
  - Operations: `forceTerminate()`, `terminateAllTasks()`, `terminateTask(transferId)`
  - Log4j hierarchy also exposed at `log4j:hiearchy=default` and `prepaid:name=log4j`.
- **No metrics / APM integration** (no Micrometer, Prometheus, Datadog, etc.).
- **No distributed tracing** (no OpenTelemetry, Zipkin, etc.).
- **Process summary** is logged at INFO level at completion: total tasks, failed, incomplete, retry, finished counts.

---

## Infrastructure Dependencies

| Dependency | Purpose | Notes |
|---|---|---|
| JVM (Java) | Runtime | Version not pinned in pom.xml; parent POM `prepaid-parent:3` likely specifies it |
| ecount Director service | Dynamic data source configuration | Address from `director.address` property |
| Core DB (ecount) | Read pending transactions | Via `core_pending_transactions_inquiry` stored procedure |
| CBase App DB | Write debit audit records | Via `card_balance_debit_update_job` stored procedure |
| eCore / Core API | Cancel transfer state transitions | `com.cbase.business.core.spi.ecore.ECoreTransfer` — network call to Core backend |
| `CBASE_HOME_URL` filesystem path | Config and log files | Must be a writable directory on the executing host |
| Windows OS (for bat script) | Batch execution | `canceltransactionprocess-abat.bat` is Windows-specific |

---

## Operational Risks

1. **Tests skipped in all CI phases.** The `.gitlab-ci.yml` skips tests in every stage. The only test is a no-op stub. Regressions are not caught by the pipeline.
2. **Default transaction limit of 101 causes hard failure.** If the pending queue exceeds 101 entries per source/facility, the process aborts with `DataLimitException` rather than processing in chunks. Operations must increase the limit or reduce queue depth manually.
3. **Thread pool shutdown race.** In multi-threaded mode, `executor.shutdown()` is called then `executor.awaitTermination()`. If the timeout (`waitTimeout`, default 1 hour) expires, `threadPoolWaitInterrupted=true` and a `Thread.sleep(waitBeforeTerminate)` (default 5000 ms) is used before `shutdownNow()`. This delay may cause the process to appear hung to the job scheduler.
4. **No re-entrancy protection between process runs.** `Controller.started` prevents double execution within a single JVM, but if the JVM is restarted and the same transfers are still pending, they will be re-processed (which is safe due to Core's end-state checks, but creates unnecessary load).
5. **Bat script does not capture log output.** The commented-out `LOG_FILE` line in `canceltransactionprocess-abat.bat` (line 2) suggests log redirection was removed; stdout/stderr handling is unclear.
6. **Spring version 2.5.6** is declared in `pom.xml` properties but the actual resolution depends on `prepaid-parent`; this is a very old Spring version and may conflict with modern security tooling.

---

## CI/CD

| Tool | Configuration | Notes |
|---|---|---|
| GitLab CI | `.gitlab-ci.yml` — inherits `maven.gitlab-ci.yml` template from `northlane/development/application-development/configuration/ci-templates` (`refactor` branch) | Maven build, test (skipped), deploy stages |
| GitHub Actions (CodeQL) | `.github/workflows/codeql.yml` — triggered weekly (Wed 18:11 UTC) and on `workflow_dispatch` | Uses `Onbe/om-ci-setup/.github/workflows/codeql-auto.yml@main`; runs on self-hosted Linux x64 runner |
| Dependabot | `.github/dependabot.yml` — Maven ecosystem, weekly schedule | Automated dependency update PRs |

Two separate CI systems (GitLab and GitHub) are active, indicating a migration from GitLab to GitHub/Onbe is in progress or both are being maintained in parallel.

Javadoc generation is skipped in the deploy phase (`-Dmaven.javadoc.skip=true`).
