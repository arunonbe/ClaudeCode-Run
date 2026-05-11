# Data Architect Report — DS_CCP_wired-caching

## Repository Nature

DS_CCP_wired-caching is an **SSIS ETL project** with no database DDL. It does not define database tables, stored procedures, views, or indexes. All schema objects it writes to are defined in DS_CCP_wired. This repo's data architecture relevance is as the **data pipeline** that populates the WIRED cache tables.

## Database Objects — None Defined

This repository contains:
- 9 SSIS packages (`.dtsx` files)
- 1 SSIS package part (`.dtsxp` — reusable control flow)
- 2 connection managers (`.conmgr`)
- 1 project parameters file (`Project.params`)
- 1 project file (`wired-caching.dtproj`)
- 1 database reference file (`wired-caching.database`)

## Connection Managers — Sensitive Data Analysis

### `wired_db.conmgr`
```xml
ConnectionString="Data Source=d-phl-db01;Initial Catalog=WIRED;
Provider=SQLNCLI11.1;Integrated Security=SSPI;Auto Translate=False;"
```
- Target: Wirecard development SQL Server `d-phl-db01`
- Authentication: Windows Integrated Security (SSPI) — service account-based
- **No credentials in connection string** — uses Windows auth, appropriate

### `ccp_dwh.conmgr`
```xml
ConnectionString="Data Source=DWH_AWS_SSH;User ID=RM_BI_USER;
Persist Security Info=True;Unicode=True;"
```
- Target: Oracle CCP DWH via named DSN `DWH_AWS_SSH` (SSH tunnel ODBC/OleDB DSN)
- Authentication: Oracle username/password — `User ID=RM_BI_USER` committed in plaintext
- Password: `<DTS:Password Sensitive="1"></DTS:Password>` — empty in file, must be provided via SSISDB
- **Finding**: Oracle username `RM_BI_USER` is committed to version control. If `RM_BI_USER` is a shared Oracle service account, this reduces accountability for DWH access. The DSN name `DWH_AWS_SSH` indicates the DWH is hosted on AWS, accessed via SSH tunnel.

### `SMTP Connection Manager.conmgr`
- Used for notification emails from SSIS packages (file receipt alerts)

## SSIS Package Inventory

| Package | Approximate Size | Purpose |
|---|---|---|
| `cache_agg_spend.dtsx` | Large | Populates `WIRED.cache_AggSpend_STG` from Oracle DWH; calls `usp_Wired_Cache_AggSpend_INS` |
| `cache_card_ship_date.dtsx` | Large | Populates `WIRED.cache_CardShipDate_STG` from Oracle DWH |
| `cache_pbr.dtsx` | Large | Populates `WIRED.cache_pbr_STG` from Oracle DWH; calls `usp_Wired_Cache_PBR_INS` |
| `cache_rapid_undeliverable_cards.dtsx` | Large | Populates `WIRED.cache_RapidUndeliverableCards_STG` from Oracle DWH |
| `cache_refresh.dtsx` | Large | Master orchestration — executes all individual cache packages in sequence; also refreshes `cache_corp_client_brands` |
| `Files_sftp.dtsx` | Large | SFTP file management/enumeration for GP data files |
| `import_cache_pbr_GP.dtsx` | Large | Reads GP file from SFTP and loads `WIRED.cache_pbr_GP` |
| `Receive_SFTP.dtsx` | 7,758 bytes (small) | Thin wrapper calling DS_CCP_sftp Receive.dtsx pattern for GP SFTP retrieval |

Note: `.dtsx` file sizes range from 7.7KB (`Receive_SFTP.dtsx`) to multiple hundred KB for the more complex packages. Exact component inventory inside each package requires parsing the XML binary — only metadata is confirmed here.

## Package Part

| File | Purpose |
|---|---|
| `PackagePart1.dtsxp` | 692 bytes — likely a shared error handling or logging control flow fragment reused across packages |

## Data Flow — Cache Population Pattern

All Oracle-sourced cache packages follow this pattern:

```
Oracle DWH (ccp_dwh.conmgr → DWH_AWS_SSH, RM_BI_USER)
    ↓
OLE DB / ADO.NET Source (SQL query against Oracle)
    ↓
SSIS Data Flow Transformations (type mapping, derived columns)
    ↓
OLE DB Destination → WIRED.dbo.cache_*_STG (staging table, truncated first)
    ↓
Execute SQL Task → WIRED.dbo.usp_Wired_Cache_*_INS (stage-and-swap to production)
```

The stage-and-swap via stored procedure provides near-atomic cache replacement — the production cache table is swapped from staging in a single procedure, minimising the window where report queries could read a partially-refreshed cache.

## Sensitive Data in Data Flows

The cache tables populated by these packages contain **programme-level financial aggregates**:
- Brand names (`brand_name`)
- Programme/promotion IDs (`promotion_id`, `virtual_corporate_account`)
- Financial amounts (`Processed Invoices`, `Payments`, `Credits`, `Debits`, `Posted Balance`, `Available Balance`)
- Card ship dates
- Corporate client names

**No PAN, CVV, SSN, DOB, or individual card numbers** are visible in the cache table definitions (DS_CCP_wired `02_data_architect.md` confirmed). The data flowing through this project is programme-aggregate level.

However, the source Oracle DWH (`DWH_AWS_SSH`) is a CDE-scope system and may contain PAN data at lower levels. The `RM_BI_USER` Oracle account's access scope should be validated to confirm it can only access the reporting views/tables that produce programme-level aggregates, not individual card records.

## Encryption

- **In-transit (Oracle DWH to SSIS)**: ADO.NET OracleClient connects via SSH tunnel (DSN `DWH_AWS_SSH`). The SSH tunnel encrypts the Oracle connection over the network.
- **In-transit (SFTP for GP files)**: Covered by DS_CCP_sftp analysis.
- **At-rest (WIRED database)**: No column encryption on cache tables. Cache data is programme-level financial data — encryption at rest is desirable but not a PCI DSS hard requirement (no PAN data).
- **SSIS sensitive parameters**: `GP_SFTP_Password` and `GP_SFTP_SSHPassphrase` use `SSIS:Sensitive="1"` — values are encrypted by SSISDB catalog master key.

## PCI DSS CDE Scope Assessment

**DS_CCP_wired-caching is borderline CDE scope:**
- The data it produces (WIRED cache tables) is **not CDE** — no PAN data
- The Oracle DWH it connects to (`DWH_AWS_SSH`) **is CDE** — the DWH contains cardholder data
- The `RM_BI_USER` account accessing the DWH is therefore a **CDE-scope account**
- The SSIS runtime environment (p-db09 server) is **in CDE scope** because it accesses the Oracle DWH

**Action required**: Verify that `RM_BI_USER` Oracle account has access restricted to reporting views/aggregates only, with no access to PAN-bearing tables. Document this as a compensating control for CDE scope limitation.
