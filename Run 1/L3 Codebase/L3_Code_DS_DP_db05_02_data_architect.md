# DS_DP_db05 — Data Architect Report

## Data Architecture — Limitations of Analysis

DB05's repository contains **no DDL (CREATE TABLE, CREATE PROCEDURE, ALTER TABLE) scripts** for application databases. All repository evidence is limited to:
1. Infrastructure/maintenance stored procedures in `master`
2. SQL Agent job scripts in `msdb`
3. A server-level trigger and permission script targeting `master`

This means **no application tables, views, stored procedures, or functions can be documented from repository evidence alone**. Any complete data architecture for DB05 requires direct catalog inspection of the live server.

---

## Objects Confirmed from Repository

### `master` Database

| Object | Type | Source file | Purpose |
|---|---|---|---|
| `IndexOptimize_AgentWrapper` | Stored Procedure | `IndexOptimize_AgentWrapper.sql` | Time-aware index maintenance wrapper (Ola Hallengren-based) |
| All Ola Hallengren objects | Stored Procedures, Tables | `MaintenanceSolution_20191201213232.sql` | Full maintenance solution: `DatabaseBackup`, `DatabaseIntegrityCheck`, `IndexOptimize`, `CommandLog`, `CommandExecute` etc. |
| `TR_check_ip_address_functional_user` | Server Trigger | Inferred from shared scripts | IP-based logon access control (identical to all other nodes) |
| `ValidIPAddress` | Table (existing, not created here) | Referenced by trigger | IP address allowlist |
| `usernames_functional_accounts` | Table (existing) | Referenced by trigger | Functional account registry |

### `msdb` Database (SQL Agent)

| Object | Type | Source file | Purpose |
|---|---|---|---|
| `DBMP User Databases -- Index and stats reorg (custom)` | SQL Agent Job | `20200212_NAMDATASVC-1880_DB05 Index and stats reorg and Integrity check jobs.sql` | Daily index maintenance using `IndexOptimize_AgentWrapper` |
| `DBMP User Databases -- Integrity Check (custom)` | SQL Agent Job | Same source | Weekly integrity check on ALL_DATABASES |

---

## Ola Hallengren Maintenance Solution — Object Inventory

The `MaintenanceSolution_20191201213232.sql` deploys the following standard objects (consistent across DB04, DB05, DB06):

| Object | Type | Purpose |
|---|---|---|
| `dbo.DatabaseBackup` | Stored Procedure | Database, differential, log backup orchestration |
| `dbo.DatabaseIntegrityCheck` | Stored Procedure | DBCC CHECKDB orchestration |
| `dbo.IndexOptimize` | Stored Procedure | Index reorganize/rebuild based on fragmentation thresholds |
| `dbo.CommandExecute` | Stored Procedure | Command execution helper with error handling |
| `dbo.CommandLog` | Table | Execution log for all maintenance operations |

---

## Databases Referenced in Permission Scripts

The `WDNAMCBTS-343_DB05 Grant temporary view definition permissions.sql` and its reversal `SQ-1448_DB05 revoke temporary view definition permissions.sql` do not explicitly name the target databases — they use `GRANT VIEW ANY DEFINITION TO [NAM\nikhil.sapre]` at the server level (master context). This means the VIEW DEFINITION grant applies to **all databases on the DB05 instance**, not a specific one.

This server-level grant means that at the time of the grant (August–December 2020), the user `NAM\nikhil.sapre` had visibility into the schema of every database on DB05 — revealing what databases exist and their full object definitions.

---

## Inferred Database Presence

While application scripts are absent, the following can be inferred:

1. **`DBAdmin` database likely present** — The cleanup job for `Audit_blocked_ip_user` follows the same shared script deployed across all nodes. If the trigger (`TR_check_ip_address_functional_user`) is deployed on DB05, the `DBAdmin` database with `Audit_blocked_ip_user` table is also present.

2. **Some user databases exist** — The integrity check job targets `ALL_DATABASES`, which would include at least the system databases and any user databases. If DB05 were completely empty of user databases, the integrity check job would be unnecessary.

3. **`EcountCore` or similar possible** — Given DB05 sits in the DS_DP cluster between DB04 and DB06, it may host a partition or subset of EcountCore data. Without direct server access, this cannot be confirmed from the repository.

---

## Schema Comparison vs. Other Nodes

| Schema element | DB01 | DB02 | DB04 | DB05 | DB06 | DB07 |
|---|---|---|---|---|---|---|
| Application DDL in repo | YES | YES | YES | **NO** | YES | YES (SSIS) |
| Maintenance solution | YES (implied) | YES | YES | **YES (explicit)** | YES | No |
| Audit trigger | YES | YES | YES | **YES (implied)** | YES | YES |
| Any named user databases | Repositorysvc, Jobsvc, Ordersvc | EcountCore, EcountCore_Process | cbaseapp | **UNKNOWN** | cf_report, Vendor | SSISDB |

DB05 is the **only node** in the six-node set with no confirmed user database names.

---

## Data Architecture Risk Assessment

| Risk | Severity | Description |
|---|---|---|
| Unknown database inventory | HIGH | No evidence of what databases exist on DB05; PCI DSS requires all in-scope systems to be fully inventoried |
| Potential shadow databases | MEDIUM | User databases may exist on DB05 with cardholder data not captured in any change script |
| Maintenance scope | MEDIUM | Integrity check on `ALL_DATABASES` with no exclusions — if cardholder data databases exist, they are being integrity-checked but not documented |
| Partition/shard ambiguity | MEDIUM | DB05's role in the sharding model is unknown |

---

## Recommended Data Architecture Actions

1. **Execute catalog discovery:** `SELECT name, create_date, state_desc FROM sys.databases` on the live DB05 server to inventory all databases
2. **Check for user tables:** For each user database, execute `SELECT TABLE_SCHEMA, TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE = 'BASE TABLE'`
3. **Identify cardholder data:** Run a discovery scan for PAN-pattern data (`LIKE '%[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]%'`) in text columns
4. **Document and scope:** Add findings to the PCI DSS system inventory and CDE scope documentation
5. **Reconcile with DB network diagram:** Confirm DB05 IP addresses are in the ValidIPAddress list and properly segmented from non-CDE systems
