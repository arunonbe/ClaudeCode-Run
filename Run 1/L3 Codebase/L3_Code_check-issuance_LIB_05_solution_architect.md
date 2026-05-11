# check-issuance_LIB — Solution Architect View

## Technical Architecture

The library is a **standalone Java batch application** structured as a Maven JAR with embedded dependencies (fat-JAR via `maven-assembly-plugin`). It follows a layered Gen-1 architecture:

```
Entry Point
  CheckIssuance.java (static main)
       │
       ├─ SpringUtils.java               [Singleton ApplicationContext loader]
       │       └─ appContext.xml         [Spring 2.5 DTD-based IoC container]
       │
       ├─ CheckIssuanceHelper.java       [Business logic — fund transfer, balance calc, enrollment]
       │       ├─ ITransferManager       [Core2 RPC — fund transfer]
       │       ├─ IDeviceInfoManager     [Core2 RPC — account/balance lookup]
       │       └─ CheckIssuanceProcessDaoInt  [DAO interface]
       │
       ├─ ProcessCheckRecordsImpl.java   [Thread pool manager — ExecutorService]
       │       └─ RequestProcessorThread [Runnable — per-batch worker]
       │
       └─ CheckIssuanceProcessDaoImpl.java  [DAO implementation]
               ├─ CreateCheckIssuanceRecords.java     [StoredProcedure]
               ├─ CheckIssuanceTransactionsList.java  [StoredProcedure + RowMapper]
               └─ CheckIssuanceUpdTransaction.java    [StoredProcedure]
```

**Key architectural characteristics:**
- No inbound API surface (batch-only).
- Spring `ApplicationContext` is lazily initialised as a static singleton in `SpringUtils` (line 10–34) — not thread-safe due to commented-out `synchronized` block (lines 18–23).
- The same `CheckIssuanceHelper` bean is retrieved from Spring context inside every `RequestProcessorThread.run()` call (line 58) — meaning all threads share a single mutable helper instance with unsynchronised state.
- `CheckIssuanceData` is an abstract class; `CheckIssuanceRequest` and `CheckIssuanceResponse` extend it with no additional fields — both are empty marker subclasses.

## API Surface

**No public API surface.** This is a library/batch executable with:
- One `public static void main(String[] args)` entry point in `CheckIssuance.java` (line 23) — ignores all command-line arguments.
- One `public` method on `CheckIssuanceHelper`: `processTransaction(CheckIssuanceData)` (line 401) and `enrollmentProcessor(CheckIssuanceData)` (line 617) and `transactionInquiryAndExceptionHandler(CheckIssuanceData)` (line 89).
- `IProcessCheckRecords` interface (three methods): `processTransactions()`, `hasAllThreadsCompleted()`, `shutdownThreadpool()`.
- `CheckIssuanceProcessDaoInt` interface (three methods): `createCheckIssuanceProcessRecords()`, `getCheckIssuanceTransactionsList()`, `updCheckIssuanceTransaction()`.

The library is consumed by other batch processes within the platform by including the JAR as a dependency and calling `CheckIssuance.main()` or by wiring the helper/DAO beans via Spring context.

## Security Posture

### Authentication & Authorization
- No authentication mechanism is implemented in the Java code itself.
- Database access is authenticated via DBCP connection pool credentials resolved through the Director service at startup.
- The BCP extraction script (`citiCPSStopRefundCheck.vbs`) authenticates to SQL Server using a plaintext username and password from an INI file (lines 75–78, 95) — a critical security deficiency.

### Secrets Management
- No secrets manager. All credentials are in plaintext files on the Windows filesystem.
- `operatorId` is injected via Spring property placeholder from `checkissuance.properties` — stored in plaintext.

### Input Validation
- **None observed.** Values from the stored procedure result set are mapped directly to `CheckIssuanceData` fields with no null checks, range validation, or sanitisation in `CheckIssuanceTransactionsList.CheckIssuanceTransactionsListExtractor.mapRow()` (lines 84–111).
- The `errorDesc` field passed to `updCheckIssuanceTransaction()` is constructed by concatenating exception messages directly (e.g., `CheckIssuanceHelper.java` line 183: `"TRANSACTION NOT SUCESSFULLY CANCELLED " + cse.getCode() + " " + cse.getMessage()`). While this goes to a DB column (not a shell), it demonstrates no sanitisation discipline.

### Data in Logs
- `dda_number` appears in multiple `logger.debug()` / `logger.error()` calls with root log level `debug`.
  - `CheckIssuanceHelper.java` line 279: `"getAccountDetails dda_number " + checkIssuanceData.getDda_number()`
  - Line 403: `"processTransaction for... dda_number : " + data.getDda_number()`
  - Line 411: `"Exception in processTransaction method for DDA Number = " + data.getDda_number()`
  - Line 476: `"The DDA = " + data.getDda_number()`
  - Line 494: `"Exception in processTransaction method for DDA Number = " + data.getDda_number()`
  - Line 504: `"Entering the method transferFunds for transaction id: ... dda_number " + data.getDda_number()`
  - Line 567: `"Sucessfully processed for DDA Number = " + data.getDda_number()`

### Dependency Vulnerabilities
- **Log4j 1.2.14:** CVE-2019-17571 (CVSS 9.8) — deserialization via SocketServer. Likely not exploitable here (no SocketServer configured), but version must be upgraded.
- **Spring 2.5.4:** Multiple historical CVEs. No longer patched.
- **jTDS 1.2.4:** No active maintenance. Potential SQL Server protocol-level issues.
- **commons-io 1.3.2:** CVE-2021-29425 (path traversal) in versions < 2.7.
- **JUnit 3.8.1:** Test-scoped only; not a runtime risk.

### Encryption
- No TLS enforcement at the application layer.
- No field-level or file-level encryption.
- GPG encryption step for stop-refund files is **commented out** in `citiCPSStopRefundCheck.vbs` (lines 153–158).

## Technical Debt

| Debt Item | Location | Severity |
|---|---|---|
| Java 1.6 compile target | `pom.xml` lines 133–134 | Critical |
| Log4j 1.2.14 (EOL + CVE) | `pom.xml` line 46 | Critical |
| Spring 2.5.4 (EOL) | `pom.xml` line 59 | Critical |
| Un-synchronized `SpringUtils.getApplicationContex()` | `SpringUtils.java` lines 18–23 | High — race condition at startup |
| Un-synchronized counter fields in `CheckIssuanceHelper` | `CheckIssuanceHelper.java` lines 54–63 | High — data race under concurrency |
| `CheckIssuanceUpdTransaction` timeout commented out | `CheckIssuanceUpdTransaction.java` line 29 | High — unbounded lock holding |
| All tests disabled in CI | `.gitlab-ci.yml` lines 3, 5, 7 | High |
| `TestClass.java` is a placeholder | `src/test/java/TestClass.java` | High |
| `old_transaction_uuid` mapped to same value as `transaction_uuid` | `CheckIssuanceTransactionsList.java` line 87 | Medium — logic defect |
| Hardcoded Windows paths in config and properties | `appContext.xml` lines 9–13, `log4j.properties` line 6 | High |
| Plaintext DB password in VBS/INI | `citiCPSStopRefundCheck.vbs` lines 75–78, 95 | Critical |
| GPG encryption commented out | `citiCPSStopRefundCheck.vbs` lines 153–158 | Critical |
| `DDA_ACCOUNT_STATUS = "active"` declared but never used | `CheckIssuanceConstants.java` line 29 | Low |
| `ISSUANCE_PROGRAM_CHECK_AMT_MAXIMUM_LIMIT = 0` (unused) | `CheckIssuanceConstants.java` line 48 | Low |
| `IncrementableInteger` class defined but never used | `concurrency/IncrementableInteger.java` | Low |
| `JobsvcDataSource` bean declared but never wired | `appContext.xml` lines 23–30 | Low |
| Commented-out `enrollDefaultCheckDevice()` method | `CheckIssuanceHelper.java` lines 587–615 | Low — dead code |
| `TODO` comments indicating incomplete logic | `CheckIssuanceHelper.java` lines 175, 207 | Medium |
| `@SuppressWarnings("unchecked")` on raw type collections | Multiple DAO files | Low — type safety |
| Version `2.0.1-SNAPSHOT` — never released | `pom.xml` line 12 | Medium |
| jTDS 1.2.4 — deprecated JDBC driver | `pom.xml` line 105 | High |
| JUnit 3.8.1 | `pom.xml` lines 27–31 | Medium |
| BCP tool path hardcoded to SQL Server 2008 | `citiCPSStopRefundCheck.vbs` line 93 | High |
| `SNODE=NDMTEST` hardcoded in CDP script | `CITISTOPREFUNDCHECK.cdp` line 3 | High — possibly wrong environment |

## Gen-3 Migration Requirements

To migrate the functionality of this library to a Gen-3 cloud-native architecture, the following are required:

1. **Replace ecount Core2 RPC with REST/gRPC services:**
   - `ITransferManager.transferDDAToOperator()` → Call a Gen-3 Fund Transfer API.
   - `ITransferManager.inquiry()`, `commit()`, `cancel()` → Call Gen-3 Transfer Lifecycle API.
   - `IDeviceInfoManager.getAccountDetails()` → Call Gen-3 Account/Device Balance API.
   - `AppProfileUserEnrollmentClass.retrieve()`/`create()` → Call Gen-3 Member Preference API.

2. **Replace SQL Server stored procedures with a service layer:**
   - `check_process_create_records` → Event-driven work queue population or scheduler trigger.
   - `check_process_transaction_auto_post` → Read from a managed queue (SQS, Kafka, or a polling REST endpoint).
   - `check_process_transaction_auto_post_status_upd` → Write status via event/API call.

3. **Replace Windows VBScript launcher with a containerised scheduler:**
   - Package as a Docker container with a Java 17/21 base image.
   - Trigger via Kubernetes CronJob or a workflow orchestrator (Temporal, Airflow).

4. **Replace Sterling Connect:Direct with a secure API integration:**
   - If Citi CPS is still the check-printing vendor, integrate via their API (if available) or replace NDM transmission with SFTP/HTTPS file delivery.
   - If the check-printing vendor has changed, the entire `citiCPSStopRefundCheck.vbs` + `citiReportParser.pl` pipeline must be replaced.

5. **Implement secrets management:**
   - Replace plaintext INI file credentials with Vault, AWS Secrets Manager, or Azure Key Vault.
   - Remove `-P password` from BCP command lines.

6. **Address thread safety:**
   - Replace plain `int` counters with `AtomicInteger` or structured metrics (Micrometer/Prometheus).
   - Fix `SpringUtils` double-checked locking (or replace with standard Spring Boot context loading).

7. **Upgrade all dependencies to supported versions:**
   - Java 17 or 21 LTS.
   - Spring Boot 3.x (replaces Spring 2.5 + XML config).
   - Log4j2 / SLF4J+Logback.
   - Microsoft MSSQL JDBC driver (replaces jTDS).
   - JUnit 5.

8. **Implement proper test coverage:**
   - Unit tests for `CheckIssuanceHelper.processTransaction()`, `retryHandler()`, `enrollmentProcessor()`.
   - Integration tests against a test SQL Server instance or H2 in-memory DB with stored procedure mocks.

9. **Re-implement observability:**
   - Structured JSON logging (not plain-text pattern-based Log4j).
   - Micrometer metrics for success/failure counters.
   - Distributed tracing (OpenTelemetry) with `transaction_uuid` as trace context.

## Code-Level Risks

1. **`SpringUtils` race condition** (`SpringUtils.java` lines 18–23): The double-checked locking pattern is implemented but the `synchronized` block is commented out. If two threads call `getBean()` simultaneously before the context is initialised, two `ClassPathXmlApplicationContext` instances may be created. Given that all `RequestProcessorThread` instances call `SpringUtils.getBean("checkIssuanceHelper")` (line 58 of `RequestProcessorThread.java`), this risk is active.

2. **Shared mutable `CheckIssuanceHelper`** (`RequestProcessorThread.java` line 58): All threads retrieve the same Spring singleton bean. All counter increments (`setFailuresCount(getFailuresCount()+1)`) are non-atomic read-modify-write operations on `int` fields — classic race condition. Under a 10-thread pool, counters will undercount failures and successes.

3. **`old_transaction_uuid` identity mapping defect** (`CheckIssuanceTransactionsList.java` line 87): `response.setOld_transaction_uuid(rs.getString(TRANSACTION_UUID))` — sets `old_transaction_uuid` to the same value as `transaction_uuid`. If the SP returns a distinct `old_transaction_uuid` column, it is being silently discarded. This may cause incorrect behaviour in `updCheckIssuanceTransaction()` when tracking UUID replacement after cancel-and-retry.

4. **`processCheckRecords.hasAllThreadsCompleted()` blocking** (`CheckIssuance.java` line 101, `ProcessCheckRecordsImpl.java` lines 99–117): After `issueCheck()` loops, `hasAllThreadsCompleted()` spins in a `while(!hasAllDone())` loop sleeping 60 seconds per iteration. If `future.get()` in `hasAllDone()` throws an `ExecutionException` (thread threw an exception), it is not caught and will propagate as an unchecked exception, terminating the process without calling `shutdownThreadpool()`. The thread pool would leak.

5. **`threadPool.shutdown()` called after `hasAllThreadsCompleted()`** (`CheckIssuance.java` line 60): `shutdownThreadpool()` is called after both `issueCheck(AUTO)` and `issueCheck(MANUAL)` have returned. However, `hasAllThreadsCompleted()` (called at the end of each `issueCheck()`) does NOT call `shutdown()` (the call is commented out at line 114 of `ProcessCheckRecordsImpl.java`). This means threads could still be running when `issueCheck(MANUAL)` starts submitting new tasks to a pool that had tasks from the AUTO run that had not yet been reaped from `allFutureObjects`. The `allFutureObjects` list is shared across both AUTO and MANUAL runs.

6. **`System.exit(-1)` in catch-all `Throwable`** (`CheckIssuance.java` line 65): If any Spring bean initialisation throws, the process exits with code `-1` without any cleanup. The thread pool (if partially initialised) will not be shut down cleanly.

7. **`fee.amount` direct field access** (`CheckIssuanceHelper.java` line 418: `fee.amount = 0`): `Funds.amount` is accessed as a public field (not via a setter), indicating the `Funds` class from the Core2 library is using public field access — a coupling risk with any future Core2 library upgrade.

8. **No null guard on `result` before field access** (`CheckIssuanceHelper.java` line 562: `result.getTransfer().getId()`): If `transferDDAToOperator()` returns a `TransferCommitResult` with a null `transfer` object, this line throws a `NullPointerException`, which is caught by the outer `Throwable` catch at line 572 — but it increments `failuresCount` rather than providing a meaningful diagnostic.
