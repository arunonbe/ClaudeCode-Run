# Enterprise Architect Report: scheduler_WAPP

## Platform Generation

**Gen-1 / Gen-2 hybrid**. The codebase originated as a Gen-1 eCount/Citi service (package prefix `com.ecount.service.scheduler`, author credited as "OFSS" — Oracle Financial Services Software, the typical eCount development partner). It has been partially modernised: Java 21 compiler target, Tomcat 10.1, Jakarta EE 6.0 web.xml schema, and a GitHub Actions CI pipeline. However, the core integration pattern remains Gen-1: Spring XML bean wiring, Spring HTTP Invoker for RPC, Quartz 2 JDBC cluster, and WAR-based deployment. No Spring Boot, no REST, no OpenAPI — this is a legacy XML-RPC-style architecture hosted in a container.

## Integration Patterns

- **Inbound**: Spring HTTP Invoker over HTTP (binary Java serialisation protocol) at `/scheduler.service`. Clients must have the `scheduler-common` JAR on their classpath to use the `SchedulerService` Java interface proxy
- **Outbound callbacks**: HTTP Invoker callbacks to registered URLs on the internal network when triggers fire; the `SimpleCallbackTask` implementation sends HTTP POST to the `callbackPath`
- **Cluster coordination**: JDBC-backed Quartz cluster using Microsoft SQL Server with row-level locking (`SELECT ... ROWLOCK`)
- **Health**: Simple unauthenticated HTTP GET `/hc`

## External Dependencies

- SQL Server instances on legacy Wirecard/Northlane network (`*.nam.wirecard.sys`) — critical dependency, referenced in `.env` files
- `com.parents:prepaid-parent:6.0.12` — internal corporate parent POM from Nexus at the old Northlane network address
- `bellsoft/liberica-openjre-alpine:21` — base Docker image; Bellsoft is a third-party JDK vendor
- APIM integration for WSDL publication (`PUBLISH_TO_APIM: true` in deployment workflow)

## Position in the Broader Platform

scheduler_WAPP is a shared infrastructure service consumed by Gen-1 and Gen-2 applications across multiple domains: card lifecycle management, order processing, reconciliation, and disbursement. It is an invisible dependency — consumers register schedule callbacks at startup and receive no direct notification if the scheduler fails. Its availability is therefore a silent prerequisite for the reliability of several cardholder-facing business processes.

The service bridges Gen-1 (eCount/Citi Java HTTP Invoker pattern) with Gen-2 operational infrastructure (GitHub Actions, Docker, ECS or Kubernetes). It is not yet aligned with the Gen-3 (Azure, Spring Boot 3.x) stack.

## Migration Blockers

1. **Spring HTTP Invoker dependency**: All callers depend on Spring HTTP Invoker, which was removed in Spring 6. Migration to REST or gRPC requires simultaneous changes across all consuming services
2. **Spring XML wiring**: The entire application context is XML-configured with no component scanning for business logic; migration to Spring Boot annotation-driven config requires full XML rewrite
3. **Quartz JDBC schema**: The `QRTZ2_` schema is tightly coupled to the shared SQL Server `jobsvc` database; migration to a new scheduling backend requires database schema migration coordination with all job-owning services
4. **Serialised Java objects in Quartz**: `callbackInputObject` is stored as Java-serialised bytes in Quartz job data; any change in class structure or classloader breaks existing jobs in the database
5. **WAR deployment model**: All Gen-1 services assume WAR packaging and JNDI DataSources; migration to Spring Boot embedded server requires removing JNDI dependency

## Strategic Status

**Candidate for replacement, not incremental modernisation**. The service performs a well-defined function (distributed scheduling) that is available natively in cloud platforms (AWS EventBridge, Azure Scheduler, Quartz wrapped in Spring Boot). The correct strategic path is to identify all consumers, build a REST-based replacement aligned with Gen-3 patterns, migrate consumers one by one, and decommission this service. In the interim, it should have its committed credentials rotated, its endpoint authenticated, and its callback URL validated against an allowlist.
