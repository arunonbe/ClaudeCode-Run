# Enterprise Architect — wirecard_automated-database-migration_LIB

## Platform Generation
**Gen-2** (Wirecard/Northlane issuing platform). Indicators:
- `com.wirecard.issuing` group ID — Wirecard platform namespace.
- `prepaid-parent:6.0.12` — Wirecard/Northlane prepaid platform parent.
- Java 21 compiler target (recently updated — suggests some investment in maintenance).
- Spring Boot dependency (version managed by parent BOM, likely Spring Boot 2.x based on parent lineage, though Java 21 target is unusual for SB 2.x — version from parent is not confirmed from the POM alone).
- Liquibase-based migration pattern is characteristic of Gen-2 Wirecard services.

## Business Domain
Platform Infrastructure / Database Operations. Shared component supporting all Gen-2 Wirecard/Northlane issuing services that maintain their own Oracle schemas.

## Role in the Architecture
- **Horizontal shared library**: Used by multiple Gen-2 services (`wirecard_check-agent_LIB`, `wirecard_corporate-client-module_LIB`, and likely others) via their `db-app` modules.
- Abstracts the Liquibase API from consuming services — services declare changelogs, this library handles execution.
- Enables **pre-deployment database migration** as a distinct step, separate from application startup, supporting zero-downtime deployment patterns.

## Dependencies
| Dependency | Source | Notes |
|---|---|---|
| `org.springframework.boot:spring-boot` | `prepaid-parent:6.0.12` BOM | Version managed by parent |
| `org.liquibase:liquibase-core` | `prepaid-parent:6.0.12` BOM | Version managed by parent |
| Oracle JDBC (`com.oracle:ojdbc8`) | Consuming service's classpath | Not declared here; provided by consumer |

## Integration Patterns
- **Annotation-driven import** (`@AutomatedDatabaseDeployment`): Consuming application imports the migration Spring context via the annotation.
- **CLI / ApplicationRunner**: Designed to be invoked as a standalone JAR with `--mode` and `--output` arguments, not as a long-running service.
- **Liquibase changelog convention**: Consuming services must provide a `liquibase.change-log` property pointing to their master changelog.

## Strategic Status
- **Active, in maintenance mode**: Java 21 compiler target suggests recent maintenance. No active feature development visible.
- **Gen-3 migration consideration**: Gen-3 services using Spring Boot 3.x with Flyway (or native Spring Boot Liquibase auto-configuration) may not need this library. If Gen-3 services use the built-in `spring.liquibase.*` auto-configuration, this library is redundant.
- **Not blocked for immediate migration**: The library itself has no `javax.*` dependencies and compiles to Java 21. However, the `prepaid-parent` BOM may pull in Spring Boot 2.x, which would need upgrading.

## Migration Blockers
1. **`prepaid-parent:6.0.12` BOM**: The Spring Boot version (and thus Liquibase version) is managed by this parent. If the parent pulls Spring Boot 2.x, the library is on an unsupported Spring Boot version. Version confirmation requires resolving the parent POM.
2. **API design**: The `DatabaseMigrationHandler` interface and `@AutomatedDatabaseDeployment` annotation are part of a shared API contract. Consuming services must be updated in sync with any interface changes.
3. **No rollback exposure**: Gen-3 migration may require rollback capability for blue-green deployments. The current interface does not support this.
