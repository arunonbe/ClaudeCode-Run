# Enterprise Architect Report — DS_CCP_wired-caching

## Platform Generation Classification

**Generation: Gen-2 (Wirecard/Northlane — WIRED ETL caching layer)**

Evidence:
- SSDT Product Version 14.0 = Visual Studio 2017-era toolchain
- SSISDB project folder `wdnam-ccp-etl` — Wirecard NAM namespace
- Oracle DWH connection DSN `DWH_AWS_SSH` — Wirecard/legacy Oracle CCP DWH on AWS
- Oracle username `RM_BI_USER` — legacy Oracle service account name from the Wirecard CCP platform
- GP SFTP default hostname `sftp-qa.nam.wirecard.com` — Wirecard QA SFTP
- `wired_db.conmgr` connection to `d-phl-db01` — Wirecard development SQL Server on `.wirecard.lan`
- Creation/modification in the 2019–2020 timeframe (per DS_CCP_db09 SSISDB job configuration dates)

This project sits at the **Gen-1/Gen-2 boundary**: it bridges the Gen-1 Oracle CCP DWH (legacy card processing platform) into the Gen-2 WIRED reporting product. The CCP Oracle DWH shut down in July 2020 makes this project's primary data feeds **stale or inactive** as of that date.

## Role in the Overall Payments Architecture

DS_CCP_wired-caching is the **data supply chain** for WIRED report delivery:

```
┌──────────────────────────────────────────────────────────────────────────┐
│              WIRED CACHE DATA SUPPLY CHAIN                               │
│                                                                          │
│  Gen-1 Oracle CCP DWH                                                   │
│  (DWH_AWS_SSH / AWS)    ──► cache_pbr.dtsx               ──► cache_pbr  │
│                          ──► cache_agg_spend.dtsx        ──► cache_AggSpend │
│                          ──► cache_card_ship_date.dtsx   ──► cache_CardShipDate │
│                          ──► cache_rapid_undeliverable.. ──► cache_RapidUndeliverable │
│                                                                          │
│  GP (Great Plains)                                                       │
│  via SFTP ─────────────► import_cache_pbr_GP.dtsx        ──► cache_pbr_GP │
│                                                                          │
│                       ↑ All coordinated by cache_refresh.dtsx            │
│                         (master orchestrator)                             │
│                                                                          │
│           [WIRED DB cache_* tables]                                      │
│                       ↓                                                  │
│  DS_CCP_wired-output ──► Report generation → Client delivery             │
└──────────────────────────────────────────────────────────────────────────┘
```

Without DS_CCP_wired-caching running successfully, the WIRED report delivery pipeline produces stale or empty reports. This project is a **critical dependency** of DS_CCP_wired-output.

## Dependencies on Other Repos/Services

| Dependency | Direction | Notes |
|---|---|---|
| DS_CCP_wired (WIRED DB) | Writes to | All cache tables written here |
| DS_CCP_sftp | Component | SFTP pattern reused in `Receive_SFTP.dtsx` |
| DS_CCP_wired-output | Consumed by | wired-output depends on freshly populated cache tables |
| Oracle CCP DWH (`DWH_AWS_SSH`) | Source | Oracle DB on AWS via SSH tunnel — **potentially decommissioned** |
| GP (Great Plains) SFTP | Source | GP financial data via `sftp-qa.nam.wirecard.com` [QA default] |
| SSISDB on p-db09 | Deployment | `wdnam-ccp-etl\wired-caching` SSISDB folder |
| SQL Agent on p-db09 | Orchestration | `wired_cache_refresh` and `wired_cache_GP` jobs |

## Critical Architecture Finding: Oracle DWH Dependency Post-CCP Shutdown

The most significant architectural concern for this project is its **primary data source decommissioning**:

- The CCP Oracle DWH (`DWH_AWS_SSH`, Oracle `RM_BI_USER`) was the source system for all cache tables except `cache_pbr_GP`.
- DS_CCP_db09 analysis confirms that CCP Oracle processing was halted in August 2020 (mass job-disable).
- The Oracle DWH SSH tunnel (`DWH_AWS_SSH` DSN) may no longer be active.

**Likely current state**: The 4 Oracle-sourced cache tables (`cache_pbr`, `cache_AggSpend`, `cache_CardShipDate`, `cache_RapidUndeliverableCards`) may contain stale data from the last successful run before CCP shutdown, or they may be empty. The `wired_cache_refresh` SQL Agent job was disabled in August 2020 (per `20200804_NAMDATASVC-2398_DB09 Disable jobs.sql`).

If WIRED reports are still being delivered to clients post-2020, the data must be coming from an alternative source not visible in these repositories. This represents a **significant architectural gap** to investigate.

## Architectural Assessment

### Strengths
1. **Orchestration via master package**: `cache_refresh.dtsx` provides a single entry point that coordinates all cache refreshes — simplifying SQL Agent job configuration.
2. **Stage-and-swap pattern**: Prevents partial cache states during report generation.
3. **Parameterised connections**: All environment-specific values are in SSISDB, not hardcoded.
4. **Separate GP cache pipeline**: GP financial data (monthly close timing) is correctly separated from the daily Oracle DWH cache, reflecting different refresh frequencies.

### Weaknesses
1. **Single Oracle DWH dependency**: All 4 primary cache packages depend on a single Oracle DWH. No fallback or alternative data source.
2. **No cache validation post-load**: After each package completes, no check verifies that the cache contains expected volumes or dates.
3. **No data lineage tracking**: No metadata in cache tables identifying when data was loaded or from which source query version.
4. **Oracle ADO.NET client**: `System.Data.OracleClient` (used in `ccp_dwh.conmgr`) is a deprecated .NET component — Microsoft deprecated it in .NET Framework 4.0 in favour of Oracle's ODP.NET. This creates a compatibility risk on newer .NET versions.

## Migration Complexity and Blockers

### Complexity: HIGH (due to Oracle DWH decommission)

1. **Oracle replacement**: The Oracle DWH source queries must be replaced with an alternative data source (Onbe's modern data platform, Azure Synapse, a replacement ERP API, or the ecountcore/Gen-1 database equivalents). This requires full analysis of what data the Oracle DWH `RM_BI_USER` queries return.

2. **`System.Data.OracleClient` migration**: Replacing the deprecated Oracle ADO.NET client with Oracle ODP.NET or migrating to an ODBC/OLEDB approach.

3. **SSH tunnel migration**: `DWH_AWS_SSH` is an ODBC/DSN defined on the ETL server that routes through an SSH tunnel to an AWS-hosted Oracle instance. This infrastructure must be documented and replaced as part of any cloud migration.

4. **GP SFTP migration**: The Great Plains SFTP-to-cache pipeline may need to be replaced as GP moves to a different integration model (direct DB connection, API, or different file delivery mechanism).

### Blockers
- Oracle DWH status confirmation (active/decommissioned) — **blocking**
- Alternative data source for all 4 Oracle-sourced caches must be identified before any migration
- SSH tunnel and AWS Oracle instance must be decommissioned with proper data migration
- GP integration method must be confirmed for post-migration approach
