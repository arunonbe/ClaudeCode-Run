# Enterprise Architect View — subaru-rewards_WAPP

## Platform Generation
**Gen-1** — Legacy J2EE / Spring 2.x era. Characteristics:
- Spring 2.0.2 dependency (released 2007).
- Spring XML DTD bean configuration (`<!DOCTYPE beans PUBLIC "-//SPRING//DTD BEAN//EN">`).
- Spring Modules cache integration (unmaintained since ~2009).
- Apache Commons Logging + Log4j 1.x.
- VBScript scheduled task launcher.
- SQL queries hardcoded as Spring XML `<value><![CDATA[...]]>` properties.
- SCM origin was SVN.
- No REST/HTTP API surface — batch processing only.
- JAXB for XML marshalling.
- No Spring Boot, no microservices patterns.

## Business Domain
**B2B Automotive Incentives / Dealer Rewards** — Specific to Subaru of America partnership. Calculates and pays rewards to Subaru dealership salespersons for vehicle sales under Ascent and Summit incentive programmes.

## Role in Ecosystem
- Standalone batch processing application (not a shared library).
- Consumes sales data ingested into the `cbaseapp` SQL Server database.
- Produces XML payment request files consumed by the Onbe payment platform (AddFunds, CreateAccount, SPIN).
- Interacts with no other microservices directly (file-based integration with payment platform).

## Dependencies
| Type | Artifact | Notes |
|------|----------|-------|
| Runtime | Spring Framework 2.0.2 | Critically EOL |
| Runtime | Spring Modules (cache) | Unmaintained |
| Runtime | EHCache 1.x | Legacy; EHCache 3.x is current |
| Runtime | Apache Commons Logging | Bridges to Log4j 1.x |
| Runtime | JAXB | XML marshal/unmarshal for payment request files |
| Build | `com.parents:service-parent:9.0.0` | External parent POM |
| Data | MS SQL Server `cbaseapp` | All application data |
| Downstream | Onbe payment platform | Receives XML payment request files |

## Integration Patterns
| Pattern | Details |
|---------|---------|
| Batch processing | State machine driven; single-threaded batch run triggered by scheduler |
| File-based integration | XML request files written to filesystem; payment platform picks up files |
| Direct JDBC | All DB access via Spring JdbcTemplate / StoredProcedure wrappers |
| EHCache | In-process read-through cache for reference data |
| VBScript scheduler | Windows-only scheduled task invocation |

## Strategic Status
**High-risk legacy system requiring modernisation.** This application:
- Uses Spring 2.0.2 (EOL ~2008) — no security patches available.
- Is tightly coupled to a specific client (Subaru of America) and their data format.
- Has no automated build pipeline.
- Processes PII and payment data without encryption at rest.
- Will require significant effort to migrate due to: state machine complexity, SQL query count, and JAXB-generated request file format.

**Recommended path:** Assess active usage. If still in production, immediate dependency uplift (Spring 5.x or 6.x + Spring Boot) and security hardening are required as interim steps before a full Gen-3 rewrite.

## Migration Blockers
| Blocker | Description |
|---------|-------------|
| Spring 2.0.2 EOL | Cannot adopt Spring Boot without full rewrite of XML configuration |
| Spring Modules cache | Not compatible with Spring 3+; cache must be replaced with Spring Cache abstraction + EHCache 3.x or Caffeine |
| VBScript scheduler | Must be replaced with a portable scheduler (Spring Batch, Quartz, Kubernetes CronJob) |
| JAXB payment request file format | Changing the XML schema or serialisation requires coordination with the Onbe payment platform |
| Hardcoded SQL in Spring XML | ~50+ SQL queries embedded in Spring XML properties; must be migrated to JPA, MyBatis, or Flyway-managed DDL |
| Three inactive modules | `subaru-rewards-service`, `subaru-rewards-web`, `subaru-rewards-requestfile` must be assessed — retain or delete |
| No automated tests | No test coverage to validate refactoring |
