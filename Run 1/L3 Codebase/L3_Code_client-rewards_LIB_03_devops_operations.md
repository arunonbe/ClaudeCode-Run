# client-rewards_LIB — DevOps & Operations View

## Build & Packaging

### Build System
- **Maven multi-module project** with root `pom.xml` (`groupId=com.ecount.service.client-rewards`, `artifactId=client-rewards`, `version=1.0-SNAPSHOT`).
- Three child modules: `client-inputfile`, `client-requestfile`, `client-expire-records` — each packaged as a **JAR with a manifest-declared main class**.
- Maven Wrapper present (`.mvn/wrapper/maven-wrapper.properties`): targets **Apache Maven 3.9.1**.
- Java source/target compatibility: **Java 1.5** (`<source>1.5</source>`, `<target>1.5</target>`) set in all three module POMs.
- Parent POM inherits from `com.ecount.service:service-parent:3`, which is an internal Onbe/ecount parent not present in this repository.

### Module Entry Points (JAR manifests)
| Module JAR | `Main-Class` |
|---|---|
| `client-inputfile` | `com.ecount.service.rewards.client.ReadInputFile` |
| `client-requestfile` | `com.ecount.service.rewards.client.RequestFileBuilder` |
| `client-expire-records` | `com.ecount.service.rewards.client.ExpireRecords` |

### Key Dependencies (version-pinned in root `pom.xml`)
| Artifact | Version | Notes |
|---|---|---|
| `org.springframework:spring` | 2.0.8 | Ancient; EOL since ~2011 |
| `com.sun.xml:jaxb-impl/api/xjc` | 2.0EA3 | Pre-release/EA JAXB; non-standard groupId |
| `log4j:log4j` | 1.2.13 | EOL; known CVEs |
| `net.sourceforge.jtds:jtds` | 1.2 | jTDS JDBC driver; not Microsoft official driver |
| `commons-dbcp:commons-dbcp` | 1.2.2 | EOL |
| `org.hibernate:hibernate` | 3.2.0.ga | Not actually used in final wiring |
| `org.apache.activemq:activemq-core` | 4.1.1 | Test scope only; EOL |
| `com.ecount:xPlatform` | 1.0.14 / 1.0.12-SNAPSHOT | Internal; inconsistent versions across modules |
| `com.ecount.service:requestfile-impl` | 1.0.1-SNAPSHOT | Internal payment request builder |

**Dependency duplication**: `client-expire-records/pom.xml` declares `jaxb-impl` and `jaxb-api` twice (lines 130–143 and 151–164).

---

## Deployment

### Runtime Model
All three modules are **standalone batch JARs** executed from the command line (or a scheduler). There is no web container, no REST endpoint, no daemon. The operator starts each JAR directly:

```
java -jar client-inputfile-1.0-SNAPSHOT.jar [optional-properties-file-path]
java -jar client-requestfile-1.0-SNAPSHOT.jar [optional-request-file-path-props]
java -jar client-expire-records-1.0-SNAPSHOT.jar
```

A Windows batch script `RunInputFile.bat` exists at `client-inputfile/src/RunInputFile.bat` (content not enumerated but its presence suggests Windows Task Scheduler deployment).

### Configuration Resolution at Runtime
All three Spring `applicationContext.xml` files use `PropertyPlaceholderConfigurer` with a **hardcoded Windows filesystem path**:
```
file:D:\c-base\config\service\client-rewards\ClientRewardsInput.properties
```
This means the application **requires a `D:\c-base\` directory layout** on the deployment host.

### Log Output
- Log files written to `D:/c-base/log/Client_Rewards_log.log` (all three modules share the same file path).
- Rolling appender: max file size 5 MB, 3 backup files.
- Also writes to stdout.

---

## Configuration Management

### Properties Files
| File | Location | Purpose |
|---|---|---|
| `ClientRewardsInput.properties` | `client-inputfile/src/main/resources/` | Input/reply/archive folder paths, director address, agent, database, member_id, program_id_prefix |
| `ClientRewardsExpireRecords.properties` | `client-expire-records/src/main/resources/` | Director address, agent, database |
| `subContext.properties` | All three modules | Redundant copy of director.address, agent, database |

**Problem**: The `applicationContext.xml` in all three modules hard-codes the external config path to `D:\c-base\config\service\client-rewards\ClientRewardsInput.properties`. The properties files checked into the repo at `src/main/resources/` are development/test defaults only. No environment-specific property injection mechanism (no profiles, no env vars) exists.

**Sensitive values in version control**:
- `agent=b2ctest` (dev credential) in `subContext.properties` and `ClientRewardsExpireRecords.properties`
- `member_id = {AE6BBCC6-52DD-41E9-9298-A270BEC19DE3}` in `ClientRewardsInput.properties`
- JNDI/director address `http://ECIFLEXAPPDEV/service/dispatch.asp`

### Spring Context
- Spring 2.0.8 XML-bean-definition contexts (one per module).
- All beans wired by setter injection.
- DataSource obtained from `DirectorConfiguredDBCPdatasourceCreator` — this couples deployment to the internal "Director" service being available.
- No Spring profiles, no environment abstraction.

---

## Observability

### Logging
- Framework: **Log4j 1.2.13** (EOL, multiple CVEs).
- All three modules configured to `debug` level for `com.ecount.service.rewards` namespace.
- File appender target: `D:/c-base/log/Client_Rewards_log.log` (Windows path, hardcoded).
- No structured/JSON logging; pattern-based only.
- No Mapped Diagnostic Context (MDC) for correlation ID or batch run ID.
- No log aggregation configuration (no Logstash, Splunk, Fluentd appender).

### Metrics & Alerting
- **None**. No metrics instrumentation (no Micrometer, no JMX), no health check endpoint, no alerting hook.
- Batch success/failure is only observable via log file review.

### Tracing
- **None**. No distributed tracing (no OpenTelemetry, no Zipkin).

### Error Reporting
- Exception stack traces written to stdout via `e.printStackTrace()` in multiple locations (e.g., `ReadInputFile.main()` lines 145, 154, 156; `CreateClientRewardsFileSP.getPartnerID()` line 99).
- No dead-letter queue or alerting on error.

---

## Infrastructure Dependencies

| Dependency | Type | Details |
|---|---|---|
| **SQL Server** | Database | `cbaseapp` on `ECIFLEXSQLDEV:1433` (dev); connection pooled via Director DBCP |
| **Director service** | Service discovery / DB config | HTTP service at `http://ECIFLEXAPPDEV/service/dispatch.asp`; supplies datasource config |
| **JobSvc / ProfileManager** | Partner ID resolution | `com.cbase.business.profile.ProfileManager` called in `CreateClientRewardsFileSP.getPartnerID()` to look up `partner_id` from `program_id` |
| **Filesystem** | File staging | Input folder, reply folder, archive folder — all on local `D:\c-base\...` path |
| **`requestfile-impl`** | Payment request file builder | `com.ecount.payment.common.*` — `PaymentRequestFile`, `RequestBuilder`, `RequestFileVO`, etc. |
| **Maven repository** | Build | Internal Onbe Nexus/Artifactory implied by parent POM; `com.ecount.*` artifacts not on Maven Central |

---

## Operational Risks

| Risk | Impact | Detail |
|---|---|---|
| No file locking on input folder | Duplicate processing | Concurrent batch runs would race on the same XML files |
| Source file not deleted after archive | PII lingering on filesystem | `deleteFile()` commented out in `ReadInputFile.moveFile()` (line 423) |
| All three JAR log to same file | Log collision | Concurrent runs overwrite each other's log entries without correlation ID |
| Hardcoded `D:\c-base\` path | Non-portable deployment | Cannot run on Linux without property override |
| SP failure returns 0 and is masked | Silent data loss | `getPartnerID()` returns 0 on any exception; reward file inserted with `partner_id=0` |
| No alerting on batch failure | Undetected failures | Only log file indicates success/failure |
| Log4j 1.x EOL | Security | Known CVEs; no upgrade path visible in POM |
| Spring 2.0.8 EOL | Security | End-of-life framework with no security patches |

---

## CI/CD

### GitHub Actions
One workflow defined at `.github/workflows/codeql.yml`:
```yaml
name: "CodeQL"
on:
  workflow_dispatch:
  schedule:
    - cron: 1 22 * * 1   # Weekly on Monday
jobs:
  analyze:
    uses: Onbe/om-ci-setup/.github/workflows/codeql-auto.yml@main
    secrets: inherit
    with:
      java-runner: "['self-hosted', 'X64', 'Linux', 'ubuntu-docker']"
```
- **CodeQL static analysis only** — runs weekly or on manual trigger using a self-hosted Linux runner.
- **No build, test, or deploy pipeline** exists in this repository's CI configuration.
- **No Maven build step** in CI — the CodeQL workflow delegates entirely to the reusable `om-ci-setup` template.

### Dependabot
`.github/dependabot.yml` configures weekly Maven dependency version checks. Given the extreme age of pinned versions (Spring 2.0.8, Log4j 1.2.13), Dependabot PRs are expected but may not be actionable without significant refactoring.

### Version Control
- SCM is SVN (`ecsvn.office.ecount.com/svn/ecount/services/client-rewards/trunk`) per `pom.xml` `<scm>` section — this is a legacy SVN-to-Git migration artefact; the repo now lives on GitHub with a shallow clone.
- No branch strategy, no PR templates, no merge rules are defined in this repository.
