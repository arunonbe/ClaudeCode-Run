# DS_DP_db01 — Solution Architect Report

## Technical Debt Inventory

### TD-01: SQL Server 2012 (End of Life)
- **Evidence:** Path `G:\MSSQL11.DB01\MSSQL\Data\` (`MSSQL11` = SQL Server 2012)
- **Risk:** CRITICAL — No security patches since July 2022. PCI DSS Req 6.3.3 violation.
- **Remediation:** In-place upgrade or side-by-side migration to SQL Server 2019/2022 with Always On AG
- **Priority:** P0

### TD-02: `sa` as SQL Agent Job Owner
- **Evidence:** All jobs use `@owner_login_name=N'sa'` (lines 29, 57 in prune job script)
- **Risk:** HIGH — Violates PCI DSS Req 7 least privilege. If `sa` credentials are compromised, all jobs can be manipulated.
- **Remediation:** Create dedicated service account `svc_sqlagent_db01`, reassign ownership
- **Priority:** P1

### TD-03: Manual Deployment Model, No CI/CD
- **Evidence:** No pipeline files in repo; flat SQL scripts with manual date prefixes
- **Risk:** HIGH — Manual deployments increase risk of out-of-order script execution, especially across DB01/DB02/DB04 which must stay synchronized on transaction code tables
- **Remediation:** Implement Flyway or Liquibase with Git-based versioning and pipeline gates
- **Priority:** P1

### TD-04: Inconsistent Date Prefix Format
- **Evidence:** Pre-2020 scripts use MMDDYYYY (`11222019_NATS-5942_...`), post-2020 use YYYYMMDD (`20200917_WDNAMCBTS-517_...`)
- **Risk:** MEDIUM — Incorrect lexicographic sorting can cause scripts to appear out of chronological order in directory listings
- **Remediation:** Standardize all filenames to ISO 8601 YYYYMMDD prefix
- **Priority:** P3

### TD-05: GUID Clustered Primary Keys in `repo_file`
- **Evidence:** `file_id UNIQUEIDENTIFIER` is the PK on `repo_file` (referenced throughout prune scripts)
- **Risk:** MEDIUM — Random GUID values cause high B-tree fragmentation (page splits). At millions of records, index maintenance overhead is significant.
- **Remediation:** Consider using `NEWSEQUENTIALID()` or an integer surrogate key with the GUID as a unique constraint
- **Priority:** P2

### TD-06: Archive on Same Instance
- **Evidence:** `Repositorysvc_rollback` archive database on the same SQL Server instance as `Repositorysvc`
- **Risk:** MEDIUM — Disk failure or instance outage destroys both primary and archive simultaneously
- **Remediation:** Archive to a separate instance or external storage (Azure Blob, S3)
- **Priority:** P2

### TD-07: Audit Log Retention Gap
- **Evidence:** `Audit_blocked_ip_user` cleanup job retains 90 days (`@retention_days INT = 90`, line 44 of cleanup job script)
- **Risk:** HIGH — PCI DSS Requirement 10.7 mandates 12 months (3 months immediately available). If no external SIEM captures these logs, the platform is non-compliant.
- **Remediation:** Either extend database retention to 12 months or confirm SIEM ingestion of security events
- **Priority:** P1

### TD-08: `WITH EXECUTE AS 'sa'` on Server-Level Trigger
- **Evidence:** `TR_check_ip_address_functional_user` executes `WITH EXECUTE AS 'sa'` (line 15 of trigger script)
- **Risk:** HIGH — The trigger has unrestricted `sa` context. A SQL injection or elevated execution path could be exploited via the trigger.
- **Remediation:** Create a dedicated low-privilege account for the trigger's execution context; remove `sa` elevation
- **Priority:** P1

### TD-09: No Foreign Key Constraints
- **Evidence:** No `FOREIGN KEY` constraints visible in any script; all associations maintained in application code
- **Risk:** MEDIUM — Data integrity depends entirely on application-layer correctness. Orphaned records accumulate without database-enforced constraints.
- **Remediation:** Add FK constraints at minimum on `repo_file_association.file_id → repo_file.file_id`
- **Priority:** P2

---

## Object Inventory (All Objects Observed)

### `Repositorysvc` Database
| Object | Type | Purpose |
|---|---|---|
| `dbo.repo_file` | Table | Core file metadata registry |
| `dbo.repo_file_association` | Table | File-to-file relationship map |
| `dbo.repo_file_attributes` | Table | Key-value attributes on files |
| `dbo.repo_file_attributes_log` | Table | Historical attribute change log |
| `dbo.repo_file_audit` | Table | User action audit trail on files |

### `Repositorysvc_rollback` Database
| Object | Type | Purpose |
|---|---|---|
| `dbo.ARCHIVE_repo_file` | Table | Archive of aged repo_file rows |
| `dbo.ARCHIVE_repo_file_association` | Table | Archive mirror |
| `dbo.ARCHIVE_repo_file_attributes` | Table | Archive mirror |
| `dbo.ARCHIVE_repo_file_attributes_log` | Table | Archive mirror |
| `dbo.ARCHIVE_repo_file_audit` | Table | Archive mirror |

### `DBAdmin` Database
| Object | Type | Purpose |
|---|---|---|
| `dbo.Audit_blocked_ip_user` | Table | Blocked login attempt audit log |
| `IX_Audit_blocked_ip_user_created` | Index | Performance index on `created` column |

### `master` Database
| Object | Type | Purpose |
|---|---|---|
| `TR_check_ip_address_functional_user` | Server-level Trigger | IP-based access control for functional accounts |
| `ValidIPAddress` | Table (existing) | IP address allowlist |
| `usernames_functional_accounts` | Table (existing) | Functional user account registry |
| `IndexOptimize_AgentWrapper` | Stored Procedure | Time-aware wrapper for Ola Hallengren index maintenance |

### `msdb` Database (SQL Agent)
| Object | Type | Purpose |
|---|---|---|
| `Z_application_Prune repository file` | SQL Agent Job | Weekly archival and purge of old repo file records |
| `DBMP - DBAdmin - Cleanup Audit_blocked_ip_user` | SQL Agent Job | Weekly cleanup of blocked login audit records |

---

## Security Vulnerability Summary

| Vulnerability | Severity | PCI DSS Req | Description |
|---|---|---|---|
| EOL SQL Server 2012 | CRITICAL | 6.3.3 | No vendor security patches available |
| `WITH EXECUTE AS 'sa'` on trigger | HIGH | 7.2 | Overprivileged execution context on logon trigger |
| `sa` as job owner | HIGH | 7.2 | Service accounts should not own agent jobs |
| 90-day audit log retention | HIGH | 10.7 | Below PCI DSS 12-month minimum |
| Archive on same instance | MEDIUM | 12.3 | Loss of instance = loss of archive |
| No FK constraints | MEDIUM | 6.2 | Application-only integrity enforcement |
| GUID clustered PK | LOW | — | Performance degradation at scale |

---

## Schema Inconsistency Notes vs. Other DS_DP Nodes

DB01's schema is the **least complex** of the 6 nodes analyzed. Key differences:
- DB01 has NO `cbaseapp` or `EcountCore` databases (present in DB02 and DB04)
- DB01 has NO partition schemes or partition functions (present in DB04)
- DB01 has NO SSIS catalog or ETL job configurations (present in DB07)
- DB01 has NO `cf_report` or `BINBANK` reporting schema (present in DB06)

This confirms DB01 is a **service-tier node** (document repository + job/order services) rather than a core transaction processing node. It is the simplest migration candidate in the shard set.

---

## Remediation Priority Matrix

| Priority | Item | Effort | Risk Reduction |
|---|---|---|---|
| P0 | Upgrade SQL Server 2012 | HIGH | CRITICAL |
| P1 | Fix `sa` job/trigger ownership | LOW | HIGH |
| P1 | Extend audit log retention to 12 months | LOW | HIGH |
| P1 | Implement CI/CD deployment pipeline | HIGH | HIGH |
| P2 | Add FK constraints | MEDIUM | MEDIUM |
| P2 | Move archive to separate instance | MEDIUM | MEDIUM |
| P3 | Fix filename date prefix format | LOW | LOW |
