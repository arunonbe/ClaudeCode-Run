# 01 Business Analyst — ecount-system_LIB

## Overview

`ecount-system_LIB` is a foundational Java library that provides the **data-access layer (DAL) infrastructure** shared across all EcountCore Generation-2 and Generation-3 services. It is packaged as a JAR under groupId `com.ecount.service.Core2`, artifactId `ecount-system`, version `4.0.4-SNAPSHOT` (`pom.xml` lines 14–15). The library name in the POM is "Ecount System — Data access layer and more".

## Business Purpose

The EcountCore platform issues prepaid cards, manages cardholder accounts, processes transactions, and interacts with multiple SQL Server databases through stored procedures. Before this library existed, individual services were responsible for establishing their own database connections, resolving connection strings from environment-specific configuration sources, and managing connection pooling. `ecount-system_LIB` centralises all of this, providing:

1. **Unified datasource resolution**: Translates legacy connection string formats (OLE DB, WebLogic JDBC, Microsoft JDBC, jTDS, Sybase) into a single canonical jTDS JDBC URL, regardless of where the service is deployed. This is crucial because the platform spans environments that use different database access formats accumulated over many years.

2. **Director integration**: Services can retrieve database credentials and connection parameters from Onbe's centralised configuration service ("Director") at runtime, rather than hard-coding environment-specific values. `DirectorConfiguredDBCPdatasourceCreator` (`dal/ds/DirectorConfiguredDBCPdatasourceCreator.java`) encapsulates this Director lookup.

3. **Stored-procedure abstraction**: `DataProcedure` and `DataProcedureEx` provide a type-safe framework for invoking SQL Server stored procedures. Individual procedures are implemented as concrete subclasses, each declaring its SQL, parameters (annotated with `@InParameter`, `@OutParameter`, `@InOutParameter`), and result-row mapper.

4. **Connection pooling**: Uses Apache Commons DBCP (`BasicDataSource`) with configurable pool sizes, eviction policies, and validation queries.

## Functional Components

| Component | Package | Purpose |
|---|---|---|
| `AbstractDataLibrary` | `dal` | Caches prepared stored-procedure objects per agent/database/procedure key; resolves datasource dynamically at first access |
| `AbstractDataProcedure` | `dal` | Base class for all stored-procedure invocations; handles output-parameter extraction via reflection |
| `DataProcedure` | `dal` | Extends `AbstractDataProcedure` with Spring `StoredProcedure` execution; executes procedures and returns typed result lists |
| `DataProcedureEx` | `dal` | Extended variant for procedures requiring specialised invocation |
| `ReflectiveDataLibrary` | `dal` | Reflective variant of `AbstractDataLibrary` |
| `CoreSystemDALError` | `dal` | Typed exception for DAL failures (DataLayerError, DatabaseError, ProcedureReturnCode) |
| `DataParameters` | `dal` | Marker base class for stored-procedure parameter objects |
| `DataObject` | `dal` | Marker base class for result objects |
| `DBCPDataSourceCreator` | `dal/ds` | Creates `BasicDataSource` instances from explicit configuration properties |
| `DirectorConfiguredDBCPdatasourceCreator` | `dal/ds` | Extends `DBCPDataSourceCreator`; self-configures from Director service at runtime |
| `DataSourceResolver` | `dal/ds` | Parses and normalises JDBC connection strings across five legacy formats |
| `LoggingUtils` | `utils` | Provides `ThreadLocalLogger` (a `ThreadLocal<Logger>`) for safe use in shared-classloader environments |
| `UUIDUtils` | `utils` | UUID string parsing utilities |

## Integration with Director

The "Director" service is an Onbe-internal configuration and credential store that provides environment-specific database settings (credentials, URLs, pool sizes) via XML-RPC. `DirectorConfiguredDBCPdatasourceCreator.loadDirectorSettings()` contacts Director to retrieve four setting maps: `DataCredentials`, `DataEnvironment`, `DataSettings`, and `DataSources`. This ensures that production database passwords are never stored in source code or property files within this library.

## Business Impact

This library is foundational: if it fails to resolve a datasource or throws a `CoreSystemDALError`, the calling service cannot execute any database operation. Because EcountCore stores cardholder accounts, transactions, and prepaid card data, a datasource failure propagates directly to payment failures. The library therefore carries **high business criticality** even though it contains no payment logic itself.
