# service-tester_WAPP — Solution Architect View

## Technical Architecture
Multi-module Maven project:
- `service-test-common`: Core domain model, user/access management, service invocation engine, JDBC DAO.
- `service-test-web`: WAR — Spring MVC user portal with JSP views.
- `service-test-web-admin`: WAR — Spring MVC admin portal with user management and runtime context loading.
- `service-test-console`: Console client.
- `service-test-swing`: Swing desktop client.

Spring MVC `DispatcherServlet` configured via XML (`service.tester-servlet.xml`, `service.tester.mvc.*.xml` files). FORM authentication via Tomcat realm. Database via JNDI. XML marshalling via XStream.

## API Surface

### Web Endpoints (from web.xml mappings)
| URL Pattern | Access Control | Description |
|---|---|---|
| `/login.html` | Public | FORM login page |
| `/index.html` | Any authenticated role | Main service method browser |
| `/lookup.html` | Any authenticated role | Context name lookup |
| `/switch.html` | Any authenticated role | Context switch |
| `/admin.html` | Any authenticated role | Admin panel (NOTE: not restricted to admin role) |
| `*.html` | Mapped to DispatcherServlet | Spring MVC handler |

## Security Posture

### Authentication
FORM-based authentication via `<auth-method>FORM</auth-method>`. Authentication is delegated to the Tomcat realm — usernames/passwords are validated by container.

### Authorisation
**Weak.** `<auth-constraint><role-name>*</role-name></auth-constraint>` in `web.xml` — any authenticated user can access any protected resource including `/admin.html`. Role-based method access is enforced at the application layer by the `Role` entity, but the admin UI itself has no container-level role restriction.

### CSRF
No CSRF token mechanism visible in web.xml, JSP templates (not fully examined), or Spring configuration. Form-based requests may be vulnerable to CSRF.

### XStream Deserialisation — CRITICAL
`XStreamMarshaller` is used to parse user-supplied XML input for service method invocations. XStream has a well-documented history of **unsafe deserialisation vulnerabilities** (CVE-2021-21351, CVE-2020-26217, CVE-2021-39149, and numerous others). User-supplied XML processed by XStream without whitelist class filters can lead to **Remote Code Execution**.

### Dynamic JAR Loading
`JarLoader.java:55-66` uses reflection to call `WebappClassLoader.addRepository(String)` on the Tomcat class loader. This dynamically adds JARs to the running application's classpath. If the JAR source directory is not access-controlled, an attacker with write access could inject malicious classes.

### Log4j 1.x
`log4j:log4j:1.2.17` declared. CVE-2019-17571: Log4j 1.x SocketServer deserialization vulnerability. Must be upgraded.

### Secrets Management
- SMTP host hardcoded: `mail.ecount.com` in `service-test.context.properties`.
- Nexus distribution URL uses plain HTTP (no HTTPS): `http://d-na-stk01.nam.wirecard.sys:8080`.
- JNDI DataSource name `jdbc/ServiceTesterDataSource` — credentials in Tomcat context.xml (not committed to source).

## Technical Debt

### Critical
- `web.xml:40-42` — `<role-name>*</role-name>` allows all authenticated users to access admin functionality.
- `XStreamMarshaller` usage without class whitelist — unsafe deserialisation.
- Log4j 1.2.17 — EOL, CVE-2019-17571.
- `JarLoader.java:55-66` — dynamic classloading into production Tomcat.

### Medium
- Java 8 — approaching EOL for LTS; CodeQL requires Java 8 JDK per `codeql-java.yml`.
- Spring Framework (version determined by parent POM) — if Spring 5.x, approaching EOL November 2024.
- `service.tester.smtp.host=mail.ecount.com` — hardcoded legacy host.
- `JdbcUserDao.java:459-484` — SQL statements in an enum (SQL.xxx) — no parameterised query builder; while parameterized (`?`), adding new queries requires code changes.

### Low
- No unit test coverage.
- Swing client and console client both duplicate `XMLServiceTester.java` entry-point class.

## Gen-3 Migration Requirements
1. Replace XStream with Jackson (JSON) or a safe XML library with class whitelisting.
2. Upgrade Log4j 1.x to SLF4J + Logback.
3. Add proper role-based access control (Spring Security) restricting `/admin.html` to admin role.
4. Add CSRF protection (Spring Security CSRF tokens).
5. Remove dynamic JAR loading or restrict to a controlled drop directory with checksum validation.
6. Upgrade Java 8 → Java 21.
7. Replace SMTP host with environment-variable-driven configuration.
8. Containerise (Docker); replace JNDI with Spring Boot DataSource auto-configuration.

## Code-Level Risks
| File | Line | Risk | Severity |
|---|---|---|---|
| `web.xml` | 40–42 | `<role-name>*</role-name>` — admin accessible to all authenticated users | HIGH |
| `XStreamMarshaller.java` | (entire class) | Unsafe XML deserialisation — potential RCE | CRITICAL |
| `JarLoader.java` | 55–66 | Dynamic JAR loading into Tomcat classloader | HIGH |
| `pom.xml` (parent) | log4j 1.2.17 | EOL Log4j with CVE-2019-17571 | HIGH |
| `service-test.context.properties` | 1 | Hardcoded SMTP host `mail.ecount.com` | MEDIUM |
| `JdbcUserDao.java` | 463 | SQL enum with `[user]` — reserved word brackets (SQL Server specific, not portable) | LOW |
