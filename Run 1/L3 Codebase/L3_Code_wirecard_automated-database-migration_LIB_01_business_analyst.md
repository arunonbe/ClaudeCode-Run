# Business Analyst — wirecard_automated-database-migration_LIB

## Business Purpose
A **Gen-2 shared database migration library** for the Wirecard/Northlane issuing platform. It provides a reusable, Spring Boot-integrated wrapper around Liquibase that allows any Wirecard/Northlane platform service to run structured database schema migrations at application startup or on demand, without exposing Liquibase internals to consuming services. It supports both direct `update` (apply migrations) and `generateSqlFile` (preview SQL before applying) modes.

## Capabilities
1. **`@AutomatedDatabaseDeployment` annotation**: A meta-annotation that consuming Spring Boot applications place on their `@Configuration` class to activate the database migration infrastructure.
2. **Liquibase migration execution** (`DatabaseMigrationHandlerImpl`): Applies all pending Liquibase changelogs (`applyChanges()`) to the target database using the configured `DataSource`.
3. **SQL file generation** (`DatabaseMigrationHandlerImpl.generateSqlFile()`): Renders pending SQL changes to a file without executing them — useful for DBA review and change-management gates.
4. **Spring Boot `ApplicationRunner` integration** (`DatabaseMigrationRunner`): Accepts `--mode=update` or `--mode=generateSqlFile --output=/path/to/file` command-line arguments to control migration execution mode when the consuming application is invoked as a CLI tool.
5. **Extended SpringLiquibase** (`ExtendedSpringLiquibase`): Subclasses `SpringLiquibase` to expose the `createLiquibase(Connection)` method and suppresses the default Spring `afterPropertiesSet()` auto-run, giving `DatabaseMigrationHandlerImpl` full control over when migrations execute.

## Entities / Domain Objects
- No business domain entities. The library operates on database schema metadata (Liquibase changelog files, `DataSource`, JDBC `Connection`).

## Business Rules
1. `--mode=update` must apply all pending changelogs to the target database.
2. `--mode=generateSqlFile` requires `--output=/path/to/file`; missing output path must throw an exception.
3. Unrecognised mode values must throw a `RuntimeException("Invalid mode ...")`.
4. If `mode` argument is absent, the runner throws `RuntimeException("mode is a required param. Pass in --mode=something.")`.
5. `ExtendedSpringLiquibase.afterPropertiesSet()` is overridden to be a no-op — migration does NOT run automatically on Spring context refresh; it only runs when explicitly invoked through the runner or handler.

## Flows
1. **Automated migration flow**: Consuming service packages this library + a `db-app` module. The `db-app` is deployed as a standalone JAR that is run before the main application starts. The Spring Boot runner receives `--mode=update`, `DatabaseMigrationRunner.run()` calls `handler.applyChanges()`, Liquibase applies pending changelogs, JVM exits.
2. **SQL preview flow**: DevOps/DBA runs the `db-app` with `--mode=generateSqlFile --output=/tmp/migration.sql` to get the SQL for review, then applies it manually or via a controlled deployment process.
3. **Rollback flow**: Not directly supported by this library in code — Liquibase rollback capability exists in the tool but is not exposed through `DatabaseMigrationHandler`.

## Compliance Relevance
- **PCI DSS Requirement 6.4 (Change Management)**: Database schema changes in a PCI-scoped environment must be tested and approved before deployment. The `generateSqlFile` capability directly supports this requirement by enabling DBA review of pending SQL before execution.
- **PCI DSS Requirement 6.3.2 (Inventory of bespoke/custom software)**: This library is part of the software inventory for Gen-2 services.
- **SOC 2 / Change Management**: Structured, version-controlled Liquibase changelogs (in consuming repos) provide the audit trail required for change management controls.

## Risks
1. `DatabaseMigrationHandlerImpl` catches all exceptions and re-wraps them as `RuntimeException` without structured logging. Migration failures may be difficult to diagnose in production.
2. No rollback capability is exposed. If a migration partially fails and the application exits, the database may be in an inconsistent state.
3. `ExtendedSpringLiquibase.afterPropertiesSet()` is a silent no-op; if a consuming application accidentally wires the `SpringLiquibase` bean directly (bypassing `DatabaseMigrationRunner`), no migration will run, with no warning.
