# Enterprise Architect Report — DS_CCP_db09

## Platform Generation Classification

**Generation: Gen-2 (Wirecard/Northlane legacy ETL layer)**

The repo is deeply embedded in the Wirecard North America (WDNAM) infrastructure:
- SSISDB folder path: `\SSISDB\wdnam-ccp-etl\` — explicitly branded Wirecard NAM
- Server naming: `p-db09.nam.wirecard.sys\db09`
- Job descriptions reference `https://confluence.wirecard.sys` (Wirecard internal Confluence)
- Creator identities in DTSX metadata: `WIRECARD\van.nguyen2`, `WIRECARD\patricia.zysk`
- Email domain migration script (`20201113_SQ-1114`) captures the transition from `wirecard.com` to `northlane.com`, placing the **transition epoch at Q4 2020**

The underlying CCP platform itself (Oracle DWH, the SSISDB projects it references) is a Gen-2 acquired system. The WIRED reporting product layered on top represents the first attempts at a client-facing reporting service built by the DS (Data Services) team under the Wirecard/Northlane organisation.

## Role in the Overall Payments Architecture

p-db09 is the **ETL orchestration hub** for the CCP data domain:

```
┌─────────────────────────────────────────────────────────────┐
│                    CCP DATA DOMAIN                          │
│                                                             │
│  Oracle CCP DWH ──── SSIS (SSISDB on p-db09) ───► ODS DB  │
│  (AWS SSH tunnel)      ccp_import_aggnetwork...             │
│                                                             │
│  FIS Flat Files ────── SSIS ───────────────────► ODS DB    │
│  (local ETL landing)   sp_FISRpt_Import*                   │
│                                                             │
│  Mastercard Files ───── SSIS ──────────────────► ODS DB    │
│  (NAM_*_TT140*.*.*)     mc_import_summary                  │
│                                                             │
│  ODS DB ─────────────── SSIS ──────────────────► WIRED DB  │
│                         wired_cache_refresh                 │
│                                                             │
│  Great Plains DB ─────── SSIS ─────────────────► WIRED DB  │
│                          wired_cache_GP                     │
│                                                             │
│  WIRED DB ──────────── SSIS ──────────────────► Reports    │
│                         wired_report_output    (WEP/Email/  │
│                                                 SFTP)       │
└─────────────────────────────────────────────────────────────┘
```

The p-db09 instance thus occupies the **centre of the CCP ETL topology**, orchestrating data movement from:
- External processor data feeds (FIS, Mastercard) into the ODS analytical store
- Oracle DWH (legacy CCP source of truth) into ODS
- ODS and GP financials into WIRED (the client-facing report delivery platform)
- WIRED into client report delivery channels (WEP portal, SFTP, email)

## Dependencies on Other Repos and Systems

| Dependency | Type | Direction |
|---|---|---|
| DS_CCP_ods | Schema definition | DB objects targeted by data-patch scripts |
| DS_CCP_wired | Schema definition | `WIRED.dbo.report_parameter_lookup` patched here |
| DS_CCP_wired-caching | SSIS project | `wired-caching\cache_refresh.dtsx` and `import_cache_pbr_GP.dtsx` executed |
| DS_CCP_ccp-import (sibling repo) | SSIS project | `ccp.import\ccp_import_aggnetworksettlement.dtsx` executed |
| DS_CCP_ccp-export-to-legacy (sibling repo) | SSIS project | `ccp.export2legacy\Export_billing_*.dtsx` executed |
| DS_CCP_ccp-export (sibling repo) | SSIS project | `ccp.export\oas_export_sunrise_fis_*.dtsx` executed |
| Oracle CCP DWH | External system | Source data via SSH tunnel (`DWH_AWS_SSH`) |
| FIS (Financial Institution Services) | External party | Flat file data feeds |
| Mastercard Network | External party | Settlement files (NAM_*_TT140 format) |
| Great Plains (GP) | ERP system | Financial data for PBR report |
| `sftp.wirecard.com` / `sftp.amer1.wirecard.com` | External SFTP | Delivery target for OAS reconciliation reports |

## Migration Complexity and Blockers for Modernisation

### Complexity: HIGH

1. **Tight coupling to SSISDB folder structure**: All job commands embed absolute SSISDB paths (`\SSISDB\wdnam-ccp-etl\...`). Migrating packages to Azure SSIS-IR or a new SSISDB instance requires updating every job command string.

2. **Oracle DWH dependency**: The `ccp_import_aggnetworksettlement` job (and related CCP Oracle imports) depend on an Oracle CCP DWH that was being decommissioned as of July 2020 (the mass-disable event). However, if any data flows still run against Oracle, the SSH tunnel (`DWH_AWS_SSH` DSN) must be maintained.

3. **Legacy FIS flat file ingestion**: FIS report imports are file-based (landing zone on ETL server drives `F:\ETL\` / `R:\ETL\`). Migration to cloud-native storage (Azure Blob, SFTP-to-blob) requires redesigning the SSIS packages that load these files.

4. **No infrastructure-as-code**: p-db09 SQL Agent configuration exists only in these manual scripts. Rebuilding the server from scratch requires replaying every script in the repo in order. Estimated effort: 2–3 weeks for a careful replay + validation.

5. **Legacy Wirecard SFTP endpoints**: `sftp.wirecard.com` and `sftp.amer1.wirecard.com` are Wirecard infrastructure hostnames. Post-acquisition, these need to be mapped to current Onbe SFTP infrastructure.

### Blockers

- **CCP Oracle DWH**: Until the Oracle DWH is fully decommissioned and replaced (or confirmed decommissioned), the CCP import jobs cannot be safely removed.
- **OAS/Sunrise Banks reconciliation**: The OAS export jobs for FIS data serve Sunrise Banks (an issuing bank partner). Client contractual obligations must be confirmed before decommissioning.
- **WIRED product EOL**: WIRED is a Gen-2 client-facing reporting product. Its replacement by a Gen-3 API-driven report delivery system must be completed before p-db09 can be decommissioned.
