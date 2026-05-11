# Solution Architect Report — DS_CCP_wired-caching

## Technical Debt Inventory

| Item | Severity | Location |
|---|---|---|
| Oracle DWH source likely decommissioned — pipeline broken | CRITICAL | All Oracle-sourced cache packages |
| Oracle username `RM_BI_USER` committed to source control | HIGH | `ccp_dwh.conmgr` |
| `System.Data.OracleClient` deprecated ADO.NET component | HIGH | `ccp_dwh.conmgr` — `System.Data.OracleClient.OracleConnection` |
| Default GP SFTP hostname points to QA environment | HIGH | `Project.params` — `GP_SFTP_HostName` default |
| Development SQL Server hardcoded in connection manager | HIGH | `wired_db.conmgr` — `d-phl-db01` |
| No cache freshness / row-count validation post-load | HIGH | All cache packages |
| No CI/CD pipeline | MEDIUM | Entire repo |
| SSH tunnel (`DWH_AWS_SSH`) not documented or version-controlled | MEDIUM | Infrastructure dependency |
| No Oracle DWH health check before package execution | MEDIUM | `cache_refresh.dtsx`, all Oracle packages |
| Package part (`PackagePart1.dtsxp`) undocumented | LOW | Root directory |
| SSISDB ENVREFERENCE integers hardcoded in SQL Agent jobs (in DS_CCP_db09) | MEDIUM | Cross-repo: DB09 job scripts |
| `Persist Security Info=True` in Oracle connection string | MEDIUM | `ccp_dwh.conmgr` |

## Security Vulnerabilities Found

### 1. Oracle Username Committed to Source Control (HIGH — Secret Management)
File `ccp_dwh.conmgr`:
```
Data Source=DWH_AWS_SSH;User ID=RM_BI_USER;Persist Security Info=True;
```
The Oracle service account username `RM_BI_USER` is committed as plaintext. While the password uses SSIS sensitive encryption (empty at rest in file), knowing the username and the DSN name `DWH_AWS_SSH` gives an attacker:
- The Oracle connection target hostname (implied by the SSH tunnel DSN)
- The service account username to target for brute-force or credential stuffing
- The schema name (likely `RM_BI_USER` owns the BI/reporting views)

**Remediation**: Store Oracle connection credentials entirely in SSISDB sensitive environment variables. Replace the static `.conmgr` file with a project-level connection manager configured only via SSISDB environment, with no username committed.

### 2. `Persist Security Info=True` in Oracle Connection (MEDIUM — PCI DSS Req 8)
`ccp_dwh.conmgr`: `Persist Security Info=True` instructs ADO.NET to keep the password in the connection object after authentication. This means the password may be persisted in memory longer than necessary and could appear in memory dumps or diagnostic traces.

**Remediation**: Set `Persist Security Info=False` (default for ADO.NET Oracle client, but explicit is better).

### 3. Deprecated Oracle ADO.NET Client (`System.Data.OracleClient`) (HIGH — Supply Chain Risk)
`ccp_dwh.conmgr`: `System.Data.OracleClient.OracleConnection, System.Data.OracleClient, Version=4.0.0.0`

`System.Data.OracleClient` was deprecated by Microsoft in .NET Framework 4.0 (circa 2010) and is not present in .NET Core or .NET 5+. It has not received security patches for many years. Use on modern Windows Server versions may have unknown behaviour, and any security vulnerabilities in this library are unfixed.

**Remediation**: Migrate to Oracle's ODP.NET Managed Driver (`Oracle.ManagedDataAccess`) or migrate the Oracle connection entirely to an ODBC DSN using Oracle Instant Client.

### 4. Default QA SFTP Hostname (HIGH — Data Misrouting Risk)
Documented in DS_CCP_sftp analysis — applies equally here. `Project.params` `GP_SFTP_HostName` defaults to `sftp-qa.nam.wirecard.com`. If production SSISDB environment override is ever dropped, GP files will be requested from/delivered to the QA SFTP.

**Remediation**: Change default to empty string or `REQUIRES-PRODUCTION-CONFIG`.

### 5. No Post-Load Cache Validation (HIGH — Data Quality Risk)
None of the cache packages validate that the loaded data meets minimum quality thresholds (minimum row count, maximum date check, non-null key fields). A silent Oracle DWH failure (connection succeeds but query returns 0 rows) will result in the stage-and-swap loading an empty production cache. WIRED reports would then contain no data, and the only indication of failure would be absent data in client reports — not an alert.

**Remediation**: Add an Execute SQL Task after each cache load that checks `SELECT COUNT(*) FROM cache_*_STG` and `MAX(DateLoaded)`. Fail the package if count is below threshold or date is stale. Trigger notification email.

## Package Inventory

| Package | Purpose |
|---|---|
| `cache_agg_spend.dtsx` | Loads `WIRED.cache_AggSpend` from Oracle DWH via stage-and-swap |
| `cache_card_ship_date.dtsx` | Loads `WIRED.cache_CardShipDate` from Oracle DWH via stage-and-swap |
| `cache_pbr.dtsx` | Loads `WIRED.cache_pbr` from Oracle DWH via stage-and-swap |
| `cache_rapid_undeliverable_cards.dtsx` | Loads `WIRED.cache_RapidUndeliverableCards` from Oracle DWH via stage-and-swap |
| `cache_refresh.dtsx` | Master orchestrator — executes all individual cache packages; also refreshes `cache_corp_client_brands` |
| `Files_sftp.dtsx` | GP SFTP file enumeration and management |
| `import_cache_pbr_GP.dtsx` | Retrieves GP file via SFTP and loads `WIRED.cache_pbr_GP` |
| `Receive_SFTP.dtsx` | Thin SFTP receive wrapper (reuses DS_CCP_sftp pattern) |
| `PackagePart1.dtsxp` | Shared package part — likely error handling/logging fragment |

## Code Quality Issues

1. **No package version numbering**: SSIS packages have version numbers (`VersionMajor/Minor/Build`) but all are likely at default `0.0.0` — confirmed for DS_CCP_sftp project; this project follows the same pattern.
2. **No package annotations**: SSIS packages in this era (VS2017) can include annotations on the design surface. Without reading full XML content, documentation quality within packages is unknown.
3. **Cache package naming inconsistency**: `cache_card_ship_date.dtsx` vs `cache_agg_spend.dtsx` (underscore in `card_ship_date`) — minor but not uniform.
4. **`wired-caching` project name contains a hyphen**: Non-standard SSIS project naming (hyphens not valid in some namespace contexts).

## Recommended Remediation Priority

| Priority | Action |
|---|---|
| P1 — Immediate | Confirm Oracle DWH (`DWH_AWS_SSH`) status — active or decommissioned. If decommissioned, identify replacement data source for all 4 Oracle cache packages. |
| P1 — Immediate | Replace `System.Data.OracleClient` with Oracle ODP.NET Managed Driver |
| P1 — Immediate | Remove Oracle `RM_BI_USER` username from `ccp_dwh.conmgr` — move entirely to SSISDB environment |
| P1 — Immediate | Change `GP_SFTP_HostName` default from QA hostname to empty/sentinel |
| P1 — Immediate | Change `wired_db.conmgr` dev server to empty/sentinel or remove static connection string |
| P2 — Short-term | Add post-load row-count and freshness validation to all cache packages |
| P2 — Short-term | Set `Persist Security Info=False` in Oracle connection string |
| P2 — Short-term | Implement CI/CD pipeline for `.ispac` build and deployment |
| P3 — Medium-term | Evaluate migration of all Oracle cache queries to Onbe's current data platform (Azure Synapse, SQL Server, or API) |
| P3 — Medium-term | Evaluate migration of GP SFTP integration to direct GP API or Azure Data Factory copy activity |
