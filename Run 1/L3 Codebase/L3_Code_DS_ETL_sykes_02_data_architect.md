# DS_ETL_sykes — Data Architect Perspective

## Schema and Data Model Overview

The `DS_ETL_sykes` project does not define a warehouse schema directly; it writes to staging and operational tables within the `cf_report` database, which is the shared reporting database for the eCount legacy platform. The Analysis Services database stub (`Sykes.database`) is present but has `State=Unprocessed` and no cube or dimension definitions, indicating it was scaffolded as a project container rather than an active OLAP deployment.

## Source Data Structures

### Excel Source Layout — Call Summary (`sykes_call_summary.dtsx`)

The `sykes_call_summary.dtsx` package reads Excel files named `Wirecard_North_America_Inc_TMOBILE_20200603.xlsx` (line 30, connection string) via the `Microsoft.ACE.OLEDB.12.0` provider. Two connection managers are defined:

- **Excel Connection** (`DTSID {221A870A-...}`) — the main data connection with `HDR=NO` (line 30), meaning the SSIS pipeline must handle header row skipping through `row_start`/`row_end` parameters rather than relying on Excel column names.
- **Excel Schema** (`DTSID {84711174-...}`) — an `ADO.NET:OleDb` connection used to dynamically enumerate worksheet schema, supporting the multi-sheet Sykes workbook format (line 36).

Both connections have their `ServerName` property overridden at runtime by the package variable `@[User::temp_file_path]` (lines 27, 40), demonstrating use of SSIS property expressions for late-bound file paths.

### Excel Source Layout — DPR (`sykes_DPR.dtsx`)

The DPR package reads `Wirecard_North_America_Inc_DPR_*.xlsx` with `HDR=YES` (line 29), meaning the first row is treated as column names. Sheet-specific row bounds are parameterised:

| Parameter | Default Value | Purpose |
|---|---|---|
| `phone_hrs_by_site_row_start` | 4 | First data row on phone-hours-by-site sheet |
| `phone_hrs_by_site_row_end` | 16384 | Last row (Excel 2007+ max) |
| `T1HG_row_start` | 4 | First data row on T1HG (Tier 1 Handle Group) sheet |
| `T1HG_row_end` | 255 | Last row on T1HG sheet |

This multi-parameter design accommodates the irregular layout of Sykes's DPR workbook, which embeds multiple logical tables in a single file across distinct worksheets.

### Excel Source Layout — Monthly Invoice (`sykes_monthly_invoice.dtsx`)

The invoice package reads from the `PREPAID$` worksheet (parameter `sheet_name`, line 77) using `HDR=NO;IMEX=1;MAXROWSTOSCAN=0` (line 29). The `IMEX=1` flag forces all columns to be read as text, preventing Excel's mixed-type column detection from truncating numeric invoice amounts. The `end_cell` parameter (`E255`, line 50) defines the rectangular data range.

## Connection Architecture

All packages share the `cf_report` connection manager defined in `Sykes\cf_report.conmgr`:

```
Data Source=d-na-db01.nam.wirecard.sys,2232;
Initial Catalog=cf_report;
Provider=SQLNCLI11.1;
Integrated Security=SSPI;
Auto Translate=False;
```

Key observations:
- **Server**: `d-na-db01.nam.wirecard.sys` on non-standard port `2232`. The `d-` prefix is consistent with a development/QA environment designation used elsewhere in the estate (`q-` for QA, `p-` for production). This connection manager points to a **development** server.
- **Authentication**: Windows Integrated Security (`SSPI`), no embedded credentials. This is compliant with PCI DSS Requirement 8.2 (use of unique IDs and strong authentication).
- **Provider**: `SQLNCLI11.1` — SQL Server Native Client 11.0, which corresponds to SQL Server 2012. This is an end-of-life provider and should be migrated to `MSOLEDBSQL` for SQL Server 2019+ compatibility.
- **Auto Translate=False**: Disables OEM/ANSI code-page translation at the OLEDB layer, required for correct handling of extended characters in Sykes report data.

## Data Transformation Patterns

### File Enumeration Pattern

Each package implements the following pipeline structure (inferred from parameter sets and connection managers):

```
[Foreach Loop: scan folder_path for file_pattern]
  -> Copy file to temp_folder_path
  -> Set Excel connection ServerName = temp_file_path (property expression)
  -> Data Flow Task: Excel Source -> Script/Derived Column -> OLE DB Destination (cf_report)
  -> Move file to archive_folder
```

### Parameterisation Model

The SSIS project uses the **Project Deployment Model** (`<DeploymentModel>Project</DeploymentModel>`, `Sykes.dtproj` line 3 equivalent in the project file structure), but `Project.params` is empty. This means all configuration is contained within individual package parameters rather than at the project level, limiting the ability to provide environment-specific overrides through SSIS Catalog environments.

## Data Quality and Lineage Concerns

1. **No watermark or CDC mechanism**: Unlike `DS_ETL_warehouse`, these packages do not implement change-data-capture or high-watermark logic. Full file loads are performed on each execution, relying on file-naming date stamps and the archive mechanism to prevent duplicate processing.

2. **Row range dependency**: Parameters like `row_end=35` (call summary) and `end_cell=E255` (invoice) are brittle. If Sykes changes their Excel report layout to extend beyond these bounds, data will be silently truncated.

3. **No null/type validation visible in package headers**: The package connection managers show `HDR=NO` with `IMEX=1` for numeric-sensitive sources (invoice), which is the correct defensive pattern, but downstream transformation logic is embedded in Data Flow tasks not visible in the header sections read.

4. **Filename space anomaly**: `Wirecard_North_America_Inc _Weekly_Grifols_*.xlsx` (line 64 of `sykes_weekly_grifols.dtsx`) contains an unintended space before `_Weekly`. If Sykes corrects this typo in future deliveries, the wildcard pattern will fail to match, causing a silent no-op execution rather than an error.

## Recommendations

- Migrate `cf_report.conmgr` provider from `SQLNCLI11.1` to `MSOLEDBSQL`.
- Promote key file path parameters to project-level parameters to enable SSIS Catalog environment overrides for dev/QA/prod deployment.
- Add explicit row-count validation steps post-load (compare loaded rows against an expected minimum threshold derived from historical loads).
- Implement a checksum or hash on the source file to detect duplicate submissions from Sykes.
- Standardise the Grifols file pattern and coordinate with Sykes to correct the filename space.
