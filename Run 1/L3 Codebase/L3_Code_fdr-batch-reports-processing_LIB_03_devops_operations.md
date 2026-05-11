# DevOps / Operations View — fdr-batch-reports-processing_LIB

## Build System

**Build Tool**: Maven (with Maven Wrapper `mvnw` / `mvnw.cmd`)  
**Java Version**: 1.5 (Java 5) — `pom.xml` lines 43–44: `<source>1.5</source>`, `<target>1.5</target>`  
**Artifact**: `FDRBatchReportsProcessing-1.0.0.jar` (executable JAR with main class defined)  
**Group ID**: `com.ecount.batch.fdr.reports`  
**Artifact ID**: `FDRBatchReportsProcessing`  
**Version**: `1.0.0`  
**Packaging**: JAR

### Maven Dependencies

| Dependency | Version | Purpose |
|-----------|---------|---------|
| `log4j:log4j` | 1.2.14 | Logging |
| `net.sourceforge.jtds:jtds` | 1.2.2 | jTDS JDBC driver for SQL Server |

Both dependencies are critically outdated (see security section).

### Maven Plugins

| Plugin | Purpose |
|--------|---------|
| `maven-jar-plugin` | Builds executable JAR with `FDRBatchReportsMain` as main class |
| `maven-compiler-plugin` | Sets source/target to Java 1.5 |

There is **no** Checkstyle, JaCoCo, OWASP dependency check, Surefire test execution, or Spotbugs configured. This reflects the Gen-1 vintage of this codebase — quality gates were not automated.

## CI/CD Pipeline

### GitHub Actions — CodeQL (`.github/workflows/codeql.yml`)

```yaml
name: "CodeQL"
on:
  workflow_dispatch:
  schedule:
    - cron: ...   # Weekly
jobs:
  analyze:
    uses: Onbe/om-ci-setup/.github/workflows/codeql-auto.yml@main
    secrets: inherit
    with:
      java-runner: "['self-hosted', 'X64', 'Linux', 'ubuntu-docker']"
```

CodeQL static analysis runs weekly via the centralized Onbe CI workflow. This is the only automated CI gate present.

**No PR build pipeline is visible**. There is no automated build-and-test, no dependency vulnerability scan triggered on commit, and no integration test execution.

### Dependabot (`.github/dependabot.yml`)
Configured for automated dependency update PRs.

## Deployment Model

This library is a **standalone batch JAR** intended to be scheduled as a cron job or batch scheduler task on a server. The deployment model is:

1. JAR is built and deployed to a server (historically `ecsqldev1` area, inferred from properties).
2. A cron job (or job scheduler) executes: `java -jar FDRBatchReportsProcessing-1.0.0.jar [optional-config-path]`
3. The properties file at `/c-base/config/FDRBatchReportsProcessor/FDRBatchReportsProcessor.properties` is read at startup.
4. The job runs, processes reports, and exits.

The default properties file path (`FDRBatchReportsMain.java` line 20):
```
/c-base/config/FDRBatchReportsProcessor/FDRBatchReportsProcessor.properties
```
This is a Unix/Linux absolute path, confirming on-premises Linux server deployment.

## Logging

- **Framework**: Log4j 1.x (`log4j:log4j:1.2.14`)
- **Configuration**: Embedded in `FDRBatchReportsProcessor.properties` (log4j properties format, lines 42–57)
- **Appenders**: ConsoleAppender + RollingFileAppender
- **Log file**: `FDRBatchReportsProcessor.log` (relative to working directory)
- **Max file size**: 100 KB with 1 backup

**Critical**: Log4j 1.x is end-of-life and has known critical vulnerabilities (CVE-2019-17571 — SocketServer remote code execution). This is a P0 security issue.

**Critical**: Connection strings including plaintext passwords are logged at DEBUG level (`FDRBatchAddFundsReportProcessor.java` line 225, `FDRBatchNewAccountReportProcessor.java` line 156, `FDRDatabaseNewAccountCreationReportReader.java` line 481). Any log aggregation system (e.g., Splunk, Elasticsearch) receiving DEBUG logs will contain database credentials.

## Operations Runbook

### Normal Execution
```bash
java -jar FDRBatchReportsProcessing-1.0.0.jar
# Or with custom config:
java -jar FDRBatchReportsProcessing-1.0.0.jar /path/to/FDRBatchReportsProcessor.properties
```

### Exit Codes
- Exit 0: All processing completed (implied — no explicit exit code management)
- Exit 1: Initialization failed (config file not found or invalid, `FDRBatchReportsMain.java` line 27)

### Failure Modes
- **DB connection failure**: Logged at ERROR level; processing of that report type is skipped. No alerting. No retry.
- **Stored procedure error**: Logged at ERROR level; processing stops for that stored procedure call.
- **Unhandled exception**: Caught by outer `try/catch Throwable` in main; logged at FATAL; cleanup runs.

### Monitoring
No health check endpoint, no metrics, no dead-letter queue. Monitoring is entirely dependent on log file inspection. Operations teams must grep the log for `ERROR` or `FATAL` messages.

## Version Management

The library is at version `1.0.0` with no indication of a release changelog. The version has likely not been incremented since initial deployment, as is typical of Gen-1 batch libraries. Any changes to this library require rebuilding and redeploying the JAR to the server.

## Recommended DevOps Improvements

1. Upgrade Java from 1.5 to 17+.
2. Replace Log4j 1.x with SLF4J + Logback or Log4j 2.x.
3. Remove password logging from all connection string debug statements.
4. Add OWASP dependency check to the Maven build.
5. Configure a proper scheduled job monitoring system (e.g., job scheduler with alerting) instead of relying on log inspection.
6. Implement a build-and-test CI pipeline triggered on PRs.
7. Consider migrating to Spring Batch for standardized batch processing patterns, retry logic, and monitoring.
