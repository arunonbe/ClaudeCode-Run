# Enterprise Architect View — file-dbcp_LIB

## Platform Generation
**Gen-1** — A legacy infrastructure utility from the ecount/C-Base era. Written to support Tomcat 6 JNDI DataSource configuration in the late 2000s. Uses commons-dbcp 1.2.2, Spring 2.5.6 (test only), and log4j 1.2.15. Represents the oldest tier of the Onbe technology stack.

## Business Domain
**Platform Infrastructure — Data Access** — Not a business domain component. This is a low-level infrastructure library that abstracts JDBC connection pool configuration from application code, enabling centralised database credential management via a shared properties file on the application server.

## Role
- **Role**: Infrastructure library enabling centralised, file-based JDBC connection pool configuration for legacy Tomcat/J2EE applications in the ecount/C-Base platform.
- Consumed by any legacy Java application that needs a DataSource and stores its connection details in `ecount-db.properties`.
- Sits at the foundation of the legacy data access stack; changing it requires coordinated updates across all consuming applications.

## Dependencies
### Inbound (consumers)
- Any legacy ecount/C-Base Java application or web application that uses `FileDataSource` or `FileDataSourceFactory` via Spring XML or Tomcat JNDI.
- Estimated impact: broad — this pattern was the standard across the legacy platform.

### Outbound (runtime)
| Dependency | Type |
|-----------|------|
| SQL Server databases | Target of the pooled connections |
| Filesystem (`ecount-db.properties`) | Properties file location |
| Apache Commons DBCP 1.2.2 | Pool implementation |
| Tomcat 6 DBCP | JNDI factory base class |

## Integration Patterns
- **JNDI DataSource Factory**: J2EE standard ObjectFactory pattern for container-managed DataSources.
- **Spring XML Bean**: `FileDataSource` used directly as a Spring `<bean>` with constructor arguments.
- **File-based configuration**: Centralised properties file as the configuration source.

## Strategic Status
**End-of-Life / Retire** — This library is a Gen-1 artefact with no upgrade path to modern patterns:
- Commons DBCP 1.2.2 has been superseded by HikariCP (used in Gen-3 exemplar) and Commons DBCP 2.x.
- Plaintext credential file pattern is incompatible with PCI DSS and modern secrets management.
- Tomcat 6 is EOL since 2016.
- There is no current business justification for this pattern; modern applications use HikariCP with Azure Key Vault or Spring Cloud Config.

**Recommended disposition**: Freeze — no new consumers. Plan migration of existing consumers to Hikari + Azure Key Vault. Retire the library once no active consumers remain.

## Migration Blockers
1. **Consumer identification**: All applications using `FileDataSource` or `FileDataSourceFactory` must be catalogued before retirement.
2. **Credential migration**: `ecount-db.properties` patterns must be migrated to Azure Key Vault or equivalent secrets management.
3. **JNDI dependencies**: Any application using JNDI DataSource lookup with this factory requires Tomcat context.xml changes to migrate.
4. **Java version**: Applications compiled to Java 5/6 consuming this library may not be easily upgradeable to modern Java without broader refactoring.
