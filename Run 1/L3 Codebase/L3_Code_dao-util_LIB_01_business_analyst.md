# dao-util_LIB — Business Analyst View

## Business Purpose
`dao-util_LIB` (artifact: `dao-util`, version 2.0.1) is a **shared JDBC/DAO infrastructure library** that provides stored-procedure execution, database connection pooling, connection-string normalisation, and resilience utilities for Onbe's legacy eCount Java services. It is a foundational plumbing library, not a business-logic service.

## Capabilities
| Capability | Class | Description |
|---|---|---|
| Stored procedure execution | `DataProcedure.java` | Extends Spring `StoredProcedure`; auto-discovers proc parameters from DB metadata, applies SQL timeout, wraps results |
| Metadata-configured stored procedure | `MetaDataConfiguredProcedure.java` | Alternative to `DataProcedure` using a separate `MetaData` instance; result-set, output-param, and function variants |
| SQL timeout management | `SqlTimeoutManager.java` | Applies per-procedure timeouts; FDR-specific timeout (`FRPC` key) vs default; default 100 seconds |
| DataSource proxy / connection proxy | `DataSourceProxy.java`, `ConnectionProxy.java`, `StatementProxy.java` | Dynamic proxies wrapping JDBC `DataSource`, `Connection`, and `Statement` to intercept connection acquisition |
| Hanging transaction cleanup | `RemoveHangingTransaction.java` | Executes `sp_reset_connection; SET TRANSACTION ISOLATION LEVEL READ COMMITTED` on SQL Server connection return |
| DBCP DataSource creation | `DBCPDataSourceCreator.java` | Creates Apache DBCP `BasicDataSource` with configurable pool settings |
| Director-configured DataSource | `DirectorConfiguredDBCPdatasourceCreator.java` | Extends DBCP creator; pulls credentials and connection strings from eCount Director configuration service |
| Connection string normalisation | `DataSourceResolver.java` | Translates OLEDB, Weblogic JDBC, Microsoft JDBC, Sybase connection strings to jTDS format |

## Key Entities
- **`DataProcedure`** — the primary abstraction for all stored-procedure calls in eCount services.
- **`SqlTimeoutManager`** — singleton Spring bean controlling query timeout per procedure name.
- **`DataSourceResolver`** — stateless utility normalising legacy connection string formats.
- **`DirectorConfiguredDBCPdatasourceCreator`** — retrieves DB credentials from the eCount Director service (a centralised configuration/credential store) to avoid hardcoded passwords.

## Business Rules
- Default SQL query timeout: 100 seconds (`SqlTimeoutManager.java` line 22).
- FDR (First Data Resources) procedure `FRPC` uses a separately configurable timeout (`SqlTimeoutManager.java` line 46).
- Stored procedures returning a non-zero return code raise a `DataException` with `DataExceptions.ExecutionError` (`DataProcedure.java` line 119).
- Hanging transactions on SQL Server connections are rolled back via `sp_reset_connection` (`RemoveHangingTransaction.java` line 21) — prevents transaction leaks across connection pool reuse.
- `DataSourceResolver` always normalises to jTDS JDBC driver format (`getDriverTypeToUse()` always returns `jdbcJTDS`, line 307).

## Compliance Notes
- `DirectorConfiguredDBCPdatasourceCreator.logConnectionSettings()`: in DEBUG mode (line 151), username and password are appended to the log message. This is controlled (`log.debug("... username and password appended")` at line 155 rather than logging the actual values), but the underlying `getPassword()` is called — review whether debug-level logging inadvertently exposes credentials in log aggregators.
- DB credentials are retrieved from Director via `IDirectorClient.VALUE_USERID` / `VALUE_PASSWORD` — not hardcoded.
- Connection proxy pattern (`DataSourceProxy`, `ConnectionProxy`, `StatementProxy`) intercepts all JDBC calls — provides a control point for audit logging, though no auditing is currently implemented in the visible code.

## Risks
- `DataProcedure` constructor (line 43) introspects stored procedure metadata from the live database at instantiation time — if the DB is unavailable at bean initialisation, the service will fail to start.
- `DataProcedure(DataSource, String, boolean)` constructor at line 77 is marked `// TODO Remove` — indicates legacy dead-code path still present.
- `SingletonBeanLocator.getInstance().getBean("sqlTimeoutManager")` in `DataProcedure` line 32: anti-pattern service-locator lookup; Spring IoC should be used instead.
