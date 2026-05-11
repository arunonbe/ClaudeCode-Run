# Data Architect — wirecard_automated-database-migration_LIB

## Data Stores
This library does not own or define any data store. It is a migration execution engine. The data stores it operates against are defined by the consuming application's `DataSource` configuration and Liquibase changelog files.

At runtime the library writes to:
- The **target Oracle or H2 database** (in consuming services): schema DDL changes as defined in the consuming service's Liquibase changelogs.
- **Liquibase tracking tables** (`DATABASECHANGELOG`, `DATABASECHANGELOGLOCK`) — created automatically by Liquibase in the target schema.
- **SQL file output** (local filesystem): when `--mode=generateSqlFile` is used.

## Schema / Tables
This library defines no tables itself. However, Liquibase automatically creates two tracking tables in the target schema:
- `DATABASECHANGELOG`: records each applied changeset (id, author, filename, dateexecuted, orderexecuted, exectype, MD5SUM, description, comments, tag, liquibase version).
- `DATABASECHANGELOGLOCK`: ensures only one Liquibase instance runs at a time (lock mechanism).

The actual schema changes (DDL for business tables) are defined in the consuming service's `db-scripts` module.

## Sensitive Data
- **Database credentials**: `spring.datasource.username` and `spring.datasource.url` are injected via `@Value` in `AutomatedDatabaseDeploymentConfiguration` and logged at INFO level: `LOG.info("Using database-user : " + this.dbUser)`. The username is logged but the password is not directly logged.
- The `DataSource` connection may use a privileged schema-owner account (required for DDL). These credentials must be protected at the platform configuration level (e.g., Spring Cloud Config with encryption, or a secrets vault).
- No cardholder data, PII, or financial transaction data is processed by this library itself.

## Encryption
- Database connections: TLS/SSL for JDBC connections is the responsibility of the consuming application's `DataSource` configuration (e.g., Oracle Wallet, SSL truststore). This library does not configure TLS — it accepts an already-configured `DataSource`.
- SQL file output: written to the local filesystem without encryption. Files containing schema DDL may reveal database structure and should be treated as sensitive artefacts.

## Data Flow
```
AutomatedDatabaseDeploymentConfiguration
  @Value("${liquibase.change-log}") --> changelog classpath path
  @Value("${spring.datasource.url}") --> logged at INFO (non-sensitive)
  @Value("${spring.datasource.username}") --> logged at INFO (non-sensitive)
  DataSource (injected) --> used for JDBC connection
    |
    v
ExtendedSpringLiquibase.create(connection)
    |
    v
Liquibase.update(contexts) --> applies DDL changesets to target DB
    OR
Liquibase.update(contexts, FileWriter(fileName)) --> writes SQL to file
    |
    v
DATABASECHANGELOG table updated in target schema
```

## Data Quality / Retention
- Liquibase changelogs are versioned in source control (in consuming repos). Changelogs must not be modified after application — doing so will cause MD5SUM validation failures.
- `DATABASECHANGELOG` provides a permanent audit trail of all applied migrations.
- SQL output files are ephemeral; they should be stored in a change-management system (JIRA, ServiceNow) if used in a PCI-controlled deployment.

## Compliance Gaps
1. **PCI DSS Req 10.3**: The `LOG.info("Using database-user: " + user)` logging means database usernames appear in application logs. Log access must be restricted per PCI DSS log management requirements.
2. **No dry-run validation**: There is no mechanism to validate changelog XML syntax or constraints without executing against the DB. A broken changelog will only be discovered at migration runtime.
3. **No schema ownership separation documented**: It is unclear if the `spring.datasource.username` used by the migration runner is the same as the application runtime user or a privileged schema-owner. PCI DSS and security best practice require the runtime application user to have minimal privileges (SELECT/INSERT/UPDATE only), not DDL privileges.
