# Business Analyst Report — services-common_LIB

## Repository Overview

`services-common_LIB` is a shared Java library (`com.ecount.service.common:services-common:3.0.2-SNAPSHOT`) that provides foundational infrastructure code reused across all ecount/Onbe service modules. This is a cross-cutting concern library — it contains the plumbing that all business services depend upon to function. It compiles to Java 21 and inherits from `prepaid-parent:6.0.12`.

## Business Value

This library is the foundation layer of the Onbe service-oriented architecture. Without it, every service would need to independently implement caching, database connectivity, XML processing, error handling, and session context management. By centralising these concerns, the library enables:

1. **Consistency across services**: All services share the same error handling patterns, caching behaviour, and database connection patterns, making system behaviour predictable and easier to troubleshoot.
2. **Regulatory compliance enablement**: The `RequestContext` class manages session context that likely carries user identity, application context, and audit trail data — directly relevant to PCI DSS Requirement 10 (audit logging) and GLBA consumer data handling.
3. **Operational efficiency**: Shared caching infrastructure (`Cache.java`, `CacheManager.java`, `TimedCachePruner.java`) reduces database load across all services, important for payment processing throughput.

## Core Functional Areas

### 1. Caching Infrastructure (`com.ecount.service.common.cache`)
Provides a thread-safe cache implementation with:
- `Cache.java` — Main cache container with observer pattern support
- `CacheElement.java` — Individual cacheable item wrapper
- `CacheObserver.java` — Notification mechanism for cache state changes
- `CacheManager.java` — Lifecycle management for multiple cache instances
- `TimedCachePruner.java` — Automatic expiry of stale cache entries
- `ReadWriteLock.java` — Custom read-write locking for thread safety

This cache is likely used to store reference data (program configurations, BIN tables, exchange rates) that is read frequently but updated infrequently — a common pattern in payment processing.

### 2. Database Access Framework (`com.ecount.service.common.dao`)
Provides annotation-driven stored procedure execution:
- `AnnotatedStoredProcedure` / `AnnotatedStoredProcedureImpl.java` — Spring-based stored procedure caller using Java annotations to map inputs/outputs
- `CbaseAppDAO.java` / `CbaseAppDAOJDBCImpl.java` — DAO layer for the `cbaseApp` core application
- `UserInquiry.java` — Stored procedure for user data lookup
- Custom `@InputParameter`, `@OutputParameter`, `@RowColumn`, `@ResultSetMapper` annotations

The naming `cbase`/`cbaseApp` references the ecount core banking application (`c-base`), Onbe's legacy prepaid card management system.

### 3. Domain Objects (`com.ecount.service.common.domain`)
- `ApplicationUser.java` — User entity with cardholder identity fields: `memberId`, `firstName`, `lastName`, `birthDate`, `emailAddress`, `phoneNumber`, address fields
- `ServiceClass.java` and `ServiceObject.java` — Large domain base classes (38 KB and 20 KB respectively) providing the core service invocation model
- `DomainObject.java` — Base serialisable domain object
- `ActionMemo.java` / `ActionMemoGroup.java` — Audit-relevant action memo framework for recording account actions

The `ApplicationUser` object handles personal data fields including date of birth, which triggers GDPR Article 9 (special category data) and GLBA considerations. The `birthDate` field (line 43) is a key data element for identity verification.

### 4. XML Processing (`com.ecount.service.common.msmapxml`, `saxtool`)
A comprehensive XML parsing and mapping framework:
- `SaxTool.java` — SAX-based XML parser wrapper
- `MapFromXML.java` / `MapToXML.java` — XML-to-object and object-to-XML serialisation
- `ParseNodeFactory.java` — Factory for building parse tree nodes

This XML processing layer is used to parse service request/response messages, consistent with the SOA architecture used in the ecount platform.

### 5. Scripting (`com.ecount.service.common.script`)
- `ScriptAgent.java` — Dynamic script execution engine

This component deserves security review — dynamic script execution in a financial services application can introduce code injection risks.

### 6. Threading Utilities (`com.ecount.service.common.pi.threads`)
- `Mutex.java`, `Semaphore.java`, `ThreadHelper.java`, `ThreadTimeoutException.java` — Low-level concurrency primitives for managing concurrent payment processing operations.

## Compliance Relevance

The `ApplicationUser` domain object contains PII fields that are regulated under GDPR, CCPA, PIPEDA, and GLBA. Any service using this object to store or transmit user data must implement appropriate data handling controls. The `RequestContext` class likely carries session state that should be audited per PCI DSS Requirement 10.
