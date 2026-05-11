# Business Analyst View — file-dbcp_LIB

## Business Purpose
A Gen-1 Java infrastructure library that extends Apache Commons DBCP connection pooling to read JDBC connection parameters from a filesystem `.properties` file rather than from JNDI or application-server configuration. It was used across the legacy ecount/C-Base platform to centralise database credentials in a single server-side properties file (`ecount-db.properties`) rather than embedding them in application XML.

## Capabilities
- `FileDataSource`: A `BasicDataSource` subclass that reads all DBCP connection properties (URL, username, password, pool sizes, validation queries, etc.) from a named `.properties` file at construction time. Properties are namespaced by a data-source name prefix (e.g., `cbaseappDS.url`).
- `FileDataSourceFactory`: A JNDI `ObjectFactory` that creates `BasicDataSource` instances for J2EE containers (Tomcat) using the same file-based properties mechanism. Registered in `context.xml` via `factory` attribute.
- Both classes support the full set of Apache Commons DBCP 1.x pool configuration properties.

## Entities
No domain entities. The library models database connection pool configuration.

## Business Rules
- The properties file path is passed as a constructor argument or JNDI `RefAddr`; the file must be accessible on the server filesystem at runtime.
- Properties in the file are namespaced by the data-source name (e.g., `cbaseappDS.password`).
- JNDI settings in server.xml or context.xml take priority over file-level properties (explicit merge order in `FileDataSourceFactory`).

## Process Flows
1. Application server (Tomcat) looks up a JNDI DataSource.
2. `FileDataSourceFactory.getObjectInstance()` is called by the JNDI container.
3. Factory reads the properties file path from the JNDI `Reference`.
4. Factory merges file properties with JNDI `RefAddr` settings (JNDI wins).
5. `BasicDataSource` is created and returned to the calling application.

## Compliance Considerations
- Passwords are stored in a plaintext `.properties` file on the application server filesystem (`\\ecappdev\d$\C-Base\config\ecount-db.properties` per test config). This is a PCI DSS Requirement 8 concern — passwords at rest on shared network drives without encryption.
- No credential rotation mechanism is built into the library; changing a password requires editing the file and restarting the pool.
- The library has no audit logging of connection establishment.

## Risks
- Plaintext passwords on a shared UNC path visible to any process or user with network access to `ecappdev`.
- No support for encrypted credential stores, key vaults, or secrets management.
- Dependencies are severely outdated (Commons DBCP 1.2.2, log4j 1.2.15, Spring 2.5.6 for tests).
- No thread-safe file-reload capability; credential rotation requires application restart.
