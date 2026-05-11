# Data Architect View — file-dbcp_LIB

## Data Stores
This library does not own or manage a data store. It is a JDBC connection pool factory. The data stores it connects to are determined by the calling application's properties file (historically SQL Server databases in the ecount C-Base platform).

## Schema / Tables
None defined in this library. The library connects to upstream databases whose schemas are owned by the calling application.

## Sensitive Data Classification
| Data Element | Location | Risk |
|-------------|----------|------|
| DB username | `ecount-db.properties` on server filesystem | Credential |
| DB password | `ecount-db.properties` on server filesystem | Credential — plaintext |
| DB connection URL | `ecount-db.properties` | Internal infrastructure disclosure |

From the test XML (`FileDbcpTest.xml`):
- `\\ecappdev\d$\C-Base\config\ecount-db.properties` — a UNC path indicating the properties file is on a network share of the `ecappdev` host.

## Encryption
- No encryption of the properties file is implemented or supported.
- No TLS configuration capability is built into the library; TLS for SQL Server connections would need to be specified in the JDBC URL or connection properties within the properties file.
- DBCP 1.x `connectionProperties` string is passed to the driver verbatim — TLS settings could be embedded there but no such pattern is documented or demonstrated in the code.

## Data Flow
1. Application server resolves JNDI DataSource or Spring XML instantiates `FileDataSource`.
2. `FileDataSource` or `FileDataSourceFactory` reads the properties file from the filesystem.
3. Properties (including credentials) are loaded into a `Properties` object in JVM heap memory.
4. `BeanUtils.copyProperty()` applies them to the `BasicDataSource` instance.
5. The DataSource establishes JDBC connections to the target SQL Server.

## Data Quality / Retention
- Not applicable — the library manages connection pool state only.
- No connection event logging or audit trail.

## Compliance Gaps
1. Credentials (username, password) stored in a plaintext file on a network share — violates PCI DSS Requirement 8.2 (secure individual credentials) and Requirement 2.2 (secure configurations).
2. The UNC path `\\ecappdev\d$\C-Base\config\` implies an administrative share (`d$`) is used — administrative shares should not be used for routine application file access.
3. No secrets rotation mechanism — changing a DB password requires manual file edit and pool restart.
4. No encryption at rest for the properties file.
5. The library was designed for Tomcat 6 JNDI (`org.apache.tomcat.dbcp`) — it is incompatible with modern application server releases without modification.
