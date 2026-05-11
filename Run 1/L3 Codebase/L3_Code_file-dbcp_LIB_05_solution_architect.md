# Solution Architect View — file-dbcp_LIB

## Technical Architecture

**Stack**: Java (Java 5/6 era), Apache Commons DBCP 1.2.2, Apache Commons Pool 1.4, Apache Commons BeanUtils 1.7.0, Tomcat DBCP 6.0.26, log4j 1.2.15, Spring 2.5.6 (test only).

**Classes**:
| Class | Pattern | Purpose |
|-------|---------|---------|
| `FileDataSource` | Extends `BasicDataSource` | File-properties-backed DataSource for Spring XML bean instantiation |
| `FileDataSourceFactory` | Implements `ObjectFactory` | JNDI factory for Tomcat context.xml DataSource registration |

Both classes implement the same core logic: read a `.properties` file by filename, extract properties prefixed by the data-source name, configure a `BasicDataSource` instance.

## API Surface
This is a library — no HTTP endpoints.

**Public API**:
- `FileDataSource(String configFile, String dataSourceName)` — constructor
- `FileDataSourceFactory.getObjectInstance(Object obj, Name name, Context nameCtx, Hashtable environment)` — JNDI ObjectFactory method
- All public methods inherited from `BasicDataSource` (jdbc:get/setUrl, getConnection, etc.)

## Security Posture

### Authentication / Authorisation
- No authentication logic in this library.

### Cryptography
- None. Passwords are stored and read as plaintext strings.

### Secrets
- **CRITICAL**: Database passwords are stored in plaintext in `ecount-db.properties`.
- The properties file path is passed as an unsanitised string constructor argument / JNDI RefAddr — no path traversal validation.
- Properties are loaded into a `java.util.Properties` object in JVM heap; no wiping of sensitive values after use.
- Test configuration (`FileDbcpTest.xml`) references `\\ecappdev\d$\C-Base\config\ecount-db.properties` — a UNC path to an administrative share.

### CVEs / Dependency Risks
- **log4j 1.2.15**: EOL; CVE-2019-17571 (SocketServer deserialization gadget chain — CVSS 9.8 critical) — while not as famous as log4shell, it is critical if `SocketServer` or `SocketHubAppender` is used.
- **commons-dbcp 1.2.2**: CVE-2018-9173 (potential JDBC URL injection). EOL — no patches available.
- **commons-pool 1.4**: EOL.
- **commons-beanutils 1.7.0**: CVE-2019-10086 (deserialization) — CVSS 7.3.
- **Tomcat DBCP 6.0.26**: Tomcat 6 EOL since 2016; CVE-2016-8745, CVE-2017-5664 and others.

## Technical Debt
1. Java 5/6 era code — no generics usage, raw types throughout.
2. No try-with-resources (pre-Java 7) — explicit finally blocks for stream closure.
3. Duplicated code: `FileDataSource` and `FileDataSourceFactory` both implement identical `loadProperties()` static methods.
4. No unit tests for `FileDataSourceFactory` — only `FileDataSource` has a test (`FileDbcpTest.xml` Spring context).
5. No support for modern JDBC features (connection pooling statistics, JMX metrics).
6. Properties loaded at construction time with no reload capability.

## Gen-3 Migration Requirements
This library should not be migrated — it should be retired and replaced:
1. Replace `FileDataSource` usage with Spring Boot 3 + HikariCP `DataSource` configured via Azure Key Vault references.
2. Replace plaintext properties file with Azure Key Vault secrets accessed via `DefaultAzureCredential`.
3. Replace Tomcat JNDI DataSource pattern with Spring Boot DataSource auto-configuration.
4. Migrate JDBC connection string management to Azure App Configuration.

## Code-Level Risks

| File | Line | Risk |
|------|------|------|
| `src/main/java/com/ecount/dbcp/FileDataSource.java` | 62-67 | `IOException` caught silently (`log.fatal`) then construction continues with null properties — NullPointerException will follow |
| `src/main/java/com/ecount/dbcp/FileDataSource.java` | 94-107 | `FileInputStream` resource leak if `p.load(in)` throws — `finally` block only closes `in` |
| `src/main/java/com/ecount/dbcp/FileDataSourceFactory.java` | 159-172 | Same resource leak pattern |
| `src/main/java/com/ecount/dbcp/FileDataSource.java` | 96 | `new FileInputStream(fileName)` returns non-null — the `if (in == null)` check at line 98 can never be true (FileInputStream throws FileNotFoundException instead) — dead code |
| `src/test/resources/FileDbcpTest.xml` | 9 | UNC administrative share path `\\ecappdev\d$\C-Base\config\ecount-db.properties` — exposes network topology and credential file location |
