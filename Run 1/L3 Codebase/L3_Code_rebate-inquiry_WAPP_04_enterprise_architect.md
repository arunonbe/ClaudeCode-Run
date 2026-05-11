# Enterprise Architect Analysis: rebate-inquiry_WAPP

## Platform Generation
**Gen-1** — Legacy Java EE WAR application.

Indicators:
- Apache Struts 1.2.7 MVC framework (released 2005; End-of-Life)
- Java 8 source/target
- xdoclet code generation (circa 2003 technology)
- JBoss deployment descriptor (`jboss-web.xml`)
- Spring 2.x XML bean configuration (DTD-based `spring-beans.dtd`)
- Dependency on cbase/eCount internal platform libraries (pre-Onbe era)
- Hard-coded Windows filesystem paths
- Log4j 1.x
- Maven Nexus at Wirecard infrastructure hostname

## Business Domain
**Consumer Payments — Rebate & Prepaid Card Fulfillment Support**

Specifically: cardholder self-service inquiry channel for undelivered rebate and prepaid debit cards, supporting the fulfillment/disbursement business domain.

## Architectural Role
Thin consumer-facing web front-end for a narrow use case: form capture + email dispatch. There is no business logic beyond form validation and email routing. The application is a channel adapter — it bridges the web UI to the internal email notification infrastructure (cbase NotificationManagerImpl).

## Internal Dependencies
| Component | Type | Coupling |
|---|---|---|
| `com.ecount:xPlatform:2.5.37` | Internal library (Gen-1 platform) | Direct; provides Member, NotificationManagerImpl, IEmailNotification |
| `struts:struts:1.2.7` | Framework | Direct; entire MVC layer |
| `javax.mail:mail:1.4` | JavaMail | Provided scope; relies on app-server mail session |
| `log4j:log4j:1.2.17` | Logging | Direct |

## Integration Patterns
- **Email notification**: Fire-and-forget outbound email via cbase `NotificationManagerImpl`. No acknowledgement or retry beyond the silent catch block.
- **File-based configuration**: Properties file loaded at startup via Spring `PropertyPlaceholderConfigurer`. No dynamic config refresh.
- **No inbound API**: Application is purely browser-driven; no machine-to-machine interface.

## Strategic Status
**Retire / Replace** — This application is a Gen-1 legacy artifact with no strategic investment value:
- Struts 1 is EOL (Apache ended support in 2013).
- xdoclet is obsolete.
- Java EE WAR on JBoss is not aligned with current containerised microservice strategy.
- Functionality is extremely narrow (form + email) and could be replaced by a lightweight Spring Boot service or a no-code form platform.
- No active development evidence in the codebase (version stuck at 2.0.2-SNAPSHOT).

## Migration Blockers
1. **cbase/xPlatform library dependency**: `com.ecount:xPlatform:2.5.37` must be decomposed or wrapped before migrating; `Member` and `NotificationManagerImpl` classes need replacement.
2. **JBoss-specific deployment**: `jboss-web.xml` requires JBoss/WildFly; migration requires containerisation.
3. **Hard-coded filesystem config paths**: Must be replaced with environment variables, Kubernetes ConfigMaps, or Azure App Configuration.
4. **Log4j 1.x**: Must be replaced with SLF4J + Logback or Log4j 2 before containerisation.
5. **Struts 1 MVC**: Complete rewrite required to move to Spring MVC, Spring Boot, or a modern front-end framework.
6. **Stale SCM/Nexus references**: Nexus and SVN URLs reference decommissioned Wirecard infrastructure.
