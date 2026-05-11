# Enterprise Architect View — DS_CCP_ccp-report-services

## Platform Generation
**Generation 2 (Gen-2) reporting layer.** SSRS 2017 on-premises reporting solution. Represents the presentation/consumption layer of the CCP data platform. No self-service analytics, no cloud BI, no API-based data delivery.

## Domain Placement
- **Domain:** Data Platform — CCP Business Intelligence and Reporting
- **Subdomain:** Operational and Financial Reporting (CCP prepaid program)
- **Consumers:** Finance team, Client Services (exception and operations), Fraud/Risk, BIN bank partners, Admin, Management

## Role in the Ecosystem
```
[ccp-import] → [ODS] ──────────────────────► [SSRS Reports] → Finance / Client Services / Fraud
[DWH Oracle] ─────────────────────────────►              → BIN Banks
[WIRED DB]   ─(cache_pbr, vw_param_Frequencies)──────────► Admin / Management
```

This project is the **reporting and analytics consumption layer** for the entire CCP data platform. It is the terminal node — it reads from ODS, DWH, and WIRED but does not write back to any operational store.

## Report Audience Matrix
| Audience | Reports | Data Sensitivity |
|----------|---------|-----------------|
| Finance | Program Balance, FIS Fees, Settlement | Financial — SOC 1 scope |
| BIN Banks | Network Settlement Report | Financial + network codes |
| Client Services — Exception | Aggregate Spending, Cardholder Account Management | PII + last-4 card — PCI DSS |
| Client Services — Operations | Aggregate Spending, Card Ship Date, RAPID Undeliverable | Operational |
| Fraud | Unposted Transactions | **Full Card Number — CDE scope** |
| Admin | (Data sources only) | Infrastructure |
| Home | Report Catalog, Subscriptions | Metadata |
| Templates | Landscape/Portrait/Legal layout templates | None |

## Key Dependencies
| System | Role | Risk if Unavailable |
|--------|------|---------------------|
| ODS SQL Server (`t-phl-db01`) | Primary data source | All operational reports fail |
| WIRED SQL Server (`t-phl-db01`) | Parameter lookups, Program Balance cache | All parameterised reports fail; Program Balance shows no data |
| DWH Oracle (`DWH_AWS_SSH`) | Cardholder Account Management | CAM report fails |
| `cache_pbr` refresh process | Program Balance data freshness | Program Balance shows stale data |
| SSRS subscription scheduler | Scheduled report delivery | Subscriptions not delivered |

## Architectural Patterns
- **SSRS server-side rendering** — reports rendered on SSRS server, delivered via web browser, email subscription, or file share
- **Shared data sources** — `.rds` files referenced by multiple `.rdl` reports (change once, affects all)
- **Stored-procedure and view abstraction** — SQL logic encapsulated in ODS/WIRED stored procedures and views, not embedded in RDL
- **Parameter cascade** — `vw_param_Frequencies` drives date parameters across all reports consistently

## Current Status
Active operational solution. Report schema version is SSRS 2016 (deployed on SSRS 2017). Several project folders contain no RDL files (Analytics, Client Custom, Job Services, Order Services, Technology, UAT, Vendor Management) — these are either empty placeholder folders or reports not committed to source control.

## Migration Blockers
1. **Legacy server dependency** — all data sources reference `t-phl-db01.wirecard.lan`; migration requires updating all data source connection strings.
2. **Oracle DWH dependency** — `DWH_AWS_SSH` is an AWS-hosted Oracle instance; any Oracle-to-non-Oracle migration requires rewriting Oracle stored procedures (e.g., `PKG_NAM_CLIE_CAM_DATA.GET_DATA`).
3. **SSRS subscription management** — subscription configurations are server-side only; migration requires exporting and re-importing subscriptions.
4. **Audience adoption** — Finance and Client Services teams have trained workflows around these SSRS reports; a Gen-3 BI tool (e.g., Power BI, Tableau) requires re-training and report redesign.
5. **Empty project folders** — unclear if reports in Analytics, UAT, Technology etc. exist on the SSRS server but are not in source control; a server-side audit is needed before migration.
