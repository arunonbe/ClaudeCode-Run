# Solution Architect Report — message-center_SVC

## 1. Solution Architecture Summary

`message-center_SVC` is a three-module Maven WAR service built on the Gen-2 eCount platform. The solution architecture layers are:

```
HTTP/XML-RPC Consumer (MPV, ClientZone)
        │
        ▼
Tomcat 10.1.28 Servlet Container (port 80)
        │
        ▼
XML-RPC Dispatcher  ←──  xsecurity-web filter chain
        │
        ▼
MessageCenterCoreServiceImpl  (message-impl)
        │  implements IMessageCenterCoreService + IMessageApplicationService
        ▼
MessageBusinessLogicImpl  (IMessageBusinessLogic)
        │
        ▼
MessageDAOImpl  (IMessageDAO)
        │  delegates to 10 StoredProcedure beans
        ▼
Director-managed DBCP connection pool  →  SQL Server (cbaseapp database)
```

All wiring is through Spring XML: `MessageCenter-datasource.xml` defines all beans; there is no `@Component` scanning or Java configuration.

## 2. Module Responsibilities

### message-common
Provides the public contract: two service interfaces (`IMessageCenterCoreService`, `IMessageApplicationService`), the `MessageServiceClient` XML-RPC stub, and all DTO classes. This module is the shared library consumed by upstream callers.

### message-impl
Contains all business logic and data access implementation. The DAO layer uses Spring's `StoredProcedure` abstraction to call SQL Server stored procedures. The `MessageBusinessLogicImpl` class mediates between the service interface and the DAO, performing any necessary DTO transformation.

### message-service
The deployable artifact. Contains only the Spring XML context files, the Tomcat server.xml, the QA certificate, and the health check class. The `--applicationContextMessage.xml` file (with the `--` prefix, effectively disabled) represents a legacy context configuration that has been superseded by `MessageCenter-datasource.xml`.

## 3. Security Design

Security is handled by the `xsecurity-web:4.0.3` library (`com.ecount.service.xsecurity`) registered as a Servlet filter via the `ForceInitialLog_xsecurity` bean. This is a Gen-2 internal security framework. Key observations:

- **No JWT/OAuth2**: There is no Spring Security OAuth2 resource server configuration. Authentication at the application layer is managed by the `xsecurity-web` library, which likely validates a session token or shared secret against a directory service.
- **TLS**: The `server.xml` in `message-service/config/` configures the Tomcat connector. The QA certificate is injected into the JVM trust store at image build time (Dockerfile line 20).
- **Credentials**: All database credentials flow through the Director service at runtime; none are in the repository. This is the Gen-2 equivalent of a secrets manager.

## 4. Health and Availability

`HealthCheck.java` in `message-service/src/main/java/com/onbe/messagecenter/health/` provides a simple HTTP health endpoint for load balancer probes. No Actuator dependency; this is a manually implemented endpoint.

The deployment workflow (`deployment.yml` line 23) uses `java-workflow.yml@main` which publishes to the Onbe legacy CI infrastructure rather than Azure Container Apps. No Kubernetes liveness/readiness probes are configured.

## 5. Known Technical Debt

| Issue | Location | Severity | Impact |
|---|---|---|---|
| Duplicate Spring XML context files | `message-service/src/main/resources/` | Medium | Confusion during config changes; wrong file could be activated |
| Raw `ArrayList` return types | `MessageCenterCoreServiceImpl.java` lines 40, 43 | Low | Runtime `ClassCastException` risk if stored procedure return type changes |
| Tomcat downloaded at build time | Dockerfile line 8 | Medium | Non-reproducible builds; pipeline failure on network outage |
| Tests skipped in CI | `deployment.yml` line 33 | High | No regression safety net before production deployment |
| `changeit` keystore password | Dockerfile line 20 | Medium | Default password on production JVM trust store |
| Two versions of XML-RPC bean wiring | Both XML context files | Medium | One file uses `StoredProcXxx` naming, the other `XxxSP` naming — must stay in sync |
| `@author: OFSS` comment | `MessageCenterCoreServiceImpl.java` line 26 | Info | Indicates external authorship (Oracle Financial Services Software); IP provenance should be confirmed |

## 6. Upgrade Path Recommendations

1. **Short-term**: Confirm which of the two XML context files is active and remove the unused one. Add integration tests and remove `Dmaven.test.skip` from CI args.
2. **Medium-term**: Replace the XML-RPC client interface with a REST API wrapper (Spring MVC `@RestController`) so MPV and other Gen-3 consumers can migrate off the XML-RPC dependency without a full service replacement.
3. **Long-term**: Replace this service with a Gen-3 Spring Boot microservice using `nexpay-parent`, PostgreSQL/Azure SQL, Flyway migrations, Azure App Configuration, and a REST API. Migrate the SQL Server stored procedures to JPA repository methods.

## 7. Security Risks Summary

| Risk | Category | PCI DSS Relevance |
|---|---|---|
| Default `changeit` keystore password | Credential | Req 8 (Authentication) |
| Tests skipped in CI | Quality gate | Req 6.3 (Security testing) |
| No audit log of message mutations | Audit | Req 10 (Logging) |
| PII potentially in message body without field-level controls | Data protection | Req 3 (CHD protection) |
| Tomcat version pinned to 10.1.28 — may have known CVEs | Patch management | Req 6.3 (Vulnerability mgmt) |
