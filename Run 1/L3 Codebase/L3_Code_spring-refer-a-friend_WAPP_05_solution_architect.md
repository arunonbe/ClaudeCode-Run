# 05 Solution Architect — spring-refer-a-friend_WAPP

## Technical Architecture
Spring 2.0.2 WAR web application (`sprint-raf:1.0-SNAPSHOT`, packaged as `rafstatus.war`). Implements a single Spring MVC `SimpleFormController` (`SearchController`) for the Sprint Refer-a-Friend referral lookup UI. Data access via JNDI-bound data sources (EcountCore, Cbaseapp, JobSvc) and cbase/xPlatform API objects. EHCache 1.2 used for phone+year lookup caching. JSP views.

Key classes:
- `SearchController` — Spring MVC `SimpleFormController`; renders `search/referral` view; handles phone + year search
- `SearchCriteria` — form backing object (phone, year)
- `SearchCriteriaValidator` — validates form inputs
- `ReferralInfo` — service layer; delegates to `Referral2DAO`, `LastLoadDateDAO`, `PlasticInfo`
- `Referral2DAO` — JDBC DAO against Cbaseapp data source
- `LastLoadDateDAO` — JDBC DAO against EcountCore data source
- `PlasticInfo` — retrieves card/member plastic status via `coreMemberManager` + `coreDeviceManager`
- `RequestContextLookup` — resolves ecount `RequestContext` from properties (configPath, appId, affiliateId, agent, classification)
- `RAFRequest` — DTO aggregating referral results (phone, year, status, errorMsg, referral list)
- `Referral2Value` — referral row value object

Design notes:
- `siteDown` flag in `SearchController` is an in-memory string toggled via `?site_admin=maintenance|up` request parameter — no authentication on this admin control
- `useCache` flag is also togglable via `?caching=on|off` query parameter — no authentication
- `flushCache` triggered by `?flushCache=on` — no authentication
- XStream used for logging DTO XML (disabled via commented-out log statement)

## API Surface
Web application with one functional URL:
- `GET/POST /search/referral.htm` — referral lookup form (phone number + year)
- `GET ?printer_friendly=true` — printer-friendly view variant
- `GET ?site_admin=maintenance|up` — **unauthenticated** maintenance mode toggle
- `GET ?caching=on|off` — **unauthenticated** cache toggle
- `GET ?flushCache=on` — **unauthenticated** cache flush

No REST API. No authentication framework visible in the WAR.

## Security Posture
- **Critical: unauthenticated admin controls** — `?site_admin=maintenance` and `?caching=on|off` and `?flushCache=on` parameters are processed without any authentication check; any user who can reach the URL can take the site into maintenance mode or manipulate cache behaviour
- No Spring Security or Acegi Security configuration visible
- Phone number is logged via `log.info("query phone: " + raf.getPhone())` — phone numbers are PII; may appear in log files
- `XStream 1.1` present (ancient; deserialisation CVEs exist in later versions, though usage here is serialisation-only for logging)
- No CSRF protection (Spring 2.0.x pre-dates Spring Security CSRF support)
- Session management: `setSessionForm(false)` — no server-side session for form state (reduces session fixation risk)
- HTTPS enforcement: not visible in WAR configuration; relies on front-end reverse proxy
- EHCache 1.2beta4: beta release, EOL; cached RAFRequest objects may contain phone numbers (PII) — cache eviction policy should be reviewed

## Technical Debt
| Item | Severity |
|---|---|
| Spring 2.0.2 (EOL > 15 years) | Critical |
| Java 5 compile target | Critical |
| Unauthenticated admin URL parameters | Critical |
| EHCache 1.2beta4 (beta, EOL) | High |
| Log4j 1.2.9 (EOL; not Log4Shell vulnerable but still EOL) | High |
| XStream 1.1 (ancient) | High |
| jtds 1.2 JDBC driver (EOL) | High |
| JNDI data source binding requires J2EE container (Tomcat); no container-independent config | Medium |
| `SimpleFormController` is deprecated in Spring 2.5+ | Medium |
| `referrals.jsp.bak` backup file in webapp directory — should not be deployed | Low |
| `Thumbs.db` in images directory committed to source control | Low |
| `maxYearlyReferrals` hard-coded as 12 in Spring XML | Low |
| Version `1.0-SNAPSHOT`; never released from SNAPSHOT state | Low |

## Gen-3 Migration
- Replace WAR with a Spring Boot 3.x application
- Implement Spring Security with role-based access; protect admin operations with `ROLE_ADMIN`
- Replace `SimpleFormController` with `@Controller` + Thymeleaf (or React front-end calling a REST API)
- Replace EHCache with a managed cache (Azure Cache for Redis or Caffeine)
- Replace JNDI data sources with Spring Boot auto-configured data sources backed by Azure Key Vault
- Redact phone numbers from application logs (log masking)
- Containerise and deploy to AKS

## Code-Level Risks
- `siteDown` is an instance variable on a Spring singleton controller bean; concurrent requests can race to set/read it — not thread-safe
- `useCache` similarly is a mutable instance variable on a singleton — not thread-safe
- `clean(phone)` strips only hyphens, dots, and spaces; does not validate that the result is a numeric phone number — a crafted phone value could be logged or stored with unexpected characters
- `referenceData()` catches `Exception` broadly and sets `SYSTEM_ERROR` status; the original exception is only printed to stdout (`e.printStackTrace()`), not to the logging framework — errors may be invisible in production log aggregation
- `rafCacheManager.getCache("rafCache")` can return `null` if the cache name is misconfigured; a subsequent `.get()` call would throw a `NullPointerException`
