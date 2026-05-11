# billing-integration_LIB — Enterprise Architect View

## Platform Generation (Gen-1/Gen-2/Gen-3)

**Generation: Gen-1 (legacy)**

Evidence:
- Spring Framework 2.0 (released 2006), Hibernate 3.2.0.cr4 (2006), Java 1.5 bytecode target (2004–2005 era)
- EJB 3.0 deployment model targeting JBoss Application Server with JBoss-proprietary annotations (`@LocalBinding`, `@RemoteBinding`, `org.jboss.annotation.ejb3.*`)
- Spring XML bean configuration (no annotations, no Spring Boot, no auto-configuration)
- No REST endpoints — service surface is an EJB local/remote interface over JNDI
- Integration with Microsoft Dynamics GP via direct JDBC to the GP SQL Server database — a classic point-to-point Gen-1 integration pattern
- Dependency on `com.ecount.*` parent POM and `springutils-ejb3` artifacts from the original ecount.com platform era
- SVN SCM URL in `pom.xml` (`ecsvn.office.ecount.com`) — predates Onbe's GitHub org migration
- Version is `1.0.0-SNAPSHOT` — the artifact has never been formally released

---

## Business Domain

**Domain: B2B Billing / Financial Settlement**

This library is responsible for translating prepaid-card order fulfillment events into billable records within the Great Plains ERP system. It sits at the intersection of:
- **Order Management** (upstream dependency: `order-pojo` service)
- **Client Billing / Accounts Receivable** (downstream: Microsoft Dynamics GP)
- **Fee Configuration** (fee schemes, contract pricing, rate cards — all sourced from GP or internal DB)

The domain entities (`SalesOrder`, `FeeScheme`, `FeeStructureItem`) represent the billing side of Onbe's client relationship, not the cardholder side.

---

## Role in Platform

**Role: ERP Integration Bridge (GP Billing Adapter)**

`billing-integration_LIB` is a **shared library** (JAR) consumed by one or more services that process order events. Its role is:

1. **Inbound**: Receive an `Order` domain object from the Order Service
2. **Enrich**: Fetch client-specific fee configuration from GP's `contractpricing` table
3. **Transform**: Apply one of six fee strategy algorithms to compute billable line items
4. **Persist**: Write a GP sales order staging record to the internal `OrderDataSource` database for downstream GP pick-up
5. **Cancel**: Support cancellation of previously staged GP sales orders

The library is a **synchronous, in-process integration** — it does not publish events, call REST APIs, or use messaging. The GP integration is entirely through direct JDBC to the GP SQL Server database.

The EJB module (`BIServiceBean`) would expose this functionality as a JBoss SLSB (Stateless Session Bean) with local and remote JNDI bindings (`BIService/local`, `BIService/remote`), indicating it was designed to be called from other EJBs or remote clients within the same JBoss cluster.

---

## Dependencies

### Upstream (this service consumes)
| Dependency | Type | Coupling |
|---|---|---|
| `com.ecount.service.order:order-pojo:1.0.1` | JAR (provided) | Tight — `Order`, `OrderItem`, `OrderItemType`, `OrderAssociation`, `FileOrder`, `OrderDao` are used directly throughout |
| `java:jdbc/OrderDataSource` | SQL Server DB | Tight — Hibernate-managed schema |
| `java:jdbc/GreatPlainsDataSource` | SQL Server GP DB | Tight — reads `contractpricing`, `inventory`; no abstraction layer on GP side |
| `java:jdbc/JobSvcDataSource` | SQL Server DB | Moderate — only used for rate-card clients via stored proc |
| `dbo.get_contract_pricing` (commented out) | GP stored proc | Legacy; replaced by inline JDBC |
| `dbo.rate_card_data_summary` | GP stored proc | Active for rate-card scheme |

### Downstream (this service produces)
| Output | Consumer |
|---|---|
| `sales_order` + `sales_order_item` rows | Presumed GP polling/sync process (not in this repo) |

### Internal Platform Dependencies
| Artifact | Purpose |
|---|---|
| `com.parents:service-parent:9.0.0` | Maven parent POM (build standards) |
| `com.ecount.springutils:springutils-ejb3:1.0.1-SNAPSHOT` | JBoss EJB3/Spring integration glue (`AbstractGenericEJB3`) |

---

## Integration Patterns

| Pattern | Where Used | Notes |
|---|---|---|
| **Strategy** | `FeeStrategy` interface + 6 implementations | Clean pattern; allows adding new fee schemes without modifying existing code |
| **Decorator** | `CommonFeeDecorator` / `CommonReloadFee` / `CommonFeeAssessor` | Applies common fee lines on top of scheme-specific fees |
| **Service Facade** | `BIService` interface + `BIServiceImpl` | Thin facade over `SalesOrderManager` |
| **DAO / Repository** | All `*Dao` interfaces + Hibernate / JDBC implementations | Standard Spring/Hibernate DAO pattern |
| **Singleton ApplicationContext** | `BIAppContext` | Anti-pattern in modern Spring; blocks testability and multiple context loading |
| **JNDI Lookup** | Datasources, EJB remote client (`appContext-bisvc-slsbclient.xml`) | JEE-era service location |
| **EJB SLSB Delegation** | `BIServiceBean` delegates to Spring bean via `AbstractGenericEJB3` | JBoss Spring-EJB bridge; opaque coupling to JBoss container |
| **Direct GP DB Access** | `JdbcGPCustomersDao`, `JdbcGPInventoryDao` | Point-to-point integration — no API, no message bus |

There is **no message-driven integration, no REST, no SOAP, no event streaming**. All integration is synchronous and request-reply.

---

## Strategic Status

**Status: Legacy / Sustain-Only**

- Java 5 bytecode on Spring 2.0 / Hibernate 3.2 is effectively a maintenance liability. No path to containerization without a full framework upgrade.
- The EJB module is already disabled (commented out in the parent POM), suggesting the EJB deployment model has been abandoned or the service is consumed differently today.
- The GP integration via direct JDBC creates a hard dependency on the GP SQL Server schema — any GP upgrade or schema change is a breaking change for this library.
- No evidence of active feature development (version stuck at `1.0.0-SNAPSHOT`).
- Original SCM at SVN `ecsvn.office.ecount.com` confirms this predates the ecount/Onbe platform modernization.
- CodeQL scanning is active, indicating it is still in use or at least on the inventory of monitored repos.
- The Wirecard-era Maven Nexus mirror (`d-na-stk01.nam.wirecard.sys`) suggests this artifact may have been built last during the Wirecard/Paywire ownership period.

---

## Migration Blockers

| Blocker | Severity | Detail |
|---|---|---|
| Java 5 / Spring 2 / Hibernate 3 | Critical | No upgrade path to Spring Boot or modern ORM without full rewrite of all DAO, config, and EJB layers |
| JBoss proprietary annotations in `BIServiceBean` | High | `@LocalBinding`, `@RemoteBinding`, `AbstractGenericEJB3` tie the EJB module to JBoss; incompatible with WildFly 10+, Quarkus, or any container runtime |
| Direct JDBC to GP SQL Server | High | GP is a black-box ERP; direct DB access bypasses GP's transactional guarantees and creates schema coupling; should be replaced by a GP API or integration platform (BizTalk, MuleSoft, etc.) |
| `order-pojo` tight coupling | High | The entire domain model is imported from `order-pojo:1.0.1`; a Gen-3 redesign requires this contract to be redefined as an API (REST/event) not a JAR dependency |
| No schema migration tooling | Medium | No Flyway/Liquibase; the `sales_order` schema is defined only through Hibernate annotation inference and is not independently documented |
| `eternal=true` cache for fee schemes | Medium | Fee configuration changes require JVM restarts; a Gen-3 version needs dynamic cache refresh |
| Hardcoded item codes | Medium | Fee item codes (e.g., `"1000"`, `"1010"`, `"10100"`) are magic strings in strategy classes; should be externalized to database or configuration |
| Credentials in source control | Critical | Must be rotated and moved to secrets management before any migration project uses this codebase as a baseline |
