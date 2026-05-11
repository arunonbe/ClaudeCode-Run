# consumerload_API — Enterprise Architect View

## Platform Generation (Gen-1/Gen-2/Gen-3)

**Classification: Gen-1**

All indicators confirm this is a first-generation ("Gen-1") service:

| Indicator | Evidence |
|---|---|
| SOAP/JAX-RPC, not REST | `ConsumerLoadWebService extends java.rmi.Remote`; Apache Axis 1.4; WSDL2Java-generated classes |
| Java 6 compilation target | Root `pom.xml` `<source>1.6</target>` |
| Spring 2.0.8 (2007 vintage) | Root `pom.xml` `spring.version=2.0.8` |
| XML-only Spring configuration | DTD-based `spring-beans.dtd` contexts; no annotations |
| No REST endpoints | `DispatcherServlet` registered but `consumerload-servlet.xml` contains an empty `<beans/>` element |
| Platform-specific file paths (Windows `D:/c-base/...`) | `consumerload-wsContext.xml` line 8; `web.xml` line 24 |
| Dual VCS (SVN + Git) | `.svn/` and `.git/` directories coexist |
| No containerization | No Dockerfile, no Kubernetes manifests |
| Proprietary eCore/cbase SDK coupling | All business logic delegates to `com.cbase.*` and `com.ecount.*` libraries |
| No automated tests | Zero test classes in `src/test/java` |
| Auto-generated WSDL2Java code | File headers on `ConsumerLoadWebService.java`, all domain/request/response classes: "This file was auto-generated from WSDL by the Apache Axis 1.4 Apr 22, 2006" |

The WSDL generation timestamp in class headers (Apr 22, 2006) indicates the service contract was established around 2006–2007, making this service approximately 18–19 years old.

## Business Domain

**Domain**: Consumer Prepaid Card Funding — Self-Load

This service sits in the **Consumer Load** subdomain of prepaid card management. Specifically:

- **Funding rail**: Credit card (CC) to eCard load (consumer-initiated top-up).
- **Identity management**: KYC data collection and status checking for regulated load operations.
- **ACH information**: Exposure of ACH/direct-deposit virtual bank account details for cardholder use.

In Onbe's business taxonomy this maps to: **B2C Disbursements / Consumer-Initiated Load** under the prepaid program management domain. The service supports the "consumer rebates" and "marketplace" client segments where cardholders load their own funds rather than receiving a corporate disbursement.

## Role in Platform

`consumerload_API` is an **internal SOAP adapter service** that exposes a limited set of consumer-facing operations to partner channels (e.g., web portals, mobile backends, IVR systems operated by partners). Its role in the platform is:

```
Partner Channel (web/mobile/IVR)
        │
        │  SOAP over HTTP
        ▼
 consumerload_API  ← THIS SERVICE
        │
        │  Proprietary cbase SDK calls
        ▼
 eCore Platform (core card management, member store, transfer engine)
        │
        ▼
 RDBMS (JobSvc + cbase databases)
```

It is a thin façade that:
1. Translates SOAP protocol to cbase SDK calls.
2. Enforces input validation and program-level business rules (limits, fees, KYC gate).
3. Does not own any persistent state.

The service is consumed by external partner applications, not by other internal microservices (no REST API, no message-bus integration).

## Dependencies

### Upstream (callers)
- Partner web applications / portals (unknown; not visible in this repository)
- Potentially a mobile backend or API gateway (not documented)

### Downstream (called by this service)
| Dependency | Artifact / Class | Nature |
|---|---|---|
| eCore platform | `ECoreDevice`, `ECoreMember`, `ECoreTransfer` (cbase SDK) | Synchronous, proprietary, in-process SDK calls that ultimately make network calls to eCore |
| GetPuid | `com.cbase.business.ecount.data.GetPuid` | JDBC query to `JobSvcDataSource` |
| Comment service | `com.ecount.services.comment.ICommentService` | Internal library; writes to audit trail DB |
| eCount Profile | `ECountProfileDriver`, `AppProfileProgramMembership`, `AppProfileProgramStrategyClass`, `AppPromotionFeatureProfileClass` | eCore profile read path |
| Fee engine | `com.cbase.business.ecount.profile.factory.Fee.getTxFeeAmount()` | eCore fee calculation |
| KYC engine | `MemberManager.doKYCCheck()` | Invoked through cbase SDK; actual KYC provider opaque |
| Spring Framework | Container, IoC | `org.springframework:spring:2.0.8` |
| Apache Axis | SOAP engine | `axis:axis:1.4` |

### Configuration dependencies
- `D:/c-base/config/ConsumerLoad/ConsumerLoad.properties` (required at startup)
- `D:/c-base/config/ConsumerLoad/log4j.xml` (required for logging)
- Tomcat JNDI: `jdbc/JobSvcDataSource`, `jdbc/CbaseappDataSource`
- Internal Maven repository for `com.ecount`, `com.citi`, `com.parents` artifacts

## Integration Patterns

| Pattern | Implementation | Notes |
|---|---|---|
| SOAP/RPC | Apache Axis 1.4, `java.rmi.Remote` interface | Synchronous request-response; no async or callback |
| Spring IoC (XML) | `consumerload-wsContext.xml`, `consumerload-implContext.xml` | DTD-based bean wiring; no annotations; all beans resolved at startup |
| Service Locator (anti-pattern) | `getWebApplicationContext().getBean("...")` throughout `ConsumerLoadWebServiceImpl` | Bypasses constructor injection; makes testing difficult |
| Template Method | `ConsumerLoadService<IN,OUT>.execute()` abstract method pattern | Each concrete service extends the abstract base |
| Helper/Utility classes | `AccountHelper`, `ProfileHelper`, `CommentHelper`, `ValidationHelper`, `InputHelper`, `OutputHelper` | Stateless static/instance helpers; not a service layer |
| No message bus | No JMS, no Kafka, no RabbitMQ | All integration is synchronous SDK calls |
| No caching | No EhCache, Hazelcast, or Spring Cache | Member lookups and profile reads are uncached |

## Strategic Status

**Status: Legacy / End-of-Life Candidate**

| Dimension | Assessment |
|---|---|
| Technology age | ~18 years old (2006 WSDL vintage); Java 6, Spring 2.x, Axis 1.4 — all EOL |
| Maintenance burden | High: any change requires understanding Axis serialization, DTD Spring XML, and cbase SDK internals |
| Security posture | Poor: no authentication, PAN/CVV in logs, no TLS enforcement, multiple EOL dependency CVEs |
| Testability | Near-zero: no tests, Service Locator pattern throughout, XML-only config |
| Scalability | No evidence of horizontal scaling; Windows-specific file paths prevent containerization as-is |
| Business value | Active: still serves the consumer self-load use case; no replacement service identified in the repository |
| Migration priority | HIGH: PCI DSS and GLBA exposure alone justify urgent modernization |

## Migration Blockers

Migrating to a Gen-3 (REST/microservice/containerized) architecture faces these specific blockers identified in the code:

1. **eCore/cbase SDK coupling**: All business logic calls proprietary `com.cbase.*` and `com.ecount.*` SDK classes. A Gen-3 service would need these replaced with documented REST or gRPC APIs to the core platform, or a strangler-fig adapter layer.

2. **WSDL contract**: External partner systems are bound to the SOAP WSDL contract. Any migration must either maintain a SOAP facade or coordinate a breaking change with all partners (partner_user_id / program_id surface is the external contract).

3. **Windows-only file path configuration**: `D:/c-base/config/ConsumerLoad/` is hardcoded in two XML files. Container images require environment-variable-driven or mounted-volume configuration.

4. **No tests**: Zero automated tests means any migration risks functional regression with no safety net.

5. **Spring XML-only IoC**: No annotations, no component scanning. Migration to Spring Boot requires a full re-wiring of all bean definitions.

6. **Comment service dependency**: `com.ecount.services.comment` provides audit-trail writes. Its interface contract and whether a REST equivalent exists must be confirmed before migration.

7. **Dual VCS**: The `.svn` working copy suggests this repository may still be actively maintained via SVN by some teams, with Git as a mirror. A migration must establish single-VCS ownership.

8. **Service bean registration discrepancy**: Service beans are registered in `consumerload-implContext.xml` but also defined (commented out) in `consumerload-wsContext.xml`. This configuration ambiguity must be resolved before migration.
