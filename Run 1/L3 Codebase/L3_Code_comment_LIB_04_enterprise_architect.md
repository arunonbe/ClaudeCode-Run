# comment_LIB — Enterprise Architect View

## Platform Generation (Gen-1/Gen-2/Gen-3)

**Classification: Gen-1 / Legacy**

Evidence:
- Parent POM is `com.parents:prepaid-parent:6.0.12` — the `ecount`/`cbaseapp` lineage is the original Onbe (formerly eCount/Wirecard) prepaid platform.
- Package namespace `com.ecount.services.comment` uses the legacy `ecount` brand, which predates the Onbe rebrand.
- The test JDBC URL references `q-lis-db01.nam.wirecard.sys` — an explicit Wirecard-era (acquired 2021) infrastructure hostname still present in the codebase.
- Spring wiring is entirely XML-based (`comment.xml`) with no annotations, no Spring Boot, and no auto-configuration — consistent with Gen-1 component design.
- All DAO classes extend Spring's `StoredProcedure` directly, a pattern prevalent in mid-2000s to early-2010s Spring JDBC applications.
- Javadoc headers contain `// TODO: Auto-generated Javadoc` throughout, indicating the code was scaffolded via IDE tooling without subsequent cleanup — consistent with long-lived legacy code.
- The `applicationId` value `12` is hardcoded in the production Spring XML, suggesting a static per-application configuration that predates any multi-tenant or configuration-service pattern.

## Business Domain

**Domain: Customer Service Operations / Cardholder Servicing**

This library sits within the CSA (Customer Service Agent) sub-domain of the cardholder servicing domain. Its responsibilities are:
- Recording of all CSA-initiated and system-initiated interactions with a cardholder account.
- Providing a structured inquiry/escalation workflow for CSA supervisors and back-office reviewers.
- Supplying reference-data lookups (inquiry types, categories, assignees) to CSA user interface components.

The prefix `csa_` on all stored procedures confirms this is the canonical Gen-1 CSA data layer.

## Role in Platform

comment_LIB is a **shared infrastructure library** — a reusable JAR that multiple platform applications import to write and read CSA comment data. It is not a microservice, not an API gateway, and not independently deployable.

Its role in the platform:
- Acts as the **single authoritative write path** for comments into the `cbaseapp.dbo` schema's CSA comment and escalation tables.
- Acts as the **standard read path** for comment history presented in CSA agent interfaces.
- Acts as an **auto-comment sink** for automated platform processes (ACH processing, card reissue, balance adjustments, etc.) that need to generate an audit trail entry without involving a human agent.

Consuming applications are expected to be Tomcat-hosted WAR applications in the Gen-1 stack that import `comment` as a Maven compile-scope dependency and load `comment.xml` into their Spring application context.

## Dependencies

### Upstream (this library depends on)
| Dependency | Type | Version |
|---|---|---|
| `com.parents:prepaid-parent` | Parent POM / BOM | `6.0.12` |
| `org.springframework:spring-context` | compile JAR | Managed by parent |
| `org.springframework:spring-jdbc` | compile JAR | Managed by parent |
| `commons-lang:commons-lang` | compile JAR | Managed by parent |
| Microsoft SQL Server `cbaseapp` | External database | SQL Server (version unknown) |
| JNDI DataSource `CbaseappDataSource` | Runtime infrastructure | Provided by consuming app server |

### Downstream (known consumers)
Not determinable from this repository alone. Any Gen-1 WAR application in the `prepaid-parent` ecosystem that imports `com.ecount.services:comment:3.0.1` (or any prior version). The `ICommentService` interface is the public contract.

## Integration Patterns

| Pattern | Implementation | Notes |
|---|---|---|
| **Shared Library / In-Process Call** | JAR dependency; Spring bean injection | Primary integration model — callers wire `commentService` bean from `comment.xml` |
| **Stored Procedure Gateway** | Spring `StoredProcedure` subclasses | All database interactions go through named T-SQL stored procedures in `dbo` schema |
| **JNDI DataSource** | `JndiObjectFactoryBean` in `comment.xml` | Production database connection obtained via container JNDI; decouples library from specific connection pool implementation |
| **XML-driven IoC** | Spring XML bean definitions (`comment.xml`) | No annotation-based or Java-config wiring; consumer must import the XML file |
| **Value Object / DTO transfer** | `CommentHistoryValue`, `CommentEscalationValue`, etc. | Serializable POJOs passed across the service boundary; all implement `Serializable` |

There are no REST, SOAP, messaging (JMS/Kafka), or gRPC integration patterns in this library. It is purely an in-process, synchronous, JDBC-backed component.

## Strategic Status

**Status: Active Legacy — Maintenance Mode**

Rationale:
- The library is still actively maintained: it is on version `3.0.1`, compiled for Java 21, and has a functioning GitHub Actions CI pipeline publishing to GitHub Packages.
- The `dependabot.yml` weekly Maven update schedule indicates ongoing dependency management.
- However, the architecture is squarely Gen-1: XML Spring configuration, stored-procedure-only data access, no REST API, no observability, no secrets management.
- The Wirecard-era hostname in the test config (`q-lis-db01.nam.wirecard.sys`) and `ecount` package names are markers of pre-migration technical debt that has not been addressed.
- The `prepaid-parent:6.0.12` parent POM lineage anchors this library within the legacy BOM; Gen-3 applications on Spring Boot would not consume this pattern directly.
- Tests are permanently disabled in CI (`-Dmaven.test.skip`), which is consistent with a library in maintenance mode where the team avoids breaking the test suite rather than fixing it.

## Migration Blockers

The following items must be resolved before migrating comment_LIB capabilities into a Gen-3 architecture:

1. **XML-only Spring wiring** — The library's bean definitions are in `comment.xml` only. A Gen-3 migration requires converting to Spring Boot auto-configuration or `@Configuration` classes. All consumers would need to update their import mechanism.

2. **Stored procedure coupling** — All database interactions are bound to named T-SQL stored procedures in the `dbo` schema of `cbaseapp` (`dbo.csa_insertcsdet`, `dbo.csa_bc_get_comment_history`, etc.). Migration requires either porting the stored-procedure logic to JPA/JDBC repository classes or replicating the procedures in a new schema. The procedure source code is not in this repository.

3. **Single shared `cbaseapp` database** — The library is architecturally bound to the monolithic `cbaseapp` SQL Server database. A Gen-3 migration would require data domain separation (e.g., a dedicated comments microservice with its own schema) and a data migration plan.

4. **Hardcoded application ID** — `applicationId = 12` in `comment.xml` is a Gen-1 per-application constant. A Gen-3 design would derive this from a service identity or configuration service.

5. **`ecount` package namespace** — All classes are under `com.ecount.services.comment`. A Gen-3 migration or rebranding exercise requires renaming packages across all consuming applications.

6. **Raw `List` return types** — Multiple methods in `ICommentService` return raw (non-generic) `List` (e.g., `getCommentCategories()`, `getCommentTypesByCategory()`, `getCommentTypes()`). This is a pre-Java-5 pattern that requires refactoring before modern clients can use the API cleanly.

7. **No secrets management** — Test credentials are committed in plaintext. A Gen-3 migration requires integration with a secrets manager (e.g., Azure Key Vault, HashiCorp Vault) for all database credentials.

8. **Lack of idempotency / transactionality** — The library does not implement transaction management; if `insertCommentEscalation` is called after a successful `insertComment` and fails, the comment record is written but the escalation record is not, with no rollback. A Gen-3 redesign needs to address transactional boundaries.

9. **`trustServerCertificate=true` in test config** — Before promoting any test infrastructure to shared environments, this flag must be removed and proper certificate trust established.
