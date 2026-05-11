# service-tester_WAPP — Enterprise Architect View

## Platform Generation
**Gen-1.** Spring MVC (XML configuration), Java 8, Log4j 1.x, JSP/Servlet, Tomcat WAR deployment, XStream XML marshalling, Apache Commons HttpClient, JNDI DataSource. Original SCM: GitLab at `northlane/development/application-development/application/service-tester`. No containerisation, no REST APIs (internal), no modern observability.

## Business Domain
**Developer/QA Tooling / Internal Testing Infrastructure.** Not part of the payments processing domain. Supports the development and testing of the Onbe service layer.

## Role in Platform
An internal integration testing console that wraps the platform's Spring-based services and exposes them via a browser UI. Historically used by developers and QA engineers to manually invoke service methods without needing a full client application. In modern platforms, this role is fulfilled by API gateway dev portals, Postman collections, or GraphQL explorers.

## Dependencies
### Consumes
| Dependency | Direction | Notes |
|---|---|---|
| All deployed Spring service beans | Inbound configuration | Configured in Spring XML contexts loaded at runtime |
| SQL Server | Outbound | User/access management |
| SMTP (mail.ecount.com) | Outbound | Email notifications |
| GitLab CI templates | Consumes | `northlane/development/.../ci-templates` |

### Produces
- WAR artefacts: `service-test-web-admin` (admin portal), `service-test-web` (user portal).

## Integration Patterns
- **Spring XML IoC**: Services injected via XML application contexts.
- **Reflection-based invocation**: `DynamicMethodLoader` uses Java reflection to discover and invoke service methods.
- **XStream XML marshalling**: `XStreamMarshaller` for serializing/deserializing service method inputs/outputs.
- **Runtime classloading**: `JarLoader` / `ContextFactory` for loading service JARs dynamically.
- **JDBC**: `JdbcDaoSupport` for user/access persistence.

## Strategic Status
**Legacy / Low Strategic Value — Candidate for Decommission.**
- Java 8, Log4j 1.x, XStream (known CVEs), XML-heavy configuration.
- Replaced functionally by API documentation tools (Swagger UI on individual services), Postman/Newman test suites, or integrated test environments.
- If still required for a specific testing workflow, it should be restricted to non-production environments only (never deployed to production).
- SCM history on GitLab (northlane org) may indicate this repo was not migrated to Onbe's GitHub and is maintained in a shadow state.

## Migration Blockers
- Tight coupling to Spring XML service configurations — re-platforming requires re-expressing all service contexts.
- Log4j 1.x dependency must be removed before any modernisation.
- XStream marshaller has known unsafe deserialisation vulnerabilities.
- Runtime JAR loading pattern is incompatible with containerised deployments.
- SMTP and JNDI references to legacy hostnames (`mail.ecount.com`, Nexus at `wirecard.sys`).
