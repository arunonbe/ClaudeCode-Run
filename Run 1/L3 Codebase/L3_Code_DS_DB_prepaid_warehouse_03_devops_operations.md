# DS_DB_prepaid_warehouse — DevOps and Operations Assessment

## 1. Build and Deployment Pipeline

### 1.1 Project Type
The repository is a **Visual Studio SQL Server Data Tools (SSDT) project** (`.sqlproj`). The project targets SQL Server 2016 (`DSP: Microsoft.Data.Tools.Schema.Sql.Sql130DatabaseSchemaProvider`) and is built with MSBuild ToolsVersion 4.0 targeting .NET Framework 4.6.1.

### 1.2 Build Artefacts
The project compiles to a DACPAC (Data-tier Application Component Package) placed in:
- Debug: `bin\Debug\Prepaid_Warehouse.sql`
- Release: `bin\Release\Prepaid_Warehouse.sql`

The `.sqlproj` sets `<DeployToDatabase>True</DeployToDatabase>`, meaning the SSDT toolchain is configured to deploy directly to a target SQL Server instance.

### 1.3 CI/CD Observations
**No CI/CD pipeline configuration files are present in this repository.** There are no `.yml`, `.json`, `.groovy` (Jenkins), or Azure DevOps pipeline files (`azure-pipelines.yml`) found in the repository tree. This is a significant operational gap — it means:
- Database schema changes are not automatically validated against a lint or syntax check.
- Deployment to production likely relies on manual DACPAC deployment or DBA-executed scripts.
- There is no automated regression testing for stored procedure logic.

The organisation has a separate `CONFIG_ci-templates` repository and a `ci-scripts_INFRA` repository visible in the broader repository listing, which may contain pipeline templates, but these are not referenced in this project.

### 1.4 `.gitignore`
A `.gitignore` file is present. Inspection of its scope is standard for SSDT projects (typically ignores `bin/`, `obj/`, `.user` files).

---

## 2. Change Management

### 2.1 DeltaSql Folder
The repository contains a `DeltaSql/` folder at the root. This folder typically holds post-deployment incremental change scripts that cannot be expressed as idempotent SSDT `CREATE` statements (e.g., data migrations, `ALTER TABLE ADD COLUMN` with data backfill, lookup table inserts). The presence of this folder indicates a hybrid deployment approach: DACPAC for schema state + DeltaSql scripts for data or transitional changes.

### 2.2 Change History Evidence
Several stored procedures have date-stamped variants committed to source control:
- `rpt_Inventory_Management_Report_card_reissue_06042013.sql`
- `rpt_Inventory_Management_Report_card_reissue_09032013.sql`
- `rpt_Inventory_Management_Report_card_reissue_09092013.sql`
- `rpt_T_Mobile_weekly02182014.sql`

This pattern of keeping old procedures with date suffixes rather than proper version control branching suggests historical change management has been informal. Dead code accumulation is a maintenance risk.

### 2.3 ETL Control and Rollback
ETL change management is partially encoded in the schema itself:
- `dbo.ETL_Master` and `dbo.ETL_Master_History` track ETL run states.
- `dbo.ETL_Master_Rollback` and rollback fact/dimension tables (`FactTransactionAccounts_Rollback`, `DimAccountHolder_Rollback`, `DimProduct_Rollback`, `DimProgram_Rollback`) provide roll-back capability for warehouse loads.
- Stored procedures `sprocInc_Rollback_DW_Load`, `sprocInc_Rollback_FactClaimablePaymentIssuance`, `sprocInc_Rollback_JobSvc_Load` execute rollback operations.

This is a positive operational design — ETL operations can be undone at the data layer.

---

## 3. Storage and Partitioning Operations

### 3.1 Partition Management
The `Storage/` folder contains DDL for three sets of partition functions and schemes. Partition maintenance (adding/removing filegroups as date ranges roll forward) requires DBA intervention. The procedure `sprocInc_Remove_Oldest_Snapshot_Partition` automates removal of the oldest `FactAccountSnapshot` partition, but similar automation for `FactPaymentTransactions` and `FactUtilizationTransactions` is not visible in the repository, suggesting those partitions grow indefinitely unless managed out-of-band.

### 3.2 Index Defragmentation
`dbo.indexDefragList`, `dbo.IndexDefragTables`, and `dbo.sproc_Defrag_Indexes` provide an in-database index defragmentation framework. This is a standard DBA maintenance pattern. The framework has its own control table (`IndexDefragTables`) to configure which indexes to defragment.

### 3.3 Storage Filegroups
`Storage/AllOtherData.sql` and `Storage/FactData.sql` define separate filegroups for fact data versus other data, which is a recommended SQL Server VLDB best practice.

---

## 4. Backup and Recovery

**No backup configuration is encoded in this repository.** SQL Server backup jobs (full, differential, log) are managed at the instance/SQL Agent level and are not part of the SSDT project. Recovery point objectives (RPO) and recovery time objectives (RTO) for this database are not documented in code.

Given the warehouse role (analytical, not OLTP), the likely backup strategy is:
- Full backups: daily or weekly
- Differential: daily
- Transaction log: not applicable if in SIMPLE recovery model

The `database.Prepaid_Warehouse_Intl.sqlproj` (Intl variant) explicitly sets `<PageVerify>CHECKSUM</PageVerify>`, suggesting page-level integrity checking is enabled. The US warehouse sqlproj does not specify this setting, meaning it relies on SQL Server defaults.

---

## 5. ETL Operational Risk

### 5.1 CDC Feed Dependency
The warehouse depends on Change Data Capture (CDC) feeds from operational source systems (EcountCore, FDR processor) through the `stagingdata` schema. If the CDC feed is interrupted or delayed, the warehouse falls out of sync with the operational systems. There is no alerting or monitoring stored procedure visible in this repo for CDC lag.

### 5.2 `sprocInc_Update_PUID` — PUID Synchronisation Risk
`sprocInc_Update_PUID` synchronises Partner User IDs from operational systems. If this procedure fails silently, cardholder identity matching across systems breaks, potentially causing incorrect analytics.

### 5.3 Hold and Work Table Accumulation
Approximately 60 work/hold/staging tables are defined. If ETL processes fail mid-run and rollback is not triggered, these tables can accumulate stale or partial data. The `ETL_Flags` table suggests some flag-based control exists, but the completeness of ETL exception handling is not verifiable from the schema alone.

### 5.4 `RecordsUpdated` Table
A table `dbo.RecordsUpdated` exists as an ETL housekeeping mechanism. Without examination of its contents, it is unclear whether it provides reliable operational reconciliation.

---

## 6. Security Operations

### 6.1 Role-Based Access
The Security folder establishes separate `cf_report_Execute` and `cf_report_Select` roles for reporting, keeping report users separated from ETL service accounts. The `NAM_PPA_PRD_ABAT` account (batch automation) has production access.

### 6.2 Emergency Access Accounts
Multiple `emer_*` accounts are defined:
- `emer_rb27292`, `emer_sk14163`, `emer_sp10000`, `emer_sr14161`
These are individual emergency access (break-glass) accounts. Their presence in source-controlled security files means every deployment re-grants these accounts access — this is appropriate if the accounts are managed and time-limited externally, but it creates a persistent access vector if accounts are not deprovisioned after emergency use.

### 6.3 FortiDB and Vulnerability Scanning
`FortiDBRptRole` and `vascan` accounts confirm the database is monitored by FortiDB (database activity monitoring) and subjected to vulnerability scanning, which are positive PCI DSS Requirement 10 and 11 compliance indicators.

---

## 7. Operational Monitoring Gaps

1. **No SQL Agent job definitions** in the repository — operational scheduling of ETL procedures is entirely external.
2. **No alerting definitions** for ETL failures or data quality checks.
3. **No database mail configuration** for operational notifications.
4. **No linked server definitions** captured in the repo, yet stored procedures reference `[REPORTINGDBSERVER].*` cross-database queries — if the linked server name changes, multiple procedures fail silently.
5. **`SqlServerVerification` is set to `False`** in the project settings — this suppresses SSDT build-time SQL syntax validation, meaning broken SQL can be committed and compiled without build failure.
