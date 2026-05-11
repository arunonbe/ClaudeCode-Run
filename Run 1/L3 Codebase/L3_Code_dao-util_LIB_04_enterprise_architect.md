# dao-util_LIB — Enterprise Architect View

## Platform Generation
- **Generation: Gen-1 / Legacy Infrastructure.**
- Apache DBCP, jTDS JDBC driver, Commons Logging, `SingletonBeanLocator` service-locator pattern — all Gen-1 technology choices.
- Compiled for Java 21 but the code style and dependencies are pre-2010.
- No reactive components, no Spring Boot auto-configuration, no modern observability.

## Domain
- **Cross-cutting Infrastructure Domain.**
- Provides database-access infrastructure for all legacy eCount Java services that require stored-procedure execution against SQL Server.

## Role in the Ecosystem
| Role | Detail |
|---|---|
| Shared library | Foundational JDBC layer for Gen-1 eCount services |
| Consumed by | All legacy services using `DataProcedure` or `MetaDataConfiguredProcedure` for stored-proc calls |
| Provides to consumers | DataSource creation, SP execution, connection proxy, timeout management, connection string normalisation |

## Upstream Dependencies
| Dependency | Version | Notes |
|---|---|---|
| `com.parents:prepaid-parent` | 6.0.12 | Parent POM; defines DBCP/pool versions |
| `ecountcore:common` | 3.0.1 | Exception types, `IDirectorClient` interface |
| `springutils-generic` | 3.0.2 | `SingletonBeanLocator` |
| Apache Commons DBCP | From parent | Legacy connection pool |
| Apache Commons Pool | From parent | DBCP dependency |

## Downstream Consumers (likely)
From the broader repository inventory, consumers likely include:
- `dao-util_LIB` itself is referenced by `spring-dbctx_LIB`, `xplatform_LIB`, `ecount-core_SVC`, `repository_LIB`, `repository-service_SVC`, and many others.
- Any service with a `DataProcedure` subclass for stored-procedure access.

## Architectural Patterns
- **Template Method pattern:** `DataProcedure` extends Spring `StoredProcedure` (template); subclasses implement `RowMapper` interface for result mapping.
- **Dynamic Proxy pattern:** `DataSourceProxy`, `ConnectionProxy`, `StatementProxy` use `java.lang.reflect.Proxy` for cross-cutting connection interception.
- **Service Locator (anti-pattern):** `DataProcedure` line 32 calls `SingletonBeanLocator.getInstance().getBean(...)` instead of constructor/setter injection.
- **Strategy pattern:** `IDataSourceCreator` interface with two implementations (`DBCPDataSourceCreator` and `DirectorConfiguredDBCPdatasourceCreator`).
- **Externalised configuration:** `DirectorConfiguredDBCPdatasourceCreator` pulls all DB settings from Director — centralised credential management pattern.

## Status
- Stable release version (2.0.1); likely under minimal maintenance.
- Forms part of the critical foundation for all legacy eCount services — changes carry high blast radius.

## Blockers / Migration Considerations
1. **jTDS driver retirement:** Must migrate all legacy services using `DataSourceResolver` to `com.microsoft.sqlserver:mssql-jdbc` before jTDS causes a security compliance failure.
2. **DBCP v1 retirement:** Migrate to HikariCP (already used in Gen-2 services).
3. **`SingletonBeanLocator` removal:** Refactor `DataProcedure` to use Spring constructor injection for `SqlTimeoutManager`.
4. **Director dependency:** `IDirectorClient` is an eCount-internal configuration service; Gen-3 should use Azure App Configuration or Dapr configuration API.
5. **Metadata introspection at startup:** Replace with explicit stored-procedure parameter declarations to eliminate DB dependency at startup.
6. **No tests:** Refactoring is high-risk without test coverage.
