# clientzone_WAPP — Solution Architect View

## Technical Architecture

### Stack Summary

| Layer | Technology | Version | Status |
|---|---|---|---|
| Frontend | JSP + Struts Tag Libraries + Apache Tiles | Struts 1.3.10 / Tiles 1.x | EOL |
| MVC Controller | Apache Struts 1 ActionServlet | 1.3.10 | EOL |
| IoC / DI | Spring Framework | 2.0.8 | EOL |
| Security | Acegi Security (pre-Spring Security) | (via xSecurity 2016.1.1) | EOL |
| ORM / Persistence | Spring JDBC (`JdbcTemplate`) + stored procedures | N/A | Active |
| Database | Microsoft SQL Server | (JDBC driver 6.1.0.jre8) | Active (driver EOL) |
| App Server | Apache Tomcat 8.5 | 8.5.x | EOL (March 2024) |
| JDK | Java SE 8 | 1.8 | Oracle: paid-support only |
| Logging | Log4j 1.2.17 + SLF4J 1.7.32 | 1.2.17 | EOL |
| XML / Serialisation | XStream 1.4.12, JAXB 2.1.12, Jackson 1.9.2 | Old | XStream 1.4.12 has known CVEs |
| Auth (modern) | MSAL4J (Azure AD) | 1.14.3 | Active |
| HTTP client | Raw `java.net.HttpURLConnection` | N/A | No timeout config |
| Caching | EhCache | (via `ehCache-ytd.xml`) | Active |
| Build | Maven | 3.x (wrapper) | Active |

### Package Structure

```
com.cbase.business.clientZone/     — Constants (ClientZoneConstants, NavigateConstants, UIConstants, BasicViewConstats)
com.cbase.business.common/         — Domain value objects (CardInfo, CardHolderInfo, PatriotActInfo, OrderInfo, etc.)
com.cbase.business.util/           — Utilities (EncryptionUtil, ClientZonePasswordUtil, MaskHelper, LogUtil, RoleUtil, SsoUserUtil, TreeUtil, CountryUtil)
com.ecount.one/                    — Application context (EcountContext, SessionConstants)
com.ecount.one.dto/                — DTOs (DepositInfoDTO, InstantIssueCardDetailDTO)
com.ecount.one.struts/             — Struts framework extensions (EcountChannelFactorySet, PostLoginDirectorImpl)
com.ecount.one.struts.action/      — Base action classes (ListAction, HttpSessionHelper, HttpServletRequestHelper, ValidationHelper, SmotsUrlConfigurer)
com.ecount.one.struts.action.administration/   — Admin Struts actions (user, program, inventory, security, cardholder)
com.ecount.one.struts.action.cardBalanceDebit/ — Balance debit actions
com.ecount.one.struts.action.cardholder/       — Cardholder actions
com.ecount.one.struts.action.help/             — Help proxy actions
com.ecount.one.struts.action.helpers/          — Business helper classes (100+ classes)
com.ecount.one.struts.action.home/             — Home/dashboard actions
com.ecount.one.struts.action.instantIssue/     — Instant issue actions (including bulk load)
com.ecount.one.struts.action.login/            — Login/authentication actions
com.ecount.one.struts.action.messageHome/      — Message home actions
com.ecount.one.struts.action.orders/           — Order processing actions
com.ecount.one.struts.action.paymentReversal/  — Payment reversal actions
com.ecount.one.struts.action.prechecks/        — Pre-check/catalog actions
com.ecount.one.struts.action.profile/          — User profile actions
com.ecount.one.struts.action.repository/       — File repository actions
com.ecount.one.struts.action.services/         — Service-oriented actions (order download, cardholder availability)
com.ecount.one.struts.action.smots/            — SMOTS (token holder) actions
com.ecount.one.struts.action.test/             — Test actions
com.ecount.one.struts.dao/                     — DAO classes (AddendaDAO, InitialDepositDao, ManageCardDao, etc.)
```

### Request Processing Pipeline

```
HTTP Request (*.do)
    |
web.xml filter chain (ordered):
    1. ParamFilter          — blocks class-pollution parameters, validates file upload
    2. Acegi FilterChainProxy:
       a. XSSFilter         — XSS input sanitisation
       b. LocalFilter       — locale resolution
       c. OverrideUrlSessionFilter
       d. HttpSessionContextIntegrationFilter
       e. SsoRedirectFilter
       f. UsernamePasswordLoginFilter (authenticationProcessingFilter)
       g. SsoAuthenticationProcessingFilter
       h. ExceptionTranslationFilter
       i. FilterSecurityInterceptor  — role-based URL access control
    3. SSLLoginFilter       — HTTPS enforcement
    4. XSSFilter            — second XSS pass
    5. AffiliateSkinFilter  — multi-skin theming
    6. CPDeviceResolverRequestFilter — mobile device detection
    7. ClientZoneUrlFilter  — URL normalisation
    8. CheckTermsOfUseFilter
    9. ForcedPasswordFilter
   10. YourToDosFilter
   11. RequestURLParaFilter — URL parameter length limit
   12. PreventDoSFilter     — DoS rate limiting
    |
Struts ActionServlet
    → ActionMapping (struts-config.xml)
    → ActionForm binding / validation
    → Action.execute()
    → Helper classes (Spring-injected via WebApplicationContextUtils)
    → Back-end service calls
    → ActionForward → Tiles layout → JSP rendering
```

---

## API Surface

ClientZone exposes **no REST or SOAP API** for external consumers. All interaction is via browser HTML/form submissions to Struts `*.do` URLs.

### Internal URL Namespaces (from `ClientZoneConstants.URI` and `struts-config.xml`):

| Namespace | Purpose |
|---|---|
| `/login/` | Login, forgot password, MFA, terms of use, domain selection |
| `/home.do` | Dashboard / order history |
| `/administration/` | User, program, security, cardholder, inventory management |
| `/orders/` | New cardholder, quickpay, file submit, order history, sweep orders |
| `/prechecks/` | Pre-check catalog and assignment |
| `/services/` | Balance sweep, file submission, order download, customer service |
| `/profile/` | Password update, user profile |
| `/instantIssue/`, `/instantVirtualExpressIssue` | Instant issue / virtual express card issuance |
| `/bulkLoad`, `/bulkLoadStatus` | Bulk file upload and status |
| `/smots/` | SMOTS token holder search |
| `/cardholder/` | Cardholder search and update |
| `/paymentReversal/` | Payment reversal workflow |
| `/repository/` | Document repository |
| `/messageHome/` | Home message management |
| `/monitor`, `/monitor.select` | Health monitoring (Spring MVC) |
| `/simpleCaptcha.png`, `/audio.wav` | CAPTCHA image/audio |
| `/dispatch.asp` | ECount XML-RPC dispatch (legacy) |

### External Service Calls Made by ClientZone

| Target | Method | Auth | Class |
|---|---|---|---|
| Azure AD token endpoint | HTTP POST (OAuth2 client credentials) | Client ID + Secret | `SharedServiceConnector.getAccessToken()` |
| OTP generate service (`${otp.generate.url}`) | HTTP POST (JSON) | Bearer token | `OtpServiceClient.generateOTP()` |
| OTP validate service (`${otp.validate.url}`) | HTTP POST (JSON) | Bearer token | `OtpServiceClient.validateOTP()` |
| OMRCP search (`${omrcp.seach.url}`) | HTTP POST (JSON) | Bearer token | `CustomerServiceAction` |
| Adobe IDP eDelivery (SOAP) | SOAP/XML | (SOAP credentials) | `InstantIssueHelper` → `EDeliveryIDCInterfaceSoapBindingImpl` |
| Google reCAPTCHA v3 (`${recaptcha.url}`) | HTTP POST | API key | `ReCaptchaService` |

---

## Security Posture

### Strengths

1. **Multi-layer filter chain** — DoS protection, XSS filtering, parameter validation, HTTPS enforcement, Terms of Use, forced password change, URL parameter length limiting are all implemented as servlet filters.
2. **Session invalidation on login** — `invalidateSessionOnSuccessfulAuthentication: true` in both `UsernamePasswordLoginFilter` and `SsoAuthenticationProcessingFilter` prevents session fixation attacks.
3. **CAPTCHA at login** — Google reCAPTCHA v3 with configurable score threshold protects login, SSO, forgot-password, and forgot-username.
4. **Log sanitisation** — `LogUtil.sanitizeForLog()` strips newlines, control chars, pipes, and quotes to prevent log injection.
5. **DoS rate limiting** — `PreventDoSFilter` with configurable `urlHitTimeInterval`.
6. **Structured security audit** — `SecurityAuditHelper` on both login filters; `security-audit-common:2017.1.0`.
7. **Password v2 policy** — `ClientZonePasswordUtil` uses `SecureRandom`, 12–64 character length, excludes ambiguous characters, requires 3 of 4 character types. Referenced as INIT-2061.
8. **Azure AD SSO** — Modern OIDC-backed SSO with MSAL4J for certain user populations.
9. **OTP service** — Azure AD-secured shared service for OTP delivery.
10. **XSS filter** — `XSSFilter` is applied twice (once in `web.xml` filter mapping and once in the Acegi filter chain).

### Weaknesses / Vulnerabilities

1. **MD5 password hashing** — `EcountMd5PasswordEncoder` (`applicationContext-xsecurity-web.xml`) uses MD5. MD5 is cryptographically broken; rainbow table attacks are trivial. PCI DSS v4 Requirement 8.3.2 mandates strong, salted, adaptive hashing (bcrypt, scrypt, PBKDF2).

2. **AES/ECB encryption** — `EncryptionUtil.encrypt()/decrypt()` instantiates `Cipher.getInstance("AES")` without specifying mode or padding. Java defaults to AES/ECB/PKCS5Padding. ECB mode is deterministic and not semantically secure. This utility is used to encrypt passwords written to Azure AD Graph API payloads (`SsoUserUtil`). PCI DSS v4 Requirement 3.5 prohibits ECB for PAN or SAD protection.

3. **EOL frameworks with known CVEs** — Apache Struts 1.3.10 (multiple unpatched RCE CVEs, including CVE-2014-0094 class-pollution), Spring 2.0.8, Acegi Security, Log4j 1.2.17 (CVE-2019-17571), XStream 1.4.12 (multiple CVEs).

4. **PAN masking deficiency** — `MaskHelper.maskCreditCardNumber(maskPattern=false)` exposes the last 8 digits. PCI DSS Requirement 3.3.1 permits at most first 6 + last 4 (10 digits total). Eight unmasked trailing digits exceeds this limit.

5. **OTP PIN in debug log** — `OtpServiceClient.validateOTP()` at line 37: `log.debug("otp check:2, sending sessionId: " + userDetails.getSessionId() + " pin" + pin)` — the full OTP PIN and session ID are logged at DEBUG level. If DEBUG logging is enabled in production, this exposes sensitive authentication tokens.

6. **SQL injection in `SsoUserUtil`** — `SsoUserUtil.processLine()` line 91 constructs SQL via string concatenation. Although this is a batch utility rather than a servlet, it represents a code quality and potential risk pattern if adapted elsewhere.

7. **No CSRF protection** — No evidence of CSRF tokens in Struts action forms or filter chain. Struts 1 does not provide CSRF protection by default. Acegi's configuration in `applicationContext-xsecurity-web.xml` does not include a CSRF filter.

8. **MFA disabled** — The `MultiFactorAuthenticationFilter` in `web.xml` (lines 203–230) is entirely commented out. MFA enforcement is absent for the standard login flow (though OTP is available via `OtpServiceClient` and security admin screens exist under `security/mfa/`).

9. **`forceHttps: false`** — `authenticationEntryPoint` has `forceHttps: false`. HTTPS enforcement depends entirely on `SSLLoginFilter`. If the filter chain is misconfigured, HTTP access is theoretically possible.

10. **`HttpURLConnection` without timeout** — `SharedServiceConnector.callSharedService()` opens `HttpURLConnection` with no `setConnectTimeout()` or `setReadTimeout()` call. A slow or unresponsive OTP or OMRCP service will block the Tomcat thread indefinitely.

11. **`XStream 1.4.12` deserialization** — XStream versions below 1.4.20 are vulnerable to arbitrary code execution via deserialization (CVE-2022-40151 and earlier series). Version `1.4.12` is significantly below the patched version.

12. **`jackson-mapper-asl:1.9.2`** — Jackson 1.x (codehaus) is EOL and subject to multiple deserialization CVEs (CVE-2017-7525 class). The `mapper-asl` artifact is unmaintained.

13. **`commons-collections:3.2`** — Apache Commons Collections 3.2 without the security patch (3.2.2) is vulnerable to deserialization RCE (CVE-2015-6420 class). The declared version `3.2` does not include the fix.

---

## Technical Debt

### Critical (Security / Compliance)

| Item | Location | Risk |
|---|---|---|
| MD5 password encoding | `EcountMd5PasswordEncoder`, `applicationContext-xsecurity-web.xml` | Credential compromise |
| AES/ECB encryption | `EncryptionUtil.java` | Data exposure |
| PAN masking >4 digits | `MaskHelper.maskCreditCardNumber(false)` | PCI DSS non-compliance |
| OTP in debug log | `OtpServiceClient.java` line 37 | Token exposure |
| SQL concat in utility | `SsoUserUtil.java` line 91 | Injection risk pattern |
| CSRF absent | No token in action forms | CSRF attacks |
| MFA commented out | `web.xml` lines 202–230 | Account takeover |
| XStream 1.4.12 | `pom.xml` `${xstream.version}` | Deserialization RCE |
| commons-collections 3.2 | `pom.xml` | Deserialization RCE |
| jackson-mapper-asl 1.9.2 | `pom.xml` | Deserialization RCE |

### High (Framework EOL / Maintainability)

| Item | Detail |
|---|---|
| Apache Struts 1.3.10 | EOL; no security patches; ~100 Actions, ~50+ Forms |
| Spring 2.0.8 | EOL since 2008; no security patches |
| Acegi Security | Superseded 2008; no patches |
| Log4j 1.2.17 | EOL; CVE-2019-17571 |
| Tomcat 8.5 | EOL March 2024 |
| Java 8 | Oracle commercial support only; OpenJDK 8 patches available but limited |
| mssql-jdbc 6.1.0.jre8 | Driver from 2016; multiple security fixes in later versions |
| Spring `DTD`-based XML config | `spring-beans-2.0.dtd` in all context files — cannot be upgraded without rewriting all Spring config |
| poi:3.0.1-FINAL | Apache POI 3.0.1 from approximately 2008; many security fixes available |
| velocity:1.4 | Apache Velocity 1.4; EOL; replaced by Velocity Engine 2.x |

### Medium (Code Quality / Architecture)

| Item | Detail |
|---|---|
| `HttpURLConnection` no timeouts | `SharedServiceConnector.java` — thread starvation risk |
| `e.printStackTrace()` | `BalanceSweepImpl.execute()` line 55 — stack traces to stdout, not logger |
| Hard-coded Windows paths | `EncryptionUtil.java` line 68, `SsoUserUtil.java` lines 20–23 — non-portable |
| Hard-coded availability window | `NewCardholderSystemAvailability` bean — 17:00–19:30 ET hard-coded as integer strings |
| EhCache not distributed | Per-node cache; stale data risk in multi-server deployments (UAT: 2 nodes) |
| `WebApplicationContextUtils.getWebApplicationContext()` | Called in action helpers to pull Spring beans at request time — defeats Spring DI purpose |
| Struts `ActionForm` model duplication | Business entities duplicated as ActionForms and helper DTOs |
| No API versioning | URL namespace (e.g., `/administration/user/`) has no version segment; breaking changes would affect all clients simultaneously |
| `rawtype` Collections (`ArrayList` without generics) | `CardInfo.cardTypeOptions`, `CardInfo.cardStatusOptions` — Java 1.4-style raw types |

---

## Gen-3 Migration Requirements

To migrate ClientZone to a Gen-3 architecture (REST API + modern SPA or server-side React/Thymeleaf, containerised, cloud-native), the following must be addressed:

### Mandatory Pre-conditions

1. **Expose platform services as REST APIs** — `xPlatform`, `order-manager`, `debitapi-impl`, `accountmanagementapi-impl`, `inventory-mgmt`, `xSecurity` must be wrapped in REST controllers with versioned contracts before ClientZone can be rebuilt as a thin client.

2. **Migrate user credentials from MD5** — All user passwords must be re-hashed using bcrypt/PBKDF2 before the new application goes live. A zero-downtime migration strategy (detect hash algorithm on login, re-hash on successful authentication) is required.

3. **Replace AES/ECB** — Any data encrypted with `EncryptionUtil` must be re-encrypted with AES/GCM or AES/CBC+HMAC before decommissioning the old encryption utility.

4. **Externalise all filesystem config** — `D:\c-base\config\cz\` must be replaced with environment variables or a secrets manager (Azure Key Vault is already in use for Azure AD config).

5. **Containerise runtime** — Remove Windows path assumptions; build Docker image; configure health checks.

### Architecture Decisions Required

| Decision | Options |
|---|---|
| UI framework | React SPA (backend-for-frontend pattern) vs. Spring Boot + Thymeleaf server-side rendering |
| Auth/AuthZ | Azure AD B2C (already partially deployed) + Spring Security 6.x OAuth2 Resource Server |
| API gateway | Azure API Management or equivalent for rate limiting, auth, and routing |
| Session management | Stateless JWT vs. Spring Session + Redis |
| Database access | Spring Data JPA vs. retain stored procedures (risk: SP logic migration) |
| MFA | OTP shared service (already REST-based) — retain and integrate via standard Spring Security MFA extension |
| i18n | Spring MessageSource / Thymeleaf i18n or React-Intl for SPA |
| Logging | SLF4J + Logback → JSON structured output → Azure Monitor / Splunk |
| CI/CD | GitHub Actions (already partially migrated from GitLab); add production deploy stage |

### Estimated Scope

- Approximately 100 Struts Action classes, 50+ ActionForms, 150+ JSP files, 130+ helper/DAO classes, 27 Spring XML context files.
- The action-form workflow is tightly coupled — helper classes call `WebApplicationContextUtils.getWebApplicationContext(request.getSession().getServletContext())` to pull beans, making static dependency analysis difficult.
- A full rewrite is estimated to be a large multi-sprint programme; incremental strangler-fig migration (new REST APIs behind an API gateway, with ClientZone proxying to them) is the lower-risk path.

---

## Code-Level Risks

| Risk | Class / File | Line Reference | Severity |
|---|---|---|---|
| AES/ECB — no IV | `EncryptionUtil.java` | `Cipher.getInstance("AES")` line 23 | Critical |
| OTP PIN debug log | `OtpServiceClient.java` | `log.debug(... + pin)` line 37 | Critical |
| SQL concatenation | `SsoUserUtil.java` | Line 91 | High |
| PAN last-8 masking | `MaskHelper.java` | `maskCreditCardNumber(false)` lines 21–31 | High |
| No HTTP timeout | `SharedServiceConnector.java` | `url.openConnection()` line 57; no `setConnectTimeout` | High |
| `e.printStackTrace()` | `BalanceSweepImpl.java` | Line 55 | Medium |
| Hard-coded key path | `EncryptionUtil.java` | Line 68 `"D:\\c-base\\config\\cz\\clientzone.properties"` | Medium |
| Hard-coded Azure tenant | `SsoUserUtil.java` | `TENANT = "ladsmarkclient"` line 23 | Medium |
| Hard-coded source member ID | `AccountManagementAPIHelper.java` | `SOURCE_MEMBER_ID = "5FCFFE5C-..."` line 24 | Medium |
| Raw ArrayList (no generics) | `CardInfo.java` | `cardTypeOptions`, `cardStatusOptions` fields | Low |
| `TODO{Description}` javadoc | `DebitAPIController.java`, `BalanceSweepImpl.java` | Multiple class-level javadocs | Low |
| Debug level `3` on Struts | `web.xml` | `<param-value>3</param-value>` lines 403, 408 | Low — verbose logging in prod |
| MFA filter commented out | `web.xml` | Lines 202–230 | High — authentication gap |
| `DisableStrongPassword` in Azure | `SsoUserUtil.java` | `"passwordPolicies": "DisablePasswordExpiration, DisableStrongPassword"` line 119 | High — Azure AD password policy bypassed for SSO users |
