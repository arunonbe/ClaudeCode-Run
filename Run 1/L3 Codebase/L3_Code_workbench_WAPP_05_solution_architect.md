# workbench_WAPP — Solution Architect View

## Technical Architecture
- **Framework stack**: Spring 2.0.3, Struts 1.2.8, Acegi Security, Hibernate 3 (AnnotationSessionFactory), Velocity 1.4
- **Runtime**: Java 8, Tomcat 8.5.5.7, WAR packaged as `ROOT.war`
- **Web tier**: JSP + JSTL + Struts EL tags + jenkov-prizetags + displaytag
- **Persistence tier**: Spring JDBC `StoredProcedure` + Hibernate 3 ORM (affiliate entities only)
- **Security tier**: Acegi Security filter chain with MD5 password encoder
- **Remoting**: Spring HTTP Invoker for JobSchedulerService; Apache Axis 1.4 for SOAP calls
- **Caching**: EhCache (in-process, single-node)
- **Modules**: Single monolithic WAR

## API Surface
This application does not expose an external API. It is a server-side rendered web application (JSP/Struts MVC). All interactions are HTTP form-post based, navigating via `.do` action URLs.

**Inbound interface:**
- HTTP form-post to `*.do` endpoints (Struts)
- File upload via `commons-fileupload 1.3.1`
- Authentication via `j_acegi_security_check` servlet path

**Outbound remote calls:**
- Spring HTTP Invoker to `${jobscheduler.service.url}` (interface: `JobSchedulerService`)
- Apache Axis SOAP client (axis 1.4) — exact endpoints not visible in this snapshot; likely used by internal service libraries

## Security Posture

### Authentication
- Acegi Security `DaoAuthenticationProvider` with custom `minimalUserDetailsService`
- Password encoded with `EcountMd5PasswordEncoder` — MD5, no salt visible in configuration
- File: `applicationContext-xsecurity-web.xml`, lines 119–131 (auth provider), line 135 (password encoder)

### Authorisation
- Role-based access via `FilterSecurityInterceptor` and `objectDefinitionSource`
- File: `applicationContext-xsecurity-thebridge-web-dao.xml`, lines 32–53
- Roles: `ROLE_REPORTS`, `ROLE_VIEW_PROGRAM`, `ROLE_DASHBOARD`, `ROLE_ORDER_HISTORY`, `ROLE_INENTORY_VIEW`, `ROLE_INSTANT_ISSUE_ADHOC_REORDER`
- Catch-all `/\*\*` mapped to `ROLE_REPORTS,ROLE_VIEW_PROGRAM,ROLE_DASHBOARD` — overly broad

### Crypto
- MD5 password hashing: cryptographically broken (pre-image attacks feasible) — `EcountMd5PasswordEncoder`
- No evidence of field-level encryption at-rest for stored config values
- `forceHttps=false` (`applicationContext-xsecurity-web.xml` line 99) — application does not redirect HTTP to HTTPS

### Secrets Management
- External properties file on server filesystem: `d:/c-base/config/workbench/application.properties`
- JNDI datasource credentials managed by Tomcat `server.xml` (outside this repo) — no vault or secrets manager
- No environment variable injection or Kubernetes secrets visible

### Known CVE Risks
| Component | Version | Risk |
|-----------|---------|------|
| Log4j 1.x | 1.2.17 | CVE-2019-17571 (deserialization RCE via SocketAppender); EOL since 2015 |
| Struts 1.x | 1.2.8 | Multiple known CVEs; EOL since 2013; OGNL injection risks |
| Apache Axis | 1.4 | CVE-2012-5784, CVE-2014-3596 (MITM, XML signature wrapping); EOL |
| Spring | 2.0.3 | Extremely old; SpEL injection not applicable at this version but no security patches |
| commons-fileupload | 1.3.1 | CVE-2016-1000031 (DiskFileItem deserialization RCE) |
| commons-collections | 3.2 | CVE-2015-4852, CVE-2015-7501 (deserialization gadget chain — critical if ObjectInputStream used) |
| Acegi Security | Any | Unmaintained; superseded by Spring Security |

## Technical Debt
1. **Framework EOL stack**: Struts 1.x, Acegi Security, Spring 2.x, Hibernate 3, Log4j 1.x, Axis 1.4 — all end-of-life with unpatched CVEs
2. **Bespoke XML dispatch framework**: ~100 action handlers in `workbench.actionprocessorhandlers.xml`; no standard pattern; high maintenance cost
3. **Duplicated action registrations**: `fileprocesswitherrors` and `filesubmittedremove` actions appear twice in `workbench.actionprocessorhandlers.xml` (lines 16–34)
4. **MD5 password hashing**: Security debt with compliance impact
5. **No unit test coverage in CI**: Tests explicitly skipped (`-Dmaven.test.skip=true`)
6. **External config file dependency**: Server-local properties file breaks immutable infrastructure principle
7. **No health-check endpoint**: CI uses root `/` as health probe which is a JSP login page
8. **Commented-out code**: `WorkBenchDaoAuthenticationProvider` commented out in auth manager config (line 113 `applicationContext-xsecurity-web.xml`)

## Gen-3 Migration Requirements
1. Rewrite UI as React SPA (consistent with `oneplatform-react_WAPP` pattern in this estate) calling REST APIs
2. New Spring Boot 3.x (Java 21) REST API backend with Spring Security 6.x replacing Acegi
3. Replace MD5 with bcrypt/Argon2 password hashing; implement password migration flow
4. Expose all operations as RESTful endpoints with JWT or OAuth2 authentication
5. Replace all embedded library dependencies with versioned API clients
6. Containerise (Docker) with externalized secrets via Azure Key Vault or similar
7. Implement structured logging (log4j2/logback with JSON output) and OpenTelemetry traces
8. Replace Spring HTTP Invoker with REST or gRPC for JobSchedulerService integration
9. Implement maker-checker workflow for configuration changes
10. Replace JNDI datasource with HikariCP application-managed pool

## Code-Level Risks (file:line references)
| Risk | File | Line |
|------|------|------|
| `forceHttps=false` — no TLS enforcement | `src/main/resources/applicationContext-xsecurity-web.xml` | 99 |
| MD5 password encoder | `src/main/resources/applicationContext-xsecurity-web.xml` | 135 |
| External properties override on disk | `src/main/resources/application.properties` | 4 |
| Duplicate action registrations | `src/main/resources/workbench.actionprocessorhandlers.xml` | 16–34 |
| Log4j 1.2.17 dependency | `pom.xml` | 33 |
| Apache Axis 1.4 dependency | `pom.xml` | 44 |
| commons-fileupload 1.3.1 | `pom.xml` | 52 |
| commons-collections 3.2 | `pom.xml` | 43 |
