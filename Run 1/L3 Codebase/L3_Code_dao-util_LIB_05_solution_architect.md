# dao-util_LIB — Solution Architect View

## Architecture Overview
Pure Java 21 library built on Spring JDBC's `StoredProcedure` abstraction. No Spring Boot, no auto-configuration. Two sub-packages:

```
com.ecount.daoutil.common.jdbc
    DataProcedure               -- Primary SP executor (extends StoredProcedure)
    MetaData                    -- Caches SP parameter metadata per DataSource
    MetaDataConfiguredProcedure -- Alternative SP executor (separate MetaData instance)
    NoResultProcedure           -- SP with no result set (inferred from class name)
    OutputParameterReturningProcedure
    ResultSetReturningProcedure
    ResultSetAndParameterReturningProcedure
    SqlTimeoutManager           -- Spring bean; per-proc timeout config
    ProcedureColumnMetaData     -- Column metadata DTO
    ProcedureMetaData           -- Collection of column metadata for one procedure

com.ecount.daoutil.common.jdbc.proxy
    DataSourceProxy             -- JDK dynamic proxy over DataSource
    ConnectionProxy             -- JDK dynamic proxy over Connection
    StatementProxy              -- JDK dynamic proxy over Statement
    RemoveHangingTransaction    -- Executes sp_reset_connection on connection return

com.ecount.daoutil.datasource
    IDataSourceCreator          -- Interface for DataSource factory
    DBCPDataSourceCreator       -- DBCP BasicDataSource factory
    DirectorConfiguredDBCPdatasourceCreator  -- Director-driven DBCP factory
    DataSourceResolver          -- Connection string format translator
    test.java                   -- Empty/test class (should be removed)
```

## DataProcedure Execution Flow
```
Consumer creates DataProcedure(DataSource, procedureName)
    --> MetaData.getInstance(dataSource).get(procedureName)
        --> DatabaseMetaData introspection (live DB call at init time)
    --> declareParameter() for each column (IN, OUT, INOUT, RETURN)
    --> compile()
    
Consumer calls execute(Map inParams)
    --> applyTimeout() (queries SqlTimeoutManager for proc name)
    --> super.execute(inParams)  [Spring StoredProcedure]
    --> if isFunction(): check RETURN_VALUE != 0 --> throw DataExceptionReturnCode
    --> return output Map
```

## Class Hierarchy
```
StoredProcedure (Spring JDBC)
    |
    +-- DataProcedure (dao-util_LIB)
    |       Adds: timeout management, return-code handling, convenience accessors
    |
    +-- MetaDataConfiguredProcedure (dao-util_LIB)
            Uses separate MetaData instance (not the singleton from DataProcedure)
```

## Security Observations
- `DataSourceProxy.invoke()` (`DataSourceProxy.java` line 28): proxies every `DataSource.getConnection()` call and wraps the returned `Connection` in `ConnectionProxy`. This provides a central intercept point for connection-level audit, but no auditing is currently implemented.
- `RemoveHangingTransaction.exe()` (`RemoveHangingTransaction.java` line 21) executes `sp_reset_connection` on every connection return — mitigates transaction-state leakage between requests through the connection pool.
- Credentials extracted from Director via `IDirectorClient` (`DirectorConfiguredDBCPdatasourceCreator.java` lines 319–334) — credentials not hardcoded. However, they are stored as `java.lang.String` in `DBCPDataSourceCreator` fields, which are immutable and GC-dependent for clearance.
- `logConnectionSettings()` explicitly avoids logging username/password at INFO but appends them at DEBUG — ensure DEBUG logging is disabled in production log aggregators.

## Technical Debt
| Item | File | Line | Description |
|---|---|---|---|
| `// TODO Remove` constructor | `DataProcedure.java` | 77 | Legacy `isFunction` constructor never removed |
| `SingletonBeanLocator` anti-pattern | `DataProcedure.java` | 32 | Service locator instead of DI |
| jTDS driver always selected | `DataSourceResolver.java` | 307 | `getDriverTypeToUse()` always returns `jdbcJTDS` — hardcoded legacy driver |
| `test.java` in src/main | `test.java` | — | Non-test class in main source tree; should be in test scope or removed |
| Raw `Map` types | `DataProcedure.java` | Multiple | Pre-generics `Map execute(Map inParams)` — unchecked casts throughout |
| Empty `convertFromJDBCJTDS()` | `DataSourceResolver.java` | 299 | Returns null; JT-DS-to-JT-DS conversion not implemented |
| No unit tests | — | — | Zero test coverage across entire library |
| `@SuppressWarnings("unused")` private constructor | `DataProcedure.java` | 35 | Dead code |

## Gen-3 Migration Path
- Replace `DataProcedure` usage with Spring Data JPA repositories or direct `JdbcTemplate` / `NamedParameterJdbcTemplate` calls where stored procedures can be replaced by service-layer logic.
- Where stored procedures must be retained: use `SimpleJdbcCall` (Spring JDBC, maintained) instead of `StoredProcedure` (deprecated in Spring 6).
- Replace DBCP with HikariCP (already used in Gen-2 services).
- Replace jTDS with `com.microsoft.sqlserver:mssql-jdbc`.
- Replace `IDirectorClient` credential resolution with Azure Key Vault / Dapr secrets.
- The `DataSourceProxy` / `ConnectionProxy` proxy chain should be evaluated for replacement with Spring AOP or Micrometer instrumentation for observability.
