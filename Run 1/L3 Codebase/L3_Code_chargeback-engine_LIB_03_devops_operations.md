# chargeback-engine_LIB — DevOps & Operations View

## Build & Packaging

- **Build tool**: Apache Maven, wrapped via Maven Wrapper (`mvnw` / `mvnw.cmd`). Wrapper targets Maven 3.9.1 (`maven-wrapper.properties` line 17).
- **Compiler target**: Java 1.6 (`pom.xml` lines 54-55 — `maven-compiler-plugin` 2.3.2 with `<source>1.6</source>` and `<target>1.6</target>`).
- **Packaging**: `jar` with a fat-JAR produced by `maven-assembly-plugin` using `jar-with-dependencies` descriptor, bound to the `package` phase (`pom.xml` lines 58-74). The output artifact is `chargeback_engine-0.0.1-SNAPSHOT-jar-with-dependencies.jar`.
- **Version**: `0.0.1-SNAPSHOT` — a SNAPSHOT version, meaning the artifact is not a stable release and will be rebuilt on every `mvn deploy`.
- **Artifact coordinates**: `com.ecount.process:chargeback_engine:0.0.1-SNAPSHOT`.

### Key Dependencies

| Dependency | Version | Status |
|---|---|---|
| `org.springframework:spring` | 2.5.6.SEC02 | End-of-life (~2009); known CVEs |
| `com.ecount.service.Core2:ecount-system` | 1.0.10 | Internal proprietary library |
| `commons-httpclient:commons-httpclient` | 3.0 | End-of-life; superseded by Apache HttpClient 4.x+ |
| `junit:junit` | 3.8.1 (test scope) | End-of-life; JUnit 3 API |

The `ecount-system` dependency is sourced from the internal Nexus repository at `d-na-stk01.nam.wirecard.sys:8081` (settings.xml line 12), which contains a Wirecard-era hostname, indicating this repository configuration predates the Onbe rebranding.

---

## Deployment

- **Execution model**: Standalone runnable JAR executed as a batch process (likely via OS task scheduler or cron). `ChargebackMain.main()` is the entry point. No application server, container, or daemon framework is used.
- **Arguments**: Accepts an optional integer `process_id` as `args[0]`. If omitted, the process calls `exec chargeback_process_begin` to obtain one.
- **Exit codes**:
  - `System.exit(1)` on any fatal error (config load failure, invalid process_id, thread timeout, end-procedure error, errors flagged by workers).
  - Implicit exit code `0` on clean completion.
- **No Dockerfile, Kubernetes manifest, or container configuration** is present. Deployment is bare-metal/VM JAR execution.
- **No deployment scripts** are included in the repository.

---

## Configuration Management

All configuration is externalised to two classpath files:

### `src/main/resources/ChargebackProcess.properties`

| Property | Value | Notes |
|---|---|---|
| `director.address` | `http://ppamwdcddcor1:80/service/dispatch.asp` | HTTP (not HTTPS); internal Director service hostname |
| `core_agent` | `b2ctest` | Agent name — value contains "test", may be incorrect for production |
| `core_database` | `ecountcore` | Core DB name |
| `core_timeout` | `60` | Seconds |
| `vendor_agent` | `b2ctest` | Same "test" agent as core — suspicious for production |
| `vendor_database` | `vendor` | Reporting DB name |
| `vendor_timeout` | `7200` | 2-hour query timeout |
| `ods_timeout` | `60` | ODS query timeout (seconds) |
| `ods.driverClassName` | `sun.jdbc.odbc.JdbcOdbcDriver` | Removed from JDK 8+; not suitable for modern JVMs |
| `ods.url` | `jdbc:odbc:mcyc` | ODBC DSN; two alternatives commented out |
| `ods.username` | `CBASEAPP` | **Plaintext credential in committed file** |
| `ods.password` | `ECOUNT` | **Plaintext credential in committed file** |
| `threadpoolsize` | `20` | Controls both thread pool size and DBCP `maxActive` |

### `src/main/resources/ChargebackProcess.xml`

Spring 2.x XML bean definition file. Loaded from the classpath at startup. There is no environment-specific profile switching — only a single configuration file is present.

- **No environment variable substitution** for sensitive values; they are read directly from the `.properties` file.
- **No secrets manager integration** (HashiCorp Vault, AWS Secrets Manager, etc.).
- **Director address uses HTTP** (not HTTPS) — all traffic to the Director service is unencrypted.
- The `vendor_agent` and `core_agent` values are both `b2ctest`, which appears to be a test/development value left in the committed configuration.

---

## Observability

### Logging

- **Framework**: Log4j 1.x (`log4j.xml`). Log4j 1.x is end-of-life and was subject to Log4Shell-adjacent CVEs (though the critical Log4Shell CVE affected Log4j 2.x; Log4j 1.x has its own separate unresolved CVEs).
- **Appenders**: Rolling file (`chargeback_engine.log`, max 10 MB, 10 backups = ~100 MB max) + Console (`System.out`).
- **Log pattern**: `%d [%.50t] %-5p %40.40c - %m%n`
- **Log levels by package**: `com.ecount` and `com.cbase` → INFO; `com.citi.prepaid` and `com.citiprepaid` → INFO; root → WARN.
- **Structured logging**: None. All log output is free-text via `log.info/debug/error`.
- **No metrics emission**: No JMX, Micrometer, Prometheus, StatsD, or any metrics instrumentation.
- **No tracing**: No distributed tracing (Zipkin, OpenTelemetry, etc.).
- **No health checks**: No HTTP endpoint or probe mechanism.
- **Sensitive data in logs**: `ChargebackHelper.java` line 36 logs `result=` from ODS, which contains `CB_PRCS_ID`. The `dda_number` is NOT directly logged, but `description` and ODS results are.

### Alerting

No alerting integration is present. Failures surface only via non-zero JVM exit code and log messages. External monitoring would need to inspect the exit code or log file.

---

## Infrastructure Dependencies

| Dependency | Type | Address / Detail |
|---|---|---|
| Director service | Internal HTTP service | `http://ppamwdcddcor1:80/service/dispatch.asp` (HTTP, no TLS) |
| Core DB (`ecountcore`) | SQL Server (inferred) | Resolved via Director using agent `b2ctest` |
| Vendor/Reporting DB (`vendor`) | SQL Server (inferred) | Resolved via Director using agent `b2ctest` |
| FDR ODS | ODBC DSN `mcyc` | Local ODBC DSN; must be pre-configured on the host OS |
| Nexus repository | Maven artifact server | `d-na-stk01.nam.wirecard.sys:8081` (Wirecard-era hostname) |
| GitHub Packages | Maven artifact server | `maven.pkg.github.com/onbe/onbe_maven_releases` |
| Java runtime | JVM | Must be Java 6-compatible; `sun.jdbc.odbc.JdbcOdbcDriver` requires Java 7 or earlier (removed in Java 8) |

The ODBC DSN requirement (`mcyc`) means the application **cannot run on any JDK 8+ host** without replacing the driver, as `sun.jdbc.odbc.JdbcOdbcDriver` was removed in Java 8.

---

## Operational Risks

| Risk | Impact | Detail |
|---|---|---|
| JDK 6/7 requirement | Critical | `sun.jdbc.odbc.JdbcOdbcDriver` removed in JDK 8; running on JDK 8+ breaks ODS connectivity |
| `core_agent=b2ctest` in properties | High | "test" agent value may route production runs to a test database; requires verification |
| No retry on ODS failure | High | Failed chargebacks are silently recorded with `fee_amount=0` and move on; no re-attempt mechanism |
| Thread pool overflow not bounded | Medium | `LinkedBlockingQueue` is unbounded (`ChargebackMain.java` line 43); if the stored procedure returns millions of rows, memory exhaustion is possible |
| Log4j 1.x with unresolved CVEs | High | Chainsaw receiver-related CVEs in Log4j 1.x remain unpatched |
| 2-hour ODS query timeout (`vendor_timeout=7200`) | Medium | Individual chargeback records queued in the thread pool could hold connections for up to 2 hours |
| `has_errors` race condition | Medium | `Context.has_errors` (plain boolean) written from multiple threads; final status may be incorrect under concurrent errors |
| No process lock / mutex | Medium | Nothing prevents two instances running simultaneously; `chargeback_process_begin` is the only guard |

---

## CI/CD

- **GitHub Actions workflow**: `.github/workflows/codeql.yml` — runs CodeQL static analysis only.
  - Trigger: `workflow_dispatch` (manual) and weekly schedule (`cron: 24 4 * * 2` — Tuesdays at 04:24 UTC).
  - Delegates to reusable workflow `Onbe/om-ci-setup/.github/workflows/codeql-auto.yml@main`.
  - Runner: self-hosted (`self-hosted, X64, Linux, ubuntu-docker`).
- **Dependabot**: `.github/dependabot.yml` — weekly Maven dependency update PRs from the root directory.
- **No build CI pipeline**: There is no workflow that builds, tests, or publishes the JAR on push or pull request. CodeQL is the only automated CI action.
- **No automated test execution in CI**: The one test class (`InitTest.java`) requires live database connectivity and is not configured to run in the CI pipeline.
- **No deployment pipeline**: No CD pipeline, Helm chart, Ansible playbook, or deployment workflow exists in the repository.
