# DS_DP_db01 — Data Architect Report

## Repository Context

All objects documented here are inferred from change scripts applied to the DB01 SQL Server instance. DB01 does not appear to be a schema-definition (DDL) repository — no CREATE TABLE statements for primary application tables are present. The scripts are operational change scripts. Schemas are cross-referenced from neighboring databases and from DML evidence.

---

## Database Instances and Schemas Observed

### `Repositorysvc` (Application database)

**Tables referenced:**

| Table | Columns observed | Sensitive data flags |
|---|---|---|
| `dbo.repo_file` | `file_id` (GUID PK), `file_name`, `file_version_number`, `file_type_id`, `created`, `program_id` (char 8), `archived_name`, `submission_channel_id`, `encryption_code` | `program_id` — card BIN/program identifier; `submission_channel_id` — may encode channel type; `encryption_code` — cryptographic key reference (**FLAG: key reference should never be stored in clear text**) |
| `dbo.repo_file_association` | `file_id`, `associated_file_id` | None sensitive in columns, but links enrollment documents |
| `dbo.repo_file_attributes` | `file_id`, `attribute_id`, `attribute_value` | `attribute_value` — **FLAG: free-form field, may contain cardholder PII or document metadata** |
| `dbo.repo_file_attributes_log` | `file_id`, `attribute_id`, `attribute_control_id`, `attribute_value` | Same as above |
| `dbo.repo_file_audit` | `file_id`, `member`, `action_code`, `date`, `host`, `host_relative_path` | Audit trail — not sensitive in itself, but reveals cardholder interaction patterns |

**Archive schema** (`Repositorysvc_rollback` database):
- `dbo.ARCHIVE_repo_file`
- `dbo.ARCHIVE_repo_file_association`
- `dbo.ARCHIVE_repo_file_attributes`
- `dbo.ARCHIVE_repo_file_attributes_log`
- `dbo.ARCHIVE_repo_file_audit`

All archive tables are direct mirrors of production. Evidence: `20191230_NAMDATASVC-1642-Job-Prune Repo File.sql`, lines 80–113.

---

### `Jobsvc` (Application database)

Referenced in permission grants only. Schema not visible from DB01 scripts. Cross-reference: DB01 hosts this alongside DB02 which also references `Jobsvc`. No DDL changes.

### `Ordersvc` (Application database)

Referenced in permission grants only. No DDL changes visible.

### `DBAdmin` (Administration database)

**Tables created in DB01 scripts:**

| Table | DDL source | Columns | Purpose |
|---|---|---|---|
| `dbo.Audit_blocked_ip_user` | `20200917_WDNAMCBTS-517_001_DBAdmin.Audit_blocked_ip_user.sql`, line 6–18 | `created` (datetime), `IP_Address` (varchar 48), `Host_Name` (nvarchar 256), `Original_Login` (nvarchar 256), `Program_Name` (nvarchar 256) | Security audit log for blocked logon attempts |

**Index:** `IX_Audit_blocked_ip_user_created` (nonclustered, on `created`, ONLINE=ON). Source: same file, lines 14–17.

**Cleanup job:** `DBMP - DBAdmin - Cleanup Audit_blocked_ip_user` — weekly Saturday 05:00 AM, retains 90 days. Source: `20200917_WDNAMCBTS-517_003_...sql`, lines 44–48.

---

### `master` (SQL Server system database)

**Objects created/modified:**

| Object | Type | Source file | Description |
|---|---|---|---|
| `TR_check_ip_address_functional_user` | Server-level logon TRIGGER | `20200917_WDNAMCBTS-517_002_master.TR_check_ip_address_functional_user.sql` | Blocks functional user accounts from logging in from non-whitelisted IP addresses. Executes as `sa`. |
| `ValidIPAddress` | Table (referenced, not created here) | Same file, line 33 | IP address allowlist — **PCI DSS CDE network control** |
| `usernames_functional_accounts` | Table (referenced, not created here) | Same file, line 31 | Functional account registry |
| `IndexOptimize_AgentWrapper` | Stored procedure | Present in DB04/DB05 shared copy; also used on DB01 | Time-aware index maintenance wrapper (Ola Hallengren-based) |

---

## Sensitive Data Field Inventory

| Field | Table | Database | Sensitivity | PCI/Regulatory Flag |
|---|---|---|---|---|
| `encryption_code` | `repo_file` | `Repositorysvc` | HIGH | **PCI DSS Req 3.5** — key management data must be protected; storing key reference in application table is a concern |
| `attribute_value` | `repo_file_attributes` | `Repositorysvc` | MEDIUM–HIGH | Free-form; may contain cardholder name, DOB, SSN fragment from enrollment docs |
| `program_id` (char 8) | `repo_file` | `Repositorysvc` | LOW-MEDIUM | BIN-derived program identifier; not PAN but a CDE-adjacent value |
| `IP_Address` | `Audit_blocked_ip_user` | `DBAdmin` | LOW | Operational security log; not cardholder data |
| `Original_Login` | `Audit_blocked_ip_user` | `DBAdmin` | MEDIUM | Username of attempted login; IAM-sensitive |

**Note:** No PAN (Primary Account Number), CVV/CVC, PIN, or full account number is visible in any DB01 script. The `ach_transfer_detail` table referenced in `20191210_NATS-6125_update_ach_transfer_detail.sql` contains `id = 199660523` (an integer row identifier, not a payment account number), `status_code`, `transfer_id` — no ACH routing or account number fields are populated in the script directly.

---

## PCI DSS CDE Scope Assessment

DB01 is **in-scope for PCI DSS CDE** because:
1. It hosts `Repositorysvc`, which stores enrollment document metadata including `encryption_code` and `attribute_value` fields that may contain cardholder identity data.
2. The `master` database logon trigger directly enforces network-level access controls to the CDE, placing DB01 within the controlled network boundary.
3. ACH transfer correction scripts indicate DB01 participates in payment processing workflows.

**CDE boundary evidence:** The IP allowlist mechanism (`ValidIPAddress` in `master`) and the logon trigger (`TR_check_ip_address_functional_user`) together constitute PCI DSS Requirement 1/7/8 controls implemented at the database server level.

---

## Schema Design Observations

1. **Archival pattern:** DB01 uses a parallel `_rollback` database for archival of aged records rather than partitioning or soft-delete. This is a simpler but less scalable approach compared to DB04's monthly partition scheme.

2. **GUID primary keys:** `repo_file.file_id` is a GUID (`UNIQUEIDENTIFIER`). GUIDs as clustered keys cause index fragmentation at scale — a potential performance concern for a repository holding millions of file records.

3. **No foreign key constraints visible** in the scripts (only column-level references). This suggests the application enforces referential integrity in code, not the database — a technical debt flag.

4. **Filegroup:** No custom filegroup for `Repositorysvc` is visible; contrast with DB02 where `FDR_DATA` filegroup is explicitly used for KYC tables.

5. **TempDB configuration:** 8 equally-sized files (10 GB each, 512 MB autogrowth) on `G:\MSSQL11.DB01\MSSQL\Data\` — follows SQL Server best practice of multiple tempdb files for SGAM page contention reduction. Evidence: `20200124_NAMDATASVC-1454_C-DB01 add tempdb files.sql`.

---

## Data Partitioning / Sharding Strategy

DB01 does not implement table-level partitioning within its own schemas (contrast DB04 which uses `cbaseapp_process_monthly_partition`). The node-level sharding (DB01 vs DB02 vs DB04 etc.) appears to be **program-based** — different card programs or client groups are assigned to different DB nodes. This inference is supported by:
- The `program_id` column present throughout all database objects across all nodes
- The presence of separate `source` and `facility` identifiers in transaction codes that encode node-aware routing
- DB06's `BINBANK` schema scripts which explicitly manage program-to-BIN mappings that could drive sharding decisions
