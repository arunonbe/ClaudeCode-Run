# chargeback-engine_LIB — Enterprise Architect View

## Platform Generation (Gen-1/Gen-2/Gen-3)

This repository is firmly **Gen-1**.

Supporting evidence:

| Indicator | Evidence |
|---|---|
| Spring 2.5.6 (2008-era) XML-driven IoC | `pom.xml` line 26-28; `ChargebackProcess.xml` |
| Java 1.6 compilation target | `pom.xml` lines 54-55 |
| `sun.jdbc.odbc.JdbcOdbcDriver` (JDBC-ODBC bridge, removed in JDK 8) | `ChargebackProcess.properties` line 9 |
| ODBC DSN dependency (`mcyc`) requiring OS-level configuration | `ChargebackProcess.properties` line 10 |
| Package namespace `com.ecount.process` | All Java source files |
| Director service for database connection resolution (proprietary ecount infrastructure) | `ChargebackProcess.xml` lines 12-14; `ChargebackProcess.properties` line 1 |
| Wirecard-era Nexus hostname in settings | `.mvn/wrapper/settings.xml` line 12 |
| No REST API, message queue, or cloud integration | Entire codebase |
| Artifact version permanently at `0.0.1-SNAPSHOT` | `pom.xml` line 7 |

---

## Business Domain

**Disputes & Chargebacks** within the Prepaid Card / Payments domain.

- The system automates the submission of "no-authorization" prepaid card chargebacks to the FDR (First Data Resources) card processor.
- It sits at the intersection of **cardholder services** (fee application, account comments), **card processing** (FDR ODS interaction), and **back-office reporting** (process lifecycle tracking in the vendor/reporting database).
- The `dda_number` and `fee_amount` fields confirm this operates directly on cardholder accounts.

---

## Role in Platform

`chargeback-engine_LIB` is a **batch processing worker** that acts as an integration bridge between three internal/external systems:

```
[Reporting/Vendor DB]  <-->  [chargeback-engine_LIB]  <-->  [FDR ODS]
                                        |
                                        v
                               [Core ecount DB]
```

- It does **not** expose any API or service interface; it is a consumer, not a provider.
- It is a **library/batch executable** — the `_LIB` suffix in the repository name and the `jar-with-dependencies` packaging confirm this role.
- It depends on the **Director service** (`ppamwdcddcor1`) for database connection provisioning — placing it firmly within the Gen-1 ecount platform's infrastructure model.
- The `ecount-system` (version 1.0.10) dependency from the internal repository is the shared platform library that provides the `DirectorConfiguredDBCPdatasourceCreator` factory. This is a proprietary coupling to Gen-1 infrastructure.

---

## Dependencies

### Upstream (inputs to this service)

| System | Interface | Details |
|---|---|---|
| Reporting/Vendor DB (`vendor` database) | SQL stored procedures | Provides chargeback records via `chargeback_process_service`; receives outcomes via `chargeback_process_callback` and `chargeback_process_end` |
| Director service | HTTP (plaintext) | `http://ppamwdcddcor1:80/service/dispatch.asp` — provides DBCP DataSource for Core and Reporting DBs |

### Downstream (systems this service calls)

| System | Interface | Details |
|---|---|---|
| FDR ODS | JDBC-ODBC (DSN `mcyc`) | Receives pre-built chargeback submission queries; returns `CB_PRCS_ID` |
| Core DB (`ecountcore`) | SQL stored procedure | Receives `chargeback_process_core_callback` to apply fees and comments |

### Build-time Dependencies

| System | Interface | Details |
|---|---|---|
| Internal Nexus (Wirecard-era) | Maven | `d-na-stk01.nam.wirecard.sys:8081` — may be decommissioned |
| GitHub Packages (Onbe) | Maven | `maven.pkg.github.com/onbe/onbe_maven_releases` — provides `ecount-system` |

---

## Integration Patterns

| Pattern | Implementation | Assessment |
|---|---|---|
| Stored-procedure invocation | All database interaction via `JdbcTemplate.queryForList()` / `queryForInt()` / `query()` on named stored procedures | Gen-1 pattern; tightly couples Java to DB schema |
| Row-streaming with callback | `ChargebackProcessor implements RowCallbackHandler` | Efficient for large result sets; but unbounded `LinkedBlockingQueue` is a memory risk |
| Thread pool for parallelism | `ThreadPoolExecutor` with fixed pool size (default 20) | Manual thread management; no framework support |
| Configuration externalisation | Spring `PropertyPlaceholderConfigurer` reading `.properties` file | Basic externalisation; no environment profiles, no secrets vault |
| Fat-JAR deployment | `maven-assembly-plugin` `jar-with-dependencies` | Simple deployment but bundles all dependencies; no OSGi or module isolation |
| Fire-and-forget with error flag | `ChargebackHelper` sets `Context.has_errors` but does not propagate individual record errors | Coarse-grained error handling |

No message queues (JMS, Kafka, RabbitMQ), REST/SOAP web services, or event-driven patterns are used. The entire integration model is synchronous stored-procedure calls and JDBC-ODBC.

---

## Strategic Status

| Dimension | Assessment |
|---|---|
| Active development | Unlikely — version is `0.0.1-SNAPSHOT`; no CI build pipeline; CodeQL is the only automated workflow |
| Production status | Uncertain — properties contain `core_agent=b2ctest` which could indicate test environment values are committed |
| Replacement planned | Assumed — Gen-1 architecture with EOL stack; expected to be superseded by a Gen-3 disputes/chargebacks capability |
| Maintainability | Very Low — Java 6 target, Spring 2.5.6, Log4j 1.x, JDBC-ODBC bridge; no developer is likely to have modern tooling that supports this stack natively |
| Operational continuity risk | High — JDK requirement is JDK 7 or earlier (JDBC-ODBC bridge removed in JDK 8); patching the JDK would break the ODS connection |

---

## Migration Blockers

| Blocker | Severity | Detail |
|---|---|---|
| ODBC DSN (`mcyc`) for FDR ODS | Critical | The FDR ODS connection uses a local ODBC DSN. Migration to Gen-3 requires replacing this with a network-accessible JDBC driver or an API-based integration with FDR/First Data |
| Director service dependency | High | `DirectorConfiguredDBCPdatasourceCreator` from `ecount-system` 1.0.10 resolves database connections through the proprietary Director service. Gen-3 migration requires replacing this with standard DataSource configuration (environment variables, secrets manager, or service discovery) |
| Stored-procedure-centric business logic | High | All business rules live in stored procedures (`chargeback_process_begin`, `chargeback_process_service`, `chargeback_process_callback`, `chargeback_process_end`, `chargeback_process_core_callback`). These procedures must be replicated or replaced before decommissioning |
| `ecount-system` internal library | High | Proprietary `com.ecount.service.Core2:ecount-system:1.0.10` must be available or its functionality (Director-based DataSource creation) must be re-implemented |
| Java 6 compilation target | Medium | All source must be verified compatible with a supported JDK (17+) before migration; use of raw types, `Hashtable`, and deprecated APIs will require remediation |
| Wirecard Nexus hostname in settings | Medium | Build infrastructure references `d-na-stk01.nam.wirecard.sys` — this may be decommissioned; needs replacement with current Onbe artifact registry |
| No unit tests covering business logic | Medium | `InitTest.java` only tests Spring context loading; zero test coverage of `ChargebackHelper`, `ChargebackProcessor`, or error paths means migration cannot be validated with automated tests |
