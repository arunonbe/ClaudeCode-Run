# echeck-claim-library_LIB — DevOps and Operations Report

## 1. Build System

| Attribute | Value |
|-----------|-------|
| Build tool | Apache Maven (multi-module) |
| Wrapper | `mvnw` / `mvnw.cmd` (Maven Wrapper) |
| Parent POM | `eCheckClaim-parent` v`1.0.0-SNAPSHOT` |
| Inherits from | `com.parents:service-parent:9.0.0` |
| Modules | `eCheckClaim-common`, `eCheckClaim-svc` |
| Java version | 1.6 (source and target in `maven-compiler-plugin 2.0.2`) |
| Packaging | JAR (`eCheckClaim-svc`) |
| Nexus | `d-na-stk01.nam.wirecard.sys:8080/nexus` (Wirecard-era internal repository) |
| CI/CD | GitHub Actions CodeQL scan (`.github/workflows/codeql.yml`) — **the only automated pipeline present** |

The Maven Wrapper (`mvnw`) allows builds without a local Maven installation. The `settings.xml` in `.mvn/wrapper/` configures the Nexus repository on `d-na-stk01.nam.wirecard.sys` — a Wirecard-era internal server.

---

## 2. CI/CD Pipeline

### Existing pipeline
A **CodeQL security scan** is configured in `.github/workflows/codeql.yml`:
```yaml
name: "CodeQL"
on:
  workflow_dispatch:
  schedule:
    - cron: 23 13 * * 5    # Every Friday at 13:23 UTC
jobs:
  analyze:
    uses: Onbe/om-ci-setup/.github/workflows/codeql-auto.yml@main
    secrets: inherit
    with:
      java-runner: "['self-hosted', 'X64', 'Linux', 'ubuntu-docker']"
```

**Assessment**: CodeQL runs weekly on a self-hosted Linux runner (`ubuntu-docker`). This is a **security SAST scan only** — no build, test, or deployment pipeline exists beyond this scan.

### Missing pipeline stages
- No Maven build verification pipeline
- No unit test execution (`mvn test`)
- No artifact publishing to Nexus
- No deployment automation

---

## 3. Configuration Management

| Configuration Item | Location | Assessment |
|---|---|---|
| Database URL | `ECheckClaimDAO.xml` line 75: `jdbc:jtds:sqlserver://ppamwdcdifsql1:2232/cbaseapp` | **Hardcoded production server** |
| Database username | `ECheckClaimDAO.xml` line 76: `b2ctest` | **Hardcoded credential in source control** |
| Database password | `ECheckClaimDAO.xml` line 77: `b2ctest` | **Hardcoded credential in source control** |
| Spring context | `eCheckClaimContext.xml` | Spring bean wiring — no environment-specific config |
| Maven settings | `.mvn/wrapper/settings.xml` | Points to `d-na-stk01.nam.wirecard.sys:8080/nexus` — Wirecard Nexus |
| Dependabot | `.github/dependabot.yml` | Weekly dependency update PRs configured |

**Critical finding**: The database credentials `b2ctest/b2ctest` are committed to `ECheckClaimDAO.xml`. This file is distributed as part of the JAR artefact at build time (it is in `src/main/resources`). Anyone with access to the JAR can extract these credentials.

---

## 4. Observability

- **Logging framework**: Apache Log4j 1.x (`log4j:1.2.15` in parent POM). Log4j 1.x reached end of life in August 2015 and is not patched for Log4Shell or other recent vulnerabilities.
- **Log instance**: `LogFactory.getLog(UserTransaction.class)` — Commons Logging façade over Log4j 1.x.
- **No distributed tracing**: No MDC correlation IDs, no OpenTelemetry, no trace headers.
- **No health endpoints**: Library, not service — no Spring Actuator or health check endpoints.
- **Log4j configuration excluded from build**: The parent POM build section explicitly excludes `**/log4j*` from packaged resources — this means log4j configuration must be provided by the consuming application. This is correct but must be verified in each consuming service.

---

## 5. Infrastructure Dependencies

| Dependency | Version | Assessment |
|-----------|---------|------------|
| `ppamwdcdifsql1:2232/cbaseapp` | SQL Server (version unknown) | Production/staging `cbaseapp` SQL Server — hardcoded |
| `d-na-stk01.nam.wirecard.sys:8080/nexus` | Sonatype Nexus (Wirecard) | Internal artifact repository — Wirecard domain |
| `net.sourceforge.jtds:jtds:1.2.2` | jTDS JDBC driver | Legacy open-source SQL Server driver; last release 2013; unmaintained |
| `org.springframework:spring:2.5.6` | Spring Framework 2.5.6 | **EOL since 2013**; known security vulnerabilities |
| `log4j:log4j:1.2.15` | Log4j 1.x | **EOL since 2015**; vulnerable to known CVEs |
| `commons-dbcp:1.2.2` | Apache DBCP | Old connection pool; superseded by DBCP2 |
| `com.ecount:xPlatform:2.5.45` | Internal xPlatform library | eCount core platform library |
| Self-hosted GitHub Actions runner | `ubuntu-docker` | CodeQL scan only |

---

## 6. Operational Risks

| Risk | Severity | Detail |
|------|---------|--------|
| Hardcoded credentials in JAR | CRITICAL | `b2ctest/b2ctest` credentials shipped inside every built JAR |
| Log4j 1.x EOL | CRITICAL | Unmaintained; multiple known CVEs; Log4j 1.x is not the same as Log4j 2.x Log4Shell but has its own CVEs (CVE-2019-17571 deserialization RCE, etc.) |
| Spring 2.5.6 EOL | CRITICAL | Spring Framework 2.5 reached EOL in 2013; major security vulnerabilities in all post-2.5 releases are not patched in 2.5 |
| jTDS JDBC driver (unmaintained) | HIGH | Last release 2013; no TLS 1.2/1.3 support; SQL Server TLS enforcement will reject connections |
| Wirecard Nexus dependency | HIGH | Build fails if `d-na-stk01.nam.wirecard.sys` is decommissioned |
| SNAPSHOT versioning | MEDIUM | `1.0.0-SNAPSHOT` — no stable release; build reproducibility not guaranteed |
| No Maven unit tests | MEDIUM | No test coverage visible; CodeQL scan is the only automated quality gate |
| `ApplicationContext` created per request | MEDIUM | `ECheckClaimImpl.claimECheck()` creates a new `ClassPathXmlApplicationContext` on every call — severe performance issue for high-throughput scenarios |
