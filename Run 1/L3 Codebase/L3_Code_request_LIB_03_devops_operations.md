# DevOps / Operations Analysis: request_LIB

## Build System
- **Maven** multi-module project (mvnw wrapper present)
- **Java**: Source/target **21**
- **Parent POM**: `com.parents:prepaid-parent:6.0.13`
- **Root artifact**: `com.citi.prepaid.service.request:request:4.2.16-SNAPSHOT`
- **Modules**: request-common, request-manager, request-processor
- **Enforcer**: `maven-enforcer-plugin` with `requireReleaseDeps` rule — SNAPSHOT dependencies in build will fail (except when parent is a SNAPSHOT).

## Module Build Outputs
| Module | Artifact | Purpose |
|---|---|---|
| request-common | request-common JAR | Domain model, interfaces, XStream serialisation |
| request-manager | request-manager JAR | DAO implementations, activity handlers, request manager |
| request-processor | request-processor JAR | Action handlers, processor implementation, SMS/CRCP integrations |

## Deployment
This is a **library** — not deployed as a standalone service. Consumed by:
- ecount-core_SVC (the main processing service)
- Batch processing services
- Client zone and other web applications

Deployed via Maven artifact publication.

## Configuration Management
- Library behaviour is entirely configured by the consuming application via Spring injection.
- `RequestServiceConfigManagerImpl` loads program processor configuration from the database.
- `ConfigCachingRequestServiceConfigManagerClient` caches program processor configuration in-process.
- SMS configuration loaded via `SmsConfigDao` from the database.
- CRCP service URL and connection details injected via Spring.
- No environment variable support within the library itself.

## Observability
- Logging: Commons Logging / SLF4J (mixed — older `request-common` uses Commons Logging; newer processor classes likely use SLF4J).
- No application-level metrics.
- No distributed tracing.
- Extensive test coverage evident from test class count (80+ test files across modules).

## Infrastructure Dependencies
| Dependency | Type | Notes |
|---|---|---|
| SQL Server | Database | All request/action/activity/config data |
| payment-service_SVC | Internal service | Payment operations (AddFunds, etc.) |
| inventory-mgmt | Internal library | Card inventory operations |
| ecount-core-client / profile-client | Internal service client | Profile lookups |
| xaffiliate-service | Internal service client | Affiliate operations |
| Shared SMS service | External HTTP endpoint | SMS delivery |
| CRCP service | Internal HTTP endpoint | Customer notification delivery |
| `springutils-jms:3.1.0` | Internal | JMS-based async messaging |
| `spring-dbctx-container:2.0.1` | Internal | Database context |
| `job-common:4.0.1` / `job-impl:4.0.1` | Internal | Job scheduling integration |
| `xplatform:6.5.8` | Internal | Platform utilities |
| `ecount-system:4.0.2` | Internal | System utilities |
| `comment:3.0.1` | Internal | Comment/memo service |

## Operational Risks
1. **SNAPSHOT version `4.2.16-SNAPSHOT`**: Root artifact is a SNAPSHOT; enforcer prevents SNAPSHOT dependencies in modules but the library itself is not a release.
2. **Thread-local state** (`SasiRequestProcessorThreadLocal`): Memory leak risk in thread pool environments if not cleared after request processing.
3. **ActionSynchronizer / RequestSynchronizer**: Synchronisation in a distributed environment (multiple JVMs) requires database-level locking; in-process synchronisation alone is insufficient for distributed deployments.
4. **Config caching** (`ConfigCachingRequestServiceConfigManagerClient`): Cached processor configuration may become stale; no cache invalidation mechanism visible.
5. **JMS dependency** (`springutils-jms`): JMS broker dependency; infrastructure must include a JMS broker (ActiveMQ/HornetQ).
6. **Wide dependency surface**: 12+ internal library dependencies; upgrades require careful coordination.

## CI/CD
No pipeline configuration present. Extensive test suite (80+ test classes) but requires live SQL Server for integration tests. No containerised test setup visible.
