# onbe-sqlserver — Business Analyst View

## Business Purpose

`onbe-sqlserver` is a containerised Microsoft SQL Server 2022 image built by Onbe Engineering for use as a development and CI/CD test database. It is not a standalone business application. Its business value is enabling development teams to run integration tests and local development workflows against a SQL Server instance pre-configured with Onbe-relevant patterns — specifically Change Data Capture (CDC) and the `petstore` demonstration schema — without requiring access to shared or production SQL Server environments.

This repository sits in the developer experience and inner infrastructure domain. It is a tool for engineers, not a system that business users interact with directly.

## Business Capabilities

| Capability | Mechanism | Business Value |
|---|---|---|
| Local SQL Server environment | Docker container from `mcr.microsoft.com/mssql/server:2022-CU13-ubuntu-22.04` | Eliminates dependency on shared dev/QA databases for integration testing |
| CDC-ready database | `init-db.sql` enables CDC on startup | Enables local testing of Debezium-based and Azure Functions SQL Trigger CDC pipelines |
| Automated schema initialisation | `scripts/entrypoint.sh` runs `init-db.sql` on first start | Zero-configuration database for new developers |
| SQL Server Agent enabled | `MSSQL_AGENT_ENABLED=true` | Enables CDC capture/cleanup jobs required for CDC operation |
| CI/CD integration database | Built and published via GitHub Actions | Provides a versioned database container for automated integration tests |

## Key Entities / Schema

The `init-db.sql` initialises a `petstore` demonstration database with a single table:

| Table | Columns | Purpose |
|---|---|---|
| `dbo.pet` | `id` (int identity PK), `name` (varchar 255 NOT NULL), `tag` (varchar 255 nullable) | Demonstration entity used by the petstore service family for CDC testing |
| `cdc.dbo_pet_CT` (auto-created) | `__$start_lsn`, `__$operation`, source columns | CDC change table capturing all DML on `dbo.pet` |

In production Onbe systems, this schema would be replaced by actual business tables (e.g., `ordersvc`, `ecountcore`, `nexpay_claimable`) with their appropriate CDC configurations.

## Business Rules

1. The container must be treated as a **development and testing artifact only** — `MSSQL_PID=Developer` activates the Developer Edition license which is not licensed for production workloads.
2. The SA password must be supplied as a runtime environment variable (`MSSQL_SA_PASSWORD`) — it must never be hardcoded in the image.
3. CDC is enabled at database and table level on startup — any service consuming CDC from this container can immediately read from `cdc.dbo_pet_CT` without additional setup.

## Flows

### Container Startup Flow
1. `entrypoint.sh` starts SQL Server in the background.
2. Polls `sqlcmd SELECT 1` every 30 seconds until SQL Server is ready.
3. Executes `init-db.sql` via `sqlcmd` using the SA account.
4. SQL Server Agent (background) creates CDC capture and cleanup jobs automatically.

### CDC Data Flow (Developer Use)
1. Developer inserts/updates/deletes rows in `dbo.pet`.
2. SQL Server transaction log records the change.
3. CDC capture agent reads the log and writes to `cdc.dbo_pet_CT`.
4. Debezium connector (or Azure Functions SQL Trigger) reads from `cdc.dbo_pet_CT` and publishes events.

## Compliance Context

While this container is primarily a development tool, the patterns it establishes (CDC configuration, SA account usage, TLS settings) serve as a reference that production DBA teams may follow. The compliance gaps noted in this analysis must not be replicated in production SQL Server configurations.

- **PCI DSS**: Developer Edition and the default CDC `@role_name = NULL` are not production-safe. Production CDC instances must use role-restricted access.
- **PCI DSS Req 6.3.3**: Container vulnerability scanning is disabled in CI — this must be re-enabled before using this pattern for production infrastructure.

## Business Risks

| Risk | Severity | Notes |
|---|---|---|
| Developer Edition used in production | High | Legal and compliance violation; must use appropriate license in non-dev environments |
| CDC tables unrestricted (`@role_name = NULL`) | High (production) | If replicated in production, any DB user can read CDC data including sensitive fields |
| Container vulnerability scanning disabled | Medium | Known CVEs in the SQL Server image may go undetected |
| SA password in process command line | Medium | Visible to other container processes via `/proc/$PID/cmdline` |
| No duplicate-bill detection in consuming services | Low | Not a risk of this repo itself, but CDC latency and redelivery must be handled by consumers |
