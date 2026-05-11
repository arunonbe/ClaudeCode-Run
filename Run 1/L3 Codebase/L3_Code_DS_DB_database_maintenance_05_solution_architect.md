# Solution Architect View — DS_DB_database_maintenance

## Technical Architecture
- **Technology**: T-SQL scripts targeting SQL Server 2005–2019 (per Ola Hallengren framework header). No minimum version constraint enforced beyond compatibility level ≥ 90.
- **Object model**: One custom stored procedure (`IndexOptimize_AgentWrapper`) in `master`; two SQL Agent jobs in `msdb`; all framework objects installed by `MaintenanceSolution_20191201213232.sql`.
- **Execution model**: SQL Agent → `CmdExec` subsystem (step 1: `sqlcmd`) and T-SQL subsystem (step 2, integrity check).

## API Surface
None. This repository has no API surface — it exposes no web endpoints, service interfaces, or inter-database stored procedure contracts consumed by application code.

## Security Posture

### Authentication
- Job execution runs as the SQL Server Agent service account (Windows auth, `sqlcmd -E`).
- Job ownership assigned to `sa` — a shared server-level login with unrestricted sysadmin rights.
  - **Finding (HIGH)**: `IndexOptimize_AgentWrapper.sql` line 29, `DBMP...sql` line 29 — `@owner_login_name=N'sa'`. Under PCI DSS Req 8.2, `sa` must be renamed or disabled. If `sa` is disabled, both jobs will fail silently.

### Authorisation
- Installation requires `sysadmin` server role (enforced in `MaintenanceSolution` line 39: `IF IS_SRVROLEMEMBER('sysadmin') = 0`).
- No least-privilege service account is established by the scripts.

### Cryptography
- No encryption in use. Not applicable for this tooling layer.

### Secrets
- No hardcoded passwords or connection strings found.
- Email notification operator `DataServicesGroup-Operator` is a string reference only; no credentials embedded.

### CVEs / Framework Currency
- Ola Hallengren solution dated `2019-12-01`. Current release is significantly newer (2023+). Known enhancements and edge-case fixes have been missed.
  - **Finding (MEDIUM)**: Stale third-party dependency — recommend update to latest Ola Hallengren release.

## Technical Debt
| Item | File | Severity | Notes |
|---|---|---|---|
| `sa` job ownership | `DBMP User Databases -- Index and stats reorg (custom).sql:29` | HIGH | PCI DSS Req 8.2 violation |
| `sa` job ownership | `DBMP User Databases -- Integrity Check (custom).sql:29` | HIGH | Same |
| Integrity check silent failure | `DBMP User Databases -- Integrity Check (custom).sql:23` | HIGH | `@notify_level_email=0` |
| Physical-only CHECKDB | `DBMP User Databases -- Integrity Check (custom).sql:43` | MEDIUM | `@PhysicalOnly='Y'` — logical corruption undetected |
| Stale Ola Hallengren version | `MaintenanceSolution_20191201213232.sql:1` | MEDIUM | 2019-12-01 build; current is 2023+ |
| MaxNumberOfPages=50GB cap | `IndexOptimize_AgentWrapper.sql:24` | MEDIUM | Large indexes never rebuilt |
| No CommandLog cleanup | (absent) | MEDIUM | Table grows without bound |
| No backup scripts | (absent) | HIGH | README claims backup coverage; not present |
| No SSDT project | (repo-level) | LOW | No build validation, no dacpac |

## Gen-3 Migration Requirements
This repo is infrastructure-only and does not gate application Gen-3 migration. If the target platform moves to:
- **Azure SQL Managed Instance**: Ola Hallengren works as-is.
- **Azure SQL Database**: Must replace `IndexOptimize` with elastic jobs + Azure Automation; `DatabaseIntegrityCheck` is not applicable (PaaS manages integrity).
- **Cloud-native (containerised SQL)**: Same as Azure SQL MI path.

## Code-Level Risks
| Risk | File:Line | Description |
|---|---|---|
| CmdExec subsystem required | `DBMP...Index and stats reorg.sql:44` | `@subsystem=N'CmdExec'` — if CmdExec is disabled at server level, step 1 fails silently |
| Dynamic server name detection fragile | `IndexOptimize_AgentWrapper.sql:17` | `LEFT(@@SERVERNAME,1) = 'C'` — one-character convention; any server starting with C is disabled, including future production servers if naming changes |
| `@TimeLimit` negative prevention | `IndexOptimize_AgentWrapper.sql:57` | `IF @TimeLimit > 0` guard exists but `ELSE` branch (business-hours outside 0–24) is not handled — code falls into `@Hour > 7` branch for hours 0–7 if conditions overlap |
| Hardcoded schedule UID | `DBMP...Index and stats reorg.sql:75` | `@schedule_uid=N'2df1f27b-...'` — will collide if script is run twice on the same instance |
