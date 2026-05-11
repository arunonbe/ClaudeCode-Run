# chargeback-engine_LIB — Solution Architect View

## Technical Architecture

The application is a single-process Java batch executor with a three-tier data access layer. There is no HTTP server, message broker, or service framework.

### Component Map

```
ChargebackMain (entry point)
    |
    +-- Spring ClassPathXmlApplicationContext (ChargebackProcess.xml)
    |       |
    |       +-- Context (bean: "config")
    |               |-- CoreGenericDAO        --> Core DB (via Director DBCP)
    |               |-- ReportingGenericDAO   --> Vendor/Reporting DB (via Director DBCP)
    |               +-- FDRODSChargebackDAO   --> FDR ODS (via JDBC-ODBC / DBCP)
    |
    +-- ThreadPoolExecutor (fixed pool, default 20 threads)
    |
    +-- ChargebackProcessor (RowCallbackHandler)
    |       Streams rows from chargeback_process_service
    |       Dispatches ChargebackHelper Runnables to thread pool
    |
    +-- ChargebackHelper (Runnable, one instance per chargeback row)
            1. Calls FDRODSChargebackDAO.execute(query)
            2. Calls ReportingGenericDAO.execute(chargeback_process_callback)
            3. Calls CoreGenericDAO.execute(chargeback_process_core_callback)
```

### Execution Sequence

1. Spring context loaded from `ChargebackProcess.xml` on classpath.
2. `process_id` obtained from CLI arg or `exec chargeback_process_begin`.
3. `exec chargeback_process_service <process_id>` streamed via `JdbcTemplate.query()` with `ChargebackProcessor` as callback.
4. Each row dispatched to `ThreadPoolExecutor`; `ChargebackHelper.run()` executes per row.
5. Main thread awaits `threadPool.awaitTermination(3600, SECONDS)`.
6. `exec chargeback_process_end <process_id>, 2|3` written.

---

## API Surface

This library exposes **no external API**. There are no REST endpoints, SOAP services, JMS topics, or RPC interfaces.

**External interfaces consumed:**

| Interface | Direction | Protocol | Details |
|---|---|---|---|
| `chargeback_process_begin` | Outbound | JDBC SQL | Stored proc on Reporting DB; returns INT `process_id` |
| `chargeback_process_service <id>` | Outbound | JDBC SQL | Stored proc; returns result set of chargeback rows |
| `chargeback_process_callback <id>, '<result>'` | Outbound | JDBC SQL | Stored proc on Reporting DB; records ODS outcome |
| `chargeback_process_end <id>, <status>` | Outbound | JDBC SQL | Stored proc on Reporting DB; terminates run |
| ODS `<query>` | Outbound | JDBC-ODBC | Pre-built query string from DB row; returns `CB_PRCS_ID` |
| `chargeback_process_core_callback '<comment>', <fee>, '<dda>'` | Outbound | JDBC SQL | Stored proc on Core DB; applies fee and comment |
| Director service | Outbound | HTTP (plaintext) | Connection factory for Core and Reporting DataSources |

**Public Java API (as a library):**

The repository name ends in `_LIB`, but no public API is defined beyond `ChargebackMain.main()`. There are no `@Service`, `@Component`, or interface definitions. The classes are concrete implementations with no abstraction layer. If this is consumed as a library by another project, it would need to instantiate `ChargebackMain` directly or replicate its wiring.

---

## Security Posture

### Critical Findings

1. **SQL Injection** (`ChargebackHelper.java` lines 42, 60):
   - `chargeback_process_callback` call: `"exec chargeback_process_callback " + chargebackRecord.get("chargeback_id") + ", '" + result + "'"` — `result` has only `'` stripped; `chargeback_id` is cast to Integer but sourced from DB row.
   - `chargeback_process_core_callback` call: `"exec chargeback_process_core_callback '" + comment + "'," + chargebackRecord.get("fee_amount") + ",'" + chargebackRecord.get("dda_number") + "'"` — `dda_number` and `comment` are string-interpolated with only `'` stripped.
   - `ChargebackHelper.java` line 35: The `query` column value is executed verbatim against the FDR ODS with only `'` stripped from the result. If the `query` column itself contains malicious SQL, it executes unchecked.
   - No parameterised queries (`PreparedStatement`) are used anywhere.

2. **Plaintext credentials in VCS** (`ChargebackProcess.properties` lines 13-14; `.mvn/wrapper/settings.xml` lines 37-50):
   - ODS: `ods.username=CBASEAPP`, `ods.password=[REDACTED — rotate immediately]`
   - Nexus proxy: `acmng` / `acmng`
   - Nexus QA: `deployment` / `dwil15?`
   - ecount release: `deployment` / `d3v0nly`

3. **Director service over HTTP** (`ChargebackProcess.properties` line 1: `http://ppamwdcddcor1:80/...`): All database connection parameters retrieved in cleartext; susceptible to MITM attack.

4. **JDBC-ODBC bridge (no TLS)** (`ChargebackProcess.properties` line 9-10): `sun.jdbc.odbc.JdbcOdbcDriver` with `jdbc:odbc:mcyc`. Transport security is entirely dependent on the OS ODBC DSN configuration with no enforcement in code.

5. **Non-volatile shared mutable state** (`Context.java` line 25): `boolean has_errors` written from multiple worker threads without synchronisation. Under Java Memory Model, writes from worker threads are not guaranteed to be visible to the main thread, potentially masking errors and reporting false success.

### Moderate Findings

6. **Unbounded `LinkedBlockingQueue`** (`ChargebackMain.java` line 43): `new LinkedBlockingQueue<Runnable>()` — no capacity limit. If `chargeback_process_service` returns a very large result set, the queue grows without bound, risking `OutOfMemoryError`.

7. **Log4j 1.x** (`log4j.xml`): Log4j 1.x is end-of-life. Known CVEs include `CVE-2019-17571` (SocketServer deserialization) and `CVE-2022-23302/23305/23307`. While these require specific configurations (Chainsaw, SocketServer), the library should be replaced.

8. **`queryForInt` deprecated** (`ChargebackMain.java` lines 62, 119, 121): `JdbcTemplate.queryForInt()` was deprecated in Spring 3.x and removed in Spring 5.x. With Spring 2.5.6 this functions, but indicates the code has never been updated.

9. **`Hashtable` usage** (`ChargebackProcessor.java` line 34; `ChargebackHelper.java` line 17): `java.util.Hashtable` is a synchronised legacy class; `HashMap` or `ConcurrentHashMap` would be more appropriate depending on access pattern.

---

## Technical Debt

| Item | Location | Debt Type |
|---|---|---|
| Java 1.6 target; JDK 8+ breaks ODS driver | `pom.xml` lines 54-55 | Obsolescence |
| Spring 2.5.6.SEC02 (EOL ~2009) | `pom.xml` line 27 | Obsolescence / Security |
| Log4j 1.x | `log4j.xml`, `pom.xml` (transitive) | Security |
| `sun.jdbc.odbc.JdbcOdbcDriver` (removed JDK 8) | `ChargebackProcess.properties` line 9 | Obsolescence / Portability |
| `commons-httpclient` 3.0 (EOL) | `pom.xml` line 43 | Obsolescence / Security |
| `junit` 3.8.1 (EOL, ~2002) | `pom.xml` line 20 | Obsolescence |
| No parameterised SQL anywhere | All DAO classes and `ChargebackHelper.java` | Security / Code quality |
| Plaintext credentials in committed files | `ChargebackProcess.properties`, `settings.xml` | Security |
| Raw types (`List` without generics) | `CoreGenericDAO.java` line 31; `ReportingGenericDAO.java` line 31 | Code quality |
| `Hashtable` instead of `Map` | `ChargebackProcessor.java` line 34 | Code quality |
| Non-thread-safe `has_errors` flag | `Context.java` line 25 | Concurrency bug |
| Unbounded task queue | `ChargebackMain.java` line 43 | Reliability risk |
| Zero unit-test coverage of business logic | Test directory | Testability |
| `0.0.1-SNAPSHOT` version never incremented | `pom.xml` line 7 | Release management |
| `core_agent=b2ctest` — test value in committed config | `ChargebackProcess.properties` line 3 | Configuration hygiene |
| Wirecard-era Nexus URL in settings | `.mvn/wrapper/settings.xml` line 12 | Infrastructure coupling |
| HTTP (not HTTPS) for Director service | `ChargebackProcess.properties` line 1 | Security |

---

## Gen-3 Migration Requirements

To migrate this capability to a Gen-3 architecture, the following changes are required:

### Must-Have (Blockers)

1. **Replace JDBC-ODBC / FDR ODS integration**: The `sun.jdbc.odbc.JdbcOdbcDriver` with ODBC DSN must be replaced. Options:
   - Direct JDBC connection to FDR database (if FDR provides a JDBC-compatible endpoint).
   - REST/API integration with FDR (preferred for Gen-3; FDR/First Data provides ISO 8583 and REST APIs).
   - Message-queue-based submission if FDR supports it.

2. **Eliminate Director service dependency**: Replace `DirectorConfiguredDBCPdatasourceCreator` with standard Spring Boot DataSource auto-configuration using environment variables or a secrets manager (Vault, AWS Secrets Manager, Azure Key Vault).

3. **Externalise all credentials**: Move `ods.password`, database passwords, and all credentials out of source control into a secrets manager. Rotate all currently committed credentials immediately.

4. **Replace stored-procedure-centric logic with domain services**: Stored procedures `chargeback_process_begin`, `chargeback_process_service`, `chargeback_process_callback`, `chargeback_process_end`, and `chargeback_process_core_callback` must be mapped to Gen-3 service layer equivalents.

5. **Upgrade to supported Java and Spring Boot**: Minimum Java 17 LTS; Spring Boot 3.x. This eliminates `queryForInt`, raw types, `Hashtable`, and Log4j 1.x in one upgrade.

### Should-Have

6. **Replace string-concatenated SQL with parameterised queries**: Use `JdbcTemplate.update(sql, param1, param2)` or named parameters throughout.

7. **Replace `ThreadPoolExecutor` with managed async**: Spring `@Async` with a configured `ThreadPoolTaskExecutor`, or a message queue (Kafka, SQS) for parallelism with back-pressure.

8. **Replace unbounded queue**: Bounded queue with rejection policy, or route to a dead-letter queue.

9. **Add structured audit logging**: Write a structured (JSON) audit record per chargeback processed, including outcome, `chargeback_id`, timestamp, and process_id.

10. **Add metrics instrumentation**: Micrometer with Prometheus/Grafana or equivalent — count of chargebacks processed, success/failure rates, ODS call latency.

11. **Fix `has_errors` thread safety**: Use `AtomicBoolean` or a proper error-collection mechanism.

### Nice-to-Have

12. **Add retry logic for ODS failures**: Configurable retry with exponential backoff for transient ODS errors.
13. **Add dead-letter handling**: Failed chargebacks written to a retry queue or error table rather than silently skipped.
14. **Proper integration tests**: Replace `InitTest.java` with testcontainer-backed integration tests.

---

## Code-Level Risks

| Risk | Class | Line(s) | Detail |
|---|---|---|---|
| SQL injection via `dda_number` | `ChargebackHelper` | 60 | `dda_number` from DB row interpolated into stored-proc call string; only `'` stripped from `comment` and `result`, not from `dda_number` |
| SQL injection via `query` column execution | `ChargebackHelper` | 35 | The entire `query` value from the DB row is executed verbatim against FDR ODS |
| Race condition on `has_errors` | `Context` | 25, 99-101 | Plain `boolean` written from multiple threads; may produce incorrect exit status |
| Unbounded memory growth | `ChargebackMain` | 43 | `new LinkedBlockingQueue<Runnable>()` with no capacity limit |
| JVM exit on thread interruption masking partial success | `ChargebackMain` | 103-104 | `InterruptedException` sets `has_errors` but does not differentiate interrupted-before-start vs interrupted-mid-run |
| ODS connection pool forced to `PrintWriter(System.out)` | `FDRODSChargebackDAO` | 34 | `dataSource.setLogWriter(new PrintWriter(System.out))` on init — may leak connection pool internals (including connection strings) to stdout |
| CLOB truncation at 8000 chars | `ChargebackProcessor` | 75 | `rs.getClob(i).getSubString(1, 8000)` — data silently truncated with no warning |
| Null return from `getCause()` not guarded | `FDRODSChargebackDAO` | 53 | `e.getCause().getMessage()` — if `getCause()` returns null (exception with no cause), this throws a `NullPointerException`, hiding the original error |
| Exception swallowed in `processRow` | `ChargebackProcessor` | 83-85 | `SQLException` is caught and stack-traced but not re-thrown and not flagged on `Context`; the record is still dispatched to the thread pool in a potentially incomplete state |
