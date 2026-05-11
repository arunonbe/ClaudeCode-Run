# Enterprise Architect Analysis: request_LIB

## Platform Generation
**Gen-1 (core) / Gen-1.5 (partially modernised)**

Gen-1 indicators:
- Shared library JAR pattern (not a microservice)
- Spring XML configuration expected from consumers
- JDBC stored procedure-based data access
- XStream XML serialisation (legacy)
- JMS messaging (traditional broker-based)
- Thread-local processing state (`SasiRequestProcessorThreadLocal`)
- Direct dependency on `xplatform:6.5.8` (eCount legacy platform)
- `cbase` types in public API (`SecureUserProfile`)
- Synchronous action processing model with in-process synchronisation

Gen-1.5 indicators:
- Java 21 compiler target
- Maven enforcer for dependency quality
- Separation of manager/processor modules

## Business Domain
**Core Platform — Prepaid Card Request & Action Processing Engine**

This library is the central business logic layer for all cardholder lifecycle operations on the Onbe prepaid card platform. It is the most business-critical shared library in the Gen-1 architecture.

## Architectural Role
**Core Business Logic Library** — Provides:
1. The request domain model (aggregate root for all card operations)
2. The action execution engine (routing 15 action types to downstream services)
3. The persistence layer for all request/action lifecycle data
4. The notification dispatch layer (SMS, CRCP)
5. The configuration management layer for processor behaviour

This library is the heart of the Gen-1 eCount platform. Virtually all card-issuing and payment operations flow through it.

## Dependency Map
### Upstream consumers
- ecount-core_SVC (primary host service)
- Batch processing services
- Client zone web applications
- Scheduling services

### Downstream dependencies
- payment-service_SVC
- inventory-mgmt
- profile-client / ecount-core-client
- xaffiliate-service
- comment service
- SQL Server databases (ecountcore, ecountbatchjobrepository, nexpay_claimable)
- JMS broker
- SMS shared service
- CRCP notification service

## Integration Patterns
- **Shared Library (JAR)**: Embedded in consuming services; no service boundary.
- **JDBC Stored Procedure**: All database access via stored procedures.
- **JMS Messaging**: `springutils-jms` suggests JMS used for async request/action dispatch.
- **HTTP Client**: CRCP and SMS services accessed via HTTP.
- **Synchronous Action Processor**: Actions are executed synchronously within the processor thread.
- **Config Caching**: Program processor config cached in-process.

## Strategic Status
**Critical Path / Highest Migration Risk**

This library is the most complex and highest-risk component for Gen-3 migration:
- It embeds the entire card operation domain model
- 15 action types have distinct persistence and processing logic
- SSN and DOB are handled without application-level encryption
- Wide consumer base means API changes cascade across the platform
- Thread-local state and in-process synchronisation are incompatible with cloud-native, stateless, horizontally-scaled services

Migration of this library requires a complete domain re-modelling effort and cannot be done incrementally without an event-driven or command-pattern bridge.

## Migration Blockers
1. **SSN/DOB handling without encryption**: Security redesign required before any migration.
2. **15 action types**: Each requires a corresponding microservice capability in Gen-3.
3. **In-process synchronisation**: Must be replaced with distributed locking (Redis, database optimistic locking) in Gen-3.
4. **JMS broker dependency**: Message broker infrastructure must be migrated or replaced (Azure Service Bus, etc.).
5. **cbase `SecureUserProfile` types in public API**: All consumers must simultaneously migrate.
6. **Thread-local SASI state**: `SasiRequestProcessorThreadLocal` — incompatible with reactive/async processing.
7. **Stored procedure schema**: Database schema for all request/action tables must be migrated with backward compatibility.
8. **XStream serialisation**: Deserialization of XStream XML is a security risk; replacement required before exposure to untrusted input.
