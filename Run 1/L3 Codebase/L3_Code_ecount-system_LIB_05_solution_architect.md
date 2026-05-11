# 05 Solution Architect — ecount-system_LIB

## All Classes and Methods

### Package `com.ecount.Core2.system.dal`

#### `AbstractDataLibrary`
File: `src/main/java/com/ecount/Core2/system/dal/AbstractDataLibrary.java`

| Method | Purpose |
|---|---|
| `AbstractDataLibrary(String agent, NamedDataSourcesList dataSourceList, String friendlyName)` | Constructor; initialises ConcurrentHashMap caches for procedures and datasources |
| `getProc(String dbName, String procName)` | Main entry point; resolves and caches `AbstractDataProcedure` instances keyed by `agent.dbName.procName` |
| `getDirectorDatasource(String agent, String dbName, String hashKey)` | Attempts to create datasource via Director; caches result |
| `getConfiguredDatasource(String datasourceName)` | Falls back to locally-configured datasource list |
| `factoryGetDataProc(String procName, DataSource dataSrc)` | Abstract factory method; implemented by concrete subclasses |
| `getDataSourceCreator()` / `setDataSourceCreator()` | Getter/setter for the Director-backed datasource creator |
| `getAgent()` | Returns the agent name |

#### `AbstractDataProcedure`
File: `src/main/java/com/ecount/Core2/system/dal/AbstractDataProcedure.java`

| Method | Purpose |
|---|---|
| `AbstractDataProcedure(DataSource ds)` | Constructor |
| `isFunction()` | Abstract; whether the underlying SQL object is a function (returns value) vs procedure |
| `getRowMapper()` | Abstract; provides result-row mapper |
| `getDataParameters()` | Abstract; provides parameter container |
| `getDs()` | Returns the DataSource |
| `updateOutputParameters(DataParameters, List<Field>, Map<String,Object>)` | Reflectively maps out parameters from the SP result map back onto the parameters object |
| `getObjectList(Object)` | Unchecked cast to `List<Object>` |
| `getStringObjectMap(Object)` | Unchecked cast to `Map<String,Object>` |

#### `DataProcedure`
File: `src/main/java/com/ecount/Core2/system/dal/DataProcedure.java`

| Method | Purpose |
|---|---|
| `DataProcedure(DataSource ds)` | Constructor; compiles the Spring `StoredProcedure` |
| `getSQL()` | Abstract; returns the SQL stored procedure name |
| `executeGetRecordList(DataParameters)` | Executes the procedure and returns typed result list |
| `execute(DataParameters)` | Core execution: collects parameters, calls procedure, updates out params, checks return code |
| `collectOutputParameters(...)` | Reflectively iterates annotated fields to build the input parameter map |
| `checkReturnCode(Map<String,Object>)` | Throws `CoreSystemDALError` if stored procedure returns non-zero |
| `invokeExecute(Map<String,Object>, Map<String,Object>)` | Delegates to Spring `StoredProcedure.execute()` |
| `putOutDebug(Map<String,Object>)` | Logs result map contents at DEBUG level (PCI risk — see below) |
| `isColumnExists(ResultSet rs, String columnName)` | Utility: checks if a column name exists in a ResultSet's metadata |

#### `CoreSystemDALError`
| Member | Purpose |
|---|---|
| `FailType` enum | `DataLayerError`, `DatabaseError`, `ProcedureReturnCode` |
| Constructors | Various overloads to carry cause, fail type, message, SQL name, return code |

#### `DataObject`, `DataParameters`
Marker base classes for result objects and stored-procedure parameter containers. No business logic.

### Package `com.ecount.Core2.system.dal.ds`

#### `DBCPDataSourceCreator`
File: `src/main/java/com/ecount/Core2/system/dal/ds/DBCPDataSourceCreator.java`

| Method | Purpose |
|---|---|
| `getNewDatasource(String agent, String dbName)` | Creates and returns a configured `BasicDataSource` |
| All getters/setters | Pool configuration properties (url, username, password, pool sizes, etc.) |

#### `DirectorConfiguredDBCPdatasourceCreator`
File: `src/main/java/com/ecount/Core2/system/dal/ds/DirectorConfiguredDBCPdatasourceCreator.java`

| Method | Purpose |
|---|---|
| `getNewDatasource(String agent, String dbName)` | Overrides parent; loads settings from Director before creating datasource |
| `loadDirectorSettings(String agent, String dbName)` | Contacts Director via XML-RPC; retrieves 4 setting maps |
| `applySettings(...)` | Orchestrates credential and environment application |
| `applyDataCredentialsSettings(...)` | Sets username and password from Director DataCredentials |
| `applyDataEnvironmentSettings(...)` | Maps DB name to environment and resolves datasource name; parses embedded user/pass |
| `applyDataSettingsSettins(...)` | Applies pool configuration from Director DataSettings |
| `logConnectionSettings(...)` | Logs URL, driver, pool settings at INFO (no password) |

#### `DataSourceResolver`
File: `src/main/java/com/ecount/Core2/system/dal/ds/DataSourceResolver.java`

| Method | Purpose |
|---|---|
| `resolve(String dataSource, IDataSourceCreator)` | Main entry: detects format and sets URL + driverClassName on the creator |
| `getDataSourceType(String)` | Returns `DriverType` enum based on connection string prefix |
| `getUrl(...)` | Dispatches to the appropriate `convertFrom*` method |
| `buildJTDSConnectionString(...)` | Constructs canonical jTDS URL |
| `convertFromOLEDB(...)` | Parses OLE DB format |
| `convertFromJDBCWeblogic(...)` | Parses WebLogic JDBC format |
| `convertFromJDBCMicrosoft(...)` | Parses `jdbc:microsoft:sqlserver://` |
| `convertFromJDBCMicrosoftSQLServer(...)` | Parses `jdbc:sqlserver://` |
| `convertFromSybase(...)` | Returns input unchanged (Sybase native) |

### Package `com.ecount.Core2.system.utils`

| Class | Method | Purpose |
|---|---|---|
| `LoggingUtils` | — | Container for `ThreadLocalLogger` inner class |
| `LoggingUtils.ThreadLocalLogger` | `initialValue()` | Returns `LoggerFactory.getLogger("com.ecount.Core2.system")` per thread |
| `UUIDUtils` | `fromString(String)` | Parses UUID strings with null-safety |

## Security Vulnerabilities and Technical Debt

### 1. DEBUG Logging of Full Result Sets (PCI DSS Risk — P1)
`DataProcedure.putOutDebug()` (`DataProcedure.java` lines 106–126) logs `out.toString()` at DEBUG level. If DEBUG logging is enabled in any environment that processes cardholder data, stored-procedure result maps containing PAN, CVV, name, or expiry will appear in plaintext in log files. PCI DSS Req 3.5.1 prohibits SAD storage; Req 10.5.1 requires log protection. This is a **P1 critical** finding.

### 2. SNAPSHOT Version (P2)
Version `4.0.4-SNAPSHOT` is mutable. Artefact integrity cannot be assured. Promote to release.

### 3. jTDS Driver (P3 — Medium)
`net.sourceforge.jtds` is unmaintained (last release 2016). It does not support modern TLS 1.2/1.3 by default. For a PCI DSS Level 1 SP, all communications must use strong cryptography (Req 4.2.1). Replace with Microsoft JDBC (`com.microsoft.sqlserver:mssql-jdbc:12+`).

### 4. Commons DBCP v1 (P4 — Low)
`commons-dbcp` v1 has known connection-leak issues under high concurrency. Replace with HikariCP or Commons DBCP2.

### 5. Credential Embedding in DataEnvironment (P2)
`DirectorConfiguredDBCPdatasourceCreator.applyDataEnvironmentSettings()` accepts a pattern `username/password@datasource` embedded directly in the DataEnvironment config value (`DATA_ENV_USER_PASS` regex, line 40). This pattern stores credentials as plaintext in the Director configuration, which may not be subject to the same access controls as a dedicated secrets store. Recommendation: move all credentials to Azure Key Vault.

## Remediation Priority Summary

| Issue | Priority | Action |
|---|---|---|
| DEBUG logging of result sets (PAN/CVV exposure) | P1 — Critical | Remove or gate `putOutDebug()` behind a non-DEBUG guard; add PAN masking |
| SNAPSHOT version | P2 — High | Release `4.0.4` |
| jTDS driver (TLS) | P2 — High | Replace with `mssql-jdbc` |
| Plaintext credentials in DataEnvironment | P2 — High | Move to Azure Key Vault |
| Commons DBCP v1 | P3 — Medium | Replace with HikariCP |
