# workbench_WAPP — Enterprise Architect View

## Platform Generation
**Gen-1** — Confirmed legacy generation.

Evidence:
- Java 8, Struts 1.2.8, Spring 2.0.3, Acegi Security (pre-Spring Security), Hibernate 3 with `AnnotationSessionFactoryBean`, Log4j 1.x
- Custom action processor XML framework (`.actionprocessorhandlers.xml`, `.screenmanager.xml`) — bespoke pre-MVC dispatch mechanism
- JSP-based UI with Struts EL tag libraries
- JNDI-based datasource lookup (J2EE era pattern)
- Parent POM `webapp-parent:10.0.0` from `com.citi.prepaid.web` namespace (Citi/Wirecard era)
- SCM URL references `gitlab.com/northlane` (legacy org name)
- Deployment on Windows Tomcat with manual Windows service start/stop

## Business Domain
**Internal Operations Platform** — Configuration Management and Operations Workbench for prepaid card programs.

This is an **internal-facing** application exclusively used by Onbe operations, product management, and configuration teams.

## Role in Platform
- **Primary configuration surface** for the Gen-1 prepaid platform (CBase)
- Acts as the UI layer over the `CbaseappDataSource` operational database
- Coordinates with `JobSchedulerService`, `xAffiliateService`, `xSecurity`, `xPlatform`, and `bankerService` through library/remote service dependencies
- Workbench is the "back-office" counterpart to client-facing portals

## Dependencies
**Runtime (inbound consumers):** None visible — internal tool, not exposed as API

**Runtime (outbound calls):**
| Dependency | Type |
|-----------|------|
| CbaseappDataSource | SQL Server (JNDI) |
| JobSchedulerService | HTTP Invoker (remote call to `${jobscheduler.service.url}`) |
| xSecurity (common/client/web/impl) | Embedded JAR |
| xAffiliateService | Embedded JAR |
| xPlatform | Embedded JAR |
| brandedCurrency (common/impl) | Embedded JAR |
| jobscheduler-common | Embedded JAR |
| banker-common | Embedded JAR |
| autofile-common | Embedded JAR |
| symbol-svc | Embedded JAR |
| spring-dbctx-container | Embedded JAR |
| i18n-utils | Embedded JAR |

## Integration Patterns
- **Spring HTTP Invoker**: Job scheduler integration via `HttpInvokerProxyFactoryBean` pointing to `${jobscheduler.service.url}`
- **JNDI Datasource**: Database connection pooling managed by Tomcat container
- **Spring Remoting (embedded JARs)**: xSecurity, xAffiliate, and other platform services are embedded libraries — tight coupling, no API boundary
- **Stored Procedures**: All database operations via SQL Server stored procedures (DBO schema)
- **Acegi Security Filter Chain**: Authentication filter applied at servlet level

## Strategic Status
**Maintain / Migrate** — This application is in extended maintenance mode.

- No active feature development visible (no SNAPSHOT version changes from CI activity)
- JavaEE-era patterns throughout (Struts, Acegi, Hibernate 3, JNDI)
- Component library versions are frozen at 2016-2020 era
- Critical security debt (MD5 passwords, Log4j 1.x, Acegi Security, no TLS enforcement at app layer)
- Replacement should be a modern Spring Boot-based internal admin application or integration into a Gen-3 admin API

## Migration Blockers
1. **Struts 1.2.8**: End-of-life since 2013; multiple known CVEs; no upgrade path within Struts 1.x; requires full UI rewrite
2. **Acegi Security**: Pre-dates Spring Security; not maintained; must be replaced with Spring Security 6.x
3. **MD5 password encoding**: Must be replaced with modern hash (bcrypt/Argon2) requiring a password migration strategy
4. **Custom action processor framework**: Proprietary XML-driven dispatch mechanism with no standard equivalent; requires mapping all ~100 actions to REST/MVC controllers
5. **Spring 2.0.3 + Hibernate 3**: Cannot be upgraded incrementally to Spring Boot 3.x without intermediate steps; namespace changes (javax → jakarta) require Java 17+ migration
6. **Windows Tomcat deployment**: No container image; migration to containerized deployment requires Dockerfile, externalized secrets, and health endpoint
7. **JNDI datasource**: Must be replaced with application-managed connection pool (HikariCP) for containerized deployment
8. **Embedded legacy JARs** (xPlatform 3.0.3, xSecurity 3.0.3, xAffiliateService 2016.1.1): Likely unavailable in modern Maven repos; source compatibility unknown
