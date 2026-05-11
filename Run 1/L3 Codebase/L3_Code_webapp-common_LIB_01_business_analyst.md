# Business Analyst — webapp-common_LIB

## Business Purpose
`webapp-common` is a **Gen-1 shared web library** originally authored under the Citi prepaid-card platform (`com.citi.prepaid.web.common`, group ID `com.citi.prepaid.web.common`). It provides reusable servlet-level infrastructure for legacy Java EE / Spring MVC web applications deployed on a shared Tomcat container. The primary deliverable is an SSL redirect filter (`SSLLoginFilter`) that enforces HTTPS across all URLs not explicitly excluded.

This library is a dependency of older Onbe web applications that predate the Spring Boot embedded-server model.

## Capabilities
1. **SSL/HTTPS Enforcement (`SSLLoginFilter`)**: A `javax.servlet.Filter` implementation that:
   - Checks if SSL enforcement is `on` (configured in `web.xml` via `check` init-param).
   - Redirects all non-HTTPS requests to their HTTPS equivalents.
   - Supports a whitelist of URL patterns / server names that bypass the SSL check (`no-ssl-urls` init-param, comma-delimited, matched against `request.getServerName()`).
   - Reconstructs the HTTPS URL preserving server name, port, URI, and query parameters.

## Entities / Domain Objects
None — this is a pure infrastructure library. No business domain entities, no persistence, no data transfer objects.

## Business Rules
1. If `check` init-param is `"on"`, all HTTP (non-secure) requests must be redirected to HTTPS unless the server name appears in `no-ssl-urls`.
2. Port mapping: if the incoming request is on port 80, the redirect must target port 443 (explicitly coded in `SSLLoginFilter.java:155`).
3. For all other ports, the same port number is preserved in the redirect URL.
4. The `no-ssl-urls` exclusion list is matched case-insensitively against the server hostname.

## Flows
1. HTTP request arrives at servlet container.
2. `SSLLoginFilter.doFilter` is invoked.
3. If SSL check is `off` → request passes through.
4. If SSL check is `on`:
   - If server name is in exclusion list → request passes through.
   - If request is already secure → request passes through.
   - Otherwise → HTTP 302 redirect to reconstructed HTTPS URL is issued.

## Compliance Relevance
- **PCI DSS Requirement 4.2.1**: All cardholder data in transit must be protected with strong cryptography. This filter is a key enforcement mechanism for ensuring web UIs never serve payment-related pages over HTTP. Its correct configuration is a PCI DSS control.
- **PCI DSS Requirement 6.2**: All system components must be protected against known vulnerabilities; the library uses extremely old dependencies (`junit 3.8.1`, parent POM version 6, `javax.servlet` API) — see Risks.

## Risks
1. **Critical: Extremely outdated technology stack** — uses `javax.servlet.Filter` (Java EE), parent POM version 6, `junit 3.8.1`. These suggest the codebase dates from 2010–2015 and has not been updated.
2. **Query string reconstruction vulnerability** (`SSLLoginFilter.java:136–145`): Parameters are reconstructed by concatenating `name=value&` without URL-encoding. This can produce malformed redirect URLs or allow parameter injection if the original query string contains special characters. The original `getQueryString()` is already available and should be used directly instead.
3. **No production test coverage**: The only test class is `AppTest.java` which appears to be a Maven archetype placeholder.
4. **Deprecated `javax.servlet` namespace**: Not compatible with Jakarta EE 9+ (which uses `jakarta.servlet`). This blocks any migration to Tomcat 10+ or Spring Boot 3.x.
