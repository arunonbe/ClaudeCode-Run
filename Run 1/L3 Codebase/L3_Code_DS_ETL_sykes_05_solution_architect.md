# DS_ETL_sykes — Solution Architect Perspective

## Solution Design Summary

`DS_ETL_sykes` is an SSIS-based batch ETL solution implementing a file-ingestion pipeline for Sykes vendor reporting data. The solution design centres on eight independent SSIS packages sharing a single connection manager (`cf_report.conmgr`) and a common filesystem convention. Each package encapsulates one logical data feed from Sykes, enabling independent scheduling and failure isolation at the package level.

## Component Design Analysis

### Connection Manager: `cf_report.conmgr`

```xml
DTS:ConnectionString="Data Source=d-na-db01.nam.wirecard.sys,2232;
  Initial Catalog=cf_report;Provider=SQLNCLI11.1;
  Integrated Security=SSPI;Auto Translate=False;"
```

**Design decision**: Sharing one `.conmgr` file across all packages rather than embedding connection definitions in each package is correct — it enables single-point connection reconfiguration. However, the file is stored at the project level and is not promoted to a project connection, which would allow SSIS Catalog environments to override the connection string per environment (dev/QA/prod) without modifying the artefact.

**Flag**: The server `d-na-db01.nam.wirecard.sys` with port `2232` is a non-standard SQL port. Port `2232` is not the SQL Server default (1433). This suggests a named instance or a port-based firewall rule. The connection must be confirmed against the current network topology — particularly important if this project has been migrated from Wirecard NA infrastructure to Onbe/NorthLane infrastructure.

### Package Parameter Architecture

The packages use a consistent parameter set:

| Parameter | Type | Purpose |
|---|---|---|
| `folder_path` | String, Required | Root directory for incoming Sykes files |
| `archive_folder` | String, Required | Destination for processed files |
| `temp_folder_path` | String, Required | Staging area for file operations |
| `file_pattern` | String | Wildcard pattern for file matching |
| `row_start` / `row_end` | Int32 | Excel row bounds for data extraction |

The `Required=True` flag on `folder_path` and `archive_folder` ensures the package fails at validation time if these are not supplied, which is correct defensive design. The `file_pattern` parameter does not have `Required=True` in all packages — if omitted, the default value (which may be a historical specific filename rather than a wildcard) would be used, potentially processing no files or a stale file.

### Property Expression Pattern

All packages use SSIS property expressions to bind the Excel connection's `ServerName` to the runtime variable `@[User::temp_file_path]`:

```xml
<DTS:PropertyExpression DTS:Name="ServerName">@[User::temp_file_path]</DTS:PropertyExpression>
```

This is the standard SSIS pattern for dynamic file path binding. The static `DTS:ConnectionString` embedded in the package XML serves as a design-time reference only and is overridden at runtime. This design is correct and supports the file-enumeration loop pattern.

### Dual Connection Manager for Excel (`sykes_call_summary.dtsx`)

Two Excel connections are defined:
1. `Excel Connection` — main data reader with `HDR=NO`
2. `Excel Schema` — `ADO.NET:OleDb` connection for dynamic schema enumeration

The `Excel Schema` connection allows the package to dynamically discover worksheet names at runtime, supporting Sykes workbooks that may have variable sheet names across delivery cycles. This is a more robust design than hardcoding sheet names, but requires the `Excel Schema` connection to also be kept in sync with the same file path as the data connection.

## Security Design Assessment

### SSIS Protection Level (Critical Finding)

**File**: `Sykes.dtproj`, line 15:
```xml
SSIS:ProtectionLevel="EncryptSensitiveWithUserKey"
```

**File**: `Sykes.dtproj`, line 29:
```xml
<SSIS:Property SSIS:Name="PasswordVerifier" SSIS:Sensitive="1">
  AQAAANCMnd8BFdERjHoAwE/Cl+sBAAAAU++NJy5gMEKBKurGNsD0dA...
</SSIS:Property>
```

**File**: `Sykes.dtproj`, line 77:
```xml
<SSIS:Parameter SSIS:Name="CM.cf_report.Password">
```

The presence of a `CM.cf_report.Password` sensitive parameter alongside `EncryptSensitiveWithUserKey` is concerning. Windows Integrated Security (SSPI) in the connection string should not require a password parameter — these are mutually exclusive authentication mechanisms. The presence of a `CM.*.Password` sensitive parameter suggests either:

1. The project was designed to support SQL Server authentication as an alternative (e.g., for environments where Windows auth is not available), with the password being supplied through the Catalog, OR
2. A legacy password was embedded during development and not cleaned up.

Since the connection manager uses `Integrated Security=SSPI`, the password parameter value should be blank. However, the encrypted `PasswordVerifier` blob indicates a value was present at some point when the project was saved. **This should be investigated by the security team.**

### No Plaintext Credentials in Connection Strings

Positive finding: All connection strings in `.conmgr` and `.dtsx` files use `Integrated Security=SSPI`. No plaintext SQL Server usernames or passwords are visible in any connection string. This is compliant with PCI DSS Requirement 8.2.1.

## Operational Design Patterns

### Archive-After-Process Pattern
The move-to-archive pattern (`archive_folder`) prevents re-processing of already-ingested files on subsequent runs. This is a correct idempotency mechanism for file-based ETL. However, there is no evidence of a file-processed audit table in `cf_report` that would allow reconstruction of which files were processed on which dates — this is an auditability gap.

### Multi-Sheet Excel Handling
The DPR package (`sykes_DPR.dtsx`) handles multiple named sheets per workbook (T1HG, phone_hrs_by_site) with independent row-range parameters for each. This design explicitly accommodates Sykes's practice of embedding multiple logical data sets in a single workbook. The sheet names are implicitly defined through parameters, which is more maintainable than hardcoded strings.

## Gaps and Remediation Plan

| Gap | Impact | Recommended Solution |
|---|---|---|
| `EncryptSensitiveWithUserKey` | Cannot deploy from CI/new user | Change to `DontSaveSensitive`; use SSIS Catalog environments |
| Developer path default (`colin.treat`) | Breaks on new host | Replace with `\\server\share\...` UNC path parameter |
| Empty `Project.params` | No central config override | Promote `folder_path`, `archive_folder` to project parameters |
| SQLNCLI11.1 EOL provider | Security vulnerability | Migrate to `MSOLEDBSQL` or `System.Data.SqlClient` |
| No post-load row count validation | Silent data loss undetected | Add Execute SQL Task to assert rowcount > expected_minimum |
| No inbound file integrity check | Truncated/corrupt Sykes files processed silently | Add file size/checksum validation before Data Flow execution |
| `wirecard.sys` domain in FQDN | Residual legacy infrastructure reference | Validate current DNS; update connection string when migrated |
