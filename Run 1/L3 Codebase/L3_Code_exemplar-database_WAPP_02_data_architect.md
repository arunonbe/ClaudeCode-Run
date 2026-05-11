# Data Architect View — exemplar-database_WAPP

## Data Stores Provisioned

This repository provisions a single Microsoft SQL Server instance containing three databases. No tables, indexes, or stored procedures are created here; schema creation is delegated to each application's Liquibase migration module.

| Database Name | Consuming Service (inferred) | Purpose |
|---------------|------------------------------|---------|
| `Theater` | exemplar-theater-service_WAPP | Microservice domain store |
| `Customer` | exemplar-customer-service_WAPP | Customer data store |
| `diiadministration` | DII administration service | Administrative data |

Source: `local/db-setup.sql` lines 1–16 and `aks/create-database.sh` lines 17–19.

## Database Technology

- **Engine**: Microsoft SQL Server 2017 CU20 (Docker image `mcr.microsoft.com/mssql/server:2017-CU20-ubuntu-16.04` per `local/Dockerfile` line 1). In AKS, Azure SQL (PaaS) is used with the `Basic` service tier.
- **JDBC Driver**: `mssql-jdbc 9.2.1.jre11` (referenced by the theater-service pom.xml).
- **Port**: 1433 (standard SQL Server port).
- **Authentication**: SQL Server Authentication (SA account) in local; `sqladmin` account in AKS.

## Sensitive Data Considerations

This repository does **not** create any tables and therefore does not directly handle cardholder data, PAN, or any Sensitive Authentication Data (SAD). However, the following observations are relevant:

1. **Hardcoded Credentials** (`local/docker-compose.yml` lines 9, 14, 24–25 and `aks/create-database.sh` lines 3, 6): The SA password `[REDACTED — rotate immediately]` and admin password `[REDACTED — rotate immediately]` are embedded in plaintext in version-controlled files. This violates PCI DSS Requirement 8.3 (protect individual non-consumer user authentication factors) and represents a credential leakage risk.

2. **Firewall Rule Scope** (`aks/create-database.sh` lines 29–34): The firewall allows connections from `0.0.0.0` to `223.255.255.255`, which exposes the SQL Server to almost all internet IP addresses. This violates PCI DSS Requirement 1 (install and maintain network security controls).

3. **SA Account Usage**: Using the `SA` (System Administrator) superuser account for application connectivity is a high-risk practice. PCI DSS Requirement 7 (restrict access to system components and cardholder data by business need to know) requires least-privilege database accounts.

## Data Flow Architecture

```
[Local Dev Machine]
       |
       | docker-compose up --build
       v
[Docker: exemplar-sqlserver container]
  - entrypoint.sh starts sqlservr
  - db-configure.sh polls until ready
  - sqlcmd executes db-setup.sql
  - Creates: Theater, Customer, diiadministration DBs
       |
       | Each app service connects via JDBC
       v
[App Services] (theater-service, customer-service, etc.)
  - Liquibase migration runs at startup
  - Creates tables/indexes in respective DB
```

## Schema Management Pattern

This repository handles **instance and database provisioning only**. Schema DDL (tables, indexes, constraints) is managed by Liquibase changelog files in each service's `-db-scripts` submodule. This enforces a clean separation of concerns:

- `exemplar-database_WAPP`: Creates the SQL Server instance and blank databases.
- Each application: Runs Liquibase to create and evolve its own schema within its assigned database.

This means there is no single schema registry here. Each service owns its own schema, consistent with the schema-per-service pattern described in the README.

## Database Naming Conventions

The `db-setup.sql` uses parameterized environment variable substitution (`$(MSSQL_DB1)`) which is resolved via Docker environment variables set in `docker-compose.yml`:
- `MSSQL_DB1` = `Theater`
- `MSSQL_DB2` = `Customer`
- `MSSQL_DB3` = `diiadministration`

This approach allows the same SQL script to be used across environments by changing only environment variables, consistent with a 12-factor app configuration strategy.

## Data Lineage

No ETL, no data transformation, and no replication are configured in this repository. The databases created here serve as the initial empty containers for application data. Data lineage for any payment-relevant data begins in the application services that populate these schemas.

## Recommendations

1. Replace hardcoded SA credentials with Azure Key Vault references or Docker secrets before any use beyond local exemplar demos.
2. Create service-specific SQL Server logins with minimum required permissions rather than using SA.
3. Restrict the AKS firewall rule to the specific AKS egress IP range.
4. Consider upgrading from SQL Server 2017 to SQL Server 2022 or Azure SQL with Always Encrypted for sensitive columns if this pattern is extended to production payment services.
