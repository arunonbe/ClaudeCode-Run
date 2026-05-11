# card-notification-restful_API — Enterprise Architect View

## Platform Generation (Gen-1 / Gen-2 / Gen-3)

**Assessment: Gen-2 (in transition toward Gen-3)**

The service straddles two generations:

| Dimension | Generation Indicator | Evidence |
|---|---|---|
| **Core business logic** | Gen-1 / Gen-2 | `card-notification-ws` module uses legacy ECount/CBase platform libraries (`xplatform`, `xaffiliate-service`, `xsearch-client`); Spring XML bean definitions; Apache Axis/WSDL-generated comment in `CardNotificationRequest.java` |
| **Deployment runtime** | Gen-2 → Gen-3 | `card-notification-boot` wraps legacy JAX-RS resources in Spring Boot 3.5.7; deploying to AKS via containerised JAR |
| **Configuration** | Gen-3 | Azure App Configuration + Azure Key Vault + Managed Identity |
| **CI/CD** | Gen-2 → Gen-3 | GitHub Actions delegating to shared `om-ci-setup` workflow; legacy GitLab CI still present |
| **Data access** | Gen-1 | Direct stored procedure calls via Spring JDBC `StoredProcedure` base class; Hibernate 5 ORM; legacy `DirectorConfiguredDBCPdatasourceCreator` in fallback path |
| **API contract** | Gen-1 | URL-encoded form POST with JAXB-unmarshalled XML body; no REST JSON contract; no authentication |

The `card-notification-boot` module is essentially a Spring Boot wrapper around unchanged Gen-1 business logic (`card-notification-ws`). The migration from Tomcat WAR to Spring Boot JAR has been completed at the packaging level, but the application logic, data access patterns, and API contract remain Gen-1.

---

## Business Domain

**Channel: SMS / Mobile Cardholder Self-Service**  
**Business Domain: Cardholder Notifications & Alerts**  
**Sub-domain: SMS Pull (cardholder-initiated)**

This service is entirely within the **cardholder-facing channel layer**. It does not process payments, manage accounts, or perform any card lifecycle operations. It is a read/query service (plus enrollment state management) that surfaces account information via SMS.

The service was originally built for Citi Prepaid, migrated through North Lane, and is now operating under the Onbe brand. Brand references in `messages.properties` are stale.

---

## Role in Platform

| Role | Description |
|---|---|
| **SMS Gateway Adapter** | Translates between SAP Mobile Services / Sinch SMS protocol (URL-form-encoded XML) and Onbe's internal ECount/CBase platform |
| **Member Identity Resolution** | Resolves mobile phone number to one or more prepaid card accounts via xSearch-XMLRPC |
| **Account Data Surfacing** | Queries ECount core for real-time balance, payment, and transaction data on behalf of the cardholder |
| **Enrollment State Manager** | Manages opt-in/opt-out records for SMS notification services in `sms_cardnotification_profile` |
| **SMS Audit Logger** | Records all SMS interactions to `sms_cardnotification_log` for operational and compliance purposes |
| **Program Eligibility Gatekeeper** | Enforces that only SMS-pull-enabled programs can use the service, via affiliate configuration |

This service has **no upstream API consumers** within Onbe's platform (it is consumed externally by SAP/Sinch). It is a leaf service in the dependency graph from a platform perspective, though it depends heavily on core infrastructure (ECount Director, xSearch, CBase DB).

---

## Dependencies

### Upstream (Services this repo calls)

| Service | Protocol | Description |
|---|---|---|
| **ECount Director** (`prod.nam.wirecard.sys:8080`) | HTTP RPC | Boot address for ECount service layer; all EDevice/EMember/AppSmsMsgProfile calls route through it |
| **xSearch-XMLRPC** (via Director) | HTTP XMLRPC | Member lookup by mobile phone; `XSearchClientFactory.getClient(XMLRPC_Client)` |
| **CBase Application DB** | JDBC SQL Server | Affiliate data, SMS profile data, enrollment records, audit logs |
| **ECount Core DB** | JDBC SQL Server | Core ECount data |
| **Job Service DB** | JDBC SQL Server | Referenced in config; no DAO usage visible |
| **Sinch/SAP SMS Gateway** | HTTPS REST | Outbound MT SMS delivery |
| **Azure App Configuration** | HTTPS/Managed Identity | All runtime configuration |
| **Azure Key Vault** | HTTPS/Managed Identity | All credential secrets |

### Downstream (Services that call this repo)

| Consumer | Protocol | Description |
|---|---|---|
| **SAP Mobile Services / Sinch** | HTTPS POST | Sends inbound SMS (MO) to `POST /Cardnotification/CardnotificationService` |
| **Azure API Management** | HTTPS | External APIM routes to this service's backend |

### Internal Library Dependencies

| Library | Artifact ID | Role |
|---|---|---|
| `xplatform` | `com.ecount:xplatform:6.5.4` | ECount core platform: EDevice, EMember, AccountBalance, AccountJournal, RequestContext, ServiceConfig, AppSmsMsgProfile |
| `xaffiliate-service` | `com.ecount.one.service.affiliate:xaffiliate-service:4.0.1` | Affiliate service for program SMS pull eligibility lookup |
| `xsearch-client` | `com.ecount.service.xsearch-new:xsearch-client:4.0.1` | XMLRPC client for member lookup by mobile number |
| `springutils-generic` | `com.citi.prepaid.springutils:springutils-generic:3.1.0` | Shared Spring utilities |

---

## Integration Patterns

| Pattern | Implementation | Notes |
|---|---|---|
| **Synchronous HTTP (Outbound MT)** | JAX-RS `Client` in `JaxRsCardNotificationService` | Jersey client posts to Sinch MT URL; no retry, no circuit breaker, no timeout configuration |
| **Request-Reply via HTTP RPC (ECount)** | `EDevice.processInquiry()`, `XSearchClientFactory` via Director | Proprietary ECount RPC protocol over HTTP; 120s timeout per `RPCTimeout.properties` |
| **Stored Procedure (Write)** | Spring `StoredProcedure` base class | `CardNotificationLogInsertDAO`, `CardNotificationProfileInsertDAO` |
| **Hibernate ORM (Read)** | `LocalSessionFactoryBean` + `AffiliateServiceImpl` | Reads affiliate program configuration |
| **In-Memory Cache** | Ehcache 3 via JCache/JSR-107 | 30s TTL, heap-only; caches member lookup results and SMS message profile templates |
| **AOP (Cross-cutting)** | AspectJ `@AfterReturning` in `CardNotificationLoggingInterceptor` | Intercepts `cardNotificationInquiry` return to write audit log |
| **Static Application Context** | `CardNotificationUtils.springctxt` static field | Legacy pattern for accessing Spring beans from non-Spring-managed classes; set by `AppContextListener` on servlet context init |
| **XML/JAXB (Inbound)** | `JAXBContext.newInstance(SMS_MO.class)` | Unmarshal URL-decoded XML request payload from SAP/Sinch |

---

## Strategic Status

| Assessment | Detail |
|---|---|
| **Active** | Service is in production use; latest tags are April 2026 (`20260424.110012`, `20260424.110038`, `20260426.041210`) |
| **Migration In Progress** | Boot JAR wrapping has been completed; WAR deployment path retained for legacy VM fallback |
| **Brand/Identity Debt** | Messages still reference "North Lane", "MyPaymentVault", and old Citi Prepaid SAP URLs — indicates incomplete brand migration |
| **Tech Debt Level: High** | Legacy XML Spring config still present in `card-notification-ws`; dual deployment targets; minimal test coverage; string equality bugs; no inbound security |
| **Consolidation Candidate** | The SMS Pull capability is a feature that could be consolidated into a broader notification platform (e.g., alongside push notification services) |
| **SAP/Sinch Dependency** | Service is tightly coupled to SAP Mobile Services / Sinch for SMS gateway; a gateway change would require significant code changes in `JaxRsCardNotificationService` |

---

## Migration Blockers

| Blocker | Description | Risk |
|---|---|---|
| **xplatform library dependency** | `EDevice`, `EMember`, `AppSmsMsgProfile`, `AccountJournal`, `AffiliateService` are all from `com.ecount:xplatform:6.5.4` — a proprietary internal library. All account inquiry logic depends on it. | High — Gen-3 migration would require re-implementing all account data access |
| **Director RPC dependency** | ECount Director at `nam.wirecard.sys:8080` is the single point of access for all account data. No REST/event-driven alternative is evident. | High — blocking until Director is decommissioned or a REST API layer is built |
| **xSearch-XMLRPC member lookup** | `XSearchClientFactory.getClient(XMLRPC_Client)` — legacy XMLRPC protocol. Gen-3 would need a REST-based member lookup. | High |
| **Legacy SQL Server stored procedures** | `dbo.sms_cardnotification_log_insert` and `dbo.sms_cardnotification_profile_insert` are the persistence layer. These are schema objects in the CBase DB that would need to be migrated or replaced. | Medium |
| **Spring XML application context** | `applicationContext.xml` and `dataSourcesContext.xml` in `card-notification-ws` are still the canonical bean definitions for the WAR deployment path. The Boot module creates parallel Java-config equivalents. | Medium — maintainability risk |
| **Static ApplicationContext reference** | `CardNotificationUtils.springctxt` is a static field set by servlet listener. In a Gen-3 reactive/non-servlet environment this pattern breaks. | Medium |
| **No inbound authentication** | Adding OAuth2/JWT authentication to the inbound endpoint would require SAP/Sinch aggregator support and potentially a gateway intermediary | Medium |
| **SAP/Sinch coupling** | SMS MT is sent inline within the same HTTP request thread; if Sinch is slow, the inbound POST from SAP will time out. Decoupling via async queue is needed for Gen-3. | Medium |
