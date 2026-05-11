# DS_DP_db01 — DevOps & Operations Report

## Repository Structure and Deployment Model

The `DS_DP_db01` repository contains **no CI/CD pipeline definitions**, no Jenkinsfile, no `.gitlab-ci.yml`, no Azure DevOps YAML, no Docker or Kubernetes manifests, and no IaC (Terraform/Ansible) files. It is a flat collection of SQL scripts and one README (containing only the text "db01").

This means DB01, like all DS_DP_db* repositories, follows a **manual or semi-automated DBA-driven change management** model rather than a code-pipeline model.

---

## Change Management Approach

### File Naming Convention
All change scripts follow the pattern:
```
YYYYMMDD_TICKETREF_Description.sql
```

Examples:
- `20200917_WDNAMCBTS-517_001_DBAdmin.Audit_blocked_ip_user.sql`
- `11222019_NATS-5942_RepoCleanUp.sql` (older pre-2020 scripts use inconsistent date prefix format MMDDYYYY)

**Observation:** There is an inconsistency between pre-2020 scripts (MMDDYYYY format: `11222019_NATS-5942_...`) and 2020+ scripts (YYYYMMDD format: `20200917_WDNAMCBTS-517_...`). This creates a sorting ambiguity in the git log and reduces operational clarity during incident response.

### Ticket System Integration
Scripts reference two ticket systems:
- **NATS-XXXXX** — internal Jira-style ticket system (NorthLane/Wirecard internal)
- **NAMDATASVC-XXXX** — Data Services sub-project tickets
- **WDNAMCBTS-XXX** — Wirecard CBTS (Card-Based Transaction Services) project
- **SQ-XXXX** — A separate ticketing prefix (post-rebrand Onbe era)

This multi-prefix pattern reflects the 2020 Wirecard-to-NorthLane corporate transition and confirms the codebase spans a major company ownership change.

---

## Environments

Evidence of multi-environment deployment is found in the IP-based trigger script and the cleanup job:

```sql
-- From 20200917_WDNAMCBTS-517_003...sql, line 17:
DECLARE @enabled TINYINT = CASE WHEN @@SERVERNAME LIKE 'C-%' THEN 0 ELSE 1 END
```

This pattern is consistent across multiple files. It reveals:

| Prefix | Environment | Behavior |
|---|---|---|
| `C-` | Cold-standby / DR replica | Jobs disabled (enabled=0) |
| `P-` | Production | Jobs enabled (enabled=1) |
| `D-` / `T-` / `Q-` | Dev / Test / QA | Referenced in DB07 SSIS configs for connection strings |

The DB01 server name follows the pattern `P-DB01` (Production) or `C-DB01` (Cold standby). TempDB file path confirms `G:\MSSQL11.DB01\MSSQL\Data\` — a dedicated drive letter typical of production SQL Server installations.

---

## SQL Agent Jobs Deployed

### `Z_application_Prune repository file`
- **Source:** `20191230_NAMDATASVC-1642-Job-Prune Repo File.sql`
- **Schedule:** Weekly, Saturdays at 20:00 (8 PM)
- **Action:** Archives repo_file records older than 3 months into `repositorysvc_rollback` then deletes from production
- **Owner:** `sa` (service account)
- **Operator:** `DataServicesGroup-Operator`
- **Category:** Database Maintenance

### `DBMP - DBAdmin - Cleanup Audit_blocked_ip_user`
- **Source:** `20200917_WDNAMCBTS-517_003_SQLAgent-DBMP - DBAdmin - Cleanup Audit_blocked_ip_user.sql`
- **Schedule:** Weekly, Saturdays at 05:00
- **Action:** Deletes `Audit_blocked_ip_user` records older than 90 days
- **Disabled on cold-standby** via `@@SERVERNAME LIKE 'C-%'` check
- **Owner:** `sa`

---

## Database Mail Configuration

- **Account name:** `NoReply` → `NoReply@northlane.com` (updated from wirecard.com)
- **Operator name:** `DataServicesGroup-Operator` (standard across all DB nodes)
- **Source:** `20201113_SQ-1114 update sql agent operator and dbmail account.sql`, lines 33–35

---

## TempDB Configuration (Infrastructure)
- **8 data files** added in January 2020 (`NAMDATASVC-1454`)
- Each file: 10 GB initial size, 512 MB autogrowth
- Path: `G:\MSSQL11.DB01\MSSQL\Data\tempdb*.ndf`
- This is a known SQL Server performance best practice for OLTP workloads with high parallelism

---

## Deployment Process (Inferred)

1. Developer or DBA raises a Jira/NATS ticket
2. SQL script is authored and committed to Git with the ticket reference in the filename
3. Script is manually reviewed (no automated linting or CI visible)
4. Script is executed on Production server by DBA, then on Cold-standby
5. Script is committed to the `master` branch of the repo as documentation/audit trail

**No rollback automation exists.** Some scripts include commented-out rollback sections (e.g., `20201201_SQ-1448_DB01 revoke remporary view definition permissions.sql` — the revoke script IS the rollback), but these require manual DBA execution.

---

## Backup and Recovery

No explicit backup scripts are present in this repo. Recovery strategy is inferred from:
1. **Cold-standby pattern** (`C-` prefix servers) — SQL Server mirroring or Always On AG with a secondary node
2. **Archive databases** (`Repositorysvc_rollback`) — application-level point-in-time recovery supplement
3. **DB mirroring references:** `20201201_SQ-261_DB01 revoke permissions for audit users to mirrored databases.sql` uses the term "mirrored databases," confirming High Availability mirroring is in use

**Recovery concern:** The `repositorysvc_rollback` archive database is on the same SQL Server instance. If the disk fails, both primary and archive are lost simultaneously. This is a gap relative to PCI DSS Requirement 12.3 (backup integrity).

---

## Operational Risk Observations

1. **No automated deployment pipeline** — all changes are manual, creating risk of deployment sequence errors across multiple DB nodes.
2. **`sa` as job owner** — all SQL Agent jobs use `sa` as the owner. This violates least-privilege principles (PCI DSS Req 7) and should use a dedicated service account.
3. **Inconsistent date format in filenames** — makes chronological sorting unreliable.
4. **No migration framework** — no Flyway, Liquibase, or SSDT project file present. Script ordering must be manually managed.
5. **Audit log retention** — 90 days for `Audit_blocked_ip_user`. PCI DSS Requirement 10.7 requires 12 months (3 months immediately available online). This job may be deleting data before the 12-month minimum is met unless there is an external SIEM ingesting these logs.
