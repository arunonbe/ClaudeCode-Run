# Enterprise Architect View — xsearch_LIB

## Platform Generation
**Gen-1** — Original cardholder/account search library. Spring XML context wiring, Commons Logging, and the search patterns all reflect early-2000s Java platform conventions.

## Business Domain
Customer Service / Cardholder Account Lookup. Provides the data-access layer for CSA (Customer Service Agent) member search across all supported search dimensions (PAN, DDA, SSN, name, PUID, eCheck, addenda).

## Role in the Platform
**Gen-1 search data-access library.** This is the database query layer consumed by the Gen-2 xsearch-new_SVC and other CSA-facing services. It abstracts the SQL Server stored procedures and parameterised queries behind a Java service interface.

## Dependency Hierarchy
```
xplatform-library_LIB (infrastructure)
        |
        v
xplatform_LIB (business logic — version 6.0.1)
        |
        v
xsearch_LIB (this repo — search data access)
        |
        v
xsearch-new_SVC (Gen-2 XML-RPC service consuming this library)
```

## Dependencies
| Dependency | Direction | Notes |
|---|---|---|
| xplatform_LIB (`com.ecount:xplatform:6.0.1`) | Upstream | Business domain objects and managers |
| EcountCoreDataSource | External | SQL Server — member and device data |
| CbaseappDataSource | External | SQL Server — secondary member data |
| WebCertOmahaDataSource | External | SQL Server — CSA comment history |
| JobSvcDataSource | External | SQL Server — job action records |
| spring-context | Framework | Spring IoC |
| XStream | Framework | XML serialisation |

## Integration Patterns
- **Shared library pattern** — compiled JAR consumed by services
- **Spring XML wiring** — `search.xml` defines the bean graph; DataSources injected by container
- **DAO pattern** — `*SpringDAO` classes wrapping Spring JDBC templates
- **Stored procedure pattern** — `DeviceInquiryStoredProcedureImpl` for device searches
- **Manager singleton pattern** — `DeviceManager.getInstance()`, `MemberManager.getInstance()`

## Strategic Status
**Maintain (superseded by xsearch-new_SVC for new features).** This library is actively consumed by xsearch-new_SVC. The Gen-2 service largely re-implements the same query logic with added capabilities. The library itself is:
- A release version (`2.0.1`) — stable
- Java 21 compiled — modernised build
- Retained as the canonical SQL query layer

Key concern: xsearch-new_SVC's own `pom.xml` (the parent is a 2022 version with Spring 2.5.4) versus this library (parent 6.0.12 with Java 21 compiler) — the version alignment between the service and this library must be verified.

## Migration Blockers
- Four-database architecture: any migration must account for all four SQL Server databases and their distinct connection pools
- Stored procedure dependencies: `DeviceInquiryStoredProcedureImpl` calls database stored procedures — stored procedures must be catalogued and versioned before migration
- `MaskCCHelper` business rules: PAN masking and BIN-check logic is embedded here — must be preserved (and corrected for PCI compliance) in any migration
- Wildcard restriction logic in `SearchServiceImpl` is a business rule that must be re-implemented in any replacement service
