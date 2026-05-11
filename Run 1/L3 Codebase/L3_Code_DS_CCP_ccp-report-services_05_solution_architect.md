# Solution Architect View — DS_CCP_ccp-report-services

## Architecture Summary
SQL Server Reporting Services (SSRS) 2017 solution organised into 15 sub-projects by business audience. Reports are RDL-based (2016 schema) with shared `.rds` data source references. Three backend data systems (ODS, WIRED, DWH/Oracle) are used. SQL logic is primarily encapsulated in stored procedures (ODS) and views (WIRED) — report RDLs do not contain embedded complex SQL except for the `Program Balance Report` which queries `cache_pbr` directly and the frequency view query which is shared across reports.

## Report Technical Architecture
```
SSRS 2017 Server
├── Shared Data Sources (.rds)
│   ├── ODS.rds  → t-phl-db01 / ODS (SQL, Windows Auth)
│   ├── Wired.rds → t-phl-db01 / WIRED (SQL, Windows Auth)
│   ├── DWH.rds  → DWH_AWS_SSH (Oracle)
│   └── Munich DWH_Dev.rds → Dev Oracle
├── Reports (RDL)
│   ├── Fraud/Unposted Transactions.rdl ← ODS SP: rpt_Unposted_Transactions
│   ├── BIN Banks/Network Settlement Report.rdl ← ODS SP: RptNetworkSettlementReport
│   ├── Client Services/Cardholder Account Management.rdl ← Oracle: PKG_NAM_CLIE_CAM_DATA.GET_DATA
│   ├── Finance/FIS - Client Daily Fee Summary.rdl ← ODS + WIRED
│   ├── Finance/Program Balance Report.rdl ← WIRED cache_pbr
│   └── ...
└── Templates
    ├── Template Landscape.rdl
    ├── Template Portrait.rdl
    └── Template Legal-Landscape.rdl
```

## API / Integration Surface
SSRS provides:
- **Web portal** — report browsing and on-demand execution
- **Email subscriptions** — scheduled delivery to recipient lists
- **File-share subscriptions** — scheduled file drop to network share
- **SSRS REST API** (2017+) — programmatic report execution possible but not confirmed as used
- **URL access** — direct report URL rendering

No external API consumers documented in this repository.

## Security Assessment
| Area | Finding | Severity |
|------|---------|---------|
| Unposted Transactions returns full Card Number | PAN visible to all users with access to Fraud folder | Critical — PCI DSS |
| Cardholder Account Management returns PII | Folder-level access control must be enforced | High |
| Dev DWH data source in some production-path reports | Dev data visible if not overridden at deploy | High |
| Windows Integrated Auth for ODS/WIRED | Acceptable if SSRS service account is properly scoped | Low |
| Oracle DWH credentials not visible in this repo | Stored on SSRS server; must be audited separately | Medium |
| Subscription email delivery of PII/CDE reports | Email recipients must be maintained; stale lists could deliver to wrong recipients | High |
| No row-level security (RLS) in reports | Entire dataset visible to any authorised user; no per-client data isolation visible | Medium |

## Technical Debt
1. **Full Card Number in Fraud report** — `rpt_Unposted_Transactions` SP returns `Card Number` column; the SSRS report exposes it to all Fraud folder users. Should be masked to last-4 unless the viewer has explicit "full PAN" access.
2. **Dev data source references** — `Munich DWH_Dev.rds` is referenced in reports intended for production audiences; should be replaced with `DWH.rds` for production deployment.
3. **Cache dependency** — `cache_pbr` in WIRED is a denormalised cache table; the refresh job is not in this repository; stale data risk is invisible to report consumers.
4. **Empty project folders** — 7 of 15 folders contain no RDL files; either reports are missing from source control or the folders are genuinely empty. This ambiguity is a maintenance risk.
5. **No CI/CD** — manual SSDT deployment; no automated post-deploy validation that reports render without error.
6. **No subscription audit trail in source** — subscription recipient lists are maintained server-side only; not version-controlled.

## Gen-3 Migration Recommendations
1. **Migrate to Power BI** (or equivalent cloud BI tool) for Finance, Client Services, and BIN Banks audiences; SSRS can remain for operational reports if SSRS Premium is available.
2. **Mask Card Number** in `rpt_Unposted_Transactions` to last-4; provide a separate secured API endpoint for full PAN access with explicit audit logging.
3. **Replace `cache_pbr`** with a proper data mart refresh pipeline (ADF or dbt) with freshness monitoring.
4. **Remove `Munich DWH_Dev.rds`** references from all non-UAT reports before any production deployment.
5. **Add automated smoke tests** — post-deploy verify that key reports execute without error and return expected row counts.
6. **Inventory SSRS server** — perform a server-side audit to identify all deployed reports and subscriptions before any migration, including those not in source control.
