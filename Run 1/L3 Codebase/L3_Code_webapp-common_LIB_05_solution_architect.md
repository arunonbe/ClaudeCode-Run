# Solution Architect — webapp-common_LIB

## Technical Architecture
- **Single filter class**: `com.citi.prepaid.web.common.filter.SSLLoginFilter` implements `javax.servlet.Filter`.
- Configured via `web.xml` `<filter>` / `<filter-mapping>` declarations in the consuming WAR.
- No Spring context dependency — works in plain servlet container (Tomcat, WebSphere, JBoss).
- Package: JAR (`webapp-common-1.0.1.jar`), consumed as a compile-time dependency.

## API Surface
No REST or SOAP API. The sole public API is the `javax.servlet.Filter` contract:
- `init(FilterConfig)` — reads `check` and `no-ssl-urls` init params.
- `doFilter(ServletRequest, ServletResponse, FilterChain)` — core redirect logic.
- `destroy()` — clears `filterConfig`.
- `isSSLCheck()` — public utility method (reads `check` init param).

## Security Posture

### Authentication / Authorisation
Not applicable to the library itself. The filter provides transport security enforcement, not authentication.

### Cryptography
No cryptographic operations. The library relies on the servlet container's TLS implementation.

### Secrets
None. No credentials, API keys, or secrets handled.

### Known Vulnerabilities and CVEs
1. **Parameter injection / URL manipulation** (`SSLLoginFilter.java:132–162`): The `redirectSecureURL()` method reconstructs query parameters by iterating `request.getParameterNames()` and concatenating `name=value&` without URL encoding. Issues:
   - Special characters in parameter names or values will produce malformed redirect URLs.
   - If a parameter value contains `&` or `=`, the reconstructed URL will be incorrect.
   - The original `request.getQueryString()` is available and should be used instead.
   - This is a **medium-severity bug** with potential for redirect manipulation.
2. **`junit:3.8.1`**: CVE-2020-15250 and multiple older CVEs affect the JUnit 3.x lineage. This is test-scope only and does not affect the runtime JAR.
3. **`commons-logging`** (via parent POM): Historical CVEs exist in old commons-logging versions. Version inherited from `webapp-parent:6` is unknown without resolving the parent POM.
4. **`javax.servlet` API** (inherited): Version unknown without parent POM resolution. Old servlet API versions do not themselves carry CVEs, but consuming applications running on old Tomcat versions may be vulnerable.

## Technical Debt
1. **Obsolete test framework**: `junit:3.8.1` and `AppTest.java` (Maven archetype placeholder) — no real test coverage. `com.citi.prepaid.web.filter.AppTest` (note: wrong package, `filter` vs `common.filter`) suggests the test was never properly set up.
2. **`javax.servlet` namespace**: Hard blocks Jakarta EE 9+ / Spring Boot 3.x migration.
3. **Parameter reconstruction bug** in `redirectSecureURL()` — see above.
4. **Port 80 → 443 hardcoded** (`SSLLoginFilter.java:155`): `if (request.getServerPort() == 80) sslRedirect = sslRedirect + ":443"`. This is correct for standard HTTP→HTTPS, but if the application runs on a non-standard HTTP port (e.g., 8080), it would redirect to `8080` on HTTPS instead of the correct HTTPS port, breaking the redirect.
5. **Raw type usage** (`SSLLoginFilter.java:133`): `Enumeration en = request.getParameterNames()` — raw type without generic parameter. This is a Java generics warning indicating the code predates Java 5 generics adoption.
6. **`com.citi.prepaid` group ID**: Not aligned with Onbe's `com.onbe` namespace. If published to the internal Nexus, it pollutes the registry with a non-standard group.

## Gen-3 Migration Requirements
To migrate consumers of this library to Gen-3 (Spring Boot 3.x):
1. **Retire this library**: Replace with Spring Security's `http.requiresChannel().anyRequest().requiresSecure()` or reverse-proxy/ingress-level HTTPS enforcement.
2. **If retention is required**: Port `SSLLoginFilter` to `jakarta.servlet.Filter`; update parent POM to a Jakarta-compatible version; fix parameter reconstruction bug; add real unit tests; migrate group ID to `com.onbe`.

## Code-Level Risks

| File | Line | Risk |
|---|---|---|
| `src/main/java/.../SSLLoginFilter.java` | 132–162 | `redirectSecureURL()` — parameters reconstructed without URL encoding; potential URL manipulation |
| `src/main/java/.../SSLLoginFilter.java` | 133 | `Enumeration en` — raw type, Java pre-5 pattern |
| `src/main/java/.../SSLLoginFilter.java` | 155 | Port 80→443 hardcoded; non-standard HTTP ports will not redirect to HTTPS port correctly |
| `src/main/java/.../SSLLoginFilter.java` | 109 | DEBUG logging of full redirect URL — may expose sensitive query parameters in log files |
| `pom.xml` | 22 | `junit:3.8.1` — obsolete; CVE-affected; zero real test coverage in the repository |
