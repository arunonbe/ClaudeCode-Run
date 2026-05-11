# dao-util_LIB — DevOps / Operations View

## Build System
- **Maven**; parent POM: `com.parents:prepaid-parent:6.0.12`.
- groupId: `com.ecount.daoutil`, artifactId: `dao-util`, version: `2.0.1`.
- Packaging: `jar`.
- Java 21 (`maven.compiler.source/target = 21`).
- `maven-jar-plugin` for JAR creation.
- `maven-enforcer-plugin`: `banTransitiveDependencies` configured with exclusions for `org.springframework:*`, `com.ecount.*:*`, `com.ecount.daoutil:*`.
- Log4j config files explicitly excluded from the packaged resources (`pom.xml` lines 72–80) — consumers supply their own logging config.

## Dependencies
| Dependency | Purpose |
|---|---|
| `com.ecount.service.core.ecountcore:common:3.0.1` | eCount core exceptions (`DataException`, `DataExceptions`, `IDirectorClient`) |
| `commons-dbcp:commons-dbcp` | Apache DBCP connection pooling (version from parent POM) |
| `commons-pool:commons-pool` | Commons Pool (required by DBCP) |
| `com.citi.prepaid.springutils:springutils-generic:3.0.2` | Spring utilities (`SingletonBeanLocator`) |

## CI/CD
- GitHub Actions: `.github/workflows/github-package-publish.yml` — publishes JAR to GitHub Packages.
- `.github/workflows/codeql.yml` — CodeQL SAST.
- Dependabot: `.github/dependabot.yml`.
- No deployment pipeline — library only.

## Artifact Publication
- Published as `com.ecount.daoutil:dao-util:2.0.1` to GitHub Packages Maven registry.
- Consumed by legacy eCount services as a compile/runtime dependency.

## Configuration
- No runtime configuration files in the library.
- `SqlTimeoutManager` is a Spring bean configured by consumer services:
  - `defaultTimeout` (seconds) — default 100.
  - `fdrProcDefaultTimeout` (seconds) — default 100.
- `DBCPDataSourceCreator` / `DirectorConfiguredDBCPdatasourceCreator` are Spring beans configured by consumer services with Director client injection.

## Observability
- `DataProcedure.execute()`: logs procedure name, return code, and execution time at INFO level (`logger.info("SQL-EXECUTE: ECountCore::%s = %d (%d ms)")`).
- `RemoveHangingTransaction`: logs at INFO on success, ERROR on failure.
- `DataSourceResolver`: logs error if connection string format is unrecognised.
- `DirectorConfiguredDBCPdatasourceCreator.logConnectionSettings()`: logs all pool settings at INFO; username/password noted but not fully logged at DEBUG (see data architect notes).
- Logger used: `org.apache.commons.logging.Log` (Jakarta Commons Logging) — routes to whatever SLF4J/Log4j2 backend is configured by the consumer.

## Infrastructure
- No containerisation.
- No infrastructure-as-code.
- Requires SQL Server accessibility from the consuming service's network.
- `sp_reset_connection` SQL Server stored procedure must be available in all target databases (standard in SQL Server, but may be restricted in some configurations).

## Risks
- Apache Commons DBCP (`commons-dbcp`) is a legacy connection pool; modern alternatives are HikariCP (used in `customer-service-rest-api`) or Tomcat JDBC pool. DBCP v1.x (implied by parent POM) has known CVEs and is not maintained.
- jTDS JDBC driver (`net.sourceforge.jtds.jdbc.Driver`) referenced in `DataSourceResolver` is unmaintained since ~2013 — vulnerability risk.
- `SingletonBeanLocator` usage in `DataProcedure` line 32 (`DataProcedure` constructor) creates a coupling to Spring ApplicationContext at instantiation time; this will fail if the bean context is not fully initialised when `DataProcedure` subclasses are constructed.
- `DataProcedure` constructor performs live database metadata introspection at startup — cold start or DB unavailability at startup causes service startup failure.
- No unit tests in repository.
