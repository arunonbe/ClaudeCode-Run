# onbe-sqlserver — Enterprise Architect View

## Platform Generation

**Generation**: Infrastructure / Developer Tooling — not a Gen-2 or Gen-3 application service in the business sense. This repository produces a containerised database image used by development teams and CI/CD pipelines. It is a supporting infrastructure component for the Gen-3 migration rather than a service being migrated.

## Business Domain

**Domain**: Developer Experience / Internal Infrastructure

`onbe-sqlserver` does not implement a business capability directly accessible to clients or cardholders. It enables engineering teams to:
1. Develop and test services that depend on SQL Server without shared environment dependencies.
2. Demonstrate and validate CDC pipeline patterns (Debezium, Azure Functions SQL Trigger) locally.
3. Provide a versioned, reproducible database container for automated integration tests.

Its relationship to business value is indirect: reliable, fast local development reduces time-to-market for the payment services that depend on SQL Server.

## Role in the Platform

`onbe-sqlserver` serves two roles in the Onbe platform architecture:

### Role 1: Local Development Database
Teams building services that target SQL Server (`order_SVC`, `ecount-core_SVC`, `nexpay-*` services, `oneplatform-azureaffiliate-function`) can run this container locally to avoid dependency on shared QA databases.

### Role 2: CDC Pattern Reference Implementation
The `init-db.sql` demonstrates the pattern for enabling CDC on a SQL Server database. The `petstore-spring-mvc-rest-server` uses this container as its backing database in Docker Compose. The CDC configuration pattern in `init-db.sql` is the template for production CDC setup on Onbe's actual databases.

### Relationship to `petstore-spring-mvc-rest-server`
```
petstore-spring-mvc-rest-server
    └── compose.yaml
            └── depends on: onbe-sqlserver image
                    (CDC enabled, petstore schema initialized)
```
This dependency makes `onbe-sqlserver` a prerequisite for local full-stack development of the MVC petstore reference implementation.

## Dependencies

### Inbound (who depends on this repo)
- `petstore-spring-mvc-rest-server` — uses this container as its development SQL Server backend.
- Any service developer who runs local integration tests against SQL Server.

### Outbound (what this repo depends on)
- `mcr.microsoft.com/mssql/server:2022-CU13-ubuntu-22.04` — Microsoft's SQL Server container image.
- `Onbe/om-ci-setup/.github/workflows/java-workflow.yml@main` — Onbe's reusable CI pipeline.
- `spring-boot-starter-parent:3.3.5` — Maven parent POM (upstream, not Onbe-internal).

## Integration Patterns

| Pattern | Implementation | Notes |
|---|---|---|
| Container image distribution | Docker build → Azure/GitHub Container Registry | Standard Onbe container delivery |
| CDC enablement | SQL Server CDC via `sys.sp_cdc_enable_db` / `sp_cdc_enable_table` | Template for production CDC configuration |
| Change Tracking (alternative) | Commented out in `init-db.sql` | For lighter-weight Azure Functions SQL Trigger use cases |
| Debezium integration | CDC tables available on port 1433 | Debezium `SqlServerConnector` pattern demonstrated in `petstore-spring-mvc-rest-server` |
| Environment-injected secrets | `MSSQL_SA_PASSWORD` env var | Kubernetes Secrets / Docker Compose `.env` |

## Strategic Status

**Status**: Active — used by development teams working on CDC-enabled services. Low maintenance burden. Key strategic value is as a pattern reference for CDC configuration in production SQL Server databases.

**Long-term outlook**: As Onbe migrates production services to Gen-3 cloud-native architecture, the CDC pattern demonstrated here will be required for all SQL Server-backed services that publish events to Azure Service Bus or Kafka. The patterns established in `init-db.sql` (role-restricted CDC, explicit retention, SQL Server Agent dependency) should be promoted to Onbe's internal DBA runbook.

## Migration Blockers

| Blocker | Impact | Notes |
|---|---|---|
| `MSSQL_PID=Developer` hardcoded | Prevents production use as-is | Trivial to change; must be parameterised via `MSSQL_PID` env var for non-dev deployments |
| Not inheriting `onbe-spring-boot-parent` | Spring Boot version drift | Low risk for a Spring Boot stub with no business logic, but creates inconsistency |
| Container scan disabled | PCI DSS Req 6.3.3 gap | Must be re-enabled before any production infrastructure patterns derived from this repo pass security review |
| `@role_name = NULL` in CDC config | Production CDC security gap | Any production replication of this CDC pattern must specify a restricted role |
