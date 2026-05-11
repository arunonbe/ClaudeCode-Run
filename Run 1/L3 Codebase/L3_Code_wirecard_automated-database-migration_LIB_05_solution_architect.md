# Solution Architect — wirecard_automated-database-migration_LIB

## Technical Architecture
Four classes comprise the library:

| Class | Role |
|---|---|
| `AutomatedDatabaseDeployment` | Meta-annotation (`@Import(AutomatedDatabaseDeploymentConfiguration.class)`); entry point for consuming apps |
| `AutomatedDatabaseDeploymentConfiguration` | `@Configuration` class; creates `ExtendedSpringLiquibase`, `DatabaseMigrationHandler`, and `DatabaseMigrationRunner` beans |
| `ExtendedSpringLiquibase` | Extends `SpringLiquibase`; exposes `create(Connection)` and overrides `afterPropertiesSet()` as no-op |
| `DatabaseMigrationHandlerImpl` | Holds `Liquibase` instance; `applyChanges()` and `generateSqlFile(String)` methods |
| `DatabaseMigrationRunner` | `ApplicationRunner`; parses `--mode` / `--output` CLI args; delegates to `DatabaseMigrationHandlerImpl` |

## API Surface
No REST API. Public programmatic API:

```java
// Annotation — consuming app @Configuration class
@AutomatedDatabaseDeployment

// Handler methods
DatabaseMigrationHandler.applyChanges()
DatabaseMigrationHandler.generateSqlFile(String fileName)

// CLI invocation
java -jar db-app.jar --mode=update
java -jar db-app.jar --mode=generateSqlFile --output=/path/to/output.sql
```

## Security Posture

### Authentication / Authorisation
- No HTTP/REST authentication. The library runs as a privileged process with database owner credentials.
- `DataSource` authentication is delegated to the consuming application's JDBC configuration.

### Cryptography
- No cryptographic operations in this library.
- Database connection TLS/SSL is configured externally by the consuming application's `DataSource`.

### Secrets
- Database credentials (`spring.datasource.url`, `spring.datasource.username`, password) are required but must be provided by the consuming application's configuration — not hardcoded here.
- `AutomatedDatabaseDeploymentConfiguration` logs `dbUrl` and `dbUser` at INFO level (`AutomatedDatabaseDeploymentConfiguration.java:33–34`). Passwords are not logged. However, depending on the JDBC URL format, connection parameters (including some credential fragments) may appear in `dbUrl` — this should be reviewed.

### Known CVEs
- `liquibase-core` version is managed by `prepaid-parent:6.0.12`. Liquibase has had security advisories (e.g., CVE-2022-0839, XML external entity vulnerabilities in older versions). The actual version in use must be confirmed from the parent BOM and checked against current CVE databases.
- `spring-boot` version managed by the same parent — must be confirmed. If Spring Boot 2.x, it is end-of-life (EOL November 2024) and may carry unpatched CVEs.

## Technical Debt
1. **All exceptions wrapped in `RuntimeException`**: `DatabaseMigrationHandlerImpl.applyChanges()` and `generateSqlFile()` catch all `Exception` and rethrow as `RuntimeException`. Specific Liquibase exceptions (e.g., `LiquibaseException`, lock errors, changeset checksum mismatches) are not individually handled. This makes debugging production migration failures very difficult.
2. **`ExtendedSpringLiquibase.afterPropertiesSet()` silent no-op**: `ExtendedSpringLiquibase.java:13` — overrides to empty method with no log warning. A consuming developer who wires up `ExtendedSpringLiquibase` directly (expecting auto-run on Spring context) will get no migration and no error.
3. **`StringUtils.isEmpty` (deprecated)**: `DatabaseMigrationRunner.java:29` — `StringUtils.isEmpty(modeOne)` is deprecated in Spring Framework 5.3+. Should use `!StringUtils.hasText(modeOne)`.
4. **No Liquibase contexts used dynamically**: `contexts` is set from `extendedSpringLiquibase.getContexts()` at construction time. Liquibase contexts are a powerful mechanism for environment-specific changesets, but there is no documentation or validation of what context values are expected.
5. **Compiler target Java 21 but codebase style is Java 8**: No use of records, var, sealed classes, or any Java 9–21 language features. The Java 21 target is a configuration setting but the code itself has not been modernised.

## Gen-3 Migration Requirements
If consuming services migrate to Gen-3 (Spring Boot 3.x), consider:
1. **Evaluate built-in Liquibase support**: Spring Boot 3.x has first-class Liquibase auto-configuration via `spring.liquibase.*`. This library may be redundant for Gen-3 services.
2. **If retaining this library**: Update parent POM to a Spring Boot 3.x BOM; update `liquibase-core` to a version compatible with Spring Boot 3.x; remove deprecated `StringUtils.isEmpty` usage.
3. **Fix exception handling**: Replace generic `RuntimeException` wraps with structured exception types and proper logging.

## Code-Level Risks

| File | Line | Risk |
|---|---|---|
| `AutomatedDatabaseDeploymentConfiguration.java` | 33–34 | `LOG.info("Using database: " + dbUrl)` — JDBC URL logged; may include embedded credentials or sensitive connection params |
| `DatabaseMigrationHandlerImpl.java` | 26–33 | Constructor wraps all exceptions in `RuntimeException` — obscures the root cause of initialisation failures |
| `DatabaseMigrationHandlerImpl.java` | 35–41 | `applyChanges()` wraps all exceptions — Liquibase lock errors, checksum failures not separately handled |
| `DatabaseMigrationRunner.java` | 29 | `StringUtils.isEmpty(modeOne)` — deprecated method |
| `ExtendedSpringLiquibase.java` | 13 | `afterPropertiesSet()` is silent no-op — no log warning, no documentation |
