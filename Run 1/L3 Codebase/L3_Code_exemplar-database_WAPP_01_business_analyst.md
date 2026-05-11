# Business Analyst View — exemplar-database_WAPP

## Repository Overview

**exemplar-database_WAPP** is a Gen-3 reference (exemplar) component that provides the shared Microsoft SQL Server database infrastructure for all exemplar-family microservices at Onbe. It does not contain application business logic. Its sole purpose is to demonstrate and enforce the approved pattern for provisioning a multi-database SQL Server instance — both locally (Docker Compose) and in Azure Kubernetes Service (AKS) — in a way that is independent of any individual application service.

The README (line 6) explicitly states: _"we are adopting a schema-per-service approach due to its low overhead."_ This is the key architectural decision documented here. Rather than a database-per-service model (which was evaluated but rejected due to local memory constraints, per README line 5), a single SQL Server instance hosts separate databases for each logical service. This pattern reduces operational overhead while maintaining some degree of isolation between services.

## Business Purpose and Patterns Demonstrated

### 1. Schema-per-Service Database Provisioning Pattern

The repository teaches new development teams how to separate database provisioning from application deployment — a critical Gen-3 pattern at Onbe. The `db-setup.sql` (local/db-setup.sql) provisions three databases: `Theater`, `Customer`, and `diiadministration`. Each corresponds to a different microservice in the exemplar family, demonstrating that one SQL Server instance can serve multiple bounded contexts.

### 2. Local Development Parity with AKS

Two deployment paths are provided:
- **Local Docker Compose** (`local/docker-compose.yml`): Spins up a containerized `microsoft/mssql-server-linux` instance, creates all three databases, and exposes port 1433 on the `dii` Docker network. The connection string (`Server=exemplar-sqlserver.lvh.me,1433`) uses `lvh.me` DNS trick for host-accessible resolution.
- **AKS (Azure SQL)** (`aks/create-database.sh`): Uses the `az sql` CLI to create an Azure SQL logical server, configure firewall rules, and provision the same three databases at the `Basic` service tier. The script closely mirrors the local setup so developers can reason about both environments uniformly.

### 3. Bootstrapped Initialization Pattern

The `local/entrypoint.sh` + `local/db-configure.sh` pattern demonstrates how a Docker container can self-configure at startup: the entrypoint launches SQL Server as a background process, polls until it is ready, then runs `sqlcmd` to execute `db-setup.sql`. This is the approved Onbe pattern for containerized database initialization and is expected to be replicated in production-grade services.

### 4. Deployment Independence

By extracting database provisioning into its own repository, Onbe enforces that:
- Databases are created before applications are deployed (README lines 8–9).
- Application teams cannot accidentally conflate schema migrations (handled in the application repo via Liquibase) with instance/database creation (handled here).
- The same database bootstrap can serve multiple exemplar services (`theater-service`, `customer-service`, `diiadministration`).

## Business Stakeholders

| Role | Interest |
|------|----------|
| Platform Engineering | Enforce standard DB provisioning across all Gen-3 services |
| Development Teams | Reference pattern for local and AKS database setup |
| Infrastructure / Cloud Ops | Azure SQL server lifecycle management |
| Security / Compliance | Confirm database credentials and firewall rules meet PCI DSS requirements |

## Scope and Limitations

This repository does **not** contain:
- Database schema migration scripts (those belong in each application's `-db-scripts` module, e.g., `theater-service-db-scripts` using Liquibase).
- Application code, REST APIs, or batch jobs.
- Any cardholder data or payment processing logic.

The three database names (`Theater`, `Customer`, `diiadministration`) correspond to the exemplar use cases only and are purely instructional. They are not production payment databases.

## Compliance Notes

The `local/docker-compose.yml` (line 9) contains a hardcoded SA password (`B00t1ful`) and the AKS script (`aks/create-database.sh` line 3) likewise uses a hardcoded admin password. These are development/exemplar credentials. Any production deployment must substitute these with secrets managed via Azure Key Vault or equivalent secrets management, consistent with PCI DSS Requirement 8 (Identify users and authenticate access to system components). The firewall rule in `create-database.sh` (lines 27–34) opens access from `0.0.0.0` to `223.255.255.255`, which is extremely permissive and not acceptable for production environments.
