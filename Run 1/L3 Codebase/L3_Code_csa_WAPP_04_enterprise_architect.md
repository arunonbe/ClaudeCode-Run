# csa_WAPP — Enterprise Architect View

## 1. Platform Generation

**csa_WAPP is a Generation 1 / Legacy platform.** It was built on the eCount / C-Base prepaid processing stack that predates Onbe's current architecture. Evidence:

- Struts 1.3.10 MVC framework (released 2008, last patched 2013)
- Spring 2.0.8 IoC container (released 2008; current: 6.x)
- Acegi Security framework (pre-dates Spring Security; superseded by Spring Security 3 in 2009)
- XDoclet code generation for Struts config (circa 2003-era toolchain)
- DWR 1.1.3 for Ajax callbacks (2007 vintage)
- JNDI-managed JDBC connections to SQL Server via Tomcat
- Java 8, Tomcat 8.5, Windows-only deployment
- Proprietary XML-RPC transport layer (`com.ecount.core.client`)
- C-Base/ECount Core as the underlying card processing engine

The application carries `com.citi.prepaid` groupId artefacts (`pom.xml` parent, `ecountCoreClient`, `directorClient`), indicating it originated during or following Citibank Prepaid ownership.

---

## 2. Domain and Bounded Context

**Domain:** Prepaid Card Customer Service Operations  
**Bounded Context:** Agent/Operator Servicing — the internal tooling layer that bridges cardholder-facing events (payments, adjustments, disputes) to the core processing platform.

This application does **not** expose APIs to external parties. It is a browser-rendered internal application exclusively. The integration surface is:

```
CSR Browser  ──►  csa_WAPP (this repo)  ──►  ECount Core (XML-RPC/Director)
                                         ──►  SQL Server (CbaseappDataSource, EcountCoreDataSource, JobSvcDataSource)
                                         ──►  CBTS REST (cross-border transfers)
                                         ──►  External services (Comment, Message Center, Affiliate, Symbol, xSecurity)
```

---

## 3. Role in the Onbe Application Portfolio

| Capability | csa_WAPP serves | Complementary systems |
|---|---|---|
| Cardholder servicing | Internal agents (CSRs, risk, programme managers) | Cardholder self-service portal (separate web app) |
| Payment orchestration | Agent-initiated ACH, check, eCard, allotment, CBTS | Payment rail services (NACHA, FDR, Wirecard) |
| Risk management | Agent-side risk adjustment, chargeback, fraud queue | Fraud detection engine (upstream) |
| KYC/CIP | CIP submission UI | Identity verification services (downstream) |
| Claimable Choice | Agent view of token payments | Claimable Choice issuance platform (upstream) |
| Comment/escalation | Agent notes, supervisor escalation | CRM (none visible in this repo) |

---

## 4. Key Dependencies

### Internal (Onbe/eCount Libraries — JAR dependencies)

| Dependency | Version | Purpose |
|---|---|---|
| `com.ecount:xPlatform` | 7.0.27 | Core platform utilities, `EMember`, device/member abstractions |
| `com.ecount.service.xSecurity:xSecurity-web/impl/common` | 2016.1.1 | Operator authentication, privilege management, password manager |
| `com.citi.prepaid.service.core.client:ecountCoreClient` | 2014.2.1 | XML-RPC client to ECount Core |
| `com.citi.prepaid.service.core.client:directorClient` | 2014.2.1 | Director service client (service discovery) |
| `com.citi.prepaid.service.core:xmlrpc` | 1.0.5 | XML-RPC transport |
| `com.ecount.service.xSearch-New:xSearch-impl` | 2014.1.1 | Member/device search |
| `com.ecount.service.brandedcurrency:brandedCurrency-common/impl` | 2016.1.1 | Gift certificate / claimable choice branded currency |
| `com.ecount.one.service.affiliate:xAffiliateService` | 2019.1.3 | Affiliate/programme configuration |
| `com.ecount.utils:i18n-utils` | 1.0.4 | Internationalisation utilities |
| `com.ecount.service.message:message-common` | 1.0.1 | Message centre client |
| `com.ecount.services:comment` | 2019.1.4 | Comment service client |
| `com.ecount.service.symbolservice:symbol-svc` | 1.0.0 | Currency symbol service |
| `com.ecount.spring-dbctx:spring-dbctx-container` | 1.0.4 | Spring DB context container |
| `com.ecount.service.core.ecountcore:common` | 2014.1.1 | ECount Core shared domain |

### External / Third-Party Libraries

| Library | Version | Risk |
|---|---|---|
| Struts 1 (`struts-core`, `struts-el`, `struts-tiles`, `struts-taglib`, `struts-extras`) | 1.3.10 | **EOL — multiple CVEs; no upstream patches** |
| Spring Framework | 2.0.8 | **EOL — 15+ years old** |
| Acegi Security | (via xSecurity 2016.1.1) | **EOL — replaced by Spring Security** |
| DWR | 1.1.3 | **EOL — 2007** |
| Apache Axis (SOAP) | 1.3 | EOL |
| XStream | 1.2 | Multiple deserialization CVEs in older versions |
| Log4j | 1.2.17 | EOL; multiple known CVEs |
| commons-fileupload | 1.4 | Check CVE-2023-24998 (DoS via multipart) |
| commons-httpclient | 3.0.1 | **EOL — replaced by HttpComponents** |
| commons-beanutils | 1.7.0 | Old; CVE-2019-10086 in 1.9.3 and below |
| iText | 5.0.5 | AGPL-licensed; old; PDF generation |
| EHCache | 1.3.0 | EOL — replaced by Ehcache 3 |
| jQuery | 1.2.3 (CEMS) | **Extremely old; numerous known XSS/prototype pollution CVEs** |
| Prototype.js | (webapp/js/) | EOL; no security support |
| Xerces | 2.8.1 | Old XML parser |
| displaytag | 1.2 | EOL |

---

## 5. Architectural Patterns

| Pattern | Implementation |
|---|---|
| MVC (Model 1.5) | Struts 1 `ActionServlet` + `ActionForm` + JSP Tiles |
| Service Delegate | `CSAMemberDelegateImpl`, `CSADeviceDelegateImpl` wrap core platform calls |
| DAO / Repository | `JdbcDaoSupport` subclasses for each entity; stored-proc wrappers |
| Command pattern | `EcardCredit`, `EcardDebit`, `CollectionsChargeOff`, `FrontlineChargeback` — all implement transaction commands wired via Spring |
| AOP Security Proxy | `eMember` bean is a `ProxyFactoryBean` intercepting `EMember.find()` |
| Template Method | `CSAAction.executeImpl()` is the abstract method; all action classes override it |
| Helper pattern | `BaseHelperImpl` → `MemberHelper`, `DeviceHelper`, `PaymentHelper`, `FeeHelper`, `EmbossHelper` etc. (Spring prototype/singleton beans) |
| Filter chain | 6 servlet filters: Acegi security, ParamFilter, RecordIdFilter, UserTimeZoneFilter, PerformanceFilter, RequestContextFilter |
| Thread-local state | `CSAThreadLocalImpl` carries per-request context |
| In-memory cache | `java.util.Hashtable` singletons for auth strategies, fee values, card profiles — no eviction |
| XDoclet-driven config | Struts action annotations generate `struts-config.xml` at build time |

---

## 6. Integration Architecture

### Synchronous Integrations

| Integration | Protocol | Library |
|---|---|---|
| ECount Core (card/member/transfer) | XML-RPC over HTTP | `com.ecount.core.client` / `xmlrpc` |
| Director (service discovery) | XML-RPC | `directorClient` |
| CBTS (cross-border transfers) | REST/HTTP | `CBTSClient` (Wirecard xclient) |
| SQL Server (3 data sources) | JDBC | JNDI, commons-dbcp 1.2.1 |
| Comment Service | Spring bean / internal | `comment-2019.1.4.jar` |
| Affiliate Service | Spring bean / internal | `xAffiliateService-2019.1.3.jar` |
| Message Center | Spring bean / internal | `message-common-1.0.1.jar` |

### Inbound Integrations

| Integration | Entry Point | Notes |
|---|---|---|
| RingCentral CTI | `GET /loginctl.do` → `RingCentralRequest` | Auto-login with card number param |
| Live Chat | `LiveChatRingCentralRequest` | AES-encrypted session handoff |
| Browser (CSR) | `POST *.do` → Struts | All form submissions |
| DWR Ajax | `POST /dwr/*` → DWR servlet | Balance lookup, adjustment lookup, validator |

---

## 7. Status Assessment

| Dimension | Rating | Notes |
|---|---|---|
| Business fitness | High | Fully functional; actively used by CS operations |
| Technical currency | Very Low | Framework stack 15+ years behind current; no active upstream security support |
| Security posture | Low | MD5 passwords, no HTTPS enforcement, EOL frameworks with unpatched CVEs |
| Maintainability | Low | XDoclet code generation, Struts 1, 550+ Java source files, no modern IoC features |
| Testability | Low | 18 test files for 550+ source files; `testFailureIgnore=true`; GitLab skips tests entirely |
| Cloud readiness | Very Low | Hardcoded Windows `D:\` paths, no Docker/Kubernetes support, no env-var config |
| Observability | Low | Log4j 1.x, no APM, no distributed tracing, no metrics endpoint |
| Compliance readiness | Medium | PAN masking and audit logging present; MD5 passwords and SSN in audit log are gaps |

---

## 8. Blockers for Modernisation

| Blocker | Impact |
|---|---|
| XDoclet generates Struts config | Cannot migrate to annotation-based routing without rewriting all 150+ action classes |
| Struts 1 `ActionForm` / `ActionServlet` central to entire MVC | No incremental migration path; requires full rewrite to Spring MVC / Jakarta EE |
| Spring 2.0 API used throughout (no namespaces, DTD-based XML config) | Upgrade to Spring 5/6 requires extensive XML refactoring |
| Acegi Security API (`org.acegisecurity.*`) throughout filter chain | Must be replaced by Spring Security (complete rewrite of auth/authz layer) |
| `com.ecount.core.client` XML-RPC dependency | If core platform exposes REST/gRPC, client layer must be replaced; no abstraction |
| Hardcoded `D:\c-base\` paths | Cannot containerise without OS-level path mapping or full config externalisation |
| MD5 password hashing in `CSAUserCryptUtility` and `EcountMd5PasswordEncoder` | Requires password migration and new hashing scheme (BCrypt/Argon2) |
| Java 8 language level | Blocks use of Java 9+ module system, records, sealed classes, virtual threads |
| `commons-dbcp 1.2.1` / no HikariCP | Connection pool tuning limited; upgrade needed |
| CBTS client hardcoded credentials | Must move to secrets management (Vault, Azure Key Vault) before any cloud migration |
