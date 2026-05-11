# Solution Architect Report — services-common_LIB

## Architectural Role

`services-common_LIB` is the foundational shared library for the Onbe service tier. Every service module that inherits from `service-parent_PARENT` ultimately depends on this library. It provides the cross-cutting infrastructure that enables service-tier modules to operate consistently.

## Dependency Graph Position

```
prepaid-parent:6.0.12
    └── services-common_LIB:3.0.2-SNAPSHOT
            ├── [All service modules that import services-common]
            └── ecountcore:common:3.0.3
                    └── [Core ecount platform library]
```

This library occupies a critical position: it is depended upon by many modules but itself has few dependencies. Changes propagate upward through the dependency graph. Breaking changes in `services-common` can cascade to break all consuming services simultaneously.

## Architecture Pattern Analysis

### 1. Service Invocation Model (`ServiceClass.java`, `ServiceObject.java`)

The 58 KB combined size of these two classes suggests they implement the core service dispatching model for the ecount platform. The pattern appears to be:

```
[HTTP Request] → [Service Layer] → ServiceObject → ServiceClass → DAO → StoredProcedure
```

This is a traditional Java EE service-oriented architecture pattern consistent with systems built in the mid-2000s. Modern microservice architecture would decompose these monolithic base classes into smaller, focused components.

### 2. Data Access Layer Architecture

The `AnnotatedStoredProcedureImpl` pattern is architecturally sound for a system that uses Microsoft SQL Server stored procedures heavily. The annotation-driven approach (`@InputParameter`, `@OutputParameter`, `@RowColumn`) reduces boilerplate and was modern at the time it was designed.

```
DomainObject (annotated with @InputParameter/@OutputParameter)
         ↓
AnnotatedStoredProcedureImpl (reflection-based parameter mapping)
         ↓
Spring StoredProcedure → MSSQL Stored Procedure
         ↓
DomainObject (populated with @OutputParameter results)
```

This pattern tightly couples the data access layer to SQL Server stored procedures. This is a known architectural constraint for systems that have invested heavily in stored procedure logic.

### 3. Custom Caching Architecture

The library implements its own caching framework rather than using Spring Cache, EhCache, or Redis. This was likely built before these options were mature. The architecture:

```
CacheManager (singleton registry)
    └── Cache (named cache instance)
            ├── CacheElement (TTL-aware wrapper)
            └── TimedCachePruner (background thread)
```

**Architectural concern**: This custom cache uses `ReadWriteLock.java` — a hand-rolled read/write lock implementation. Java's `java.util.concurrent.ReentrantReadWriteLock` (introduced in Java 5, 2004) provides the same capability with far more testing and correctness guarantees.

### 4. XML Processing Architecture

Two XML processing pathways exist:
- **SAX path**: `SaxTool.java` → `SaxToolContentHandler.java` for stream-based parsing
- **Mapping path**: `MapFromXML.java` / `MapToXML.java` for object mapping

The SAX factory pool (`SaxParserFactoryPool`) is a performance optimisation that amortises the cost of `SAXParserFactory.newInstance()` across multiple requests. This is architecturally appropriate for a high-throughput payments processing system.

## Technical Debt Assessment

| Component | Age Estimate | Debt Level |
|---|---|---|
| `ReturnStatus extends Throwable` | ~25 years (2001) | HIGH |
| `ServiceClass.java` (38 KB god class) | ~20 years | HIGH |
| Custom `ReadWriteLock` | ~15+ years | HIGH |
| Custom cache implementation | ~15+ years | MEDIUM |
| Annotation-driven stored procedures | ~10 years | LOW |
| `ScriptAgent.java` | Unknown | HIGH (security risk) |

## Modernisation Roadmap

### Phase 1 — Stabilisation (1–2 Quarters)
1. Add comprehensive unit and integration test suite
2. Disable external entity processing in XML parsers (security fix)
3. Replace custom `ReadWriteLock` with `java.util.concurrent.ReentrantReadWriteLock`
4. Override `ReturnStatus.fillInStackTrace()` to eliminate overhead

### Phase 2 — Modernisation (2–4 Quarters)
1. Replace custom cache with Spring Cache + Caffeine or Redis
2. Implement PII field masking in domain object `toString()` methods
3. Decompose `ServiceClass.java` and `ServiceObject.java` into focused components
4. Security audit and redesign of `ScriptAgent.java`

### Phase 3 — Strategic (6–12 Months)
1. Evaluate migration from stored-procedure-centric DAO to JPA/Hibernate or jOOQ
2. Introduce Spring Boot auto-configuration modules to replace XML wiring
3. Consider extracting the caching layer into a separate microservice for distributed caching (Redis)
4. Align domain objects with GDPR/CCPA data minimisation principles

## SBOM and Dependency Health

The library currently publishes to GitHub Packages (via `github-package-publish.yml`). An SBOM should be generated at publish time to support PCI DSS Requirement 6.3.2 (maintain a software inventory). The Maven Cyclone DX plugin can generate SBOM automatically:

```xml
<plugin>
    <groupId>org.cyclonedx</groupId>
    <artifactId>cyclonedx-maven-plugin</artifactId>
    <version>2.8.0</version>
    <executions>
        <execution>
            <phase>package</phase>
            <goals><goal>makeAggregateBom</goal></goals>
        </execution>
    </executions>
</plugin>
```

This would provide machine-readable inventory of all transitive dependencies, facilitating rapid response to newly published CVEs.
