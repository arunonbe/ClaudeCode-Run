# Solution Architect Analysis: rebate-inquiry_WAPP

## Technical Architecture
- **Framework**: Apache Struts 1.2.7 (MVC), Spring 2.x (IoC/DI via XML), Tiles (view composition)
- **Java**: JDK 8
- **Packaging**: WAR, deployed to JBoss/WildFly
- **Build**: Maven 3 with antrun/xdoclet code generation
- **Config**: Spring PropertyPlaceholderConfigurer reading from `D:/c-base/config/rebate-cardinquiry/rebate.properties`
- **Logging**: Log4j 1.2.17 with JSON event layout (logstash-compatible)

### Module Structure
```
rebate-inquiry_WAPP/
  src/main/java/com/ecount/
    listener/PropertiesContextListener.java      - Spring bean; holds program config
    one/web/filter/SSLRedirectFilter.java        - Servlet filter; HTTP->HTTPS redirect
    rebate/notification/
      EmailNotification.java                     - Delegates to cbase NotificationManagerImpl
      NotificationHelper.java                    - Builds email template from form fields
      RebateEmailTemplateImpl.java               - Email template for rebate card
      PrepaidCardEmailTemplateImpl.java          - Email template for prepaid card
    rebate/struts/action/
      RebateCardInquiryAction.java               - Struts action; handles rebate form POST
      PrepaidDebitCardInquiryAction.java         - Struts action; handles prepaid form POST
    rebate/struts/form/
      InquiryForm.java                           - Base ValidatorForm with PII fields
      RebateCardInquiryForm.java                 - Subclass for rebate card
      PrepaidDebitCardInquiryForm.java           - Subclass for prepaid card
```

## API Surface
No REST or SOAP API. HTTP endpoints via Struts action mappings (*.do):
- `/rebateCardInquiry.do` — POST: processes rebate card inquiry form
- `/prepaidDebitCardInquiry.do` — POST: processes prepaid debit card inquiry form
- GET forms served by corresponding GetFormAction classes

All endpoints are unauthenticated and publicly accessible.

## Security Posture

### Authentication & Authorisation
- **None**. There is no login, session authentication, or authorisation check. Any internet user can submit a form.

### Cryptography
- HTTPS enforcement via `SSLRedirectFilter` (redirects HTTP port 80 to HTTPS). However, the redirect logic at `SSLRedirectFilter.java:110-111` reconstructs the URL with query parameters concatenated via string operations — potential for parameter injection if query parameters contain special characters.
- No application-level encryption.

### Secrets Management
- Program configuration (agent ID, member ID, recipient email addresses) stored in plaintext in `rebate.properties` on the filesystem. No secrets vault integration.
- Log4j configuration path and properties file path both hard-coded in `web.xml` and `applicationContext.xml`.

### Known CVEs / Vulnerable Dependencies
| Library | Version | Known Issues |
|---|---|---|
| `struts:struts` | 1.2.7 | Multiple critical CVEs (ClassLoader manipulation, remote code execution) — EOL since 2013. CVE-2014-0114 and others affect this version range. |
| `log4j:log4j` | 1.2.17 | CVE-2019-17571 (SocketServer deserialization RCE), CVE-2022-23302/23303/23305 (JMSAppender, SMTPAppender, JDBCAppender RCE chains) |
| `xercesImpl` | 2.8.1 | Older version; check CVE-2012-0881 (infinite loop DoS) |
| `commons-httpclient` | 3.0.1 | CVE-2012-5783 (SSL hostname verification disabled) |
| `xstream` | 1.3.1 | Multiple critical CVEs for arbitrary code execution via deserialization (CVE-2013-7285, many others) |
| `junit` | 3.8.1 | Test scope only; no runtime risk |

## Technical Debt
1. **Struts 1 (EOL 2013)**: Entire MVC layer must be rewritten.
2. **xdoclet code generation** (`pom.xml:222-244`): Obsolete; generates Struts XML from JavaDoc annotations at build time.
3. **xstream 1.3.1**: Critically outdated serialisation library with many deserialization CVEs.
4. **Hard-coded Windows paths** in `web.xml:13` and `applicationContext.xml:9` — ties to specific server layout.
5. **Hard-coded config file path** referenced in `RebateCardInquiryAction.java:37` as a constant (`CONFIG_PROPERTIES = "D:/c-base/config/rebate-cardinquiry/rebate.properties"`) — unused in action code (actual loading is in Spring context) but misleading.
6. **Silent exception swallowing** at `RebateCardInquiryAction.java:91`: email send failures are logged but user gets a success page regardless.
7. **Stale Nexus/SCM URLs**: Maven distributionManagement points to decommissioned Wirecard infrastructure.
8. **Spring DTD-based XML config** (`applicationContext.xml:2`): Uses old DTD namespace, not schema-based — indicates Spring 2.x era configuration.

## Gen-3 Migration Requirements
1. Replace Struts 1 + Spring 2 MVC with Spring Boot REST API + modern SPA (React/Angular) or Spring MVC Thymeleaf.
2. Replace `xPlatform`/cbase `NotificationManagerImpl` with a call to the Gen-3 notification microservice.
3. Externalise all configuration to environment variables / Azure App Configuration / Kubernetes Secrets.
4. Replace Log4j 1.x with SLF4J + Logback.
5. Add authentication (OAuth2/OIDC) if the form is to be accessible only to authenticated users, or add CAPTCHA/rate-limiting if it remains public.
6. Containerise with a standard Onbe Dockerfile pattern; remove JBoss dependency.
7. Upgrade or replace all vulnerable transitive dependencies (xstream, struts, commons-httpclient, xerces).
8. Implement proper error handling with user-visible feedback on email delivery failure.

## Code-Level Risks (File:Line References)
- `RebateCardInquiryAction.java:37` — hard-coded `D:/c-base/config/...` path constant (unused at runtime but indicates OS coupling).
- `SSLRedirectFilter.java:92-93` — unencoded query parameter concatenation in SSL redirect URL construction; potential for open redirect / parameter injection.
- `SSLRedirectFilter.java:67` — redirect only enforced when port is 80; HTTPS enforcement may be bypassed on non-standard ports.
- `applicationContext.xml:9` — hard-coded Windows file path for properties file; startup failure if path absent.
- `web.xml:13` — hard-coded Windows file path for log4j config.
- `NotificationHelper.java:24` — `setSenderFromEmail(form.getEmail())` uses user-supplied email as the From address without validation, potentially enabling email spoofing or header injection through the cbase library.
- `pom.xml:124` — `xstream:1.3.1` is present; critical deserialization CVEs if XStream is used to deserialise untrusted input.
