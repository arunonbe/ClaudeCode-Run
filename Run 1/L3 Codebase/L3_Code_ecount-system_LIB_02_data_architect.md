# 02 Data Architect — ecount-system_LIB

## Data Architecture Role

`ecount-system_LIB` does not define domain entities or database schemas. Its role is purely **infrastructure**: it resolves, creates, and manages JDBC `DataSource` objects and provides the base classes through which services invoke SQL Server stored procedures. All business data resides in the databases accessed by consuming services.

## Datasource Configuration Model

The library supports two datasource-creation paths:

### Path 1 — Director-Configured (Runtime)
`DirectorConfiguredDBCPdatasourceCreator.getNewDatasource(String agent, String dbName)` calls Director via XML-RPC to retrieve:

| Director Key | Content |
|---|---|
| `IDirectorClient.SYSTEM_DATACREDENTIALS_KEY` | Username and password for the agent |
| `IDirectorClient.SYSTEM_DATAENVIRONMENT_KEY` | Maps database names to environment/datasource names |
| `IDirectorClient.SYSTEM_DATASOURCES_KEY` | Maps datasource environment names to JDBC connection strings |
| `IDirectorClient.SYSTEM_DATASETTINGS_KEY` | Pool configuration (max connections, idle timeout, validation query, etc.) |

File: `DirectorConfiguredDBCPdatasourceCreator.java` lines 72–129.

**Credential handling**: Credentials are extracted from `DataCredentials` and set on the `BasicDataSource` via `setUsername()` / `setPassword()` (lines 370–389). The DataEnvironment value may also contain embedded credentials in the form `username/password@datasourceName` (pattern `DATA_ENV_USER_PASS`, line 40), which override the DataCredentials values. **Credentials exist only in memory** in the JVM heap — they are not logged by default, but the `logConnectionSettings()` method (lines 150–167) logs the JDBC URL, driver class, and pool settings to INFO level. It does **not** log the password.

### Path 2 — Static Configuration (Local / Fallback)
`DBCPDataSourceCreator.getNewDatasource()` creates a `BasicDataSource` from properties injected by Spring XML or passed programmatically. This path is used in local development, unit tests, and as a fallback when Director is unreachable.

### Connection String Formats Supported
`DataSourceResolver.resolve()` (`DataSourceResolver.java` lines 35–56) normalises all of the following to a canonical jTDS URL (`jdbc:jtds:sqlserver://...`):

| Format | Example Prefix |
|---|---|
| OLEDB | `Provider=SQLOLEDB;Network Address=...` |
| WebLogic JDBC | `jdbc:weblogic:mssqlserver4:` |
| Microsoft JDBC (legacy) | `jdbc:microsoft:sqlserver://` |
| Microsoft SQL Server JDBC | `jdbc:sqlserver://` |
| jTDS JDBC | `jdbc:jtds:...` |
| Sybase | `jdbc:sybase:Tds:` |

All formats are converted to: `jdbc:jtds:sqlserver://host:port/database[;instance=name][;sendStringParametersAsUnicode=false]`

## Databases Accessed by Consuming Services

The library does not define which databases it connects to — that is determined by the `agent` and `dbName` parameters passed by consuming services. From the `ecount-core_SVC` context (`DataSources.xml`) the following named datasources are used:

| Bean ID | JNDI / Director Name | Purpose |
|---|---|---|
| `ecountCoreDS` | `jdbc/ecountCoreDS` | Primary EcountCore business database |
| `jobsvcDS` | `jdbc/jobsvcDS` | Job service scheduling database |
| `strongboxDS` | `jdbc/strongboxDS` | StrongBox key-management database |
| `fdrODSDS` | `jdbc/fdrODSDS` | FDR (First Data Resources) ODS — card processing |
| `cbaseappDS` | `jdbc/CbaseappDataSource` | CBASE application database |

## Sensitive Data Flows

The library itself does not access PAN, CVV, expiry, or PII data directly. However, consuming services invoke stored procedures through this library that query tables containing cardholder data (e.g., `ecountCoreDS` in SQL Server). The `DataProcedure.executeGetRecordList()` method (`DataProcedure.java` lines 42–67) returns strongly-typed result objects. If a calling service maps a stored-procedure result set that contains PAN or CVV columns, those values will flow through the result-mapping layer into memory.

**Debug logging risk** (`DataProcedure.java` lines 106–126): When DEBUG logging is enabled, the library logs the full `out.toString()` of the stored-procedure result map (up to 4 KB). If the result map contains PANs or CVVs, they will appear in the DEBUG log. PCI DSS Req 3.5.1 and Req 10.5.1 both apply.

## Annotations Defining Stored-Procedure Parameters

| Annotation | Package | Purpose |
|---|---|---|
| `@InParameter` | `dal.annotations` | Marks a field as an input parameter |
| `@OutParameter` | `dal.annotations` | Marks a field as an output parameter |
| `@InOutParameter` | `dal.annotations` | Marks a field as bidirectional |

These annotations drive the reflection-based parameter collection in `DataProcedure.collectOutputParameters()` (lines 142–161).

## Pool Configuration Defaults

| Setting | Default Value | Class |
|---|---|---|
| `maxActiveConnections` | 16 (from Director) | `DBCPDataSourceCreator` |
| `maxIdleConnections` | 8 (from Director) | `DBCPDataSourceCreator` |
| `defaultTransactionIsolation` | `READ_COMMITTED` | `DBCPDataSourceCreator` line 32 |
| `validateOnCheckout` | `true` | `DBCPDataSourceCreator` line 35 |
| `validationQuery` | `SELECT 1` | `DBCPDataSourceCreator` line 36 |
| `timeBetweenEvictionRunsMillis` | 60,000 ms | `DBCPDataSourceCreator` line 38 |
| `minEvictableIdleTimeMillis` | 600,000 ms | `DBCPDataSourceCreator` line 40 |
