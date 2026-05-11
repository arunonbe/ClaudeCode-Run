# 04 Enterprise Architect — ecount-system_LIB

## Platform Generation

`ecount-system_LIB` spans **Generation 1 to Generation 2** of the EcountCore platform:

- The package namespace `com.ecount.Core2.system` (note the `Core2` capitalization) indicates this is a Core2-era rewrite of an earlier Core1 data-access layer.
- The parent POM `com.parents:prepaid-parent:6.0.13` is the same parent used by the Gen-2/3 `ecount-core_SVC`, placing this library squarely in the Gen-2 lineage.
- Java 21 compiler target indicates a recent upgrade to current LTS.
- The `DirectorConfiguredDBCPdatasourceCreator` still uses Apache Commons DBCP and jTDS — legacy components — while the containing service (`ecount-core_SVC`) has migrated to HikariCP and Microsoft SQL Server JDBC.

## Role in the Platform Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                    EcountCore Platform                           │
│                                                                  │
│  ┌─────────────────┐    ┌─────────────────┐    ┌──────────────┐│
│  │ ecountCoreService│    │  ecountCoreDAO  │    │ embossExtract││
│  └────────┬────────┘    └────────┬────────┘    └──────┬───────┘│
│           │                     │                     │        │
│           └─────────────────────┴─────────────────────┘        │
│                                 │                               │
│                    ┌────────────▼──────────────┐               │
│                    │    ecount-system_LIB       │               │
│                    │  (AbstractDataLibrary,     │               │
│                    │   DataProcedure,           │               │
│                    │   DataSourceResolver)      │               │
│                    └────────────┬──────────────┘               │
│                                 │                               │
│               ┌────────────────┬┴──────────────────┐           │
│               │                │                   │           │
│        ┌──────▼──────┐  ┌──────▼──────┐  ┌────────▼────────┐  │
│        │  Director   │  │  SQL Server │  │  SQL Server     │  │
│        │  Service    │  │  ecountcore │  │  jobsvc/cbase   │  │
│        └─────────────┘  └─────────────┘  └─────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

The library is **horizontally shared** across all services that access SQL Server via stored procedures. It is the exclusive data-access abstraction for the stored-procedure-based EcountCore database layer.

## Key Architectural Decisions

1. **Stored-procedure first**: All database operations are encapsulated in SQL Server stored procedures (`dbo.*`). The library does not support ad-hoc SQL queries (no `JdbcTemplate` direct usage). This enforces a database API contract and centralises business logic in the database tier — a deliberate architectural choice from the EcountCore Gen-1 era.

2. **Agent-based multi-tenancy**: The `agent` parameter in `AbstractDataLibrary` and `DirectorConfiguredDBCPdatasourceCreator` maps to an EcountCore deployment unit (a "PPA" agent, e.g., `b2cstage`). Multiple agents can share the same JVM with different datasources. This is fundamental to the multi-programme prepaid platform model.

3. **Dynamic configuration via Director**: Database connection parameters are pulled from Director at runtime, enabling zero-downtime credential rotation (new credentials can be deployed to Director without redeploying services). This is an important PCI DSS Req 8 control for managing service account credentials.

4. **Connection string polyglot support**: The platform evolved through WebLogic, OLE DB, legacy Microsoft JDBC, and jTDS eras. `DataSourceResolver` enables older configuration formats to continue working without migration, reducing operational risk.

## Migration Complexity

| Migration Scenario | Effort | Notes |
|---|---|---|
| Replace jTDS with Microsoft JDBC | Medium | jTDS is unmaintained; `DataSourceResolver` would need an additional conversion path for `jdbc:sqlserver://` output |
| Replace Commons DBCP with HikariCP | Low-Medium | `DBCPDataSourceCreator` and `DirectorConfiguredDBCPdatasourceCreator` would need rewrites |
| Replace stored-procedure pattern with JPA/Spring Data | Very High | Would require rewriting all DAO implementations across all consuming services |
| Migrate Director-based config to Azure App Configuration | High | Director XML-RPC API would need to be replaced with Spring Cloud Azure Config; credential handling would use Azure Key Vault |

## Dependencies on Other Platform Libraries

| Library | Version | Role |
|---|---|---|
| `director-client:2.0.2` | `com.citi.prepaid.service.core.client` | XML-RPC client for Director service |
| `common:3.1.5` | `com.ecount.service.core.ecountcore` | Shared EcountCore constants and utilities |

The `director-client` groupId (`com.citi.prepaid`) reflects the Citi acquisition origin of the EcountCore codebase — a historical artefact from the platform's provenance.
