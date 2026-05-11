# job_LIB — Enterprise Architect View

## Platform Generation

**Gen-1** — Legacy eCount / Citi-era platform library.

Evidence:
- Parent POM group ID: `com.citi.prepaid.service.job` (Citi-era naming convention retained)
- Spring XML context wiring (no Spring Boot, no annotation-based configuration)
- JMS-over-JNDI remoting (ActiveMQ pattern from early-2000s J2EE architecture)
- Configuration via filesystem properties files through `CBASE_HOME_URL` environment variable
- Use of legacy Ecount-internal utilities: `xplatform`, `springutils-generic`, `springutils-jms`, `spring-dbctx`
- Stored-procedure-centric data access (no JPA/ORM, no repository pattern)

## Business Domain

**Job Scheduling / Batch Enrolment** — Core platform domain covering:
- Bulk account creation and funding (prepaid card issuance)
- Partner–internal identity mapping (PUID ↔ ecountId ↔ ememberId)
- Programme-level agent routing

## Role in the Platform

`job_LIB` is the **shared API contract** library for the job-management domain. It is not deployed independently; it is embedded into:
- `jobservice_SVC` (the runtime job manager service)
- Batch-processing services and workers that need to resolve user mappings or job statistics
- Job integration libraries (e.g., `jobservice-integration_LIB`) that call the job manager to import and enrol users

## Dependencies

### Upstream (libraries job_LIB depends on)
| Dependency | Concern |
|---|---|
| `com.citi.prepaid.service.job:job` parent POM v4.0.1 | Version/BOMs; Citi-era |
| `com.ecount:xplatform` | Ecount platform utilities |
| `com.citi.prepaid.springutils:springutils-generic` | Spring AOP + utilities |
| `com.citi.prepaid.springutils:springutils-jms` | JMS invoker factory |
| `com.citi.prepaid.spring-dbctx:spring-dbctx-*` | DB context container |
| `com.thoughtworks.xstream:xstream` | XML/object serialization for JMS |
| `org.springframework:spring-context` | Spring IoC |
| `commons-lang` | Apache utilities |

### Downstream (consumers)
- `jobservice_SVC` — the primary consumer; hosts the `JobManager` bean
- `jobservice-integration_LIB` / `jobserviceintegration_LIB` — call via JMS client path
- Various batch workers that need `findUserMapping` or `mapUser`

## Integration Patterns

1. **JMS Request-Reply** (remote path): `AgentCachingJobManagerClient` wraps a `ConfigurableJmsInvokerProxyFactoryBean`; the JobManager interface is exposed over a JMS destination. Messages are serialized with XStream.
2. **In-process direct call** (local path): When deployed in the same JVM as `JobManagerImpl`, the proxy is bypassed and calls go directly.
3. **JDBC Stored-Procedure** (data access): All writes and most reads go through named SQL Server stored procedures; inline SQL is used only for simple reads (job_statistics, simplesolve_versionvalidation).
4. **Spring AOP Interceptor**: All DAO and JobManager beans are wrapped in Spring AOP proxy for audit logging.

## Strategic Status

| Dimension | Assessment |
|---|---|
| Lifecycle | **Maintain / Retire** — Library should be kept operational while Gen-1 batch platform is active, but no new features should be built. Migration path is Gen-3 NexPay services. |
| Technical debt | High — Citi-era group IDs, XML-based Spring config, JNDI/JMS wiring, no observability |
| Replacement target | NexPay Gen-3 microservices (nexpay-claim-code-svc, nexpay-order-orchestrator, etc.) |
| Risk level | Medium — Library is stable; risk is mainly around dependency resolution and Java version compatibility |

## Migration Blockers

1. **Group ID namespace**: `com.citi.prepaid.*` parent POMs must be resolvable from the Onbe artifact repository; the Citi heritage creates a dependency on legacy Nexus or mirrored artefacts.
2. **CBASE_HOME_URL filesystem config**: Migrating to container/cloud requires replacing this with environment variable injection or a secret manager.
3. **JMS/JNDI coupling**: Any service consuming the JMS-based client path must co-migrate its JMS provider.
4. **Stored procedures**: All business logic in `jobsvc` stored procedures must be re-implemented before this domain can be retired.
5. **`is_encoded` PUID encoding**: The encoding algorithm is opaque (inside SPs); re-implementation requires reverse-engineering that behaviour.
