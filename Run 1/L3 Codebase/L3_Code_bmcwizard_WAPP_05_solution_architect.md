# bmcwizard_WAPP — Solution Architect View

## Technical Architecture

### Runtime Stack
- **Java 8** (OpenJDK/Oracle JDK)
- **Apache Tomcat 8.5** (Windows, service-managed)
- **Apache Struts 1.3.8** MVC (servlet: `org.apache.struts.action.ActionServlet`, mapped to `*.do`)
- **Spring Framework 2.0.3** (XML-driven IoC container, Spring JDBC, no Spring MVC)
- **Acegi Security 1.x** (predecessor of Spring Security, filter chain proxy pattern)
- **Hibernate 3** (annotation-based session factory, used only for xAffiliateService entities)
- **EhCache 1.x** (`SingletonEhCacheProvider`)
- **Apache Struts Tiles** (page layout/templating)
- **Log4j 1.2.17** (commons-logging facade)

### Package Structure (source code)
```
com.cbase.web.product.workbench.*        — Infrastructure/filter classes (workbench-owned)
  ApplicationControllerLifecycleManager  — App startup/shutdown lifecycle
  CachePreventionFilter                  — HTTP cache-control headers on all responses
  GlobalRequestIdFilter                  — UUID-based request correlation
  JobSchedulerConfigurer                 — Job scheduler initialization
  MultiReadHttpServletRequest            — Request body re-read wrapper
  ParamFilter                            — Input validation filter (CVE-2014-0114)
  PerformanceLogLifecycleManager         — [commented out]
  SystemLogLifecycleManager              — [commented out]
  TokenBasedRememberMeServices           — Custom Acegi remember-me cookie handler
  databean.*                             — Config label, symbol, promotion data beans
  error.*                                — Error codes and action status enums
  filler.symbols.*                       — Symbol group loading utilities
  helpers.*                              — DateHelper, LabelValueBean
  listener.*                             — AppContextListener (Spring context saver)

com.ecount.bridge.*                      — Main Wizard business logic (workbench-owned)
  audit.*                                — AuditTrailImpl/DAO/StoredProc
  business.*                             — Business Impl and Interface classes
  business.helper.*                      — ~50 helper classes for each config section
  business.czsetup.*                     — CZ Setup business logic
  business.dto.*                         — Data Transfer Objects
  business.enrollment.*                  — Enrollment Setup
  business.globalsetup.*                 — VAT, Risk Rules
  dao.*                                  — ~45 DAO classes
  dao.czsetup.*                          — CZ Setup DAOs
  dao.ecap.*                             — eCap DAOs
  dao.login.*                            — User password DAO
  dao.notification.*                     — Notification DAOs
  dao.opsetup.*                          — MPV/OP Setup DAOs
  web.cache.*                            — EhCache wrappers
```

### Request Processing Flow

```
HTTP *.do request
  → GlobalRequestIdFilter (UUID in MDC)
  → Acegi FilterChainProxy
      → HttpSessionContextIntegrationFilter
      → [AuthenticationProcessingFilter for /j_acegi_security_check]
      → RememberMeProcessingFilter
      → AnonymousProcessingFilter
      → ExceptionTranslationFilter
      → FilterSecurityInterceptor (role-based access)
  → CachePreventionFilter (no-cache headers)
  → ParamFilter (Unicode/octal input sanitization, multipart handling)
  → ResponseOverrideFilter (displaytag export)
  → Struts ActionServlet
      → Action class (com.ecount.bridge.struts.action.*)
          → Business Impl (e.g., ProgramProfileImpl)
              → Helper classes
              → xPlatform Profile Classes (FDRCardProfileClass etc.)
                  → Stored Procs → SQL Server (CbaseappDataSource / EcountCoreDataSource)
              → DAO → StoredProc → SQL Server
          → AuditTrailImpl → AuditTrailDAO → AuditTrailStoredProc → CbaseappDataSource
      → Struts Tiles → JSP view
```

## API Surface

**This application has no external API surface.** There are no REST endpoints, SOAP services, or message-based interfaces. All interaction is:

- **Browser-based HTML forms** submitted to `*.do` URLs via HTTP GET/POST.
- **Struts Action classes** handle form processing (xdoclet-generated `struts-config.xml` defines the action mappings).

Blocked HTTP methods via `web.xml` security-constraint: DELETE, SEARCH, COPY, MOVE, PROPFIND, PROPPATCH, MKCOL, LOCK, UNLOCK, TRACE, PUT, TRACK, LINK, UNLINK. Only GET and POST are operational.

The application consumes external services:
- **httpCryptoService** HTTP endpoints (via `HTTPCryptoServiceClient` — multiple PGP servers)
- **Job Scheduler** XML-RPC endpoint (via `JobServiceHelper`)
- **xSecurity / xAffiliateService** as JAR-embedded service calls to the same SQL Server databases

## Security Posture

### Authentication
- **Mechanism:** Acegi Security `VelocityCheckingAuthenticationProcessingFilter` at `/j_acegi_security_check`
- **Password encoding:** `EcountMd5PasswordEncoder` (MD5, application_id=8) — **cryptographically weak, no evidence of salting**
- **Remember-me:** Custom `TokenBasedRememberMeServices` — MD5-HMAC cookie (`ACEGI_SECURITY_HASHED_REMEMBER_ME_COOKIE`), 30-minute token validity in Spring config but cookie set to **5-year max age** (line 265 of `TokenBasedRememberMeServices`). `alwaysRemember=true` means all sessions get a persistent cookie.
- **Session timeout:** 60 minutes (`web.xml` session-config).
- **Session invalidation on login:** `invalidateSessionOnSuccessfulAuthentication=true` — protects against session fixation.
- **In-memory test credentials:** `applicationContext-xsecurity-web.xml` line 241–246 defines `memoryAuthenticationDao` with `user=password,USER`. This bean is defined but **not wired into the authenticationManager providers list** (providers list uses only `minimalDaoAuthenticationProvider` + `anonymousAuthenticationProvider` + `rememberMeAuthenticationProvider`). The in-memory credentials are dormant but their presence is a code quality risk.

### Authorization
- **Pattern:** Acegi `FilterSecurityInterceptor` with `AffirmativeBased` decision manager using `RoleVoter` + `AuthenticatedVoter`.
- **URL-to-role mappings:** Defined in `objectDefinitionSource` bean (referenced in `applicationContext-xsecurity-thebridge-web-dao.xml`, not directly visible in scanned files).
- **Role management:** `UserRoleSettingImpl` and `CZRoleSetupImpl` manage role assignments via stored procs.

### Input Validation
- **`ParamFilter`** (`com.cbase.web.product.workbench.ParamFilter`): Validates all request parameters and cookies against Unicode escape (`\\u[A-Fa-f0-9]{4}`) and octal (`\\([0-7]{1,4})`) patterns. Redirects to `systemunavailabledisplay.jsp` on match. This is a CVE-2014-0114 mitigation for Struts 1 ClassLoader manipulation.
- **Struts Validator:** `validation.xml` and `validation-special-characters.xml` provide declarative field-level validations.
- **MultiReadHttpServletRequest:** Wraps requests to allow multiple reads of the body — relevant when ParamFilter needs to inspect multipart requests.

### Transport Security
- **HTTPS enforced at infrastructure level** (URLs in CI reference `https://`), but `forceHttps=false` in `authenticationEntryPoint` means the application itself will not redirect HTTP to HTTPS.
- Remember-me cookie sets `Secure; HttpOnly` attributes manually via `Set-Cookie` response header in `makeValidCookie()` (lines 268–269). However, the standard `Cookie.setSecure()` is not called — only the raw header string approach is used, which bypasses the servlet API.

### HTTP Security Headers
- **`CachePreventionFilter`** sets anti-caching headers on all responses (no `Cache-Control`, `Pragma: no-cache` etc.) — prevents caching of sensitive config pages.
- No evidence of `X-Frame-Options`, `Content-Security-Policy`, or `X-Content-Type-Options` headers.

## Technical Debt

Severity ratings: Critical (C), High (H), Medium (M), Low (L).

| Item | Severity | Evidence |
|---|---|---|
| **Java 8 (EOL for public updates)** | H | `pom.xml` `java.version=1.8`; Java 8 public security updates ended Jan 2019 |
| **Log4j 1.2.17 (EOL 2015)** | H | `pom.xml` `log4j.version=1.2.17`; multiple CVEs (CVE-2022-23302, CVE-2022-23305) |
| **Spring 2.0.3 (EOL ~2013)** | H | `pom.xml` `spring-verison=2.0.3` (note typo in property name) |
| **Acegi Security (unmaintained ~2008)** | H | `applicationContext-xsecurity-web.xml`; replaced by Spring Security since 2008 |
| **Struts 1.3.8 (EOL 2013)** | H | `pom.xml`; multiple unpatched CVEs beyond CVE-2014-0114 |
| **MD5 password hashing** | C | `EcountMd5PasswordEncoder` in `applicationContext-xsecurity-web.xml` line 177 |
| **5-year remember-me cookie vs 30-min session** | H | `TokenBasedRememberMeServices` line 265: `cookie.setMaxAge(60 * 60 * 24 * 365 * 5)` while `tokenValiditySeconds=1800` |
| **`alwaysRemember=true`** | H | All sessions get persistent cookies — no opt-out |
| **In-memory credentials bean defined** | M | `memoryAuthenticationDao` bean with `user=password,USER` in xsecurity-web.xml; not active but present |
| **Hibernate 3 (EOL)** | H | `org.hibernate.cfg.AnnotationConfiguration` API (Hibernate 3 only); Hibernate 3 EOL |
| **xdoclet code generation** | M | `maven-antrun-plugin` generates Struts XML at build time; xdoclet unsupported |
| **Source encoding Cp1252** | M | `pom.xml` line 93: `project.build.sourceEncoding=Cp1252`; should be UTF-8 |
| **Windows-only paths** | H | `D:\c-base\...` in multiple config files; prevents containerization |
| **`spring-verison` typo** | L | `pom.xml` line 98: property name has typo; no functional impact but indicates low maintenance |
| **Tests skipped in GitLab CI** | H | `.gitlab-ci.yml`: `-Dmaven.test.skip=true` hardcoded for all phases |
| **No HTTPS enforcement at app layer** | H | `forceHttps=false` in `authenticationEntryPoint` |
| **No X-Frame-Options / CSP headers** | M | No evidence of clickjacking protection headers |
| **Audit trail missing before-value** | M | `AuditTrailDataBean` only captures new value; see field definitions |
| **Static `RequestContextFactory.getAppContext()`** — Service locator anti-pattern | M | Used in `LaunchProgramImpl`, `AuditTrailImpl`, `EscheatmentConfigImpl`, etc. — bypasses DI |
| **Raw type usage** | L | Multiple `@SuppressWarnings("unchecked")` and raw `Dictionary`/`List`/`Enumeration` types throughout |
| **No structured logging** | M | All logging via `LOG.error(...)` with string concatenation; no JSON/MDC-structured output |
| **Dual CI systems** | M | Both GitLab and GitHub Actions active; risk of divergence |
| **`Cp1252` source encoding** | M | Non-portable; any non-ASCII characters in source will be misinterpreted on non-Windows systems |
| **Jetty 6.0.2 for local dev** | L | Extremely old; uses deprecated configuration model |

## Gen-3 Migration Requirements

The following capabilities and decisions are required to replace this application with a Gen-3 equivalent:

### 1. API Design
- Design REST API covering all wizard configuration domains: program profile, card settings, fees, funding controls, embossing, escheatment, regulatory limits, notifications, CZ setup, MPV setup, enrollment, audit trail.
- All responses must be JSON. No HTML-rendering endpoints in the Gen-3 API layer.
- API must be stateless (JWT / OAuth2) — no server-side session state.

### 2. Stored Procedure Migration
- Catalog all ~100+ stored procedures in `CbaseappDataSource` and `EcountCoreDataSource` that this application calls.
- Determine ownership of each proc: are they shared with other applications (BMC, cardholder portal, etc.)?
- Decision required: migrate procs to JPA/ORM or to new stored procedures in a migrated DB schema.

### 3. xPlatform Profile API Replacement
- `xPlatform:7.0.27` encapsulates all profile domain logic (`FDRCardProfileClass`, `EMEAProfileClass`, `AppGlobalEscheatmentProfileClass`, etc.). These must be replaced with explicit service-layer logic or a new internal API.
- This is the largest single migration risk. Without xPlatform source code or documentation, migration requires full behavioral analysis.

### 4. Authentication & Authorization
- Replace Acegi/MD5 with a standards-based identity provider (Okta, Azure AD, or internal IdP).
- Role-based access must be migrated to the new RBAC model.
- Eliminate remember-me cookie in favor of proper token refresh with short-lived JWTs.

### 5. Database Modernization
- Upgrade SQL Server JDBC driver (`sqljdbc:1.1` → current Microsoft JDBC driver).
- Evaluate whether all four databases (CbaseappDataSource, NotificationServiceDataSource, JobSvcDataSource, EcountCoreDataSource) remain separate in Gen-3 or are consolidated.

### 6. Notification Service
- Email/SMS notification templates and event configuration currently managed directly via stored procs into the notification DB. Gen-3 should use the canonical notification microservice API, not direct DB access.

### 7. Feature Parity Checklist (non-exhaustive)
Every wizard section must be mapped to Gen-3 API endpoints:
- [ ] Program Dashboard (search, type selection)
- [ ] Program Profile (all sub-sections: features, regulatory, PGP, emboss, alerts, labels)
- [ ] Card Settings (FDR Domestic, FDR DDA, EMEA profiles, access levels, card purge, dormancy)
- [ ] Fees (tiers, grace, credit periods, miscellaneous, symbols)
- [ ] Fee Credit Groups
- [ ] Funding Controls (ACH, precheck, payment reversal, available cash, rewards, refill, balance sweep, account maintenance, PIN, access check)
- [ ] Embossing Profile (all delivery/plastic/TPIN config)
- [ ] Global Regulatory Limits (AGML, CBL, LML per country/currency)
- [ ] Escheatment Config (per state/channel)
- [ ] Promotion Settings (ACH-OUT, allotment, redeemable payment, access check, email notification, PPD group, management)
- [ ] Configuration screen (all feature flags)
- [ ] User/Role Management
- [ ] CZ Setup (configuration, hierarchy, role setup, user setup, inventory control, instant issue, reports)
- [ ] MPV/OP Setup (fees, T&C, graphics, content approval)
- [ ] Notification Setup (email, SMS)
- [ ] Enrollment Setup
- [ ] eCap Setup
- [ ] Claimable Choice Setup
- [ ] CSA / Partner Detail Setup
- [ ] Program Launch (status management, summary)
- [ ] Audit Trail

### 8. Containerization Prerequisites
- Eliminate all Windows filesystem dependencies (`D:\c-base\...` paths).
- Move to externalized config via environment variables or a config service (Vault, Kubernetes ConfigMaps).
- Change source encoding to UTF-8.
- Package as Docker image, not Windows WAR.

## Code-Level Risks

1. **Service locator anti-pattern** — `RequestContextFactory.getAppContext().getBean(...)` is used in `LaunchProgramImpl` (lines 104–108, 121–126, 142–147), `AuditTrailImpl` (line 31–32), and other business classes. This makes unit testing difficult (requires full Spring context) and creates hidden dependencies.

2. **TokenBasedRememberMeServices cookie max-age** — Line 265: `cookie.setMaxAge(60 * 60 * 24 * 365 * 5)` sets a 5-year cookie while `tokenValiditySeconds=1800` (30 min). The cookie outlives the valid token by a factor of ~87,000. A stolen cookie remains on the client long after it is cryptographically invalid, but still presents an attractive target.

3. **`alwaysRemember=true` in rememberMeServices** — Every user gets a persistent remember-me cookie regardless of preference (`TokenBasedRememberMeServices.rememberMeRequested()` always returns true). This is a security policy decision that should be reviewed.

4. **MD5 remember-me token** — The token signature is `MD5(username:expiry:password:key)`. MD5 is collision-vulnerable. If password hash is leaked (from DB), an attacker can forge valid cookies.

5. **No HTTPS redirect** — `authenticationEntryPoint` has `forceHttps=false`. If a user accidentally browses via HTTP, credentials could be transmitted in clear text.

6. **Deprecated fields suppression via static global flag** — `BridgeGlobalConstants.hideDeprecatedFields` is a static field read from properties at startup. It is checked in `LaunchProgramImpl.highlightChanges()` and `retrieveDormancyFeeDetails()`. If this flag changes without a restart, behavior is undefined (static field, set once). The flag's value in production affects which regulatory fields are visible to operators — an error here could hide mandatory compliance fields.

7. **`ProfileAuditor.validateDBSave()` logs but does not block** — After a profile save, this auditor compares in-memory label values against the DB (lines 28–58). Discrepancies are only logged at ERROR level; the save is never rolled back. This means silent data divergence can occur if the save partially fails.

8. **Raw `@SuppressWarnings("unchecked")` on core business methods** — Methods like `LaunchProgramImpl.retrieve()`, `retrieveBulkPromoSummary()`, `retrieveCardSummary()`, `GlobalRegulatoryLimitImpl.retrieveGlobalRegulatoryLimitData()` all suppress unchecked warnings. At runtime, any type mismatch in the stored proc result maps will throw `ClassCastException`, which in this codebase would propagate as an unhandled exception.

9. **EhCache disk overflow to `java.io.tmpdir`** — `ehcache.xml` configures `countryNamesCache` with `overflowToDisk=true`. On a shared Windows server, `java.io.tmpdir` may be world-readable or cleared unexpectedly. The data (country names) is not sensitive, but the pattern is a risk in general.

10. **Jetty 6.0.2 for development** — The local development server is 18+ years old. Behavior differences between Jetty 6 and Tomcat 8.5 can mask bugs (e.g., servlet spec compliance, JNDI behavior, connection handling).

11. **`Cp1252` source encoding in `pom.xml`** — Any Java source file containing non-ASCII characters (e.g., in string literals, comments) will be misread on a Linux build agent. The GitHub Actions CI uses Linux runners for CodeQL; source encoding mismatch could cause compilation warnings or subtle errors.

12. **xdoclet at `generate-sources` phase** — The `maven-antrun-plugin` execution runs xdoclet to regenerate `struts-config.xml` and validation XML at every build. If xdoclet fails silently or produces stale output, the deployed Struts config may not match the Java source. This coupling makes debugging action-mapping issues difficult.
