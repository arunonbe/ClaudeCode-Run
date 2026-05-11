# ecap-backend-process_LIB — DevOps & Operations Report

## Build System

The library uses **Apache Maven** with a Maven Wrapper (`mvnw`, `mvnw.cmd`). Build configuration:
- `pom.xml` defines `ecap-card-creation-impl-1.0.1` as the final artifact name (line 149), despite the POM version being `2.0.0-SNAPSHOT` (line 15) — an inconsistency between artifact naming and version
- **Java source/target: 1.7** (`pom.xml` lines 153–154) — Java 7 is EOL since July 2019
- Parent POM: `com.citi.prepaid:prepaid-parent:3` — a Citibank/prepaid lineage POM
- Maven Assembly Plugin produces a fat JAR with dependencies for standalone execution
- Main class: `com.ecount.service.ecap.EcapCardCreationClient` (configured in `pom.xml` lines 166–167)

The library is designed to be **executed as a standalone runnable JAR** (`EcapCardCreationClient` as `mainClass`) as well as consumed as a dependency by other services.

---

## CI/CD Pipeline

### GitLab CI (`.gitlab-ci.yml`)
The repository has a GitLab CI configuration (485 bytes). Given its small size, it likely defines a minimal pipeline with:
- `mvn package` or `mvn install` build step
- Artifact publishing to the internal Maven repository

No test stage, no static analysis, no dependency vulnerability scanning, and no security scanning are evident from the file size.

### GitHub Actions (`.github/workflows/codeql.yml`)
A CodeQL workflow (269 bytes) exists for automated security scanning via GitHub. This is a minimal CodeQL setup — likely a GitHub-generated default template.

### Dependabot (`.github/dependabot.yml`)
Dependabot is configured (515 bytes) for automated dependency update pull requests.

---

## Maven Settings (`settings.xml`)
`src/.mvn/wrapper/settings.xml` (5,088 bytes) contains the Maven settings for the build environment, including internal repository server configuration. This file should be reviewed to confirm it does not contain plaintext repository credentials.

---

## Deployment Model

Based on the `main` class configuration, this library is deployed as a **scheduled batch job**:
1. Built as a fat JAR (`ecap-card-creation-impl-1.0.1-jar-with-dependencies.jar` equivalent)
2. Executed on a schedule via cron, Windows Task Scheduler, or a job service
3. Configuration loaded from `d:/c-base/config/ecap-backend-process/card-creation.properties` at runtime

The presence of a Windows-style path (`d:/c-base/config/`) and the SSDT/Windows-era architecture suggest this runs on **Windows Server** hosts.

---

## Operational Risks

### Risk 1: Java 7 Compilation Target — CRITICAL
The library compiles for Java 1.7 (EOL July 2019). This means:
- No Java 8 lambda support, no Stream API, no modern security features
- No TLS 1.2+ guarantee (TLS 1.2 requires Java 7u6+ and explicit enabling; TLS 1.3 requires Java 11+)
- PCI DSS Requirement 4.2.1 mandates strong cryptography; TLS 1.0/1.1 must not be used. A Java 7 runtime may not enforce TLS 1.2 by default.

### Risk 2: log4j 1.2.15 — HIGH
`pom.xml` (line 45) declares `log4j:log4j:1.2.15`. This version is affected by:
- **CVE-2019-17571** (CVSS 9.8) — Log4j 1.x SocketServer deserialization RCE
- **CVE-2022-23302/23305/23307** — Multiple Log4j 1.x vulnerabilities disclosed in 2022

While these are distinct from Log4Shell (CVE-2021-44228 affecting Log4j 2.x), the log4j 1.x socket appender vulnerabilities are exploitable if the SocketServer or SMTPAppender is configured.

### Risk 3: Spring 2.0.8 — HIGH
`pom.xml` (line 35) uses Spring Framework 2.0.8 (released ~2007). This version:
- Is 17+ years old
- Has numerous known CVEs patched in later versions
- Does not support Spring Security modern authentication features
- Cannot use Spring Boot

### Risk 4: No Retry/Dead-Letter Queue for Failed Card Requests
`EcapCardCreationProcessImpl.run()` (lines 33–75) processes all requests in a single pass without a dead-letter queue or retry policy at the batch framework level. Failure handling is:
- A failure notification email is sent to the purchaser
- The `process_counter` is incremented
- The status code is updated

But if the process fails mid-batch (e.g., JVM crash, database timeout), there is no idempotency guarantee. The `process_counter` increment provides some protection, but it is not a complete idempotency solution.

### Risk 5: Thread Pool Shutdown on Every Run
`EcapCardCreationProcessImpl.run()` (line 73) calls `fixedThreadPoolExecutor.shutdown()` at the end of every run. This means the thread pool is created, used, and destroyed on every job execution, which is wasteful for a scheduled job that runs frequently.

### Risk 6: `e.printStackTrace()` in Production Code
`EcapEmailNotificationImpl.java` (line 86) calls `e.printStackTrace()` in a catch block. In Java, `printStackTrace()` writes to `System.err`, not to the log4j logger. This means exception details are:
- Not captured in the application log file
- Only visible if `System.err` is redirected to a file
- Potentially lost in production environments where `System.err` is discarded

---

## Version Management

| Component | Current Version | Current Status |
|---|---|---|
| Library artifact | `2.0.0-SNAPSHOT` | SNAPSHOT — not a release |
| Java source target | 1.7 | EOL since 2019 |
| Spring Framework | 2.0.8 | EOL since ~2012 |
| log4j | 1.2.15 | EOL; CVEs present |
| JTDS JDBC | 1.x (implied by `msbase`/`mssqlserver`) | Deprecated |
| mssql-jdbc | 6.4.0.jre7 | Outdated (current: 12.x) |

The library is in a perpetual SNAPSHOT state, suggesting it has never had a formal release process, and version management is informal.

---

## Monitoring and Alerting

No monitoring configuration is present:
- No JMX metrics
- No health check endpoints
- No alerting on batch job failure
- No metrics for cards processed per run

Operational visibility depends entirely on log file parsing (if logs are being shipped to a SIEM or log aggregator).
