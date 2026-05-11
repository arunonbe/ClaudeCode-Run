# cancel-transaction-process_LIB — Solution Architect View

## Technical Architecture

The component is a single-module Maven project producing a standalone fat JAR batch process. It follows a layered Gen-1 Spring XML architecture:

```
CLI Entry Point
  CancelTransactionProcessMain (main)
      |
      v
  Spring IoC Container (ClassPathXmlApplicationContext)
      |
      +-- Controller (IController)
      |       |
      |       +-- ProcessRunData           (config & runtime parameters)
      |       +-- ITransferDAO / TransferDAO  (data access)
      |       |       |
      |       |       +-- CorePendingTransactionsInquiry (StoredProcedure, Core DB)
      |       |       +-- UpdateDebitAuditInfo           (StoredProcedure, CBase App DB)
      |       |
      |       +-- TransferHelper           (Core API orchestration)
      |       |       |
      |       |       +-- ITransferManager (com.cbase — Core cancel API)
      |       |
      |       +-- ThreadPoolExecutor       (parallel task execution)
      |       +-- IRequestContextHolder    (Global Request ID / ThreadLocal)
      |       +-- MDCWriter                (Log4j MDC propagation)
      |
      +-- ControllerJMXExporter (JMX bridge to IController)
```

**Concurrency model:** `Controller` can execute tasks single-threaded (`maxPoolSize == 1`) or via a `ThreadPoolExecutor` (multi-threaded). Tasks are `Runnable` (`CancelTask`), each responsible for one transfer's full cancel lifecycle including retry loop. Thread-local request context is propagated to worker threads by capturing the Global Request UUID at construction time in `CancelTask` (line 57 of `CancelTask.java`).

**State machine (per CancelTask):**
```
NEW --> RUNNING --> FINISHED
                --> FAILED (retried up to maxTry; StatePhaseOutOfSync = no retry)
```

---

## API Surface

This library has **no inbound API surface** (no REST endpoints, no SOAP, no message listeners, no gRPC).

**Outbound API calls:**

| Interface | Implementation Class | Protocol/Mechanism | Purpose |
|---|---|---|---|
| `ITransferDAO.getPendingTransactionGroup()` | `CorePendingTransactionsInquiry` | JDBC stored procedure | Query pending transfers from Core DB |
| `ITransferDAO.updateDebitAuditInfo()` | `UpdateDebitAuditInfo` | JDBC stored procedure | Write audit record post-cancellation |
| `ITransferManager.cancel(Transfer)` | `TransferManagerImpl` (ecount Core2) | In-process / ecore API | Cancel transfer in Core system |

**Management API (JMX):**

MBean: `prepaid:name=CancelProcess` via `ControllerJMXExporter`

| Operation/Attribute | Type | Description |
|---|---|---|
| `taskCount` | int (read) | Total tasks submitted |
| `failedCount` | int (read) | Tasks in FAILED state |
| `incompleteCount` | int (read) | Tasks in NEW or RUNNING state |
| `finishedCount` | int (read) | Tasks in FINISHED state |
| `retryCount` | int (read) | Tasks that required >1 attempt |
| `forceTerminate()` | int (operation) | Calls `shutdownNow()`, returns queued task count |
| `terminateAllTasks()` | int (operation) | Removes all NEW tasks from queue |
| `terminateTask(transferId)` | boolean (operation) | Removes specific NEW task by transfer UUID |

---

## Security Posture

### Authentication & Authorisation
- **No authentication mechanism** is implemented in this library. Access is controlled entirely by OS-level process execution permissions (who can run the bat script / trigger the scheduler job).
- **JMX endpoint has no authentication configured** in `appCtx-jmx.xml`. `MBeanExporter` is configured with `REGISTRATION_REPLACE_EXISTING` but no `MBeanServerFactoryBean` with security constraints. JMX access to `forceTerminate()` or `terminateAllTasks()` by an unauthorised party would disrupt the running process.
- **No Spring Security, no RBAC** present in any context file.

### Credential Management
- Database credentials are externalised via the ecount Director service (not hardcoded). The Director's own security model is not visible in this codebase.
- The `agent` and `memberId` values are passed via properties file and Spring XML. These act as authentication tokens to the Core API and should be treated as secrets.

### Data Security
- `dda_number` (DDA account number) is loaded into JVM heap via `TransferDTO.accountId` from the Core DB result set. It is **not masked, tokenised, or encrypted** in memory or in any log output.
- `transfer_id` (UUID) is logged extensively at INFO level. UUIDs are generally not sensitive, but in aggregate they could be used to enumerate transactions.
- `amount` (long) is in memory but not logged in the identified log statements.
- No TLS/SSL configuration is present in JDBC data source setup — this is delegated to the Director DBCP factory.

### Code-level Security Observations
- `UpdateDebitAuditInfo` uses `com.cbase.pi.log.SystemLog` (a Gen-1 platform logger) alongside `FormatLog`. `SystemLog.write()` is called with a reference to `ds.toString()` at constructor time — this could leak connection string details to the system log if `DataSource.toString()` includes credentials (vendor-dependent).
- `PendingTransactionGroupParameter` has **public fields** (no encapsulation): `programId`, `transactionType`, `startDate`, `endDate`, `limitTrans` — a minor code quality issue but not a direct security risk.

---

## Technical Debt

| Debt Item | Location | Severity | Description |
|---|---|---|---|
| Disabled `-transfer` mode with "Bad boy." message | `Controller.validateParameters()` line 288–291 | High | Single-transfer CLI mode is parsed but blocked. The comment is unprofessional; the feature is half-implemented. |
| Spring 2.5.6 (EOL) | `pom.xml` line 20 | Critical | Spring 2.5.6 is from 2008 and has known CVEs; no security patches available. |
| JUnit 3 test framework | `pom.xml` line 100–104 | High | JUnit 3 (`3.8.1`) is severely outdated; no parameterised tests, no annotations. |
| Zero functional test coverage | `AppTest.java` | Critical | The only test is `assertTrue(true)` — a no-op stub. Zero coverage of any business logic. |
| Tests skipped in all CI stages | `.gitlab-ci.yml` | High | Even the stub test is skipped. No test execution gate in CI. |
| `program_id` always null in query | `Controller.java` line 75 | Medium | `parameter.programId = null` hardcoded; the stored procedure parameter exists but is never used. Program filtering is done in-application post-query, wasting database selectivity. |
| Public fields in parameter class | `PendingTransactionGroupParameter.java` | Low | `programId`, `transactionType`, `startDate`, `endDate`, `limitTrans` are all `public` (no getters/setters). TODO comment notes this. |
| Inverted numeric encoding for TransactionPhase vs TransferState | `TransactionPhase.java` / `TransferState.java` | Medium | PENDING maps to int 1 in `TransactionPhase` but int 0 in `TransferState`. This inconsistency is a latent bug source. |
| `COMITTED` typo in enum values | `TransferState.java` line 8, `TransactionPhase.java` line 8 | Low | Both enums spell `COMMITTED` as `COMITTED` — propagating through the comparison logic in `TransferHelper`. |
| `SystemLog` in `UpdateDebitAuditInfo` | `UpdateDebitAuditInfo.java` lines 37–46 | Medium | Mixed logging frameworks (Gen-1 `SystemLog` + `FormatLog`); `ds.toString()` could expose connection details. |
| `maven-assembly-plugin` uses deprecated `attached` goal | `pom.xml` line 60 | Low | `<goal>attached</goal>` is deprecated in maven-assembly-plugin 2.2+; should be `<goal>single</goal>`. |
| `wagon-webdav:1.0-beta-2` extension | `pom.xml` lines 36–40 | Medium | Very old beta WebDAV wagon; only needed for legacy Maven 2 repository deployment. |
| Version SNAPSHOT in production config | `pom.xml` line 12 | Medium | `1.0.1-SNAPSHOT` is a non-release version. SNAPSHOT artifacts are mutable and not reproducible. |
| `SpringUtils.getApplicationContex()` typo | `SpringUtils.java` line 26 | Low | Method name missing the 't' (`getApplicationContex` not `getApplicationContext`). |
| Double-checked locking in `SpringUtils` | `SpringUtils.java` lines 15–23 | Low | Pattern is safe in Java 5+ with `volatile` but `context` is not declared `volatile` — theoretically unsafe under JMM. |
| No executor configuration in bundled XML | `cancelTransactionProcessContext.xml` | Medium | The `executor` bean is referenced but not defined in the bundled context XML, meaning it must be provided by the consumer config. If missing, startup fails with a `NoSuchBeanDefinitionException`. |

---

## Gen-3 Migration Requirements

A Gen-3 re-implementation of this component would require:

1. **Framework replacement:** Spring Boot 3.x (replacing Spring XML 2.5.6). All bean wiring to be annotation/Java-config driven.
2. **Batch framework:** Spring Batch or Quartz scheduler to replace the bespoke batch loop and manual retry logic. Spring Batch provides built-in job tracking, restartability, and chunk-oriented processing.
3. **Data access:** Spring Data JPA or JDBC Template (annotation-driven, no `StoredProcedure` subclassing). If stored procedures must be retained, use `SimpleJdbcCall`.
4. **Core API decoupling:** Abstract `ITransferManager.cancel()` behind a Gen-3 service client interface (REST or gRPC) to break the direct dependency on `com.cbase.business.core.impl.TransferManagerImpl` and `ECoreTransfer`.
5. **Configuration:** Replace `CBASE_HOME_URL` + properties file with Spring Boot `application.yml` + cloud-native secret/config management (AWS SSM Parameter Store, Secrets Manager, or Kubernetes ConfigMaps/Secrets).
6. **Data sources:** Replace `DirectorConfiguredDBCPdatasourceCreator` with HikariCP (Spring Boot default) configured from environment variables or secrets manager.
7. **Logging/Observability:** Replace Log4j 1.x / Commons Logging with SLF4J + Logback (Spring Boot default). Add structured JSON logging, distributed tracing (OpenTelemetry), and metrics (Micrometer + Prometheus/Datadog).
8. **JMX:** Replace `MBeanExporter`-based JMX with Spring Boot Actuator endpoints (`/actuator/health`, `/actuator/metrics`) accessible over HTTP.
9. **Test coverage:** Replace JUnit 3 stub with JUnit 5 + Mockito tests covering `Controller`, `CancelTask`, `TransferHelper` state machine logic, and DAO mapping.
10. **Deployment:** Replace Windows bat + fat JAR with a containerised deployment (Docker image) on a Kubernetes CronJob or ECS Scheduled Task, eliminating the Windows-specific scheduler dependency.

---

## Code-Level Risks

1. **`Controller.validateParameters()` line 288–291 — blocked transfer ID mode:**
   ```java
   if (processRunData.getTransferId() != null) {
       throw new IllegalArgumentException("Bad boy.");
   }
   ```
   The `-transfer` CLI switch is fully parsed in `CancelTransactionProcessMain.parseCommandLineArgs()` and set in `ProcessRunData`, but then immediately blocked at validation. This makes the switch a dead code path. Risk: an operator invoking `-transfer` will receive a cryptic error and the process will exit with code 3 (`System.exit(3)`).

2. **`Controller.executeProcess()` — `program_id` always null (line 75):**
   ```java
   parameter.programId = null;
   ```
   The stored procedure's `program_id` filter is never used. All filtering is in-memory post-query. With the 101-record limit, high-volume queues will trigger `DataLimitException` before filtered transfers are returned.

3. **`TransferHelper.cancelTransaction()` — state/phase name comparison (line 44):**
   ```java
   if (!transferState.name().equals(transactionState.name())) {
   ```
   This compares enum names as strings (`"PENDING"`, `"COMMITTED"`, etc.). Because `COMITTED` is misspelled identically in both enums, the comparison works for existing values. However, if one enum is corrected and the other is not, all transfers will fail with `StatePhaseOutOfSyncStateException`.

4. **`UpdateDebitAuditInfo` constructor — `SystemLog` with DataSource toString (lines 44–46):**
   ```java
   SystemLog.write(..., " dataSource := " + ds.toString());
   ```
   If the DBCP `DataSource.toString()` implementation includes JDBC connection URL or credentials in its string representation, this would leak sensitive infrastructure details to the system log.

5. **`CancelTask.executeTask()` — unprotected thread interrupt (line 152):**
   ```java
   Thread.sleep(sleepTime);
   ```
   `InterruptedException` from `Thread.sleep()` in the retry loop is caught by the outer `catch (Exception e)` block (line 157), which sets `state = TaskState.FAILED`. An external interrupt (e.g., JVM shutdown) during a sleep will silently mark the task as failed rather than propagating the interrupt signal.

6. **`SpringUtils` — non-volatile double-checked locking (lines 15–23):**
   ```java
   private static ApplicationContext context;
   ...
   if (context == null) { synchronized (SpringUtils.class) { if (context == null) { ... } } }
   ```
   `context` is not declared `volatile`. Under the Java Memory Model, without `volatile`, a second thread could observe a partially-constructed `ApplicationContext`. In practice this is unlikely to cause issues on modern JVMs with JIT, but it is technically incorrect.

7. **`Controller.terminateTask()` — ConcurrentModificationException risk (lines 473–489):**
   The method iterates `taskList` with a for-each loop and calls `taskList.remove(task)`. This will throw `ConcurrentModificationException` at runtime if any other thread is iterating the same list. The `terminateAllTasks()` method correctly uses an `Iterator.remove()` but `terminateTask()` does not.

8. **`DataLimitException` error code collision risk:** `ErrorCodes.resolve(int)` (line 28) always returns `ERROR_DATA_RETRIEVAL` for any unrecognised code, masking unexpected stored procedure return codes silently.
