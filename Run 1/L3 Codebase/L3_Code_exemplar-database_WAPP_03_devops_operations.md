# DevOps / Operations View — exemplar-database_WAPP

## Repository Classification

**Type**: Infrastructure / Database bootstrap  
**Suffix**: `_WAPP` (Web Application family) — though this repo contains no Java application, the naming follows the exemplar family convention.  
**Deployment scope**: Local development and AKS (Azure Kubernetes Service).

## Build System

There is no Maven or Gradle build in this repository. The repository consists entirely of shell scripts, SQL, and Docker artifacts. There is no CI/CD pipeline configuration (no `.github/workflows/`, no Jenkinsfile, no GitLab CI) present in the scanned file tree. This means there is no automated gate (linting, scanning, automated test) before merging changes to this repo.

## Local Deployment

### Workflow

1. Navigate to `local/` directory.
2. Run `docker-compose up --build`.

### Docker Compose Configuration (`local/docker-compose.yml`)

- **Image**: `microsoft/mssql-server-linux` (note: this is the older Docker Hub image; the Dockerfile overrides it with `mcr.microsoft.com/mssql/server:2017-CU20-ubuntu-16.04`).
- **Container name**: `exemplar-sqlserver`.
- **Restart policy**: `unless-stopped`.
- **Network**: `dii` (custom bridge network, allowing other exemplar containers to reach this server by hostname `exemplar-sqlserver`).
- **Ports**: `1433:1433`.
- **Environment variables** inject database names and SA password.

### Dockerfile (`local/Dockerfile`)

1. Base image: `mcr.microsoft.com/mssql/server:2017-CU20-ubuntu-16.04`.
2. Copies scripts and SQL files to `/usr/src/app`.
3. Makes `entrypoint.sh` and `db-configure.sh` executable.
4. Sets `ENTRYPOINT ["./entrypoint.sh"]`.
5. Includes a `HEALTHCHECK` (line 19): polls `sqlcmd -Q "select 1"` every 15 seconds and checks that `config.log` contains `MSSQL CONFIG COMPLETE`.

### Initialization Scripts

| Script | Purpose |
|--------|---------|
| `local/entrypoint.sh` | Starts SQL Server daemon, then calls `db-configure.sh` |
| `local/db-configure.sh` | Polls until SQL Server is ready (up to 30 attempts), then runs `db-setup.sql` via `sqlcmd` |
| `local/db-setup.sql` | Idempotent `IF NOT EXISTS` creation of the three databases |

The use of `IF NOT EXISTS` guards in `db-setup.sql` makes the initialization script idempotent — safe to re-run without destroying existing databases.

## AKS Deployment

### Workflow

1. Navigate to `aks/` directory.
2. Execute `create-database.sh` within the AKS cluster context.

### Script: `aks/create-database.sh`

- Uses `az sql server create` to create a logical Azure SQL server named `exemplar-sqlserver` in resource group `exemplar`.
- Opens a firewall rule allowing connections from `0.0.0.0` to `223.255.255.255` (all non-RFC-1918 IPs — operationally dangerous).
- Creates three Azure SQL databases at the `Basic` service tier (very low DTU — suitable for exemplar/demo only, not production workloads).

**Azure SQL Basic Tier Limitations**: Maximum 5 DTUs, 2 GB storage. Not suitable for production card processing workloads.

## Operations Runbook Notes

### Starting the Local Database
```bash
cd local
docker-compose up --build
```

### Stopping Without Data Loss
```bash
docker-compose stop
```

### Full Teardown (Data Destroyed)
```bash
docker-compose down
```

### Verifying Database Readiness
The Dockerfile health check provides automatic readiness detection. Alternatively, connect with SSMS:
- Server: `exemplar-sqlserver.lvh.me,1433`
- Authentication: SQL Server Authentication
- Login: `SA` / Password: `[REDACTED — rotate immediately]`

### Log Review
The `db-configure.sh` appends status messages to `./config.log` within the container. The health check grep (`grep -q "MSSQL CONFIG COMPLETE" ./config.log`) can be used to confirm successful initialization.

## Missing CI/CD Infrastructure

The absence of any CI/CD pipeline in this repository means:
- No automated validation when shell scripts or SQL are changed.
- No SAST (Static Application Security Testing) on the Dockerfile or scripts.
- No automated credential scanning (the hardcoded `[REDACTED — rotate immediately]` password would not be caught by an automated gate).

**Recommendation**: Add a GitHub Actions workflow (consistent with the pattern in `exemplar-theater-service_WAPP/.github/workflows/codeql.yml`) that at minimum:
1. Runs `hadolint` on the Dockerfile.
2. Runs `shellcheck` on the shell scripts.
3. Runs a secrets scanner (e.g., `truffleHog`, `gitleaks`) to detect committed credentials.

## Versioning

There is no version tag or semantic version in this repository. Changes are tracked only via Git commits. For operational traceability, it is recommended to introduce a `VERSION` file or Git tags corresponding to significant changes to the DB provisioning scripts.
