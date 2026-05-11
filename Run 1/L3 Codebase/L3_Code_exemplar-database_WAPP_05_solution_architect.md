# Solution Architect View — exemplar-database_WAPP

## Technical Summary

This repository contains 7 files across two deployment contexts. There is no compiled code — all logic is expressed in shell scripts, SQL, and Docker configuration. The technical debt is concentrated in hardcoded credentials and an over-permissive firewall rule.

## Complete File Inventory and Purpose

| File | Purpose |
|------|---------|
| `README.md` | Architecture decision record: schema-per-service rationale, deployment instructions |
| `local/docker-compose.yml` | Docker Compose service definition for local SQL Server container |
| `local/Dockerfile` | Docker image definition based on SQL Server 2017 CU20 |
| `local/entrypoint.sh` | Container entrypoint: starts SQL Server, calls db-configure.sh |
| `local/db-configure.sh` | Polls for SQL Server readiness, then runs db-setup.sql via sqlcmd |
| `local/db-setup.sql` | Idempotent T-SQL to create Theater, Customer, diiadministration databases |
| `aks/create-database.sh` | Azure CLI script to provision Azure SQL server, firewall rule, and databases |

## Security Vulnerabilities — CRITICAL

### VULN-1: Hardcoded SA Password (CRITICAL)
**File**: `local/docker-compose.yml` lines 24–25 and `local/db-configure.sh` line 9  
**Detail**: The SA password `B00t1ful` is committed in plaintext to version control. Any developer or CI/CD runner with access to this repository can extract this credential. Although this is an exemplar repo, teams copying this pattern may inadvertently replicate the pattern.  
**PCI DSS**: Violates Requirement 8.3.1 (user authentication management).  
**Remediation**: Replace with Docker secrets or environment variable injection from a secrets manager. Use `${SA_PASSWORD}` resolved from Azure Key Vault or HashiCorp Vault at deploy time.  
**Priority**: P1 — Fix before this pattern is used as basis for any production or CDE-adjacent service.

### VULN-2: Hardcoded AKS Admin Password (CRITICAL)
**File**: `aks/create-database.sh` line 3  
**Detail**: `export password=B00t1ful` commits the Azure SQL admin password to version control.  
**Remediation**: Use `az keyvault secret show` to retrieve at runtime, or use Azure Managed Identity with Azure AD authentication (passwordless).  
**Priority**: P1.

### VULN-3: Over-Permissive Firewall Rule (HIGH)
**File**: `aks/create-database.sh` lines 29–34  
**Detail**: `startip=0.0.0.0` / `endip=223.255.255.255` opens the Azure SQL server to virtually all internet traffic. This effectively makes the database internet-accessible.  
**PCI DSS**: Violates Requirement 1.3 (prohibit direct public access between internet and the CDE).  
**Remediation**: Replace with AKS egress IP range only.  
**Priority**: P1 — Non-negotiable for any production or CDE-adjacent deployment.

### VULN-4: SA Account for Application Connectivity (HIGH)
**File**: `local/docker-compose.yml` lines 24–25, `local/db-configure.sh` line 9  
**Detail**: Applications that follow this exemplar will connect as `SA`, which has unrestricted access to all databases on the instance, violating least-privilege.  
**Remediation**: Create per-service SQL logins with SELECT/INSERT/UPDATE/DELETE on their own database only.  
**Priority**: P2.

### VULN-5: Outdated Base Image (MEDIUM)
**File**: `local/Dockerfile` line 1 — `mcr.microsoft.com/mssql/server:2017-CU20-ubuntu-16.04`  
**Detail**: SQL Server 2017 on Ubuntu 16.04 (EOL). Ubuntu 16.04 reached end-of-standard-support in April 2021.  
**Remediation**: Upgrade to `mcr.microsoft.com/mssql/server:2022-latest` on Ubuntu 22.04.  
**Priority**: P2.

## Technical Debt

| Item | Debt Type | Description |
|------|-----------|-------------|
| No CI/CD pipeline | Process | No automated validation, no credential scanning, no Dockerfile linting |
| No versioning strategy | Process | No VERSION file, no Git tags |
| Azure SQL Basic tier | Infrastructure | 5 DTU / 2 GB limit, not suitable for production |
| `unless-stopped` restart policy | Operational | Will auto-restart even after intentional stop unless `docker-compose down` is used |
| SQL Server 2017 | Technical | EOL platform, missing 5+ years of security patches |

## Shell Script Quality Notes

### `local/db-configure.sh`
- **Polling loop** (lines 7–11): Uses `i=$i+1` which in Bash performs string concatenation, not integer addition. After one iteration `i` becomes `11` (string "1" + string "1"), after two `i=111`, etc. The loop will never exit early via the counter — it only exits when SQL Server responds. This is a latent bug: if SQL Server never starts, the loop runs indefinitely until the `$STATUS` check at line 13 catches the outer `while` exit condition, which actually works correctly despite the counter bug because `$STATUS` is checked properly.
- **Recommendation**: Use `((i++))` for integer arithmetic.

### `aks/create-database.sh`
- No error handling: if `az sql server create` fails, the script continues to `firewall-rule create` and `db create` against a non-existent server.
- **Recommendation**: Add `set -e` at the top to fail fast on any error.

## Remediation Priority Summary

| Priority | Item |
|----------|------|
| P1 | Remove hardcoded passwords (VULN-1, VULN-2) |
| P1 | Restrict firewall rule to specific CIDR (VULN-3) |
| P2 | Implement least-privilege SQL logins (VULN-4) |
| P2 | Upgrade SQL Server base image (VULN-5) |
| P2 | Fix shell arithmetic bug in `db-configure.sh` |
| P3 | Add CI/CD pipeline with secret scanning and Dockerfile linting |
| P3 | Add version tagging strategy |
