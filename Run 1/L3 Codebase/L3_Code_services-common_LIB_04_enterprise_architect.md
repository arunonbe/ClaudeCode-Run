# Enterprise Architect View — services-common_LIB

## Platform Generation

**Gen-1 / Gen-2 shared infrastructure library**, now compiled for Java 21. This is one of the foundational shared libraries of the eCount/Citi prepaid platform lineage. Despite the Java 21 compilation target, the code patterns are firmly Gen-1:

- Custom threading primitives (pre-`java.util.concurrent`)
- Custom SAX parser and XML serialization for the eCount XML-RPC message format
- Spring XML wiring patterns (no annotation-based or Java configuration in the library)
- `RequestContext` design mirrors the eCount service-call pattern (agent + classification + affiliateId tuple)
- `CbaseAppDAO` accesses the `cbaseapp` database, which is the Gen-1 core application database

The Java 21 compilation target indicates an active effort to maintain the library's compatibility with Gen-2/Gen-3 runtime environments (Java 21 JVMs) without refactoring the business logic.

## Integration Patterns

- **Stored procedure pattern** (Gen-1): `AnnotatedStoredProcedure` framework provides annotation-driven JDBC stored procedure invocation — the canonical Gen-1 data access pattern across all eCount services
- **XML-RPC message format**: `msmapxml/` package provides bidirectional Map↔XML serialization for the eCount internal XML-RPC message format; this is the Gen-1 inter-service communication substrate
- **RequestContext propagation**: The `RequestContext` object (agent, classification, affiliateId) is the cross-service correlation mechanism for all Gen-1 services; it is serialized to `Hashtable` for XML-RPC dispatch
- **In-process cache**: Custom cache infrastructure used by multiple Gen-1 services for program configuration and user-lookup caching

None of these patterns are used in Gen-3 services (which use REST, Dapr, Azure Service Bus, Redis, and Spring Cache).

## External Dependencies

| Dependency | Version | Status |
|---|---|---|
| ecountcore:common | 3.0.3 | Internal; current |
| commons-lang | BOM-managed | Maintained |
| commons-pool2 | 2.11.1 | Active |
| jakarta.servlet-api | BOM-managed | Jakarta EE 9+ |

No external EOL dependencies in this version (3.0.2), unlike the older version referenced by screen-configs_LIB. The Java 21 upgrade and Jakarta namespace migration have been applied.

## Position in the Broader Platform

services-common_LIB is a **foundational shared library** for all Gen-1 and Gen-2 service components:

```
Gen-1 / Gen-2 Services (order_SVC, request_LIB, job_LIB, etc.)
  → services-common_LIB (shared infrastructure)
    → ecountcore:common (eCount core)
      → SQL Server (cbaseapp, ecountcore databases)
```

Key architectural roles:
1. **Cross-service correlation**: `RequestContext` enables correlation of requests across service calls without a distributed tracing system
2. **DAO framework**: `AnnotatedStoredProcedure` reduces boilerplate for stored procedure calls across all Gen-1 services
3. **Caching**: In-process cache used by multiple services to avoid repeated database lookups for slowly-changing data (program configuration, user lookup)
4. **XML message serialization**: `msmapxml` package is required by any service that exchanges data via the eCount XML-RPC protocol

## Migration Blockers

1. **XML-RPC coupling**: `msmapxml/` and `saxtool/` packages are intrinsically tied to the eCount XML-RPC protocol. Any service that migrates to REST must replace these with Jackson/standard JSON serialization — the libraries themselves cannot be reused.
2. **`RequestContext` design**: The `RequestContext` object carries agent/classification/affiliateId as a simple tuple. In Gen-3, this context is carried in JWT claims, Azure AD tokens, or HTTP headers — not as a serialized `Hashtable`. Migration requires a context adapter layer.
3. **Custom threading and cache**: `pi/threads/` and `cache/` packages must be replaced with `java.util.concurrent` primitives and Spring Cache (or Redis) respectively. The replacements exist in Gen-3 but require consuming services to be refactored.
4. **`cbaseapp` database dependency**: The `CbaseAppDAO` accesses `cbaseapp` directly. In Gen-3, cardholder/account data should be accessed via a service API (e.g., nexpay microservices), not direct database access. This is a major architectural migration point.
5. **`3.0.2-SNAPSHOT` instability**: Consumers using the SNAPSHOT version get non-reproducible builds; a stable release is needed before any Gen-3 migration effort depends on this library.

## Strategic Status

**Maintain with targeted investment for Gen-2 transition; selectively replace for Gen-3**.

- **Short term**: Cut a stable release version; maintain `AnnotatedStoredProcedure` and `RequestContext` for existing Gen-1/Gen-2 services; add observability hooks to the custom cache.
- **Medium term**: For Gen-3-bound services migrating off XML-RPC, replace `msmapxml/` and `RequestContext` propagation with JWT-based context and JSON serialization. The `AnnotatedStoredProcedure` framework may be reused for services that retain SQL Server direct access during migration.
- **Long term**: Retire this library as Gen-1/Gen-2 services are decommissioned. The `cbaseapp` database access must be encapsulated behind a service API before legacy direct-JDBC callers can be removed.
