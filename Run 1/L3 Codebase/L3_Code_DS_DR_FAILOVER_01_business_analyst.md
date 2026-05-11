# Business Analyst Report — DS_DR_FAILOVER

## Repository Identity

**Repository:** DS_DR_FAILOVER  
**Classification:** Disaster Recovery — Failover Runbook (SQL Scripts)  
**Technology:** Microsoft SQL Server T-SQL — executed manually during DR events  
**Structure:** 7 ordered step directories (0010 through 0070), each containing SQL scripts per server  

---

## Business Purpose

DS_DR_FAILOVER is the **documented, manual failover runbook** for Onbe's SQL Server database infrastructure. It provides the ordered sequence of T-SQL scripts required to transition from the production database environment to the disaster recovery (DR) environment following a primary data centre outage or major infrastructure failure.

This repository is directly relevant to **business continuity** for Onbe's core payment-processing, card-issuance, and financial-reporting operations. A failure to execute failover correctly, or a failure to keep these scripts current, would result in extended downtime for:
- Prepaid card transaction authorisation
- Sales Order automation and fee invoicing
- GP (Great Plains) financial reporting
- Atlys revenue and forecast reporting
- ATM cash management

---

## Failover Procedure — Step Sequence

The repository is organised into 7 ordered phases:

### Step 0010 — Disable Log Shipping Jobs
**File:** `0010_disable_log_backup_jobs/Disable_all_logshipping_jobs_run_on_all_servers.sql`  
**Run on:** ALL production database instances  
**Purpose:** Stops all log shipping jobs (identified by `description LIKE 'log shipping%'`) on every production server. This prevents log files from being applied to the DR instance while the failover is in progress, avoiding data consistency conflicts.  
**Method:** Cursor iterating over `msdb.dbo.sysjobs` — all log shipping jobs are disabled via `sp_update_job`.

### Step 0020 — Take Tail-Log Backups
**Files:** Per-server SQL scripts for `p-az-db14`, `pc-db01`, `pc-db02`, `pc-db03`, `pc-db04`, `pc-db05`, `pc-db06`  
**Purpose:** Captures the final committed transactions that have not yet been shipped to the DR instance. Uses `WITH NO_TRUNCATE, NORECOVERY` to capture the tail of the log even if the database is in a damaged state.

Production servers covered:

| Server | Databases Backed Up |
|---|---|
| `p-az-db14` | AcctgWf, ATLYS_E, ATLYS_Fc_NCA, ATLYS_Fc_NUS, ATLYS_FcCR, ATLYS_Rv_NCA, ATLYS_Rv_NUS, ATLYS_RvCR, DBAdmin, DYNAMICS, ECAN, ECNT, Banker_NA, Banker, TWO, EMEAM, EMXN |
| `pc-db01` | Ordersvc, JobSvc, DBAdmin, jobsvc_rollback, Repositorysvc, repositorysvc_rollback |
| `pc-db02` | (per restore script) Ecountcore, ECountCore_Service, Ecountcore_Process |
| `pc-db03` | Cbaseapp, NotificationSvc |
| `pc-db04` | (separate file) |
| `pc-db05` | Analysis, Cbaseapp_Archive, CCP, cf_report, Dbadmin, Ecountcore_Archive, EcountIds, ODS, RiskDB, RS2008, RS2008TempDB, Vendor, ECNT_R, ECAN_R, ATLYS_E_R, ATLYS_Fc_NCA_R, ATLYS_fc_NUS_R, ATLYS_rv_NCA_R, ATLYS_rv_NUS_R, plus mirrored DBs |
| `pc-db06` | (per restore script) Ecountcore and related |

Backup files are written to UNC paths (`\\<server>\shipping\`) — a shared network location on each server.

### Step 0030 — Restore Tail-Log Backups on DR
**Files:** Per-DR-server restore scripts — target servers named `pc-az2-db*` and `p-az2-db14`  
**Purpose:** Applies the tail-log backups to the DR SQL Server instances, bringing them to the point of the last committed transaction on production. Databases are brought online in `MULTI_USER` mode after restore, making them available to applications.  
**Mirrored Databases:** The pc-db05 restore script also handles mirrored databases (`Cbaseapp`, `NotificationSvc`, `Ecountcore`, `ECountCore_Service`, `Ecountcore_Process`, `Ordersvc`, `JobSvc`) which are restored with `NORECOVERY` first, then require a final log backup from primary and restoration to prepare for mirroring.

### Step 0040 — Apply Data Patches
**Files:** `p-az2-db14_data_patches.sql`, `pc-az2-db05_data_patch.sql`, `pc-az2-db06_data_patches.sql`  
**Purpose:** Updates hardcoded server name references in configuration tables after failover. The DR servers have different names than production, so any configuration storing the server name must be updated.  

Key updates applied on `p-az2-db14`:
- `ATLYS_E.dbo.tblCompanies.gp_db_name` — updated with new server name using `QUOTENAME(@@SERVERNAME)`
- `Banker.dbo.SSISConfigurations.ConfiguredValue` — server name replacements: `p-az-db14` → `p-az2-db14`, `pc-db05,2231` → `pc-az2-db05\pi_az2_db05`
- `Banker.dbo.SSISJobConfigurations.ProcessLoopParameters` and `.JobParameters` — XML column replacements for server names and UNC paths
- `ATLYS_E.dbo.tblPaths` — file share path updates: `P-AZ-FS01` → `P-AZ2-FS01`
- `ECNT.dbo.asi12303.ASI_Crystal_Report_Name` — report path updates
- `ECAN.dbo.asi12303.ASI_Crystal_Report_Name` — report path updates

### Step 0050 — Backup and Restore for Mirroring
**Files:** Per-database backup and restore scripts for `pc-az2-db01`, `pc-az2-db02`, `pc-az2-db03`, `pc-az2-db05`  
**Purpose:** Takes log backups on the DR servers (now primary) for databases that use SQL Server Database Mirroring, then restores them to the DR mirror instances to establish mirroring on the DR side.

### Step 0060 — Recreate Replication
**Files:** `001_p-az2-db14_gen_create_replication.sql`, `002_pc-az2-db05_create_replication.sql`, `003_p-az2-db14_create_subsctriptions.sql`  
**Purpose:** Re-establishes the SQL Server Transactional Replication topology on the DR servers. The replication setup script configures:
- Distribution database on `pc-az2-db05\pi_az2_db05`
- Publisher: `p-az2-db14`
- Subscriptions for ATLYS_* databases (`ATLYS_E_to_ATLYS_E_R`, and others)
- Pull subscription agents with `NAM\sql_svc` as the job login

**Critical Note:** The replication script (`002_pc-az2-db05_create_replication.sql`) contains placeholder text:
```
**replace_with_password**   (distributor admin password)
**replace_sqlsvc_password** (NAM\sql_svc password)
```
These passwords must be manually substituted at failover time.

### Step 0070 — Enable Jobs on DR
**File:** `0070_enable_all_jobs_in_dr/EnableJobs_Run_All_Servers.sql`  
**Run on:** ALL DR servers  
**Purpose:** Reads the list of production-enabled jobs from `dbadmin.dbo.enabled_production_jobs` (populated from production via log shipping) and enables those same jobs on the DR SQL Agent instances.

---

## Regulatory Relevance

### PCI DSS Req 12.3 — Business Continuity / Disaster Recovery
PCI DSS Requirement 12.3 mandates that entities maintain a business continuity plan that addresses DR for systems in the CDE. The databases covered by this failover runbook include `ECNT`, `ECAN`, `CCP`, `EcountIds`, and `Ecountcore` — all potential CDE databases given their role in prepaid card processing.

**Key compliance observations:**
- The runbook is documented as executable scripts (positive), but is entirely manual
- No documented RTO (Recovery Time Objective) or RPO (Recovery Point Objective) is present in the repository
- No evidence of DR test execution is recorded (test logs, test schedules)

### NACHA / ACH Processing
`Ordersvc`, `JobSvc`, and `Repositorysvc` support ACH processing pipelines. A failover gap in these databases would disrupt ACH payment settlements.

### SOX Financial Reporting
`DYNAMICS`, `ECNT`, `ECAN`, `AcctgWf`, and the `ATLYS_*` databases support financial reporting. DR for these systems is relevant to SOX business continuity controls.
