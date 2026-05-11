# bmcwizard_WAPP — Enterprise Architect View

## Platform Generation (Gen-1/Gen-2/Gen-3)

**bmcwizard_WAPP is a Gen-1 application.**

Evidence:
- **Spring 2.0.3** (2007) and **Acegi Security** (pre-Spring Security, ~2006–2008): This is the original ecount/Citi Prepaid technology stack, predating any modern platform redesign.
- **Struts 1.3.8** MVC framework — Struts 1 reached EOL in 2013. No REST/JSON APIs; all interactions are browser-based form submissions via `*.do` URL patterns.
- **xdoclet code generation** — Struts action and validation XML generated from Java doclet annotations at build time. This pattern was prevalent in early 2000s Java EE development.
- **Parent POM: `com.citi.prepaid.web:webapp-parent:10.0.0`** — The `citi.prepaid` groupId indicates this originated in the Citi Prepaid / ecount era, predating Onbe's rebranding.
- **Artifact version `2.1.4-SNAPSHOT`** with legacy internal library versions (`xPlatform:7.0.27`, `brandedCurrency:2016.1.1`, `jobscheduler-common:2016.1.1`) — library versions frozen circa 2016–2019.
- **Windows-only, D:-drive absolute paths** throughout configuration files — characteristic of Gen-1 on-premise Windows Server deployment model.
- **All database access via stored procedures** — Gen-1 pattern; no ORM-driven schema management.
- **No REST APIs, no microservices, no message queues visible** in this application.
- **`nam.wirecard.sys` domain** — Infrastructure domain from the Wirecard/ecount era, not yet migrated.

## Business Domain

**Program Configuration & Operations Setup** — Internal back-office tooling for the Onbe prepaid card platform.

This application sits in the **Platform Configuration** domain. It does not process transactions, manage cardholders, or disburse funds directly. Instead, it is the system of record for how prepaid card programs are configured — determining which fees apply, what card settings govern issuance, what regulatory limits are enforced, what notification events fire, and which roles can access which programs.

Downstream domains that depend on correct Wizard configuration:
- **Card Processing** — card platform, expiry, PIN settings, access levels
- **Fee Processing** — fee structures, grace periods, dormancy schedules
- **ACH/Disbursement** — ACH details, funding controls, balance sweep, addenda
- **Notifications** — email/SMS event templates
- **Compliance** — escheatment rules, regulatory load/balance limits
- **CDE / Cardholder Data** — embossing profiles determine data sent to card manufacturers
- **Reporting** — CZ reports configuration

## Role in Platform

bmcwizard_WAPP is the **primary program lifecycle management UI** for the legacy ecount platform. It is:

1. **The sole GUI** for setting up new prepaid programs before they can accept cardholders.
2. **The sole GUI** for configuring program-level fee, card, ACH, notification, regulatory, and escheatment parameters.
3. **A delegator** — it does not own its data schemas directly; it writes configuration through the `xPlatform` stored procedure layer into the core ecount databases (`CbaseappDataSource`, `EcountCoreDataSource`).
4. **Not a transactional system** — it configures programs; it does not process card transactions or move money.
5. **The CZ (client zone) admin portal** — configures hierarchy, roles, instant issue, and user access for client-facing zones.

There is no API for external systems to call into this application. It is purely operator-facing.

## Dependencies

### Inbound (who calls bmcwizard_WAPP)
- **Human operators** (Onbe operations, client admins) via web browser.
- No machine-to-machine callers identified.

### Outbound (what bmcwizard_WAPP calls)

| Dependency | Type | Version | Notes |
|---|---|---|---|
| `xPlatform` (ecount core) | Library (JAR) | 7.0.27 | All profile/business object classes (`com.cbase.business.ecount.profile.*`). The most critical dependency. |
| `xSecurity` service | Library (JAR) + Spring beans | 3.0.5 | Authentication, user management, password management, privilege management |
| `xAffiliateService` | Library (JAR) | 2019.1.3 | Affiliate/skin management via Hibernate |
| `httpCryptoService` | Library + HTTP | 1.3 | PGP key operations on remote crypto servers |
| `symbol-svc` | Library (JAR) | 1.0.0 | Symbol/lookup value service used for dropdowns |
| `jobscheduler-common` | Library + XML-RPC | 2016.1.1 | Job scheduler for batch operations |
| `notification` service | Library (JAR) | 1.0.1 | Email/SMS notification engine |
| `brandedCurrency` | Library (JAR) | 2016.1.1 | Branded/loyalty currency support |
| `screenconfigs` | Library (JAR) | 2016.2.1 | Screen configuration service |
| `ecount-system` | Library (JAR) | 1.0.7 | Core system utilities |
| `director-client` | Library (JAR) | 1.0.9 | Present but commented out in active config |
| `banker-common` | Library (JAR) | 2.1 | Banking utilities |
| `MessageCenter` client | Library | 1.0.1 | Message center service |
| Microsoft SQL Server | Database | JDBC 1.1 | All four databases (CbaseappDataSource, NotificationServiceDataSource, JobSvcDataSource, EcountCoreDataSource) |
| PGP Crypto Servers | HTTP | N/A | External crypto servers accessed via `HTTPCryptoServiceClient` |
| Job Scheduler | XML-RPC | N/A | External job scheduler service |

### Internal Library Coupling

The `com.cbase.*` and `com.ecount.*` package namespaces span both this WAR's source code and the external JAR dependencies. The `xPlatform` JAR provides all the `com.cbase.business.ecount.profile.*` classes that form the core business objects. This means the application cannot be updated independently of the platform libraries — a version change in `xPlatform` can break all profile-related functionality.

## Integration Patterns

1. **Stored Procedure Pattern** — All database write and read operations use Spring `StoredProcedure` subclasses. No SQL strings embedded in Java code (consistent with the xPlatform architecture). This is a tightly coupled integration to the SQL Server schema.
2. **Spring XML Bean Wiring** — All dependencies injected via Spring 2.0 XML. No annotations-based DI in the Wizard-specific code (annotations used only in xAffiliateService Hibernate entities).
3. **Struts MVC** — Browser → `ActionServlet` → `Action` → `Business Impl` → `Helper` → `DAO/StoredProc` → DB. A classic layered MVC with deep delegation chains.
4. **Service Library Pattern** — Business services (security, notification, affiliates, crypto) are consumed as compiled JAR libraries wired via Spring, not as network microservices with APIs (except for httpCryptoService which makes HTTP calls, and JobScheduler which uses XML-RPC).
5. **JNDI Data Source Pattern** — All database connections obtained from container JNDI registry. No connection pooling configuration in the WAR itself.
6. **EhCache for read-through** — Country names lookup table cached in-process to reduce database round-trips.
7. **XML-RPC** — Job scheduler communication via classic XML-RPC (`xmlrpc:1.0.9`).

## Strategic Status

**Status: Legacy / Maintain-only — High migration priority.**

- The application is in active use and receives incremental updates (version 2.1.4-SNAPSHOT, GitHub Actions CI active, CodeQL scanning active).
- It is not being modernized within this repository — all technology decisions (Spring 2, Struts 1, Java 8, Acegi) are unchanged.
- The `hideDeprecatedFields` feature flag and cleanup of deprecated card configuration fields suggests some ongoing rationalization work.
- The dual CI system (GitLab + GitHub Actions) is a migration artifact — GitHub Actions is the current CI target.
- The `pom.xml` parent `com.citi.prepaid.web:webapp-parent` retains legacy Citi branding, indicating the base infrastructure has not been replatformed.
- Server names in `nam.wirecard.sys` indicate pre-migration infrastructure.

## Migration Blockers

The following represent significant obstacles to replacing or modernizing this application:

1. **`xPlatform` JAR (7.0.27) API lock-in** — The entire business logic depends on opaque internal classes in `com.cbase.business.ecount.profile.*`. These classes (FDRCardProfileClass, EMEAProfileClass, AppGlobalEscheatmentProfileClass, etc.) encapsulate all stored procedure calls. No REST API or modern interface exists. Migration requires either reverse-engineering these APIs or replacing them.

2. **Stored procedure ownership** — Business logic is split between Java and ~100+ SQL Server stored procedures in three databases. The stored procedures are not in this repository. Migrating to a Gen-3 architecture requires identifying, documenting, and rewriting all these procedures.

3. **Java 8 + Struts 1 + Spring 2 + Acegi** — Five major framework versions that are all EOL. Upgrading each has breaking changes. Spring 2 → Spring 6 is not a drop-in upgrade. Struts 1 has no upgrade path to Struts 2 or Spring MVC without a full rewrite.

4. **xdoclet code generation** — Struts config generated from doclet annotations. This pattern is deprecated and unsupported in modern toolchains.

5. **Windows-only filesystem paths** — Containerization (Docker/Kubernetes) requires Linux compatibility. All `D:\c-base\...` references, `Cp1252` source encoding, and Windows service-based deployment must be replaced.

6. **Session-based security (Acegi/cookie)** — Stateful session-based auth with remember-me cookies. Migration to stateless JWT/OAuth2 requires complete auth layer replacement.

7. **Tight coupling to internal domain libraries** — All of `xSecurity`, `xAffiliateService`, `brandedCurrency`, `ecount-system` are internal private JARs with no public API documentation visible in this repo. Replatforming requires parallel migration of all these services.

8. **No existing API surface** — Since the application has no REST API, there is no strangler-fig migration path. A parallel Gen-3 replacement must be built and operated alongside until full feature parity is reached.

9. **xdoclet merge files in `src/main/xdocletmerge/web/`** — Global exceptions, forwards, validation rules defined in separate XML merge files; these must be manually migrated to a modern framework's configuration model.
