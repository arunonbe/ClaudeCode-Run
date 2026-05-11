# Data Architect View — services-common_LIB

## Data Models

services-common_LIB (`com.ecount.service.common:services-common:3.0.2-SNAPSHOT`, Java 21) is a shared infrastructure library. Its data models are utility types used across all Gen-1 and Gen-2 eCount services:

**Core domain objects** (`domain/`):
- `DomainObject` — base class for all domain entities
- `ServiceObject` / `ServiceObjectEx` — base classes for service request/response transfer objects
- `ServiceClass` — enumeration or type marker for service classification
- `ApplicationUser` — represents the authenticated user context (agent, CSA, batch user)
- `ActionMemo` / `ActionMemoGroup` / `ActionMemoRow` — audit memo structure for recording agent actions on accounts; multi-level hierarchy (group → memos → rows)

**Request context** (`core/`):
- `RequestContext` — carries request metadata: `agent` (String), `classification` (String), `affiliateId` (int); serialized to `Hashtable` for XML-RPC dispatch. This is the fundamental cross-service correlation object for the eCount platform.
- `ReturnStatus` — standard return code envelope

**DAO infrastructure** (`dao/`):
- `AnnotatedStoredProcedure` / `AnnotatedStoredProcedureImpl` — annotation-driven stored procedure invocation framework; Java annotations (`@InputParameter`, `@OutputParameter`, `@ResultSetMapper`, `@RowColumn`, `@NestedRowColumn`) define parameter mappings
- `CoreStoredProcedure` — base class for all stored procedure wrappers
- `CbaseAppDAO` / `CbaseAppDAOJDBCImpl` — DAO for the `cbaseapp` database (core application database)
- `UserInquiry` — stored procedure for user lookup in `cbaseapp`
- Exception types: `CbaseAppExceptions`, `CbaseAppServiceException`, `AnnotatedStoredProcedureException`, `DataTypeConversionException`
- `DataTypeConverter` — converts between SQL and Java types

**Cache infrastructure** (`cache/`):
- `Cache` / `CacheElement` / `CacheManager` / `CacheObserver` — in-memory cache with read/write lock; `TimedCachePruner` for TTL-based eviction
- Custom implementation (predates Spring Cache, Ehcache integration); uses `ReadWriteLock` from `pi/threads/`

**XML serialization** (`msmapxml/`):
- `MapToXML` / `MapFromXML` — bidirectional Map-to-XML serialization; custom SAX-based parser for the eCount internal XML format used in XML-RPC message payloads
- `XMLEncode` — XML character escaping

**SAX parsing** (`saxtool/`):
- `ParseNode` / `ParseNodeFactory` / `ParseStack` — custom SAX event-driven parser framework for eCount XML messages

**Threading utilities** (`pi/threads/`):
- `Mutex`, `Semaphore`, `ThreadHelper`, `ThreadTimeoutException` — low-level threading primitives (predates `java.util.concurrent`)

## Sensitive Data Handled

| Data Category | Presence | Notes |
|---|---|---|
| Agent identity | `ApplicationUser`, `RequestContext.agent` | CSA/batch user identifier; not cardholder PII |
| Affiliate ID | `RequestContext.affiliateId` | Program/client identifier; not sensitive |
| Classification | `RequestContext.classification` | DB routing context; not PII |
| Cardholder data (indirect) | Via `CbaseAppDAO` queries | cbaseapp stores cardholder account data; DAO queries may return PAN-adjacent data |
| Action memos | `ActionMemo*` | Agent-written notes; may contain cardholder PII if agents write names/account details in memos |

The `ActionMemo` hierarchy is a significant area: agent action memos often contain free-text notes that could include cardholder name, partial account numbers, or other PII. If these are stored without controls, they represent a GLBA and PCI DSS data minimization concern.

## Encryption and Protection Status

- No application-level encryption in this library
- The `ReadWriteLock` and `Mutex` implementations are custom threading primitives — no crypto
- DataSource injection via Spring XML; credentials externalized to application context
- The `cbaseapp` database connection (via `CbaseAppDAO`) relies on the hosting application's DataSource configuration for encryption of the database connection

## Database Schemas

The library provides DAO access to:
- **cbaseapp database** (`CbaseAppDAO`): Core application database containing user accounts, program configuration, cardholder account data
- Stored procedures are the exclusive data access pattern (no ORM, no direct SQL in this library)
- The `UserInquiry` stored procedure retrieves user/agent information from `cbaseapp`

The `AnnotatedStoredProcedure` framework provides reusable infrastructure for all stored procedure wrappers across the Gen-1/Gen-2 platform.

## Data Flows

```
Any Gen-1/Gen-2 service
  → RequestContext (carried through the call stack)
    → serialized to Hashtable for XML-RPC dispatch
      → downstream service (XML-RPC call)

CbaseAppDAO
  → SQL Server (cbaseapp database)
    → UserInquiry stored procedure
      → User/agent records

ActionMemo hierarchy
  → persisted by calling service
    → audit trail in SQL Server
```

## Retention Concerns

- `ActionMemo` records: these are audit/compliance records. GLBA requires financial records to be retained per applicable regulations (typically 7 years). If memos contain agent actions on cardholder accounts, they are in scope for this requirement.
- `RequestContext` is transient (request lifecycle only); no persistence concern.
- In-memory cache entries: subject to `TimedCachePruner` TTL eviction; no persistence concern.

## PCI DSS Data Storage Compliance

- The library is infrastructure code; compliance obligations are primarily on the calling services
- The `CbaseAppDAO` connecting to `cbaseapp` must use encrypted connections to SQL Server (TLS enforced at DataSource level)
- The `ActionMemo` data model, if it stores free-text agent notes, must be governed by a data minimization policy to prevent inadvertent PAN or SAD storage in memo fields
- The `AnnotatedStoredProcedure` framework must ensure that stored procedure parameters containing PAN or account data are not logged (the annotation-based parameter mapping could inadvertently include sensitive parameters in debug log output)
