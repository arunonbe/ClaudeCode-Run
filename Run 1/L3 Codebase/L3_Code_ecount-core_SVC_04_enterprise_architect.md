# 04 Enterprise Architect — ecount-core_SVC

## Platform Generation Assessment

`ecount-core_SVC` is a **Generation 2 → Generation 3 transitional service**. It represents the most complex point in the Onbe platform architecture — a hybrid system that has been progressively modernised but carries significant Gen-1 heritage:

| Dimension | Gen-1 Heritage | Gen-2/3 Modernisation |
|---|---|---|
| Java | Java 5 origins | Java 21 compiler |
| Runtime | Tomcat 10.1.42 (WAR) | Containerised via Docker; JNDI replaced with env-var injection |
| Framework | Spring XML context (2.x style) | Spring 6 (Jakarta EE namespace), partial annotation-driven config |
| Persistence | Stored-procedure DAOs (custom framework) | Still stored-procedure based; no JPA |
| Logging | Log4j 1.x API (via bridge) | Log4j 2 core; JSON event layout |
| Messaging | IBM MQ 9.4 (Jakarta) | Modern MQ client |
| API style | XML-RPC (legacy) + Spring MVC REST | REST expanding; XML-RPC maintained for backward compatibility |
| Database driver | jTDS (legacy paths), mssql-jdbc (new paths) | Migration to mssql-jdbc underway |
| Configuration | External file (`ecountcore.properties`) | Azure App Configuration (`AzureService.xml`) |
| Security | Internal auth | Azure AD OAuth2 |
| Version | 3.x | Still evolving |

## Role in Platform Architecture

EcountCore is the **system of record** for prepaid card accounts and transactions. All other Onbe services are ultimately either upstream (delivering data to EcountCore) or downstream (consuming EcountCore data). Its position:

```
External Partners / Clients
          │
          ▼
  embedded-payments-api  ◄──── Azure APIM
          │
     (REST calls)
          │
          ▼
  ┌───────────────────────────────────────────────────────────┐
  │              ecount-core_SVC (Tomcat WAR)                 │
  │  ┌──────────────────────────────────────────────────────┐ │
  │  │ ecountCoreRestController  │  XML-RPC endpoints       │ │
  │  └──────────────────────────────────────────────────────┘ │
  │  ┌────────────────────────────────────────────────────────┐│
  │  │ ecountCoreService (EMember, EDevice, ETransfer, etc.)  ││
  │  └────────────────────────────────────────────────────────┘│
  │  ┌────────────────────────────────────────────────────────┐│
  │  │ ecountCoreDAO (stored-procedure wrappers)              ││
  │  └────────────────────────────────────────────────────────┘│
  └───────────────────────────────────────────────────────────┘
          │
  ┌───────┴──────────────────────────────────────────────┐
  │    SQL Server Databases                              │
  │  ecountcore, jobsvc, strongbox, cbaseapp, fdrODS     │
  └──────────────────────────────────────────────────────┘
```

Other consumers: `emboss-extract_LIB` (direct DB), `clientapi_API`, `cs-api*`, batch processing jobs.

## Key Dependencies

| Dependency | Consumed Service | Nature |
|---|---|---|
| `strongbox-impl:2.0.1` | StrongBox | HSM key management |
| `actimizekyc:1.0` | Actimize | KYC/AML |
| `com.ibm.mq.jakarta.client:9.4.0.0` | IBM MQ | Async messaging |
| `cybersource:jakarta-ics:5.0.3` | Cybersource ICS | Payment gateway |
| `director-client` | Director | DB config / credential lookup |
| `azure-data-appconfiguration:1.3.0` | Azure App Config | Runtime configuration |
| `azure-identity:1.5.3` | Azure AD | Identity / OAuth |
| `correlation-web:2.0.1` | Correlation library | Distributed tracing |
| `xplatform:6.5.8` | xplatform_LIB | Shared platform utilities |

## Migration Complexity

| Scenario | Effort | Notes |
|---|---|---|
| Remove XML-RPC, keep only REST | Very High | Requires client migration across all consuming services |
| Migrate WAR to Spring Boot executable JAR | High | Would eliminate Tomcat dependency; JNDI datasource wiring needs replacement |
| Replace stored-procedure DAOs with JPA/Spring Data | Very High | Thousands of stored procedures; major risk |
| Complete Azure App Configuration migration | Medium | `AzureService.xml` already exists |
| Replace IBM MQ with Azure Service Bus | High | Message topology changes |
| Remove Log4j 1.2-api bridge | Medium | Requires updating all callers of Log4j 1.x API |

## PCI DSS Compliance Architecture

As the system of record for cardholder data, EcountCore's PCI scope is:

- **Req 2**: Secured Tomcat configuration; non-root container user (`PPA_QA_MQ`)
- **Req 3**: PAN encryption via StrongBox HSM; ehcache PAN caching must be verified
- **Req 4**: TLS for all inbound and outbound connections; QA cert import in Dockerfile
- **Req 6**: Java 21 + Spring 6 (modern security baseline); Log4j 2 (post-Log4Shell patched)
- **Req 7/8**: Azure AD OAuth2 for service authentication
- **Req 10**: Log4j 2 + JSON event layout; correlation IDs for audit trail
- **Req 12**: Service owner: Onbe Engineering (maintainer: `anil.tadigiri@onbe.com` per Dockerfile LABEL)
