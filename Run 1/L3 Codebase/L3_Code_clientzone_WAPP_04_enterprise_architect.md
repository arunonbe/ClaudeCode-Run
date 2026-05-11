# clientzone_WAPP — Enterprise Architect View

## Platform Generation (Gen-1 / Gen-2 / Gen-3)

**Classification: Gen-1**

Evidence for Gen-1 designation:

| Signal | Evidence |
|---|---|
| MVC framework | Apache Struts 1.3.10 — original version of the Struts framework, now EOL |
| Web framework | Spring 2.0.8 — Spring 2.x from approximately 2007, severely EOL |
| Java version | Java 8 (1.8), both compile target and runtime |
| UI technology | JSP with Struts tag libraries (`struts-bean`, `struts-html`, `struts-logic`, `struts-tiles`, `struts-nested`), Apache Tiles 1.x, DisplayTag 1.1 |
| Security framework | Acegi Security (the pre-Spring Security framework, `org.acegisecurity.*`) — superseded by Spring Security in 2008 |
| Deployment | WAR on bare-metal/VM Windows Server, Apache Tomcat 8.5 |
| RPC protocol | `ECount.System.RPC.rpcServlet` — bespoke XML-RPC servlet (`dispatch.asp` URL) |
| Persistence | Stored procedure-centric JDBC, `JdbcTemplate`-style DAOs, no ORM |
| Config management | XML Spring config (`applicationContext.xml` DTD-based, Spring 2.0), no annotations |
| xdoclet | `src/main/xdoclet/web/` directory contains xdoclet-style XML fragments for Struts action generation |
| Version history | Version `2.0.52-SNAPSHOT`; parent `webapp-parent:9`; `groupId com.citi.prepaid.*` — originates from a Citi Prepaid / ECount lineage |
| Artifact SCM origins | Domain `ecount.com` appears in `<url>` (`http://clientzone.ecount.com`) and package names throughout |

This application exhibits the canonical characteristics of the ECount/North Lane Gen-1 platform: Struts 1, Acegi, Spring 2, stored-procedure DAO, JSP views, and Windows/Tomcat deployment.

---

## Business Domain

**Client Portal / Program Administration**

ClientZone is the **B2B client-facing portal** that sits between Onbe's corporate clients (program sponsors) and the underlying prepaid card processing platform. It enables:

- Corporate client administrators to manage their prepaid card programs.
- Customer service agents (on behalf of clients) to look up, update, and service cardholders.
- Back-office operations staff to process instant-issue, virtual card issuance, balance debits, file submissions, and payment reversals.

It is the **primary operational interface** for the Onbe East product line (formerly North Lane / ECount / Citi Prepaid Cards).

Supported business segments (inferred from code):
- Healthcare disbursements (implied by instant issue, precheck workflows)
- Insurance / refunds (implied by payment reversal, balance sweep)
- Gig/creator (PUID-based loading, virtual express)
- Retail / loyalty (companion cards, promotions)
- Corporate incentives (file-based bulk loads)

---

## Role in Platform

```
External Corporate Client (browser)
        |
        v
  clientzone_WAPP  ◄── This application
  (B2B Portal)
        |
        |--- xPlatform / ECount Core (member, device, transfer mgmt)
        |--- Order Service (order-manager, request-manager)
        |--- Job Service (job-manager)
        |--- xSecurity (authentication, user management)
        |--- Debit API (balance sweep, fund recovery)
        |--- Account Management API (virtual card creation)
        |--- Repository Service (file storage/download)
        |--- Inventory Management (instant issue card tracking)
        |--- Comment Service (audit comments)
        |--- Screen Configs Service (UI configuration)
        |--- eDelivery (Adobe LiveCycle — statement delivery)
        |--- Affiliate Service (multi-skin, branding)
        |--- OTP Shared Service (Azure-backed, REST)
        |--- OMRCP Search (cardholder search, REST)
        |--- Message Center (in-app notifications)
        |
        v
  MS SQL Server (6 databases)
```

ClientZone is an **orchestrating application** — it has no domain logic of its own beyond UI workflow; all business operations are delegated to internal platform services via Spring-wired helpers.

---

## Dependencies

### Upstream (consumes)

| Service / Library | Coordinates | Interface |
|---|---|---|
| xPlatform (core) | `com.ecount:xPlatform:3.0.27` | Java library (in-process), proprietary ECount RPC |
| xSecurity | `com.ecount.service.xSecurity:xSecurity-web/impl/common:2016.1.1` | Java library (Spring beans) |
| Order Manager | `com.citi.prepaid.service.order:order-manager:3.1.8` | Java library |
| Request Manager | `com.citi.prepaid.service.order:order-common:3.1.8` | Java library |
| Job Manager | (via `appCtx-JobManagerImport.xml`) | Java library |
| Debit API | `com.citi.prepaid.webservices.debitapi:debitapi-impl:2015.3.1` | Java library |
| Account Management API | `com.citi.prepaid.accountmanagementapi:accountmanagementapi-impl:2.0.9` | Java library |
| Repository Service | `com.citi.prepaid.service.repository:repository-impl:2.0.1` | Java library |
| Inventory Management | `com.citi.prepaid.service.inventory:inventory-mgmt:2016.1.1` | Java library |
| RSA MFA | `com.citi.prepaid.service.rsa-mfa:rsa-mfa-impl:1.0.9` | Java library |
| eDelivery Client | `com.citi.prepaid.service.eDeliveryClient:eDeliveryClient:0.0.1` | SOAP (Adobe IDP) |
| Comment Service | `com.ecount.services:comment:2019.1.4` | Java library |
| Screen Configs | `com.ecount.service.screenconfigs:screenconfigs:2015.3.1` | Java library |
| Affiliate Service | `com.ecount.one.service.affiliate:xAffiliateService:2019.1.3` | Java library |
| xSearch | `com.ecount.service.xSearch-New:xSearch-impl:2022.1.4` | Java library |
| spring-dbctx | `com.citi.prepaid.spring-dbctx:spring-dbctx-container:1.0.6` | Java library |
| webapp-common | `com.citi.prepaid.web.common:webapp-common:1.0.1` | Java library |
| Security Audit Common | `com.citi.prepaid.audit:security-audit-common:2017.1.0` | Java library |
| eccm (tags) | `com.ecount.web.tags:eccm:1.1.1` | JSP tag library |
| Azure AD / MSAL4J | `com.microsoft.azure:msal4j:1.14.3` | OAuth2 client |
| OTP Shared Service | REST endpoint at `${otp.generate.url}` / `${otp.validate.url}` | REST/JSON (Azure AD secured) |
| OMRCP Search | REST endpoint at `${omrcp.seach.url}` | REST/JSON (Azure AD secured) |
| Adobe IDP eDelivery | SOAP service | SOAP/XML |

### Downstream (no application calls ClientZone — it is a terminal UI)

No evidence of downstream application-to-application callers. ClientZone is a browser-facing application only.

---

## Integration Patterns

| Pattern | Implementation | Notes |
|---|---|---|
| In-process Java library | xPlatform, xSecurity, Order Service, Debit API, etc. | All major back-end integrations are compiled-in JAR dependencies, not network services. High coupling. |
| Stored procedure calls (Spring JDBC) | `JdbcTemplate` / `StoredProcedure` subclasses | Multiple DAOs implement stored procedure wrappers. |
| Synchronous HTTP client (raw `HttpURLConnection`) | `SharedServiceConnector.java` | Used for OTP and OMRCP services. No connection pooling, no timeout configuration visible. |
| SOAP (Apache Axis / Adobe IDP) | `EDeliveryIDCInterfaceSoapBindingImpl` | Legacy SOAP for eDelivery — Adobe LiveCycle. |
| OAuth2 Client Credentials (MSAL4J) | `SharedServiceConnector.getAccessToken()` | Token acquisition for Azure AD-secured REST services. Tokens are re-used across requests (silent acquire with fallback). |
| Spring MVC (monitoring only) | `monitor-servlet.xml` | Separate DispatcherServlet for health/monitor endpoint. |
| Acegi/Spring Security filter chain | `applicationContext-xsecurity-web.xml` | Authentication and authorisation. |
| XDoclet-style XML descriptor generation | `src/main/xdoclet/web/` | Legacy Struts action/form mapping generation fragments. |
| EhCache | `ehCache-ytd.xml` | Local in-memory caching. Not distributed — each Tomcat instance has its own cache. |
| Tiles layout engine | `tiles-defs.xml` | UI composition via Apache Tiles 1.x. |
| Multi-affiliate skin | `AffiliateSkinFilter`, `affiliateContext.xml` | Dynamic CSS/branding based on affiliate configuration. |
| Multi-region URL routing | `regionRedirectURLMap` bean, `RegionSelEcountContextListener` | Redirects domestic vs. international users to region-specific URLs. |

---

## Strategic Status

**Status: Legacy / Active Production — Migration Required**

| Dimension | Assessment |
|---|---|
| Business criticality | High — primary B2B portal for corporate clients |
| Technical currency | Very low — Struts 1, Acegi, Spring 2, Java 8, Tomcat 8.5, all EOL |
| Maintainability | Low — deep coupling to Gen-1 service libraries; 100+ helper/action classes; XML-heavy Spring config |
| Security posture | Poor (see solution architect view) — MD5 passwords, ECB encryption, EOL frameworks with known CVEs |
| CI/CD maturity | Partial — production deploy is commented out; tests skipped in CI |
| Cloud readiness | Very low — Windows filesystem dependencies, hardcoded paths, no containerisation |
| Gen-3 suitability | Not suitable without full rewrite — architecture is incompatible with modern API-first, containerised patterns |

The application is being incrementally modernised in specific areas (Azure AD SSO, OTP via REST shared service, reCAPTCHA v3) while the core remains Gen-1. This creates an architectural hybrid that complicates both maintenance and migration.

---

## Migration Blockers

Ranked by severity:

1. **In-process library coupling** — All major platform services (`xPlatform`, `xSecurity`, `order-manager`, `debitapi-impl`, `accountmanagementapi-impl`, `inventory-mgmt`, `screenconfigs`) are embedded JAR dependencies with no API contracts. Decomposing to microservices requires first exposing these as versioned REST/gRPC APIs.

2. **Struts 1 / Acegi action-form architecture** — Approximately 100 Struts Actions, 50+ ActionForms, Struts Tiles layout. There is no REST or API layer — all business operations are expressed as HTTP form submissions to `*.do` URLs. A rewrite requires redesigning all user workflows.

3. **Stored procedure orientation** — Business logic is distributed between Java helpers and SQL stored procedures. Migrating away from stored procedures requires understanding undocumented database-side logic.

4. **Windows filesystem dependencies** — Config at `D:\c-base\config\cz\`, runtime at `D:\c-base\runtime\`, log at `D:\c-base\config\cz\log4j.xml`. All must be externalised to environment variables or a secrets manager before containerisation.

5. **Session-bound state** — Cardholder data (including SSN, PAN display data) lives in `HttpSession`. Stateless API design requires moving this to token-bound or server-side session stores.

6. **xDoclet / XML-heavy configuration** — `src/main/xdoclet/web/` and `WEB-INF/struts-config.xml` contain hundreds of action/form mappings in XML. These have no equivalent in modern Spring Boot or Quarkus.

7. **Acegi Security** — Pre-dates Spring Security; custom extensions (`ClientZoneDaoAuthenticationProvider`, `EcountMd5PasswordEncoder`, `UsernamePasswordLoginFilter`, `SsoAuthenticationProcessingFilter`) must be rewritten against a modern security framework.

8. **Adobe IDP SOAP dependency** — eDelivery integration via Adobe LiveCycle is a legacy SOAP interface. The vendor dependency and SOAP protocol are migration targets.

9. **ECount proprietary RPC** — `ECount.System.RPC.rpcServlet` (mapped to `/dispatch.asp`) is a proprietary binary/XML-RPC mechanism. Its replacement requires understanding the wire format and all callers.

10. **Multi-locale JSP resource bundles** — i18n is implemented via Struts `ApplicationResources.properties` files for `en_US`, `es_ES`, `pt_BR`, `en_GB`. Migrating to a modern i18n framework requires careful mapping of all message keys.
