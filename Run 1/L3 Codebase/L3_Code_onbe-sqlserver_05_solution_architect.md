# onbe-sqlserver — Solution Architect View

## Technical Architecture

`onbe-sqlserver` is a thin wrapper repository whose primary deliverable is a Docker image rather than a Java application. The Spring Boot component (`OnbeSqlserverApplication`) is effectively a scaffold with no functional code — its presence enables the Onbe reusable CI/CD Java workflow to build, test (skipped), and publish the container image.

### Component Layout

```
onbe-sqlserver repository
├── Dockerfile                         ← Primary artifact: SQL Server 2022 container image
├── scripts/
│   ├── entrypoint.sh                  ← Database initialization orchestrator
│   └── init-db.sql                    ← Schema + CDC DDL
├── src/main/java/.../
│   └── OnbeSqlserverApplication.java  ← Spring Boot stub (no business logic)
├── src/main/resources/
│   └── application.properties         ← spring.application.name only
└── .github/workflows/
    └── deployment.yaml                ← GitHub Actions CI/CD
```

### Runtime Architecture
```
Docker container: onbe-sqlserver:latest
├── Process: /scripts/entrypoint.sh (PID 1)
│     ├── Background: /opt/mssql/bin/permissions_check.sh
│     └── Foreground: /opt/mssql/bin/sqlservr
│           ├── SQL Server Engine (port 1433)
│           ├── SQL Server Agent (CDC jobs)
│           │     ├── cdc.petstore_capture job
│           │     └── cdc.petstore_cleanup job
│           └── Databases:
│                 ├── master
│                 ├── msdb (Agent job metadata)
│                 ├── tempdb
│                 └── petstore
│                       ├── dbo.pet (source table)
│                       └── cdc.dbo_pet_CT (change table)
└── Spring Boot JVM (not started — init-only scaffold)
```

## API Surface

`onbe-sqlserver` does not expose an HTTP or REST API. Its interface is:

| Interface | Protocol | Port | Consumer |
|---|---|---|---|
| SQL Server TDS protocol | TCP | 1433 | JDBC clients (`SqlServerConnector`, `JdbcTemplate`, `R2DBC`) |
| CDC change tables | SQL (via JDBC) | 1433 | Debezium `SqlServerConnector`, Azure Functions SQL Trigger |
| CDC change functions | SQL (via JDBC) | 1433 | `cdc.fn_cdc_get_all_changes_*`, `cdc.fn_cdc_get_net_changes_*` |

### Connection Parameters (Development)
```
Server: localhost:1433
Username: sa
Password: ${MSSQL_SA_PASSWORD}
Database: petstore
Encrypt: false (dev); true (production)
TrustServerCertificate: true (dev); false (production with CA cert)
```

## Security Posture

### Strengths
- Non-root container execution (`USER mssql`).
- Base image pinned to specific CU (no uncontrolled updates).
- SA password injected at runtime, not baked into image.
- SQL Server Agent enabled — CDC cleanup jobs prevent unbounded table growth.

### Weaknesses and Gaps

| Finding | Severity | PCI DSS Ref | Detail |
|---|---|---|---|
| Container scan disabled | High | Req 6.3.3 | `CONTAINER_SCAN: false` — SQL Server 2022 + Ubuntu 22.04 packages carry CVEs that go undetected |
| CDC `@role_name = NULL` | High (prod) | Req 3.3 | Any DB user can query CDC change tables; must restrict to named role in production |
| Self-signed TLS certificate | Medium | Req 4.2.1 | Default SQL Server self-signed cert; `trustServerCertificate: true` required by clients |
| SA password in process args | Medium | Req 8.3 | `sqlcmd -P "${MSSQL_SA_PASSWORD}"` — visible in `/proc/$PID/cmdline` |
| SQL Server Audit not configured | Medium | Req 10.2 | No audit trail for logins or DML in `init-db.sql` |
| `MSSQL_PID=Developer` | Medium | Licensing | Developer Edition not for production; must parameterise |
| TDE not configured | Low (dev) | Req 3.5 | Not required for dev/test; required for production CDE databases |

## Technical Debt

| Item | Severity | Remediation |
|---|---|---|
| Container scan disabled | High | Re-enable; configure Trivy suppression file for confirmed false positives |
| Not inheriting `onbe-spring-boot-parent` | Low | Update parent POM to `com.onbe.spring.boot:onbe-spring-boot-parent` |
| Spring Boot 3.3.5 (behind platform standard) | Low | Update to match platform parent version |
| `init-db.sql` not idempotent | Medium | Add `IF NOT EXISTS` guards around `CREATE DATABASE` and `CREATE TABLE` |
| No `HEALTHCHECK` in Dockerfile | Low | Add `HEALTHCHECK` instruction for Kubernetes readiness |
| Startup polling interval 30s | Low | Reduce to 5–10s for faster CI test startup |
| SA password visible in command line | Medium | Use `sqlcmd` connection string file or pipe credentials via stdin |

## Gen-3 Migration Assessment

`onbe-sqlserver` does not require a Gen-3 migration in the traditional sense — it is infrastructure tooling, not a migrated application service. However, the following Gen-3 alignment work is warranted:

1. **Production CDC pattern hardening**: Before any Gen-3 service uses CDC against a production SQL Server, the `init-db.sql` pattern must be updated with: `@role_name` set, explicit retention periods, SQL Server Audit configuration, and TDE enablement.

2. **Kubernetes deployment**: Add a Kubernetes manifest (`k8s/deployment.yaml`) that uses `secretKeyRef` for `MSSQL_SA_PASSWORD` from Azure Key Vault via External Secrets Operator.

3. **Azure SQL Managed Instance compatibility**: As Onbe migrates to Azure-managed SQL, the CDC configuration may need adjustment — Azure SQL MI has different CDC setup requirements than SQL Server on containers.

4. **Re-enable container scanning**: A working Trivy or Microsoft Defender suppression file is required for CI gates to align with PCI DSS.

## Code-Level Risks

### `scripts/entrypoint.sh` — SA password in command line argument
```bash
/opt/mssql-tools/bin/sqlcmd -S localhost -U sa -P "${MSSQL_SA_PASSWORD}" -d master -i /scripts/init-db.sql
```
The SA password is passed as a `-P` flag, which is visible to other processes via `/proc/$PID/cmdline` on Linux. While the container has limited process visibility, this is a known weakness. The recommended alternative is to use a `sqlcmd` config file:
```bash
echo "[ODBC]" > /tmp/sqlcmd.ini
echo "UID=sa" >> /tmp/sqlcmd.ini
echo "PWD=${MSSQL_SA_PASSWORD}" >> /tmp/sqlcmd.ini
sqlcmd -S localhost -dsn /tmp/sqlcmd.ini -d master -i /scripts/init-db.sql
```

### `init-db.sql` — CDC role_name NULL
```sql
EXEC sys.sp_cdc_enable_table
     @source_schema = N'dbo',
     @source_name = N'pet',
     @role_name = NULL,   -- ← RISK: all users can read CDC tables
     @supports_net_changes = 1;
```
This is the single highest-risk pattern in the repository when replicated to production. Any production CDC setup must replace `NULL` with a named, least-privilege role.

### `Dockerfile` — `MSSQL_PID=Developer` not parameterised
The Developer Edition flag is baked into the `ENV` instruction rather than being a build argument or runtime variable. Teams copying this Dockerfile for production SQL Server deployments may overlook this. The recommended pattern is:
```dockerfile
ARG MSSQL_PID=Developer
ENV MSSQL_PID=${MSSQL_PID}
```
This allows `docker build --build-arg MSSQL_PID=Enterprise` for production images without modifying the Dockerfile.
