# Enterprise Architect Report — DS_CCP_wired

## Platform Generation Classification

**Generation: Gen-2 (Wirecard/Northlane — WIRED product)**

Evidence:
- Product name "WIRED" = Wirecard Intelligent Report Engine Delivery — explicitly branded Wirecard
- SSDT project creator/modifier context: `WIRECARD\patricia.zysk` throughout seed data and procedure comments
- Active development period: late 2019 to early 2020 (dates in stored procedure headers)
- Security roles reference `WIRECARD\` AD group names
- Connection manager `wired_db.conmgr` in sibling repos points to `d-phl-db01.wirecard.lan` — Wirecard LAN
- SSISDB folder: `wdnam-ccp-etl` — Wirecard NAM

WIRED represents a **Gen-2 proprietary report delivery product** built by Wirecard North America's Data Services team. It is a client-facing capability with a defined lifecycle that was in active development through 2020 and appears to have been stabilised rather than evolved post-acquisition.

The CCP Oracle DWH source of truth for WIRED cache data is a **Gen-1 system** (legacy Oracle-based card processing platform), placing WIRED at the interface between Gen-1 data and Gen-2 delivery infrastructure.

## Role in the Overall Payments Architecture

WIRED occupies the **client-facing reporting tier** of the CCP data architecture:

```
┌──────────────────────────────────────────────────────────────────────────┐
│                    CCP REPORTING ARCHITECTURE                            │
│                                                                          │
│  Gen-1 Oracle CCP DWH ──► DS_CCP_wired-caching ──► WIRED.cache_*       │
│                                                                          │
│  GP Financials ──────────► DS_CCP_wired-caching ──► WIRED.cache_pbr_GP  │
│  (Great Plains ERP)                                                      │
│                                                                          │
│  WIRED.report_requests ──► DS_CCP_wired-output ──► Report files         │
│  (subscription config)      (SSIS pipeline)         (PDF, XLSX, CSV)    │
│                                                                          │
│                                         WEP SFTP Portal (clients)       │
│                                         Client SFTP servers             │
│                                         Email delivery                  │
│                                         sftp.amer1.wirecard.com         │
└──────────────────────────────────────────────────────────────────────────┘
```

WIRED is the **final delivery layer** in the CCP reporting stack. Its value proposition to Onbe's clients is:
- Automated, scheduled report delivery without client IT involvement
- Multiple delivery channel options (portal, SFTP, email)
- Configurable schedules (daily, weekly, monthly, quarterly, custom)
- Multiple report types (Programme Balance, Aggregate Spending, Card Ship Date, RAPID Undeliverable Cards)

## Report Types Delivered (from seed data in `insert_report_requests.sql`)

| Report Name | Report Folder | Purpose |
|---|---|---|
| Program Balance Report | Finance | Financial balance summary per programme/brand |
| Program Balance Report Plus Fee | Finance | PBR with fee details |
| Card Ship Date | Client Services - Operations | Card shipment date tracking |
| RAPID Undeliverable Cards Report | Client Services - Operations | Cards returned as undeliverable |
| Aggregate Spending | Client Services - Operations | Spend aggregation per programme |

## Dependencies on Other Repos/Services

| Dependency | Direction | Notes |
|---|---|---|
| DS_CCP_wired-caching | Upstream | Populates all `cache_*` tables in WIRED DB |
| DS_CCP_wired-output | Downstream consumer | Reads `report_requests`, `report_schedule`, cache tables to generate reports |
| DS_CCP_db09 | Orchestration | SQL Agent jobs for cache refresh and report output |
| Oracle CCP DWH (`DWH_AWS_SSH`) | Upstream data source | Source of cache data (via SSH tunnel) |
| GP (Great Plains ERP) | Upstream data source | PBR GP data via SFTP |
| SSRS / Crystal Reports | Downstream | Report rendering engine called by WIRED output |
| `sftp.amer1.wirecard.com` / WEP | Downstream delivery | Portal delivery target |
| Client SFTP servers | Downstream delivery | Direct client delivery |

## Architectural Assessment

### Strengths
1. WIRED decouples report delivery scheduling from report execution — the `report_schedule` computed column approach is clever and database-native.
2. The cache architecture provides performance isolation between the slow Oracle DWH source queries and the responsive report generation queries.
3. Multiple delivery methods (WEP, SFTP, Email) in a single subscription model provides flexibility.

### Weaknesses
1. **No self-service client interface**: Report subscriptions are entered by Data Services staff. The UI described in `usp_Wired_InsertReportRequest_UI_INS` comments appears to be an internal admin UI, not a client-facing portal.
2. **Single-brand per subscription**: Each `report_requests` row covers one `BrandName` — large clients with many brands require many subscription records.
3. **Crystal Reports / SSRS rendering dependency**: The report rendering engine is not visible in this repo but is a significant infrastructure dependency. Migration away from SSRS/Crystal requires parallel report reimplementation.
4. **Oracle DWH source dependency**: WIRED cache accuracy depends entirely on the Oracle DWH being populated. CCP Oracle shutdown (2020) broke this data chain, making cache data stale unless an alternative population path was established.

## Migration Complexity and Blockers

### Complexity: HIGH

1. **Oracle DWH replacement**: The cache loading pipeline (DS_CCP_wired-caching) sources data from the Oracle CCP DWH. With CCP Oracle shut down in 2020, the cache tables may contain stale data unless an alternative source was established. Migrating WIRED to a modern platform requires identifying the new authoritative source for programme balance, aggregate spending, and card shipment data.

2. **SSRS/Crystal Reports migration**: The report rendering layer must be migrated to a modern reporting platform (Power BI, SSRS on Azure, Telerik, etc.) before WIRED output can move to cloud.

3. **Client delivery channel migration**: The WEP portal (`sftp.amer1.wirecard.com`) and any configured client SFTP endpoints must be validated and migrated. Client contracts may specify delivery to specific SFTP endpoints.

4. **Schedule and subscription data migration**: The `report_requests` and `report_schedule` data represents active client commitments. Any migration must preserve these subscription configurations and maintain delivery continuity.

### Blockers
- Oracle DWH decommission / replacement (data source for cache tables)
- Report rendering engine (SSRS/Crystal) replacement
- WEP portal migration to Onbe-managed infrastructure
- Client SFTP delivery endpoint migration (requires client coordination)
- Wirecard AD group references in security model must be replaced with Onbe identities before the schema can be deployed to an Onbe-managed SQL Server instance
