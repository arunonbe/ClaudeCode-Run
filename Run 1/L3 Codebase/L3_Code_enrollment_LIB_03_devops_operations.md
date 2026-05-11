# DevOps & Operations Analysis — enrollment_LIB

## Repository Overview

**Repo:** `enrollment_LIB`
**Build:** Maven (`pom.xml`), artifact `enrollment-2.0.3-SNAPSHOT.jar`
**Java:** Source/target 1.6 (`pom.xml` lines 118–120)
**CI:** GitHub Actions CodeQL (`codeql.yml`)
**Distribution:** File-based Maven repository (legacy `T:/mvn/release` mapped drive, `pom.xml` lines 56–68)

---

## Build System

### Maven Configuration
The POM references a legacy internal Maven repository on a Windows mapped drive (`T:/mvn/release` and `T:/mvn/snapshot`). The commented-out entries show that the original repository was a WebDAV server at `ecsvn.office.ecount.com:8080` — a legacy infrastructure reference that no longer resolves.

**Operational impact:** Building this library in a modern CI environment will fail artifact resolution unless:
- The `T:` drive is mapped, or
- The Maven settings.xml is updated to point to a current Nexus/Artifactory instance.

### Assembly Configuration
`src/assembly/assembly.xml` is referenced by the `maven-assembly-plugin`. This generates a distribution archive alongside the JAR, likely bundling dependencies for standalone execution.

### Wrapper
Maven Wrapper (`mvnw`, `mvnw.cmd`) is present, with a `settings.xml` in `.mvn/wrapper/` that likely points to the internal Nexus repository (`pom.xml` line 371 references `d-na-stk01.nam.wirecard.sys:8080/nexus/`).

---

## CI/CD

### GitHub Actions — CodeQL
`.github/workflows/codeql.yml` runs a CodeQL analysis on a schedule (`56 6 * * 6` — Saturday mornings) and on workflow dispatch. It delegates to the shared Onbe CodeQL workflow:
```yaml
uses: Onbe/om-ci-setup/.github/workflows/codeql-auto.yml@main
```
Runner: `self-hosted, X64, Linux, ubuntu-docker`.

**Coverage:** This provides automated SAST (Static Application Security Testing) for Java. However, given the age of the codebase (Java 1.6, Spring 2.0.8), CodeQL findings are expected to be numerous.

**Gap:** No build CI pipeline (no compile, test, package stage in GitHub Actions). The CodeQL job only scans — it does not verify the build succeeds or that tests pass.

### Dependabot
`.github/dependabot.yml` is present, suggesting automated dependency version monitoring is configured. However, given the legacy dependency versions (`spring:2.0.8`, `jtds:1.2`, `commonslang:2.1`), dependabot updates may not be actionable without a significant refactor.

---

## Deployment Model

### Execution
This library is a **batch process** executed as a standalone Java process:
```bash
java -jar enrollment.jar
```
`ProcessMain.main()` is the entry point (`pom.xml` line 89). The main class is declared in the JAR manifest.

### Configuration
Spring XML configuration (`src/main/resources/spring.xml`) uses property placeholders that are resolved from:
- `${CBASE_HOME_URL}/config/processes/enrollment/application.properties`
- `${CBASE_HOME_URL}/config/director-client.properties`

`CBASE_HOME_URL` is an environment variable pointing to the cBase configuration server, a legacy Onbe/eCount infrastructure component. This means the process **cannot run without access to the cBase environment**.

### Infrastructure Dependencies at Runtime

| Dependency | Purpose | Technology |
|------------|---------|------------|
| SQL Server database | Enrollment records, status, profiles | jTDS JDBC (legacy Microsoft SQL Server driver) |
| Director service | Database connection routing (`spring.xml` line 17–20) | `DirectorConfiguredDBCPdatasourceCreator` |
| StrongBox service | Sensitive data de-tokenisation | XML-RPC over HTTP (`StrongBoxClient.java`) |
| Filesystem | Output flat file staging | Local filesystem path (`${output.location}`) |
| FTP server | File delivery | `${input.ftp.location}` staging path |
| cBase config server | Externalised configuration | `${CBASE_HOME_URL}` |

---

## Operational Runbook

### Process Status Codes
| Code | Meaning | Action |
|------|---------|--------|
| `0` exit | All programmes processed successfully | None |
| `1` exit | One or more programmes failed | Review log; check `programCurrentStatus` values; re-run failed programmes |

### Re-run Strategy
The status table (`Status` DAO) records `ReportStatus.FAILED_MOVE` (status 2) for programmes where the extract was generated but the file move failed. The `switch` in `ProcessMain.java` lines 76–95 implements resume logic: a programme with status 2 skips extract generation and retries only the file move step.

### Logging
Uses `log4j.properties` (`src/main/resources/log4j.properties`). All logging is to `log` via `LogFactory.getLog("ProcessMain.class")`. Log statements are `log.info()` — no MDC context, no structured logging. This makes log correlation across programmes difficult in production.

### Monitoring Gaps
- No metrics emission (no JMX, no Prometheus).
- No alerting hooks.
- No health endpoint.
- No record count validation.

---

## Security Operations Concerns

| Concern | Detail |
|---------|--------|
| jTDS driver | `net.sourceforge.jtds:jtds:1.2` is an end-of-life third-party driver last updated circa 2012. The official Microsoft JDBC driver should be used (`mssql-jdbc`). |
| StrongBox HTTP (not HTTPS) | `StrongBoxClient.java` uses `HttpClient` without explicit TLS enforcement. If StrongBox is accessed over plain HTTP, PII decryption responses are unencrypted in transit. |
| Flat file encryption | No evidence of at-rest encryption for the generated flat files. Files containing SSN, DOB, and ACH data must be encrypted (PCI DSS Req 3.5, GLBA). |
| Spring 2.0.8 | Ancient Spring version with many known CVEs. |
| `commons-lang:2.1` | Very old; CVE exposure likely. |

---

## Upgrade and Retirement Assessment

This library is a **legacy Gen-1 artifact** with significant technical debt. The recommended path is:
1. **Short-term:** Run existing code in an isolated, network-segmented environment. Ensure flat file output is encrypted. Verify StrongBox calls use TLS.
2. **Medium-term:** Migrate to Spring Batch on Spring Boot 3.x with JPA, structured logging, Micrometer metrics, and the official `mssql-jdbc` driver.
3. **Long-term:** Replace batch file delivery with event-driven enrollment notification (consistent with Gen-3 Dapr patterns seen in `exemplar-customer-service_WAPP`).
