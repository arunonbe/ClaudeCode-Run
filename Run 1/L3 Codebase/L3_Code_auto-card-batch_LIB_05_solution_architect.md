# auto-card-batch_LIB — Solution Architect View

## Technical Architecture

**Runtime model**: Standalone Java process, launched via `CommandLineJobRunner` (Spring Batch CLI entry point). No application server. No embedded container. The fat JAR produced by `maven-shade-plugin` bundles all dependencies and is invoked directly via `java -cp`.

**Framework stack**:
- Spring Framework 2.5.6 (IoC, AOP, TX, JDBC)
- Spring Batch 2.1.1 (job/step/chunk processing, job repository)
- Log4j 1.2.15
- Apache Commons DBCP 1.2.2 / Pool 1.4 (connection pooling)
- Microsoft SQL Server JDBC 1.1

**Package structure** (`com.ecount.batch.autocardbatch`):

```
common/
  AutoCardConstants.java         — constants + Status enum + error code lists
dao/
  IAutoCardDao.java              — DAO interface (updateStatus)
  ThresholdProgramVirtualCardSP.java — StoredProcedure wrapper for threshold check
  jdbc/
    AutoCardDaoImpl.java         — JdbcTemplate-based status updater
    AutoCardCountRowMapper.java  — maps totalcount → AutoCardCount
    AutoCardCreateRowMapper.java — maps RS row → AutoCardMember
    AutoCardLoadRecordsRowMapper.java — maps totalcount for load records step
helper/
  AutoCardCountSavingListener.java        — afterStep: determine exit status, infinite-loop guard
  AutoCardLimitDecider.java               — decider: CONTINUE vs COMPLETED
  AutoCardSampleIncrementer.java          — adds jobrun.time parameter per invocation
  AutoCardTransactionCountSavingListener.java — afterStep: aggregate executed/exception counts
  ProgramIdUtils.java                     — programId parser (8-char decomposition)
service/
  ICardCreateService.java        — service interface
  CardCreateService.java         — core business logic: card issue + enroll + status update
vo/
  AutoCardCount.java             — DTO: transactionCount
  AutoCardMember.java            — DTO: id, memberid, created, status, isIssuance
writer/
  AutoCardCountWriter.java       — writes count to StepExecutionContext
  AutoCardCreateWriter.java      — delegates each member to CardCreateService
  AutoCardLoadRecordsWriter.java — no-op (load is SP side-effect)
```

**Job topology** (Spring Batch XML, two jobs):

```
autoCardLoadRecordsJob (AutoCardLoadRecordsJob.xml)
  └─ autoCardLoadRecordsStep [chunk, commit-interval=1]
       reader:    StoredProcedureItemReader → dbo.auto_card_creation_order_load
       processor: PassThrough
       writer:    AutoCardLoadRecordsWriter (no-op)

autoCardProcessJob (AutoCardProcessJob.xml)
  ├─ autoCardCountStep [chunk, commit-interval=1]
  │    reader:    StoredProcedureItemReader → dbo.autocard_get_count
  │    processor: PassThrough
  │    writer:    AutoCardCountWriter → puts totalTransactionsCount + executedTransactionsCount=0 in StepContext
  │    listeners: AutoCardCountSavingListener, ExecutionContextPromotionListener
  │    transitions: RECORDS FOUND→processStep | NO RECORDS FOUND→END | EXCEPTION THRESHOLD→END | INFINITELOOP→END
  ├─ autoCardProcessStep [partitioned, grid-size=5, SimpleAsyncTaskExecutor]
  │    └─ autoCardCreateStep [chunk, commit-interval=1] ×5 threads
  │         reader:    StoredProcedureItemReader → dbo.autocard_get_record(count=5)
  │         processor: PassThrough
  │         writer:    AutoCardCreateWriter → CardCreateService.processAutoCardRecord()
  │         listeners: AutoCardTransactionCountSavingListener, ExecutionContextPromotionListener
  └─ autoCardLimit [JobExecutionDecider → AutoCardLimitDecider]
       CONTINUE → autoCardProcessStep (loop)
       COMPLETED → END
```

## API Surface

This is a **library with no external API surface**. It exposes no REST endpoints, no messaging interfaces, and no public Java API beyond the interfaces intended for internal Spring wiring.

**Internal interfaces**:
- `IAutoCardDao` — single method: `updateAutoCardMemberStatus(AutoCardMember)`
- `ICardCreateService` — three methods: `issueCard(AutoCardMember)`, `enrollCardHolder(AutoCardMember)`, `processAutoCardRecord(AutoCardMember)`

**External API dependencies** (consumed, not exposed):
- `IDeviceManager` (`com.cbase.business.core`) — `getDefaultEcard(Member)`, `createECard(Member)`, `issuePlastic(AccountDefinitionECard, String, Funds, boolean)`
- `AppProfileUserEnrollmentClass` (`com.cbase.business.ecount.profile`) — `retrieve()`, `create(AppProfileUserEnrollment)`
- SQL Server stored procedures: `dbo.autocard_get_count`, `dbo.autocard_get_record`, `dbo.auto_card_creation_order_load`, `dbo.check_threshold_program_virtual_card`

## Security Posture

### Credentials and Secrets
- **Critical**: `.mvn/wrapper/settings.xml` contains plaintext passwords committed to SCM:
  - `nexus-qa` server: `deployment` / `dwil15?`
  - `ecount.release` server: `deployment` / `d3v0nly`
  - `ecount.snapshot` server: `deployment` / `d3v0nly`
  - `wirecard-mavenproxy-repository`: `acmng` / `acmng`
  These credentials must be considered compromised and rotated immediately.

### PII / Sensitive Data Exposure
- `memberid` is logged at DEBUG level in `AutoCardCreateWriter.write()` (line 63). The root logger is set to `debug` in `log4j.properties` (line 1), so this executes in all configurations using the committed log config.
- `dda_number` (account number extracted from eCard DDA) is passed as a plain VARCHAR SQL parameter with no masking (`ThresholdProgramVirtualCardSP`, line 49).
- No input validation or sanitisation on `memberid` before use in SQL UPDATE (`AutoCardDaoImpl.updateAutoCardMemberStatus()` uses `JdbcTemplate.update()` with parameterised query — SQL injection is mitigated by parameterisation, which is correct).

### Authentication / Authorisation
- No authentication layer within the batch itself. Access control is entirely at the OS/scheduler level (who can execute the `.bat` scripts).
- Database authentication is delegated to the Director service. No credentials are in this codebase (correct for DB auth).
- The `ecountcore.agent` value (`B2CTEST` in the committed properties) is used as an agent identifier for both data source resolution and eCore API calls. This is a service-identity mechanism, not user authentication.

### Network Security
- JDBC TLS configuration is not controlled by this application.
- No HTTPS/TLS configuration present (no REST endpoints; not applicable to the batch itself).
- The Nexus build dependency at `d-na-stk01.nam.wirecard.sys:8081` uses plain HTTP (port 8081 typically non-TLS).

### Dependency Vulnerabilities
- **Log4j 1.2.15**: While not affected by Log4Shell (CVE-2021-44228, which is Log4j 2.x), Log4j 1.x has its own known CVEs (CVE-2019-17571: SocketServer deserialization RCE; CVE-2022-23302, CVE-2022-23303, CVE-2022-23305 — patched only in Log4j 2.x). Log4j 1.x is EOL and should be replaced.
- **Spring 2.5.6**: Multiple known CVEs affecting Spring Framework 2.x. No active security support.
- **commons-dbcp 1.2.2**: Multiple known CVEs. EOL.
- **sqljdbc 1.1**: Extremely old — known vulnerabilities; no TLS 1.2 support in early versions.
- **spring-mock 2.0.8**: Deprecated test artifact — should not be on compile classpath.
- **JUnit 4.4** on compile classpath (missing `<scope>test</scope>`): Test dependency leaks into production classpath.

## Technical Debt

| Item | Location | Severity |
|---|---|---|
| Plaintext passwords in `settings.xml` | `.mvn/wrapper/settings.xml` lines 37–54 | Critical |
| Java 5 compile target | `pom.xml` lines 192–195 | Critical |
| Spring Framework 2.5.6 (15+ years EOL) | `pom.xml` line 15 | Critical |
| Spring Batch 2.1.1 (14+ years EOL) | `pom.xml` line 16 | Critical |
| Log4j 1.x (EOL) | `pom.xml` line 37 | Critical |
| PII logged at DEBUG globally | `log4j.properties` line 1 + `AutoCardCreateWriter` line 63 | High |
| DDA number unmasked | `ThresholdProgramVirtualCardSP` line 49, `CardCreateService` lines 136–137 | High |
| `CoreServiceException` swallowed without status update | `CardCreateService` lines 176–179 | High |
| Double `enrollCardHolder()` call in `processAutoCardRecord()` | `CardCreateService` lines 223–231 | High |
| Empty `AutoCardLoadRecordsWriter.write()` | `AutoCardLoadRecordsWriter` line 32 | High |
| Property key mismatch: `autocard.sp.autocard_order_load` vs `autocard.sp.auto_card_creation_order_load` | `AutoCardLoadRecordsJob.xml` line 35 vs `autocardbatch.properties` line 23 | High |
| Missing `autocard.threshold.issue.plastic` in committed properties | `autocardbatch.properties` | High |
| Hard-coded `D:\c-base\` paths | `AutoCardBatch.xml` line 23, `log4j.properties` line 9 | High |
| `autocard-build.bat` manually patches JAR (redundant with shade plugin) | `autocard-build.bat` | Medium |
| Tests always skipped in CI | `.gitlab-ci.yml` lines 3–5 | Medium |
| JUnit on compile classpath (missing test scope) | `pom.xml` lines 127–130 | Medium |
| `spring-mock` on compile classpath | `pom.xml` lines 150–153 | Medium |
| Raw types used throughout (`RowMapper`, `Hashtable`, `List`, `Map`) | All DAO/SP classes | Medium |
| `AutoCardLoadRecordsRowMapper` used for count but returns `AutoCardCount` with no field mapping relevance | `AutoCardLoadRecordsJob.xml` + `AutoCardLoadRecordsRowMapper` | Medium |
| Log filename contains "test" (`autocardtest.log`) | `log4j.properties` line 9 | Low |
| `ISSUNACE` and `NOT_ISSUNACE` typos | `AutoCardConstants` lines 103–104 | Low |
| `AutoCardCountSavingListener` log message says "EventACHCountSavingListener" | `AutoCardCountSavingListener` line 67 | Low |
| `pom.xml` finalName `autocard-batch-1.0.1` does not match version `2.0.2-SNAPSHOT` | `pom.xml` lines 11, 278 | Low |
| Dual JUnit declarations (3.8.1 and 4.4) | `pom.xml` lines 27–32 and 127–130 | Low |
| Nexus Wirecard URL no longer valid | `.mvn/wrapper/settings.xml` line 13 | Low |

## Gen-3 Migration Requirements

To migrate `auto-card-batch_LIB` to a Gen-3 cloud-native architecture, the following changes are required:

### Technology Upgrades
1. Upgrade to Java 17 or 21 LTS.
2. Migrate to Spring Boot 3.x with Spring Batch 5.x.
3. Replace Log4j 1.x with SLF4J + Logback or Log4j 2.x.
4. Replace Commons DBCP 1.x with HikariCP.
5. Replace `sqljdbc 1.1` with the current `com.microsoft.sqlserver:mssql-jdbc` (12.x).

### Architecture Changes
1. **Containerise**: Replace `.bat`-based invocation with a Docker container. Remove all `D:\c-base\` hard-coded paths. Externalise config via environment variables or a secrets manager (e.g., Azure Key Vault, AWS Secrets Manager).
2. **Secret management**: Remove credentials from `settings.xml`. Use CI/CD secrets (GitHub Actions / GitLab CI masked variables) for Maven repository authentication.
3. **Event-driven triggering**: Replace scheduled `.bat` file invocation with an event or message-driven trigger (e.g., AWS SQS, Azure Service Bus) or a Kubernetes CronJob.
4. **Replace stored-procedure readers**: Migrate `StoredProcedureItemReader` patterns to either JdbcPagingItemReader with parametrised queries, or REST API calls to a data service — aligning with Gen-3 API-first patterns.
5. **Replace cbase/eCore API calls**: `IDeviceManager`, `AppProfileUserEnrollmentClass` must be replaced with modern API clients (REST/gRPC). This requires the downstream platform to expose Gen-3 APIs for card issuance and enrollment.
6. **Observability**: Integrate Micrometer metrics, structured JSON logging, and distributed tracing (OpenTelemetry) to replace the current Log4j-only observability.
7. **Remove PII from logs**: Add log masking for `memberid` and any DDA-derived values before they reach log appenders.
8. **Fix double-enrollment logic**: Refactor `processAutoCardRecord()` to remove the redundant second call to `enrollCardHolder()` (already called within `issueCard()` when `isIssuance == 0`).
9. **Fix `CoreServiceException` handling**: Add proper status assignment (`FAILED` or `RETRY`) when a `CoreServiceException` is caught.
10. **Fix property key mismatch**: Align `autocard.sp.autocard_order_load` key usage in XML with the property key defined in the properties file.

### What Can Be Preserved
- The two-job separation (load then process) is a sound pattern and can be preserved as two distinct batch jobs or two steps in a single job.
- The exit-code-driven flow control (RECORDS FOUND / NO RECORDS FOUND / EXCEPTION THRESHOLD / INFINITE LOOP) is a solid operational pattern and should be preserved in the Gen-3 design.
- The exception threshold and infinite-loop detection logic in `AutoCardCountSavingListener` and `AutoCardLimitDecider` represent meaningful operational safeguards that should be re-implemented.
- The `AutoCardMember` and `AutoCardCount` domain objects are thin and simple; they can be directly translated to Gen-3 model classes.

## Code-Level Risks

1. **`CardCreateService.processAutoCardRecord()` — double enrollment** (lines 223–231): `issueCard()` already calls `enrollCardHolder()` at line 152 when `isIssuance == 0`. `processAutoCardRecord()` then calls it again at line 228. If the first call succeeds and the second raises `ProfileException`, status is set back to `INVALID` even though the card and enrollment are complete. This produces false-failure records in the journal.

2. **`CoreServiceException` leaves member in indeterminate state** (lines 176–179): The catch block logs the error but does not call `setStatus()`. The member retains whatever status it had at the point of exception. If status was `P` (processing), it remains `P` and the record may be re-selected in the next batch run without resolution.

3. **`ProgramIdUtils.getProgramIdUtils()` returns `Integer.parseInt(programId)`** (line 18): Parses the entire 8-character programId as an integer. If programId starts with a letter or contains non-numeric characters, this will throw `NumberFormatException` that is not caught anywhere in `CardCreateService.issueCard()` — it would propagate as an unchecked exception, causing the member to be caught by the outer `RuntimeException` handler and marked `FAILED`.

4. **`ThresholdProgramVirtualCardSP` uses raw `Map` without generics** (lines 45–50): `@SuppressWarnings` not present; compiler warnings. More importantly, `out.get("countValue")` is cast directly to `Integer` without null-safety on the map value — mitigated by the `if (null != out)` check but the inner `out.get("countValue")` check is also present.

5. **`AutoCardCreateWriter` catches no exceptions from `CardCreateService`** (lines 55–72): If `processAutoCardRecord()` throws an unchecked exception not caught within `CardCreateService`, Spring Batch will mark the chunk as failed. With `commit-interval=1`, this means one record failure per chunk, which Spring Batch will attempt to skip/retry based on its skip/retry policy. However, no skip or retry policy is configured in `AutoCardProcessJob.xml` for `autoCardCreateStep` — an uncaught exception will fail the entire step.

6. **`SimpleAsyncTaskExecutor` for partitioning** (`AutoCardProcessJob.xml` line 49, `AutoCardLoadRecordsJob.xml` line 49): `SimpleAsyncTaskExecutor` creates a new thread per task with no thread pool limit. Under high record volumes, this could exhaust thread resources. A `ThreadPoolTaskExecutor` with bounded pool size would be safer.

7. **`AutoCardTransactionCountSavingListener` synchronises on `this`** (line 51): The `synchronized(this)` block is used to aggregate execution counts across partitioned step threads. While technically correct for in-process partitioning, this is a non-standard pattern for Spring Batch and could become a contention bottleneck with larger grid sizes. The Spring Batch `ExecutionContextPromotionListener` is a more appropriate mechanism (and is also used in parallel in this same step).

8. **`autocard.pagesize = 5` and `autocard.gridsize = 5`**: Maximum 25 records per job invocation. If the pending queue grows beyond 25, the `AutoCardLimitDecider` CONTINUE loop handles it — but with 5 threads each reading 5 records at the same time from the same SP with no partitioning key, there is a risk of the same records being read by multiple partitions (the SP must implement row-locking or status-based exclusion to prevent duplicate processing).
