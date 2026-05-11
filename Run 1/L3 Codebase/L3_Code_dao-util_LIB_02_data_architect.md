# dao-util_LIB — Data Architect View

## Data Stores
This library does not own any database. It provides the access infrastructure for SQL Server databases used by eCount legacy services, connecting via Apache DBCP (BasicDataSource) or delegating to Spring JDBC.

## Database Technology
- **SQL Server** exclusively (all connection string normalisation targets SQL Server).
- JDBC driver: `net.sourceforge.jtds.jdbc.Driver` (jTDS) — `DataSourceResolver.java` line 16. Note: jTDS is an open-source JDBC driver not maintained since ~2013; Microsoft's official `com.microsoft.sqlserver:mssql-jdbc` is the current standard (used in `customer-service-rest-api`).

## DataSource Configuration (`DBCPDataSourceCreator.java`)
| Property | Default | Notes |
|---|---|---|
| `driverClassName` | Resolved from Director | Always jTDS |
| `username` / `password` | From Director | Not hardcoded |
| `maxActiveConnections` | Director-configured (default 16) | |
| `maxIdleConnections` | Director-configured (default 8) | |
| `defaultAutoCommit` | true | |
| `defaultReadOnly` | false | |
| `defaultTransactionIsolation` | `READ_COMMITTED` | SQL Server default |
| `validateOnCheckout` | true | Runs `SELECT 1` before returning connection |
| `timeBetweenEvictionRunsMillis` | 60000 | 1-minute eviction scan |
| `minEvictableIdleTimeMillis` | 600000 | 10-minute idle eviction threshold |

## Connection String Formats Supported (`DataSourceResolver.java`)
| Format | Example Prefix | Conversion Target |
|---|---|---|
| OLEDB | `Provider=SQLOLEDB;...` | jTDS |
| Weblogic JDBC | `jdbc:weblogic:mssqlserver4:` | jTDS |
| Microsoft JDBC | `jdbc:microsoft:sqlserver://` | jTDS |
| jTDS (pass-through) | `jdbc:jtds:` | No conversion |
| Sybase | `jdbc:sybase:` | Returned as-is |

## DataSource / Connection Proxy Chain
```
DirectorConfiguredDBCPdatasourceCreator.getNewDatasource()
    --> BasicDataSource (commons-dbcp)
        --> wrapped by DataSourceProxy (java.lang.reflect.Proxy)
            --> ConnectionProxy (wraps java.sql.Connection)
                --> StatementProxy (wraps java.sql.Statement)
                --> RemoveHangingTransaction.exe() on connection return
```

## Sensitive Data
| Item | Location | Risk |
|---|---|---|
| DB username | `DBCPDataSourceCreator.username` field | Retrieved from Director; logged at DEBUG level (with warning comment) |
| DB password | `DBCPDataSourceCreator.password` field | Retrieved from Director; DEBUG log comment says "password appended" but actual value is described but not shown — verify |
| Director credentials (`VALUE_PASSWORD`) | `DirectorConfiguredDBCPdatasourceCreator.applyDataCredentialsSettings()` line 328 | Stored in memory as String — susceptible to heap dumps |

## Encryption
- No encryption of in-memory credential strings.
- TLS for DB connections: not configured in the library itself — depends on the jTDS connection string and SQL Server listener configuration.
- Password stored as `String` in `DBCPDataSourceCreator.password` — immutable in JVM memory; cannot be zeroed after use. Recommend `char[]` for passwords (standard Java security guidance).

## Data Quality
- `DataProcedure.execute()` logs execution time in milliseconds at INFO level when `logger.isInfoEnabled()` (`DataProcedure.java` lines 101–118).
- Non-zero stored procedure return codes throw `DataExceptionReturnCode` (line 119) with the return code value — enables callers to distinguish specific error conditions.
- `RemoveHangingTransaction` ensures connection is returned to pool in a clean state (`READ COMMITTED` isolation, no open transactions).

## Compliance Gaps
- jTDS driver (`net.sourceforge.jtds.jdbc.Driver`) is unsupported/unmaintained. Using an unsupported component in a payment environment may fail PCI DSS Req 6.3.3 (all system components protected from known vulnerabilities) and 12.3.4 (hardware and software evaluated periodically).
- DB password held as `java.lang.String` in memory — minor risk but counter to security hardening best practices.
- No audit logging of stored procedure calls (procedure name, parameters, return code) beyond timing/return-code logging at INFO level.
