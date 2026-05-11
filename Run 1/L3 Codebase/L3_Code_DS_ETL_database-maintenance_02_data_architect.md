# Data Architect View — DS_ETL_database-maintenance

## Repository Overview

**Repo path:** `E:\OnbeEast363\repos\DS_ETL_database-maintenance`
**SSIS Project format:** Project Deployment Model (`.ispac`-ready)
**Protection level:** `EncryptSensitiveWithUserKey` (dtproj line 15)

---

## Source and Target Systems

| Role | System | Connection String (from dtsx line 27) |
|---|---|---|
| Maintenance Target | `d-phl-db01.wirecard.lan` — `master` database | `Data Source=d-phl-db01.wirecard.lan;Initial Catalog=master;Integrated Security=True;Application Name=SSIS-IndexReorganize-Large_MK2-{393BFD4A...}` |
| Audit Log (implicit) | Same server — `master.dbo.CommandLog` | Written by `dbo.IndexOptimize` internally |

The `d-phl-db01.wirecard.lan` hostname uses the legacy `wirecard.lan` domain suffix, indicating this target server is the Wirecard-era on-premise SQL Server. During Onbe operations this connection string parameter is overridden at deployment time via the SSIS catalog environment variable `CM.Index Server.ServerName` (dtproj line 216).

---

## SSIS Package Inventory

### Package: `IndexReorganize-Large.dtsx`

**Object Name (internal):** `IndexReorganize-Large`
**DTSID:** `{4317A2B8-7F0E-4790-BE2A-C3E33DBB5D0D}`
**Created:** 2020-02-21, SSIS 2012 (v11.0.7001.0)
**VersionBuild:** 157

#### Connection Managers

| Name | Type | Purpose | Connection String |
|---|---|---|---|
| `Index Server` | ADO.NET (`System.Data.SqlClient`) | Target SQL Server where `dbo.IndexOptimize` resides | `d-phl-db01.wirecard.lan;master;Integrated Security=True` (dtsx line 27) |

**Authentication:** Windows Integrated Security — no SQL login credentials embedded.

#### Package Parameters

| Parameter | Data Type | Default | Description |
|---|---|---|---|
| `exec_delay` | Int32 | 60 | Seconds to wait between retry cycles |
| `exec_time_limit` | Int32 | 3600 | Max seconds per execution cycle |
| `fragmentation_limit` | Int32 | 10 | Minimum fragmentation % to qualify |
| `indexes` | String | `ALL_INDEXES` | Ola Hallengren index selector |
| `max_number_of_pages` | Int32 | 0 (infinity) | Max index size in pages |
| `min_number_of_pages` | Int32 | 6,553,600 | Min index size in pages (large-index filter) |
| `time_limit` | Int32 | 28800 | Total package runtime limit (seconds) |

#### Control Flow Tasks

| Task | Type | Purpose |
|---|---|---|
| `Get Start Time` | Expression Task | Captures `GETDATE()` into `User::start_time` |
| `Exec Loop Container` | For Loop | Iterates until done or time limit reached |
| `Execute Index Reorganize` | Script Task (C#, .NET 4.0) | Calls `dbo.IndexOptimize` stored procedure |
| `Calculate Elapsed Time` | Expression Task | Recalculates `elapsed_time` after each cycle |

#### Data Flow Tasks

**None.** This package has no Data Flow Tasks. All processing is via T-SQL stored procedure invocation.

---

## Sensitive Data Assessment

| Data Element | Present? | Classification |
|---|---|---|
| Financial amounts | No | N/A |
| Account numbers | No | N/A |
| Card numbers (PANs) | No | N/A |
| Database credentials | No (uses Windows Auth) | N/A |
| Server hostnames | Yes — `d-phl-db01.wirecard.lan` | Internal infrastructure — low sensitivity, but exposes internal DNS naming convention |

**No sensitive financial or cardholder data flows through this package.** The only data exchanged are SQL procedure parameter values (integers and strings) and execution status.

---

## Encryption in Transit

- **Connection type:** ADO.NET (`System.Data.SqlClient`) with `Integrated Security=True`
- **TLS:** The connection string does not explicitly set `Encrypt=True`. SQL Server 2012 clients negotiate encryption based on server configuration. Without explicit enforcement, connections may traverse the network without TLS encryption.
- **Risk:** If `d-phl-db01` is not configured for forced encryption, the ADO.NET SQL connection could be unencrypted. For a maintenance-only connection to `master` that passes no PII or financial data, this is a low-to-medium risk, but it conflicts with PCI DSS Requirement 4.2.1 if any network path crosses untrusted segments.
- **Recommendation:** Add `Encrypt=True;TrustServerCertificate=False;` to the connection string parameter `CM.Index Server.ConnectionString` in the SSIS catalog environment.

---

## Protection Level Analysis

The project uses `EncryptSensitiveWithUserKey` (dtproj line 15). This means:
- Sensitive properties (e.g., passwords) are encrypted with the Windows DPAPI key of the user who last saved the project
- **Risk:** If the project is opened or deployed by a different Windows user account, sensitive properties are silently stripped or fail to decrypt. This is a common cause of production deployment failures and is flagged in the `PasswordVerifier` element (dtproj line 29 — `AQAAANCMnd8BFdERjHoAwE/...` — a DPAPI-protected blob)
- **Recommendation:** Migrate to `EncryptSensitiveWithPassword` with a shared deployment password, or better, use SSIS catalog environments with `Sensitive` parameter values stored in the SSISDB catalog (which uses its own AES-256 encryption)

---

## Database Objects Referenced

| Object | Database | Type | Called From |
|---|---|---|---|
| `dbo.IndexOptimize` | `master` | Stored Procedure (Ola Hallengren) | `ScriptMain.cs` line 503 |
| `dbo.CommandLog` | `master` | Table (Ola Hallengren audit) | Implicit via `@LogToTable = 'Y'` |

---

## Architecture Notes

- This is a **single-package, single-connection** SSIS project — the simplest possible SSIS architecture
- The Ola Hallengren dependency (`dbo.IndexOptimize`) must be pre-installed on `master` of every target server; this is not managed by this repository
- The `min_number_of_pages = 6,553,600` default (approximately 51 GB of index data at 8KB per page) means this specific package variant only reorganises extremely large indexes. A companion rebuild variant presumably exists elsewhere (potentially `IndexRebuild-Small.dtsx` or similar, not present in this repo)
- Project Deployment Model (SSIS 2012+) is used, which supports proper parameterisation via the SSIS catalog — a positive finding compared to older legacy configuration-file-based packages seen in other repos
