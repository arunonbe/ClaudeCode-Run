# check-issuance_LIB — DevOps & Operations View

## Build & Packaging

- **Build tool:** Apache Maven 3.9.1 (via Maven Wrapper; `mvnw` / `mvnw.cmd`; `maven-wrapper.properties` line 17).
- **Java source/target level:** Java 1.6 (`pom.xml` lines 133–134 — `maven-compiler-plugin` configuration). This is severely outdated (EOL since 2013).
- **Packaging:** JAR with dependencies fat-JAR produced by `maven-assembly-plugin` at `package` phase; goal `attached`. Final name is `CheckIssuance-1.0.0` (`pom.xml` line 185). The assembly descriptor `assembly.xml` also packages a ZIP containing the JAR and runtime dependencies.
- **Source JAR:** `maven-source-plugin:3.2.0` is configured to produce a `-sources.jar` artefact alongside the binary JAR.
- **Release plugin:** `maven-release-plugin:3.0.0-M1` is configured. The SCM URL (`pom.xml` lines 20–23) points to `gitlab.com/northlane/development/application-development/libraries/check-issuance.git`.
- **Version:** `2.0.1-SNAPSHOT` — library is in an unreleased snapshot state.
- **Parent POM:** `com.citi.prepaid.service:service-parent:8` — this parent must be resolvable from the Maven repository at build time; it is an internal Citi/ecount/Northlane artefact not available in Maven Central.
- **Tests are skipped in CI:** `.gitlab-ci.yml` sets `MAVEN_BUILD_OPTS`, `MAVEN_TEST_OPTS`, and `MAVEN_DEPLOY_OPTS` all to `-Dmaven.test.skip=true`. Tests are never executed in any pipeline phase.
- **Tests are also trivially empty:** `src/test/java/TestClass.java` contains only `System.out.println("hii")`.

## Deployment

- **Runtime model:** Standalone Java batch process launched by `CheckIssuance.VBS` (Windows VBScript). The VBS launches the JAR via:
  ```
  java -classpath .;CheckIssuance-1.0.0-jar-with-dependencies.jar; com.ecount.process.check.CheckIssuance
  ```
  (`CheckIssuance.VBS` line 61)
- **OS requirement:** Windows (VBScript launcher, WMI process enumeration, `D:\` drive paths throughout).
- **Concurrency guard:** `CheckIssuance.VBS` uses WMI `Win32_Process` enumeration to detect if another instance is already running. If a duplicate is found, it exits with code `-999` (line 44). This guard is brittle — it relies on exact command-line string matching.
- **Stop-Refund Check deployment:** `citiCPSStopRefundCheck.vbs` requires:
  - `perl.exe` on `d:\c-base\bin\`
  - `C:\Program Files\Microsoft SQL Server\100\Tools\Binn\bcp.exe` (SQL Server 2008 R2 BCP tool)
  - Sterling Connect:Direct client (`NDM-EXEC.VBS`)
  - A config INI file at `D:\C-Base\runtime\ndmroot\<USER>\program\importconfig.ini`
- **Target environment:** A Windows server with `D:\c-base\` directory structure, Perl runtime, SQL Server BCP utilities, and Sterling NDM client installed.
- **No containerisation:** No Dockerfile, no Docker Compose, no Kubernetes manifests. The deployment model is a traditional Windows scheduled task or job-scheduler invocation.

## Configuration Management

All runtime configuration is externalised via two properties files referenced in `appContext.xml`:

| File Path (hardcoded) | Properties Used |
|---|---|
| `file:///d:/c-base/config/checkissuance/checkissuance.properties` | `ecount.agent`, `ecountcore.database`, `jobsvc.database`, `select_query_timeout`, `update_query_timeout`, `checkissuance.records.count`, `checkissuance.maximum.threads`, `exception_code_list`, `operatorid`, `max.recovery.retries` |
| `file:///d:/c-base/config/director-client.properties` | `director.address` |

Key configuration parameters and their purpose:

| Property | Used In | Purpose |
|---|---|---|
| `checkissuance.records.count` | `CheckIssuanceTransactionsList` constructor | Batch size per SP call |
| `checkissuance.maximum.threads` | `ProcessCheckRecordsImpl` constructor | Thread pool size |
| `exception_code_list` | `CheckIssuanceHelper` | Comma-separated error codes treated as terminal (no retry) |
| `operatorid` | `CheckIssuanceHelper.transferFunds()` | Operator ID for fund transfer |
| `max.recovery.retries` | `CheckIssuanceHelper.retryHandler()` | Max retries before force-cancel (default 3) |
| `select_query_timeout` | `checkIssuanceTransactionsList` bean | SP read timeout (seconds) |
| `update_query_timeout` | `checkIssuanceUpdTransaction` bean | SP write timeout (NOTE: commented out in Java code) |
| `ecount.agent` | Multiple beans | Agent identifier used for core API calls |

**Problems:**
- Config file paths are absolute Windows paths hardcoded in `appContext.xml` — not environment-parameterised.
- There is no secrets manager (Vault, AWS Secrets Manager, etc.) integration. DB passwords for the BCP operations are in plaintext INI files.
- The `appContext.xml` Spring config uses the old Spring 2.x DTD format (`spring-beans.dtd`) — not namespace-based XML and not Spring Boot auto-configuration.

## Observability

- **Logging framework:** Apache Log4j `1.2.14` (EOL; known CVEs including Log4Shell-adjacent issues, though direct Log4Shell CVE-2021-44228 is a Log4j2 issue).
- **Log destination:** Rolling file at `D:/c-base/log/CheckIssuance/checkissuance.log` with max 10 MB per file and 50 backup indices (`src/main/resources/log4j.properties`). A console appender is also declared (`src/log4j.properties`).
- **Log verbosity:** Root logger is `debug` — all debug-level statements including DDA numbers and device IDs are written to disk by default.
- **Operational counters:** `CheckIssuanceHelper` logs summary counters at the end of each `issueCheck()` call:
  - `failuresCount`, `successCount`, `commitCountFailure`, `cancelCountFailure`
  - `simpleFeeInquiryFalureCount`, `getAccountDetailsFalureCount`, `transactionInquiryFailureCount`
  - `accountNotActiveORbalance`, `exceptionCodeCountFailure`
  These are only emitted to the log — there is no metrics emission (no JMX, no Prometheus, no StatsD).
- **No distributed tracing:** No correlation IDs are propagated beyond the `transaction_uuid`.
- **No health checks:** No HTTP endpoint or JMX bean exposes process health.
- **No alerting integration:** No SNMP trap, no webhook, no email notification on failure from the Java code itself.
- **Exit codes:** `CheckIssuance.java` calls `System.exit(0)` on success and `System.exit(-1)` on `Throwable` — allowing the VBS wrapper to capture and act on the return code.

## Infrastructure Dependencies

| Dependency | Type | Notes |
|---|---|---|
| Microsoft SQL Server | RDBMS | Connected via jTDS 1.2.4 JDBC driver; exact version unknown |
| ecount Core API (Director) | Internal RPC service | `TransferManagerImpl`, `DeviceInfoManagerImpl`, `ECoreTransfer` — proprietary ecount/cbase platform |
| Director service | Service registry | Resolves data source connection strings at runtime |
| Sterling Connect:Direct (NDM) | File transfer | Used for transmitting stop-refund files to Citi mainframe |
| Citi Mainframe (MVS) | Downstream processor | Receives check issuance and stop-refund files; runs `PGM=CSYUEV3` |
| Perl runtime | Script dependency | `d:\c-base\bin\citiReportParser.pl` — requires Perl modules: `Text::CSV`, `Date::Manip`, `Date::Calc`, `Digest::SHA1`, `Encode` |
| SQL Server BCP tool | Data extraction | `C:\Program Files\Microsoft SQL Server\100\Tools\Binn\bcp.exe` — SQL Server 2008 R2 vintage |
| Windows WMI | Process guard | `CheckIssuance.VBS` uses WMI for duplicate-instance detection |
| ehcache 1.2.3 | Caching | Declared as dependency — not observed in use within this library's own classes |
| commons-pool 1.4 | Connection pooling | Used by DBCP for SQL Server connection pool |

## Operational Risks

1. **Java 1.6 runtime requirement** — Java 6 is EOL. No security patches have been available since February 2013. Any modern JRE will run the bytecode but the compiled target is Java 6 class format — a compliance liability.
2. **Log4j 1.2.14** — Log4j 1.x reached end-of-life in 2015 and has known CVEs (CVE-2019-17571 — SocketServer deserialization RCE). Upgrade to Log4j 2.x or SLF4J+Logback is required.
3. **No graceful shutdown handling** — `System.exit(0)` is called without waiting for in-flight threads to fully complete (the `shutdownThreadpool()` call on line 60 of `CheckIssuance.java` does not call `awaitTermination()`). If the process is killed mid-run, transactions can be left in status `1` (in-progress).
4. **Race condition in success counter** — `failuresCount`, `successCount`, and all other integer counters in `CheckIssuanceHelper` are plain `int` fields without `AtomicInteger` or `synchronized` access. Multiple `RequestProcessorThread` instances write to the same `CheckIssuanceHelper` bean concurrently. These counters will produce incorrect totals under load.
5. **BCP SQL Server 2008 tool** — The hardcoded path `C:\Program Files\Microsoft SQL Server\100\Tools\Binn\bcp.exe` references the SQL Server 2008 (v10.0 = `100`) BCP client. This is incompatible with modern SQL Server versions and is deeply outdated.
6. **Single point of failure on Director service** — All database connections are resolved through a central Director service. If Director is unavailable, the batch cannot connect to any data source and will fail silently at startup.
7. **No transaction compensation on JVM crash** — If the JVM crashes after a fund transfer is initiated but before `updCheckIssuanceTransaction()` persists the success status, the transaction remains in-progress and will be re-attempted on next run. The retry logic partially mitigates this but depends on `transactionInquiry()` to detect the prior transfer state.

## CI/CD

- **GitLab CI:** `.gitlab-ci.yml` includes a shared Maven CI template from `northlane/development/application-development/configuration/ci-templates` (ref: `refactor`). All three pipeline phases (build, test, deploy) skip tests via `-Dmaven.test.skip=true`.
- **GitHub Actions:** `.github/workflows/codeql.yml` runs a scheduled CodeQL analysis every Wednesday at 05:30 UTC and on manual dispatch. It uses `Onbe/om-ci-setup/.github/workflows/codeql-auto.yml@main` and targets a self-hosted Linux x64 runner. This is the only security scanning in place.
- **Dependabot:** `.github/dependabot.yml` is configured for weekly Maven dependency updates. However, most dependencies (Spring 2.5.4, Log4j 1.2.14, jTDS 1.2.4, commons-io 1.3.2) are far below current versions and represent significant upgrade effort due to the parent POM constraints.
- **No deployment pipeline:** There is no CD stage that deploys the JAR to a target server. The artefact is deployed to a Maven repository (`mvn deploy`) and then presumably installed manually on the Windows batch server.
- **No environment-specific profiles:** The Maven POM has no `<profiles>` section. Environment differentiation is entirely handled by external properties files.
- **Repository mirrors:** The library originates from GitLab (`gitlab.com/northlane/...`) but has a GitHub mirror with GitHub Actions workflows — dual-VCS maintenance overhead.
