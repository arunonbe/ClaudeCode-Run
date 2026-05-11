# cicd-testapp_SVC — Enterprise Architect View

## Platform Generation (Gen-1/Gen-2/Gen-3)

**Classification: Gen-1 / early Gen-2 hybrid.**

Evidence:
- Spring XML-driven configuration (hundreds of beans in XML files) is a hallmark of Gen-1 enterprise Java architecture (pre-annotation Spring). The primary service-exposure mechanism is an XML-RPC servlet (`XmlRPCServlet` at `/dispatch.asp`) — a 2000s-era RPC protocol.
- A REST layer has been bolted on (Spring MVC `@RestController` in `ecountCoreRestController`) exposing JSON/XML endpoints at `/device`, `/member`, `/transfer`, `/ach`, `/check`, `/precheck` — representing a Gen-2 migration overlay added without retiring the XML-RPC layer.
- No microservice decomposition, no container orchestration, no service mesh, no cloud-native configuration (Spring Boot absent; instead, Spring 4 XML + traditional WAR deployment to named Tomcat hosts).
- Version is `2.0.0-SNAPSHOT` but the architecture pattern pre-dates typical Gen-2 event-driven or API-first patterns.

## Business Domain

**Payments Platform — Prepaid Card Core (Card Lifecycle, Funds Movement, Member Registry)**

This service is the **core platform service** for prepaid card issuance and lifecycle management. Its business domain spans:
- **Card issuance and personalisation** (eCard, credit card, DDA, IEFT, eCheck, ACH device types)
- **Member identity and KYC** (member registry with KYC and sanctions screening)
- **Funds movement** (transfer lifecycle: begin/commit/cancel; ACH; IEFT)
- **Card controls** (block codes, activation, PIN management, fulfillment)
- **Check management** (PreCheck, physical check-book, stop-payment)
- **Regulatory compliance infrastructure** (Actimize AML/OFAC, country regulation checks)

The Northlane lineage (SCM URL, config server client `com.northlane`, artifact parent `com.citi.prepaid.service`) confirms this is the inherited Northlane/Citi Prepaid core, now operating within Onbe's platform.

## Role in Platform

`cicd-testapp_SVC` (EcountCore) is a **shared platform service** — a backend-for-backend that sits between front-end program clients and:
- The FDR (First Data Resources) card processing system (authoritative card record)
- SQL Server operational databases (member, device, transaction data)
- IBM MQ infrastructure (ECS+, FDR ODS, Actimize, GPP)
- StrongBox (encrypted PII storage)
- The Northlane Config Server

It is consumed by client applications via two protocols:
1. **XML-RPC** over HTTP (`/dispatch.asp`) — legacy protocol; all services exposed: eDevice, eMember, eManage, eTransfer.
2. **REST/JSON+XML** over HTTP — newer overlay; same service interfaces exposed at `/device`, `/member`, `/transfer`, `/ach`, `/check`, `/precheck`.

The service does **not** directly face end users; it is an internal platform API.

## Dependencies

### Upstream dependencies consumed by EcountCore

| System | Integration | Criticality |
|---|---|---|
| SQL Server (ecountCoreDS) | JDBC stored procedures | Critical — all card/member/transaction data |
| SQL Server (jobsvcDS) | JDBC stored procedures | High — PUID member search |
| SQL Server (strongboxDS) | JDBC | High — PII encryption |
| FDR ODS | IBM MQ JMS (FDR XML/EBCDIC protocol) | Critical — authoritative card record |
| ECS+ / ECS Authorization | IBM MQ JMS | Critical — authorization processing |
| Actimize | IBM MQ JMS | High — AML/OFAC sanctions screening |
| GPP | IBM MQ (send-only) | Medium — account status notification |
| Northlane Config Server | HTTP Spring Cloud Config | Critical — all runtime configuration |
| Nexus (Wirecard domain) | HTTP DAV Maven | Build-time only (CI critical) |
| CyberSource ICS | Library (`cybersource:ics:5.0.3`) + SP call | Medium — credit card fraud scoring |

### Downstream consumers

Consumers are not visible in this repository. Based on the dual-protocol exposure and the `StrongBox` / `Director` client interfaces in `common/src/main/java/com/ecount/core/client/` (`IConfigClient`, `IDirectorClient`), likely consumers include:
- Web portals and customer service applications
- Batch processing jobs (job service)
- Program management UIs

## Integration Patterns

1. **Request/Reply over IBM MQ (FDR ODS, ECS+)**: Synchronous over asynchronous messaging. `MQJMSImp.executeGetReply()` sends a JMS message and blocks waiting for a correlated response using `JMSCorrelationID` selector. Retry logic with 3 attempts at 2-second intervals on JMS exceptions.
2. **Fire-and-forget over IBM MQ (GPP, Actimize partial)**: `executeSendMessage` in `MQJMSImp` — send-only pattern for status notifications.
3. **XML-RPC (legacy)**: `XmlRPCServlet` at `/dispatch.asp` exposes all services via the custom `com.ecount.core.xmlrpc.servlet.XmlRPCServlet`. DTOs mapped by Spring bean aliases (`ECountCore.eDevice.Create.Impl`, etc.).
4. **Spring HTTP Invoker (internal)**: `core-servlet.xml` exposes service interfaces via `RequestContextHttpInvokerServiceExporter` using XStream marshalling — used for internal service-to-service calls (eDevice, eMember, eManage, eTransfer remoting).
5. **JDBC Stored Procedures**: All database access uses Spring `StoredProcedure` subclasses — no ORM, no JPQL, no dynamic SQL. Fully parameterised stored procedure calls enforce SQL injection prevention.
6. **Spring AOP for transaction management**: Transaction management applied at DAO level (not service), using `DataSourceTransactionManager` with `tx:advice` (`DataSources.xml`). No distributed/XA transactions despite `ECSXAQueueConnectionFactory` being declared in `context.xml`.
7. **Config Server integration**: `SpringCloudConfigContext` bootstraps all `${property}` placeholders from the Northlane config server at startup.

## Strategic Status

**Retain with migration planning required.**

- The service is active, has tests (even if skipped in CI), has CodeQL SAST scanning, has Dependabot, and has REST APIs being developed alongside the legacy XML-RPC layer — indicating active investment.
- However, it carries significant technical debt: Spring 4 (EOL), Log4j 1 (EOL), Java 8, XML-RPC protocol, SNAPSHOT dependency on Wirecard Nexus infrastructure, and hard dependency on FDR ODS via IBM MQ.
- The REST controller overlay (`ecountCoreRestController`, `ecountCoreRestApi`) represents the migration path to a Gen-2/Gen-3 API-first interface but is incomplete (not all XML-RPC operations have REST equivalents visible).
- The parent POM (`com.citi.prepaid.service:service-parent:8`) and SCM URL at `gitlab.com/northlane/...` confirm this is under the Northlane-origin stack; Onbe migration effort is in progress.

## Migration Blockers

1. **Spring 5 upgrade blocked**: explicitly documented in `pom.xml` line 76 comment — `KYCService.xml`, `web.xml`, `Configuration.xml` all need changes; `Log4jConfigListener` removal; `MBeanExporter` API change. Resolution requires targeted refactoring before any framework upgrade.
2. **Log4j 1.x deeply embedded**: `log4j:1.2.15` used throughout; `Log4jConfigListener` in `web.xml`; `Log4jMDCWriter` in `GlobalRequestID.xml`. Migration to SLF4J + Logback or Log4j 2 requires all logger references and Spring listeners to change.
3. **XML-RPC protocol**: The `XmlRPCServlet` and all 40+ XML-RPC operation aliases (eDevice, eMember, eManage, eTransfer) have active consumers. These must be cut over to REST or gRPC before the XML-RPC layer can be removed.
4. **IBM MQ JMS dependency**: All FDR ODS and ECS+ integration uses IBM MQ (`com.ibm.mq.jms.*` classes referenced in `context.xml`). Migration away from IBM MQ requires replacement messaging infrastructure.
5. **FDR ODS protocol**: FDR ODS uses a proprietary XStream/EBCDIC message format with ~30+ operation types. Replacing FDR requires parallel operation support or a complete card platform migration.
6. **Wirecard Nexus infrastructure**: `d-na-stk01.nam.wirecard.sys:8080` is the release/snapshot Nexus. If decommissioned, all builds that do not have artifacts in a local cache will fail. Internal artifacts (`strongboxImpl 1.0.2`, `xmlrpc`, `DAO-Util`, `springutils`) must be migrated to Onbe-controlled artifact repository.
7. **WAR + Tomcat deployment model**: Migrating to containerised (Docker/Kubernetes) deployment requires externalising JNDI resources, removing `antiJARLocking`, replacing config server bootstrapping, and rebuilding the health endpoint.
8. **Java 8 baseline**: multiple libraries pin to Java 8 APIs; modernisation to Java 17+ requires validating all 30+ dependencies including `cybersource:ics:5.0.3`, `aspectj:1.5.2a`, `commons-beanutils:1.7.0`, `jtds:1.2.2`.
