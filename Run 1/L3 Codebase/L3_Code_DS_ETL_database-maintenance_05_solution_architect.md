# Solution Architect View — DS_ETL_database-maintenance

## Repository Overview

**Repo path:** `E:\OnbeEast363\repos\DS_ETL_database-maintenance`
**Package count:** 1 (`IndexReorganize-Large.dtsx`)
**Connection managers:** 1 (`Index Server` — ADO.NET, Windows Integrated Security)

---

## Complete Object / Package Inventory

### SSIS Packages

| Package | DTSID | Internal Name | Purpose |
|---|---|---|---|
| `IndexReorganize-Large.dtsx` | `{4317A2B8-7F0E-4790-BE2A-C3E33DBB5D0D}` | `IndexReorganize-Large` | Reorganises fragmented indexes on large tables across all user databases; wraps Ola Hallengren `IndexOptimize` |

### Connection Managers

| Name | DTSID | Type | Server | Database | Auth |
|---|---|---|---|---|---|
| `Index Server` | `{393BFD4A-87A6-4ACC-87AB-C21B73A79233}` | ADO.NET SqlClient | `d-phl-db01.wirecard.lan` | `master` | Windows Integrated |

### Variables

| Variable | Type | Purpose |
|---|---|---|
| `User::elapsed_time` | Int32 | Tracks seconds elapsed since package start |
| `User::exec_delay` | Int32 | Mirror of `$Package::exec_delay` parameter |
| `User::exec_done` | Boolean | Set to `true` when `IndexOptimize` completes without timeout |
| `User::exec_SQL_wait` | String | Dynamic `WAITFOR DELAY '00:01:00'` T-SQL expression |
| `User::exec_time_limit` | Int32 | Mirror of `$Package::exec_time_limit` |
| `User::fragmentation_limit` | Int32 | Mirror of `$Package::fragmentation_limit` |
| `User::indexes` | String | Mirror of `$Package::indexes` |
| `User::max_number_of_pages` | Int32 | Mirror of `$Package::max_number_of_pages` (null if 0) |
| `User::min_number_of_pages` | Int32 | Mirror of `$Package::min_number_of_pages` |
| `User::start_time` | DateTime | Package start timestamp |
| `User::time_limit` | Int32 | Mirror of `$Package::time_limit` |

---

## Security Vulnerabilities

### 1. Hardcoded Server Hostname in Default Connection String

**File:** `IndexReorganize-Large.dtsx`, line 27
**File:** `database-maintenance.dtproj`, line 157

```
Data Source=d-phl-db01.wirecard.lan;Initial Catalog=master;Integrated Security=True;...
```

**Severity:** Medium
**Finding:** The development/default target server `d-phl-db01.wirecard.lan` is embedded in the connection string. The domain suffix `.wirecard.lan` reveals the internal DNS naming convention for Onbe's legacy on-premise infrastructure. While the server name is overridable via the SSIS catalog, the default is baked into the `.dtsx` and `.dtproj` XML and committed to git.

**Remediation:** Ensure the SSIS catalog environment variable `CM.Index Server.ServerName` is always set before execution. Consider replacing the default with a placeholder value (e.g., `<SET_AT_DEPLOY_TIME>`) to prevent accidental execution against the wrong server.

### 2. `EncryptSensitiveWithUserKey` Protection Level

**File:** `database-maintenance.dtproj`, line 15
**File:** `IndexReorganize-Large.dtsx` (implicitly, via project-level protection)

**Severity:** Low-Medium
**Finding:** The project protection level `EncryptSensitiveWithUserKey` ties encrypted values to the Windows DPAPI key of the developer's account. The `PasswordVerifier` blob at dtproj line 29 (`AQAAANCMnd8BFdERjHoAwE/...`) is a DPAPI-protected verification value. Any sensitive parameters that exist (currently the `CM.Index Server.Password` parameter — dtproj line 176, marked `Sensitive=1`) will be blanked out when the project is opened by a different user.

**Remediation:** Switch to `EncryptAllWithPassword` for transport or `DontSaveSensitive` with SSIS catalog–managed sensitive parameters.

### 3. No Encryption Enforced on SQL Connection

**File:** `IndexReorganize-Large.dtsx`, line 27

The connection string uses `Integrated Security=True` but does not set `Encrypt=True`. SQL Server 2012 clients negotiate encryption only if the server forces it.

**Severity:** Low (no sensitive data transmitted; maintenance commands only)
**Remediation:** Add `Encrypt=True;TrustServerCertificate=False;` as a best practice baseline, even for maintenance connections.

### 4. Script Task Includes Binary DLL Blob

**File:** `IndexReorganize-Large.dtsx`, lines 791–953

The C# Script Task compiles the C# code and embeds the resulting `.dll` as a base64-encoded binary (`<BinaryItem Name="ST_1b86cfc714f2401bb9b61c017fdbcbda.dll">...`). This is standard SSIS behaviour, but it means:
- The compiled binary is committed to git alongside source
- There is no separate compilation step; the binary may be out of sync with source changes
- Security scanners may flag the embedded binary as suspicious

**Severity:** Low
**Remediation:** Accepted SSIS pattern — no change required unless static analysis tools flag it.

---

## Technical Debt

| Item | Severity | Notes |
|---|---|---|
| Visual Studio 2010 solution format | Medium | Cannot be opened without backward-compatibility mode in VS 2019/2022 SSDT; upgrade needed |
| SSIS 2012 package format version 6 | Low | Still deployable to SSIS 2019 catalog but lacks modern features |
| No automated deployment pipeline | High | All deployments are manual; no repeatability guarantee |
| No alerting within the package | Medium | Silent failures possible |
| Single-server scope | Medium | No fan-out to other SQL Server instances; separate instances need separate jobs |
| .NET 4.0 target framework | Low | Functional but end-of-mainstream-support |

---

## Remediation Priority

| Priority | Action |
|---|---|
| 1 (High) | Implement automated deployment: add a PowerShell script to deploy the `.ispac` and configure SSIS catalog environments for dev/QA/prod |
| 2 (High) | Add a Send Mail Task on the failure path to alert the DBA/operations team |
| 3 (Medium) | Upgrade the solution to Visual Studio 2019/2022 SSDT format |
| 4 (Medium) | Replace `EncryptSensitiveWithUserKey` with SSIS catalog–managed parameter sensitivity |
| 5 (Low) | Add `Encrypt=True` to the connection string template |
| 6 (Low) | Evaluate replacing the SSIS wrapper with a pure T-SQL SQL Agent job step |

---

## No Plaintext Credential Findings

The connection string uses `Integrated Security=True`, meaning **no username or password is embedded in the connection string.** The `CM.Index Server.Password` parameter (dtproj line 176) is present in the project manifest but has no assigned value (`Sensitive=1` with no `Value` element), confirming that SQL authentication is not used. This is the correct pattern.

The `PasswordVerifier` blob at dtproj line 29 is a project-level DPAPI-protected checksum, not an actual password, and cannot be used to authenticate to any system.
