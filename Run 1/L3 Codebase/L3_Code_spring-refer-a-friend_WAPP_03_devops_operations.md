# DevOps / Operations View — spring-refer-a-friend_WAPP

## Build System

- **Build tool**: Maven (no Maven Wrapper; plain `mvn` commands used)
- **Java version**: Java 1.5 source/target (`<source>1.5</source>`, `<target>1.5</target>` in maven-compiler-plugin) — **severely EOL**
- **GroupId**: `com.ecount.one.raf`; **ArtifactId**: `sprint-raf`; **Version**: `1.0-SNAPSHOT`
- **Packaging**: WAR (`<packaging>war</packaging>`); context path `rafstatus`; final name `rafstatus`
- **Key dependencies**:
  - `org.springframework:spring:2.0.2` — Spring Framework 2.0.2 (**2007; severely EOL**)
  - `log4j:log4j:1.2.9` — Log4j 1.x (**EOL since 2015; CVE-2019-17571 and others**)
  - `net.sf.jtds:jtds:1.2` — jTDS JDBC driver (**EOL; limited TLS 1.2 support**)
  - `xstream:xstream:1.1` — XStream 1.1 (**severely EOL; multiple RCE CVEs**)
  - `ehcache:ehcache:1.2beta4` — Ehcache 1.2 beta (**pre-release from ~2005; EOL**)
  - `taglibs:standard:1.1.2` — JSTL standard tag library
  - `javax.servlet:servlet-api:2.4` — Servlet API 2.4 (2003 era)
  - `junit:junit:3.8.1` — EOL
- **Notable**: `spring-dbctx-mock:1.0.1-SNAPSHOT` is listed as a production dependency (not test scope) — a mock implementation is on the production classpath
- **Embedded Jetty**: `maven-jetty-plugin:6.0.2` configured for local development; `contextPath=/sprintstatus`

## CI/CD Pipeline

- **GitHub Actions**: `.github/workflows/codeql.yml` — CodeQL static analysis (Java)
- **Dependabot**: `.github/dependabot.yml` — automated dependency update PRs
- **No deployment workflow**: No GitHub Actions deployment pipeline observed
- **No GitLab CI**: No `.gitlab-ci.yml` present
- **SCM**: SVN (`ecsvn.office.ecount.com`) — the original source control was SVN, not Git; this repository is likely a Git mirror of an SVN checkout

## Deployment Model

- **Artifact type**: WAR file (`rafstatus.war`)
- **Target container**: JBoss (`.github/workflows` deploys to JBoss per `src/main/webapp/WEB-INF/jboss-web.xml`); Jetty for local development
- **Context path**: `/rafstatus` (Jetty) or per `jboss-web.xml` configuration
- **Current deployment status**: Unknown — likely dormant/decommissioned given the Sprint brand and 2007-era dependencies

## Runtime

- **Java**: 1.5 source compatibility; runtime JVM version unknown (likely running on Java 8 or older)
- **Application server**: JBoss (per `jboss-web.xml`); development on embedded Jetty 6.0.2
- **Spring**: 2.0.2 (no Spring Boot; pure Spring MVC with XML configuration)
- **Logging**: Log4j 1.2.9 (EOL; CVE-vulnerable) configured in `src/main/webapp/WEB-INF/log4j.properties`
- **Web framework**: Spring MVC `SimpleFormController` (deprecated in Spring 3.x; removed in Spring 4.x)

## Secrets Management

- JDBC connection credentials are managed via `spring-dbctx-mock` (mock) and the Spring XML context (`rafContext.xml`)
- No secrets management integration observed
- The SCM URL in `pom.xml` points to an internal SVN server that may no longer be accessible
- Database credentials in the Spring XML context (`datasourceTestContext.xml`) may contain plaintext test credentials

## Observability

- **Logging**: Log4j 1.2.9 to application log; phone numbers logged at INFO level (PII concern)
- **No metrics**: No monitoring hooks
- **No health endpoint**: No Actuator or equivalent
- **No alerting**: Monitoring responsibility on the application server (JBoss admin)
- **Maintenance mode**: Controlled via URL parameter (`site_admin=maintenance`) — not a proper operational control

## Known EOL Runtimes and CVEs

This application has the most severe EOL/CVE profile of the repositories analyzed:

- **XStream 1.1**: CVE-2021-21345, CVE-2021-21346, CVE-2021-21347, and many others — **Remote Code Execution** via Java object deserialization. Any untrusted input processed through XStream is a critical vulnerability. Versions prior to 1.4.18 are affected by multiple critical CVEs.
- **Log4j 1.2.9**: CVE-2019-17571 — deserialization vulnerability in `SocketServer`. Log4j 1.x is EOL since 2015.
- **Spring 2.0.2**: Spring Framework from 2007; numerous unpatched CVEs including CSRF, XSS, and injection vulnerabilities.
- **Ehcache 1.2beta4**: Pre-release beta from 2005; completely unmaintained.
- **jTDS 1.2**: EOL JDBC driver; limited TLS support; no security patches.
- **Java 1.5 source target**: Java 5 is EOL since 2009; compiling against Java 5 APIs limits the use of security improvements in later Java versions.
- **`spring-dbctx-mock` in production scope**: Mock implementations on the production classpath could allow bypassing of real database connection validation.
- **Strategic recommendation**: This application should be **decommissioned** if the Sprint RAF program is no longer active. If it is still serving users, an emergency remediation is required: at minimum, XStream must be updated or removed, Log4j 1.x replaced with Log4j 2.x or Logback, and the unauthenticated maintenance mode control must be removed or secured.
