# ecore-batch_LIB — Solution Architect View

## Technical Architecture
- **Language**: Java (source/target: Java 1.5 / Java 5)
- **Framework**: Spring Framework 2.5.6, Spring Batch 2.1.1.RELEASE
- **Build**: Maven (pom.xml), Maven Assembly plugin for fat JAR
- **Config**: Spring XML IoC (`ECoreBatch.xml`, `data-source-context.xml`, per-job XML files)
- **Deployment**: Standalone fat JAR on Windows server; invoked via `.bat` / `.vbs` scripts
- **DB access**: Spring JDBC (`StoredProcedureItemReader`, `JdbcTemplate`), commons-dbcp 1.2.2 connection pool
- **Logging**: Apache Commons Logging 1.1 (likely backed by log4j, not in repo)
- **Testing**: JUnit 4.4, Spring-mock 2.0.8, Spring Batch Test 2.1.1

## Key Classes and Their Roles
| Class | Package | Role |
|---|---|---|
| `ECoreBatch.xml` | resources | Root Spring context — imports all sub-contexts; defines job launcher, repository, registry |
| `EventImpl` | service.eventach.impl | Orchestrates event trigger: get dispatch, get handler, execute, end dispatch |
| `EventDAOImpl` | dao.eventach | Wraps eventActionDispatchBegin/End stored procedures |
| `NotificationServiceHelperImpl` | service.eventach.helpers | Core notification assembly: retrieves bank data, member data, profile labels, calls NotificationManagerImpl |
| `EcountCoreServiceHelperImpl` | service.eventach.helpers | Calls eMember inquiry extended service; calls IEFT journal inquiry DAO |
| `StrongboxServiceHelperImpl` | service.eventach.helpers | Calls Strongbox RepositoryService.Read for bank info |
| `ECoreBatchConstants` | batch.common | All string/int constants for column names, exit codes, RPC keys |
| `DynamicJobParameters` | domain.common | Generates unique job parameters for each run (prevents duplicate job instance errors) |
| `ExitCodeMapperImpl` | domain.common | Maps Spring Batch exit codes to process exit codes (11=NoRecordsFoundException, 12=ExceptionThreshold, 13=InfiniteLoop) |

## API Surface
- **No REST or SOAP API.** Invoked as a command-line Java process.
- Entry point: Spring Batch `SimpleJobLauncher.run(job, parameters)` called from `.bat`/`.vbs` script.
- Exit codes returned to the calling OS process via `ExitCodeMapperImpl` — consumed by the Windows batch scheduler.

## Security Posture

### Authentication
- Database connections via `DirectorConfiguredDBCPdatasourceCreator` — credentials resolved from Director service; not visible in source code. **Cannot confirm whether DB passwords are stored in plaintext in `director-client.properties`.**
- cbase service calls use `RequestContext` (agent-based auth) — the `agent` value is injected via Spring XML; the actual agent credential is in `ECoreBatch.properties` (not in repo).
- No OAuth, JWT, or modern token-based auth.

### Secrets / Credentials
- `director.address`, `springbatch-agent`, `database`, `batchrepodatabase` — all in external properties files (not in repo). **Risk: if `D:\c-base\config\` is accessible to non-batch users, credentials may be exposed.**
- StrongboxServiceHelper retrieves bank data using a `reference` string — this reference is logged at INFO level:
  - File: `StrongboxServiceHelperImpl.java:41` — `_log.info("...reference id:"+reference)`
  - Risk: if `reference` encodes an account identifier, it appears in application logs.

### PII in Logs — HIGH RISK
- `EcountCoreServiceHelperImpl.java:80-82`:
  ```java
  _log.info("...registration.email_address:"+Utility.getHashtableValue(rpcOutputs, RPC_KEY_REGISTRATION_EMAIL_ADDRESS));
  _log.info("...registration.first_name:"+...);
  _log.info("...registration.last_name:"+...);
  ```
  These log statements emit cardholder PII at INFO level on every event processed. This is a **CCPA/GLBA violation** if logs are retained or forwarded to any log aggregation system.

### Crypto
- No encryption configuration in source code.
- Commons-dbcp 1.2.2 — legacy DBCP; no built-in TLS/SSL configuration; TLS depends on JDBC URL and driver.
- `sqljdbc` version 1.1 (SQL Server JDBC driver) — extremely old (2005-era); TLS 1.0 only. **Critical CVE risk.**
- Data in transit to Notification/Strongbox/eMember services — encryption depends on those service endpoints; not configured in this library.

### CVE Risk — Framework Versions
| Dependency | Version | EOL Date | Known CVE Risk |
|---|---|---|---|
| Spring Framework | 2.5.6 | 2013 | Multiple CVEs post-EOL; SpEL injection, path traversal |
| Spring Batch | 2.1.1.RELEASE | ~2012 | EOL; no security patches |
| Java target | 1.5 (Java 5) | 2009 | Running on EOL JVM |
| commons-dbcp | 1.2.2 | EOL | No TLS support; connection leak risks |
| commons-pool | 1.4 | EOL | Pool exhaustion vulnerabilities |
| sqljdbc | 1.1 | EOL | TLS 1.0 only; multiple security issues |
| aspectjweaver | 1.5.3 | EOL | |
| junit | 4.4 | Old (not EOL) | No runtime risk |

## Technical Debt
| Item | Severity | Evidence |
|---|---|---|
| Java 5 target | Critical | `pom.xml` lines 143-149 (`<source>1.5</source>`) |
| Spring 2.5.6 / Batch 2.1.1 EOL | Critical | `pom.xml` lines 10-11 |
| sqljdbc 1.1 (TLS 1.0 only) | Critical | `pom.xml` lines 113-117 |
| PII logged at INFO level | Critical | `EcountCoreServiceHelperImpl.java:80-82` |
| commons-dbcp 1.2.2 EOL | High | `pom.xml` lines 87-91 |
| Hardcoded D:\c-base\ path | High | `ECoreBatch.xml:33` |
| StrongboxServiceHelper logs reference ID | High | `StrongboxServiceHelperImpl.java:41` |
| Built JAR committed to target/ | High | `target/ecore-batch-1.0.0-SNAPSHOT*.jar` |
| SimpleAsyncTaskExecutor (no thread pool limit) | High | `eventACHBatchJob.xml:111`, `processCoreTransferBatchJob.xml:123` |
| `setShouldValidate(false)` on notifications | Medium | `NotificationServiceHelperImpl.java:149` |
| Spring XML config (no annotation support) | Medium | All `job/context/*.xml` files |
| VBScript launcher (deprecated) | Medium | `src/test/CoreDeviceBatchJob.vbs` |
| Raw `Dictionary` type (unchecked generics) | Low | Multiple service helper classes |
| OFSS copyright / no current owner | Low | All Java files — author OFSS |

## Gen-3 Migration Requirements
1. **Replace sqljdbc 1.1 with Microsoft JDBC Driver 12.x** — supports TLS 1.2+, modern SQL Server features.
2. **Upgrade to Spring Boot 3.x + Spring Batch 5.x** — modern annotation-driven config, built-in security hardening.
3. **Migrate to Java 17 LTS or Java 21 LTS** — supported, secure JVM.
4. **Replace commons-dbcp with HikariCP** — modern, performant, TLS-capable connection pool.
5. **Remove PII log statements** (`EcountCoreServiceHelperImpl.java:80-82`).
6. **Replace Strongbox reference ID logging** (`StrongboxServiceHelperImpl.java:41`) with a masked/non-identifying log message.
7. **Replace cbase proprietary APIs** with Onbe platform equivalents (Strongbox → vault/secret manager, eMember → cardholder API, Notification → modern notification service).
8. **Replace Director service** with HikariCP + environment-injected credentials (Kubernetes secrets, AWS Secrets Manager, etc.).
9. **Containerize** — remove Windows-specific `.bat`/`.vbs` launchers; replace with Docker/Kubernetes Job.
10. **Add CI/CD pipeline** — Maven build + test on every commit; vulnerability scanning (OWASP Dependency Check, Snyk).
11. **Remove built JARs from target/** — add to `.gitignore`.

## Code-Level Risks (File:Line References)
| Risk | File | Line |
|---|---|---|
| PII logged (email, first name, last name) | `EcountCoreServiceHelperImpl.java` | 80-82 |
| StrongboxServiceHelper logs reference ID | `StrongboxServiceHelperImpl.java` | 41 |
| Java 5 source/target | `pom.xml` | 144-148 |
| sqljdbc 1.1 dependency | `pom.xml` | 113-117 |
| Spring 2.5.6 / Batch 2.1.1 | `pom.xml` | 10-11 |
| Hardcoded D:\c-base\ path | `ECoreBatch.xml` | 33 |
| Unbounded thread executor | `eventACHBatchJob.xml` | 111; `processCoreTransferBatchJob.xml` | 123 |
| setShouldValidate(false) | `NotificationServiceHelperImpl.java` | 149 |
| Built JAR in source control | `target/ecore-batch-1.0.0-SNAPSHOT-jar-with-dependencies.jar` | — |
| Raw Dictionary (unchecked) | `EcountCoreServiceHelperImpl.java` | 49; `StrongboxServiceHelperImpl.java` | 37 |
