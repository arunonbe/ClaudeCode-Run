# csa_WAPP — Solution Architect View

## 1. Architecture Overview

**csa_WAPP** is a monolithic Java EE web application following the Struts 1 MVC pattern. It is deployed as a single WAR (`ROOT.war`) on Apache Tomcat 8.5 and serves all customer-service agent interactions. The architecture is a classic N-tier web application:

```
┌─────────────────────────────────────────────────────────────────┐
│                         Browser (CSR)                           │
└─────────────────────────────┬───────────────────────────────────┘
                              │ HTTPS (not enforced in-app)
┌─────────────────────────────▼───────────────────────────────────┐
│               Apache Tomcat 8.5 / Servlet Container             │
│                                                                  │
│  Filter Chain:                                                   │
│    Acegi FilterChainProxy  →  ParamFilter  →  PerformanceFilter  │
│    →  UserTimeZoneFilter  →  RecordIdFilter  →  RequestContextFilter│
│                                                                  │
│  Struts 1 ActionServlet (*.do)   DWR Servlet (/dwr/*)           │
│                                                                  │
│  Spring ApplicationContext (15 XML config files loaded at startup)│
│    └── 150+ Action beans, 50+ DAO/SP beans, Helper beans,        │
│        AuditManager, SecurityFilterChain                         │
└──────────────────────────────────────────────────────────────────┘
         │                │                │
         ▼                ▼                ▼
   SQL Server        XML-RPC/Director   REST (CBTS)
   (3 JNDI pools)   (ECount Core)      (Wirecard)
```

---

## 2. API and Request Handling

### Request Routing
- All business requests: `*.do` pattern → `ActionServlet` → action class lookup via `struts-config.xml`
- Ajax/DWR: `/dwr/*` → `DWRServlet` → Java beans (`AdjustmentLookup`, `AvailableBalanceManager`, `InquiryByManager`, `CardHolderProgramValidator`, `Validator`)
- CTI auto-login: `GET /loginctl` → `RingCentralRequest` (unauthenticated, `ROLE_ANONYMOUS`)
- Live-chat login: `GET /livechatloginctl.do` → protected by full filter chain

### Action Class Pattern
All actions extend `CSAAction` (which extends Struts `Action`). The entry point is:
```java
// CSAAction (abstract) delegates to:
public abstract ActionForward executeImpl(ActionMapping mapping, ActionForm form,
    HttpServletRequest request, HttpServletResponse response, CSASessionBean sessionBean);
```
Each concrete action (e.g., `TransactionHistoryDisplayAction`, `ManagementAdjustmentAction`) overrides `executeImpl`.

**Action Interceptors:**
- `AuditActionInterceptor` — pre/post state capture for audited actions
- `AuditSetupActionInterceptor` — sets up audit session context
- `AbstractAuditInterceptor` — base class for audit interceptors

### XDoclet Annotations (generate struts-config.xml)
```java
// TransactionHistoryDisplayAction.java line 35
// @struts.action path="/pages/account/transactionHistoryDisplay" name="transactionHistoryDisplayForm"
//               scope="request" validate="false" input="failure"
```
All ~150 action classes use this pattern; `webdoclet` regenerates `struts-config.xml` during Maven test phase.

### DWR (Direct Web Remoting) Beans
Defined in `WEB-INF/dwr.xml`. Exposed beans:
- `AdjustmentLookup` — look up eligible adjustments by type
- `AvailableBalanceManager` — real-time balance Ajax calls
- `InquiryByManager` — inquiry method lookup
- `CardHolderProgramValidator` — validate card-programme combination
- `Validator` — generic field validation

---

## 3. Security Architecture

### Authentication Flow
```
Browser POST /j_acegi_security_check
    → Acegi AuthenticationProcessingFilter
        → OperatorAuthenticationProcessingFilter.onSuccessfulAuthentication()
            → MinimalUserDetailsServiceImpl (xSecurity)
                → EcountMd5PasswordEncoder.isPasswordValid()
                    → CSAUserCryptUtility.createMD5Hash() [MD5, no salt]
            → UserDomainHome.getActiveUserDomain() → role lookup
            → OperatorManager.fetchOperatorInformation() → Operator object
            → addToSessionForLegacy() → stores role, name, operator ID in HttpSession
            → AUDIT_ROLE cookie set (HttpOnly, Secure via CSAConstants)
```

**Session keys** (from `CSAConstants`):
- `csa_username`, `csa_userrole`, `csa_useroperatorid`, `csa_user_device_operator_id`
- `SESSION_KEY_USERID`, `SESSION_KEY_APPLICATION_ID`

### Authorisation
- URL-level: `objectDefinitionSource` bean in `applicationContext-xsecurity-web.xml` (lines 184-208) — ANT-pattern → role list
- Method-level: AOP `MethodSecurityInterceptor` on `EMember.find()` and `DDAOnlyEMember.findDDAOnly()` (lines 353-373)
- 20+ named roles: `1st Level Call Center Rep`, `2nd Level Call Center Manager`, `Risk`, `ISA`, `PM`, `RM`, `IM`, `Production Support`, `Chargeback`, etc.
- `/ctistart.do` = `ROLE_ANONYMOUS` — publicly accessible (CTI integration)

### Input Validation
- Struts `validation.xml` / `validator-rules.xml` — declarative form validation
- `EcountStrutsValidator` — custom extension
- `InputValidator` — additional input sanity checks
- `ParamFilter` — servlet-level parameter sanitisation (`web.xml` line 65)
- `MultiReadHttpServletRequest` — wraps request to allow body re-reading (for logging)

### Notable Security Gaps
1. **MD5 without salt** (`CSAUserCryptUtility.java` line 14) — all CSA operator passwords
2. **`forceHttps=false`** (`applicationContext-xsecurity-web.xml` line 108) — HTTPS not enforced
3. **SSN in audit state** (`audit.properties` line 48) — PII written to `audit_event` table
4. **DWR 1.1.3** — EOL; known CSRF and XSS vulnerabilities in old DWR versions
5. **jQuery 1.2.3** (`webapp/js/cems/`) — 2008 vintage; numerous XSS CVEs
6. **XStream 1.2** — deserialization CVEs in versions prior to 1.4.18 (pom.xml line 382)
7. **Struts 1** — CVE-2014-0114 (ClassLoader access via ActionForm); no patch available
8. **`ROLE_ANONYMOUS` for CTI** — unauthenticated entry point injects credentials into session

---

## 4. Technical Debt Inventory

| Debt Item | Location | Severity |
|---|---|---|
| MD5 password hashing | `CSAUserCryptUtility.java:14`, `applicationContext-xsecurity-web.xml:149` | Critical |
| Struts 1.3.10 (EOL 2013) | `pom.xml:31`, all `*Action.java` | Critical |
| Spring 2.0.8 (EOL) | `pom.xml:17-18`, all `csa.xml`, `csa-context.xml` | Critical |
| Acegi Security (EOL) | `applicationContext-xsecurity-web.xml`, `OperatorAuthenticationProcessingFilter.java` | Critical |
| DWR 1.1.3 (EOL) | `pom.xml:483`, `WEB-INF/dwr.xml`, `WEB-INF/web.xml:201` | High |
| jQuery 1.2.3 | `webapp/js/cems/jquery-1.2.3.min.js` | High |
| Log4j 1.2.17 | `pom.xml:339` | High |
| XStream 1.2 | `pom.xml:382` | High |
| commons-httpclient 3.0.1 | `pom.xml:390` | High |
| XDoclet code generation | `pom.xml:100-123` | Medium |
| `java.util.Hashtable` as cache | `csa.xml` lines 776-788 | Medium |
| Duplicate bean `ecountCoreJdbcTemplate` | `spring-jdbc.xml:9`, `csa-context.xml:977` | Medium |
| Federal holiday list frozen 2006 | `csa.xml` `distACHCalendar` | Medium |
| `@Deprecated` fields on `ClaimablePayment` | `ClaimablePayment.java:33-46` | Low |
| `testFailureIgnore=true` | `pom.xml:169` | High |
| Hardcoded `D:\c-base\` paths | `csa.xml:13-17`, `web.xml:43` | High |
| Missing `@SuppressWarnings` generics cast | `ClaimCodeRedemptionInfoRetrieveDao.java:39` | Low |
| Acegi `FilterToBeanProxy` | `web.xml:57` | Medium |
| Prototype.js (EOL) | `webapp/js/prototype.js` | Medium |
| `commons-beanutils 1.7.0` (pre-CVE-2019 patch) | `pom.xml:317` | Medium |
| `Cp1252` source encoding | `pom.xml:33` | Low |

---

## 5. Generation 3 Readiness Assessment

Gen3 in the Onbe context means: Spring Boot 3.x / Jakarta EE 10, REST APIs, containerised (Docker/K8s), cloud-native config, modern security (Spring Security 6, OAuth2/OIDC), event-driven where appropriate.

| Dimension | Current State | Gap to Gen3 |
|---|---|---|
| Framework | Struts 1 + Spring 2 | Must rewrite to Spring MVC / Spring Boot 3 |
| Security | Acegi + MD5 | Must implement Spring Security 6 + BCrypt/Argon2 |
| Config | Property files on `D:\` | Must externalise to env vars / Secrets Manager |
| Deployment | WAR → Tomcat Windows service | Must containerise; replace JNDI with Spring Boot datasource config |
| APIs | No REST; only Struts `*.do` + DWR | Must expose REST endpoints for all agent operations |
| Observability | Log4j 1.x | Must adopt SLF4J + Logback/Log4j2 + Micrometer/OpenTelemetry |
| Testing | 18 tests, failures ignored | Must achieve meaningful coverage (>60%) with enforced quality gate |
| Data access | `JdbcDaoSupport` + stored procs | Could migrate to Spring Data JDBC / JPA where schema is owned |
| Session state | `HttpSession` (distributed via `<distributable/>`) | Must move to stateless JWT or externalised session (Redis) |
| Build | Maven + XDoclet code gen | Drop XDoclet; use standard Spring Boot starters |

---

## 6. Code-Level Risks

| Risk | Class / File | Line | Description |
|---|---|---|---|
| SSN in audit log | `audit.properties` | 48 | `submitCIP.state` explicitly names SSN sub-fields |
| No HTTPS enforcement | `applicationContext-xsecurity-web.xml` | 108 | `<value>false</value>` for `forceHttps` |
| MD5 password encoder | `CSAUserCryptUtility.java` | 14 | `MD5` from `qpl.util` — no salt, broken |
| ROLE_ANONYMOUS CTI | `applicationContext-xsecurity-web.xml` | 189 | `/ctistart.do=ROLE_ANONYMOUS` |
| RingCentral session invalidation | `RingCentralRequest.java` | 74 | `request.getSession().invalidate()` followed by `getSession(true)` — session fixation risk if attacker can guess new session ID before redirect |
| Duplicate Spring bean definition | `csa-context.xml` | 977, `spring-jdbc.xml` | 9 — `ecountCoreJdbcTemplate` defined twice; last-wins behaviour depends on context load order |
| BIN hardcoded | `CardMaskUtils.java` | 149 | `galileoAccountCheck = "514977"` hardcoded Galileo BIN |
| Logging sanitisation | `PerformanceFilter.java` | 61 | `LogUtil.sanitizeForLog()` applied to URL but full request body not sanitised |
| CBTS credentials as constructor args | `csa-context.xml` | 785-786 | Username/password injected from property file; no secrets vault integration |
| `singleton="true"` in DTD-based config | `csa-context.xml` | 701 | Pre-Spring 2.0 `singleton` attribute usage; deprecated in Spring 2.0+ |
| Typo in constant | `CSAConstants.java` | 135 | `Management_Adjustment = "Management Ajustment"` — misspelling propagated in display |
| Typo in constant | `CSAConstants.java` | 146 | `PARTIAL_TRANSFER = "partail"` — misspelling; may break filter comparisons |
| `Hashtable` cache no TTL | `csa.xml` | 776-788 | `authenticationStrategiesCache`, `customerFeeValueCache` etc. are `Hashtable` singletons with no eviction or TTL |
| `commons-fileupload 1.4` | `pom.xml` | 308 | CVE-2023-24998 (unlimited upload count DoS) fixed in 1.5; 1.4 remains exposed |

---

## 7. Observed Architecture Violations

1. **Business logic in Action classes** — `ManagementAdjustmentAction`, `RiskFixedTransactionManager` etc. contain business decision logic that should be in a service/domain layer, not the presentation tier.
2. **Static utility methods for security** — `SanctionFieldHelper.isDisable()` is a static method modifying static state (`sanctionFieldStateMap` is `static`), making it non-thread-safe if reloaded.
3. **Session as data bus** — `CSASessionBean` and numerous `session.setAttribute()` calls spread throughout all action classes; no clear contract for session lifecycle.
4. **XDoclet reverse dependency** — the presentation tier (actions) drives routing configuration generation, inverting the normal configuration-drives-code relationship.
5. **In-memory cache leaks** — `java.util.Hashtable` singletons hold programme/card profile data with no clear refresh or eviction; stale data will accumulate over the application lifetime.
6. **Multiple Spring context files with overlapping beans** — `csa.xml`, `csa-context.xml`, `spring-jdbc.xml`, `accountContext.xml` all define related beans; `BlockBeneficiarieDao`/`BlockBeneficiarieSP` defined in **both** `csa.xml` (lines 1839-1851) and `csa-context.xml` (lines 871-882).
