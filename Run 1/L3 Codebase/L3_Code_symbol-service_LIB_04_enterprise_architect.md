# Enterprise Architect View — symbol-service_LIB

## Platform Generation
**Gen-1 / early Gen-2** — Gen-1 architecture pattern (Spring XML, stored procedures, JTDS) with a Gen-2 uplift (Java 21 compiler target, SLF4J, GitHub Actions CI). Characteristics:
- Spring XML bean configuration (no Spring Boot, no annotations-based configuration).
- All data access via stored procedures (`StoredProcedure` / `NoResultProcedure` Spring JDBC wrappers).
- JTDS JDBC driver (not Microsoft's official JDBC driver).
- Author attribution `@author OFSS` — third-party vendor development.
- No REST/HTTP API surface — library only.
- Java 21 compiler target signals recent uplift.

## Business Domain
**Reference Data / Internationalisation** — Provides currency and locale symbol reference data to display layers and other platform services. Low business criticality but broad dependency potential across the platform.

## Role in Ecosystem
- Shared library; no direct business workflow ownership.
- `symbol-common` module provides the interface (`ISymbolService`) and value objects for loose coupling.
- `symbol-svc` module provides the implementation; consumers that want to call the service directly include both modules.
- Likely consumed by: UI rendering services, statement generation services, any service displaying monetary amounts or localised text.

## Dependencies
| Artifact | Version | Notes |
|----------|---------|-------|
| `com.parents:prepaid-parent:6.0.12` | Parent POM | External |
| `com.ecount.daoutil:dao-util:2.0.1` | Internal JDBC utilities | |
| `com.ecount.service.core.ecountcore:common:3.0.1` | Internal ECount commons | |
| `com.ecount.service.symbolservice:symbol-common:2.0.0` | Self-referential | `symbol-svc` depends on `symbol-common` |
| SLF4J | — | Via parent POM |
| Log4j2 (test) | — | Test logging only |
| JTDS (test scope) | — | SQL Server JDBC |

## Integration Patterns
| Pattern | Details |
|---------|---------|
| Library (JAR dependency) | Consumers import `symbol-common` and/or `symbol-svc` |
| Direct JDBC (stored procedures) | All DB access via `StoredProcedure` Spring JDBC wrappers |
| DataSource injection | Production DataSource (`JobSvcDataSourceSymbol`) injected by consuming app's Spring context |

## Strategic Status
**Maintain with minor modernisation.** This component:
- Has low security risk (no sensitive data).
- Has a clean interface (`ISymbolService`) enabling future replacement.
- Java 21 target and GitHub Actions CI indicate active maintenance.
- Should be evaluated for migration to Spring Data JPA or JOOQ to eliminate stored procedure coupling.
- Long-term: a REST microservice exposing symbol data would decouple consumers from the JDBC dependency.

## Migration Blockers
| Blocker | Description |
|---------|-------------|
| Stored procedure coupling | `symbol_create`, `symbol_update`, `symbol_retrieve_group` procedures exist on the target SQL Server; migration requires DDL access and coordination |
| DataSource aliasing | Consumers that inject `JobSvcDataSourceSymbol` must be updated if the data store is migrated |
| Tests require live SQL Server | No self-contained tests; refactoring is risky without test coverage |
| JTDS driver | Should be replaced with Microsoft's official `mssql-jdbc` driver |
