# Enterprise Architect View — spring-refer-a-friend_WAPP

## Platform Generation

**Gen-1 (eCount/Citi lineage), extreme legacy**. This is one of the oldest observable applications in the Onbe codebase:

- SVN source control origin (`ecsvn.office.ecount.com`) — predates Git adoption
- Java 1.5 compilation target (2004 era)
- Spring 2.0.2 (2007)
- XStream 1.1, Ehcache 1.2beta4 — pre-2006 libraries
- Sprint brand — the Sprint prepaid card program under eCount/Citi predates the Wirecard era
- `SimpleFormController` — a Spring MVC class deprecated in Spring 3 (2009) and removed in Spring 4 (2013)

This application represents the absolute oldest end of the Gen-1 spectrum — earlier than most other Gen-1 artifacts in the portfolio.

## Integration Patterns

- **Spring MVC (SimpleFormController)**: HTTP form submission and response rendering via JSP templates. No REST interface.
- **Direct JDBC (jTDS driver)**: SQL Server access via the jTDS JDBC driver — no ORM, no stored procedure abstraction framework beyond Spring JDBC templates
- **Ehcache in-process**: Referral lookup results cached in JVM memory keyed by phone+year
- **XStream serialization**: Used for debugging/logging serialization of `RAFRequest` objects (not as a primary data exchange format)
- **Axis WSDD**: `server-config.wsdd` in `WEB-INF/` suggests Axis web service deployment descriptor — the application may have exposed a SOAP/Axis web service endpoint in addition to the Spring MVC form interface
- **No XML-RPC**: Unlike other Gen-1 services, this application uses Spring MVC directly rather than the eCount XML-RPC pattern

## External Dependencies

| System | Interface | Status |
|---|---|---|
| SQL Server (sprint_referral tables) | JDBC (jTDS 1.2) | EOL driver |
| JBoss application server | WAR deployment | Legacy target |
| Ehcache | In-process JVM | EOL (1.2 beta) |
| Sprint brand assets | Static images | Dormant program |
| eCount SVN | Source control | Defunct (migrated to Git) |

## Position in the Broader Platform

```
CSA / Program Admin (browser)
  → spring-refer-a-friend_WAPP (Spring MVC WAR)
    → SQL Server (Sprint RAF tables)
    → eCount card service (via PlasticInfo, if active)
```

This application is an **isolated, single-purpose web application** with no known consumers or dependents. It does not serve as an infrastructure dependency for other services — it is a standalone feature application for the Sprint RAF program.

The `jboss-web.xml` and Axis WSDD configuration suggest it was deployed alongside other JBoss-based Gen-1 applications on a shared application server. If that shared JBoss server hosts other active applications, the CVE profile of this application represents a risk to the entire server.

## Migration Blockers

1. **SVN origin**: The codebase has not been materially updated since it was migrated from SVN to Git. No active development team appears to own it.
2. **Dormant program**: If the Sprint RAF program is no longer active, there is no business case for migration — the application should be decommissioned.
3. **No tests**: No viable automated test suite (JUnit 3.8.1 tests are likely not passing in a modern Maven environment).
4. **Spring 2.0.2**: Cannot be upgraded to Spring Boot without a complete rewrite.
5. **Axis WSDD**: If any SOAP endpoints are active, consumers must be identified and migrated before decommissioning.

## Strategic Status

**Decommission immediately** (or emergency remediation if still serving active users).

- **If the Sprint RAF program is terminated**: Shut down the application, archive the database records per the applicable data retention schedule (GLBA, NACHA), and remove the deployment from the JBoss server.
- **If the Sprint RAF program is still active** (unlikely): Emergency remediation required:
  1. Remove XStream or upgrade to 1.4.18+ with security configuration
  2. Replace Log4j 1.x with Logback
  3. Mask phone numbers in all log statements
  4. Remove or authenticate the `site_admin` maintenance mode control
  5. Replace jTDS with Microsoft JDBC driver
  6. Assess and terminate if the business value does not justify remediation cost

The security risk profile (XStream RCE, Log4j deserialization, unauthenticated maintenance mode, phone number logging) makes this application unsuitable for continued production operation without immediate remediation.
