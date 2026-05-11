# DS_RPT_crystal-invoice-templates-can — Business Analyst View

## Business Purpose
A collection of **SAP Crystal Reports invoice templates** used to generate customer-facing billing and sales order documents for the **Canadian operations** of eCount/NorthLane/CitiPrepaid Canada. These reports render Sales Order Processing (SOP) documents from Microsoft Great Plains for invoicing, order tracking, and procurement workflows in Canada.

## Capabilities
The repo contains 9 Crystal Reports (`.rpt`) files covering:
1. **SOP Document - Historical with Comments (SQL)** — Multiple versions (v01, v02, v03, v05) and a "Copy of" variant. Historical posted SOP documents with annotation fields.
2. **Great Plains SOP Order Rollup** (v02, v03) — Aggregated order summary reports.
3. **SOP Document - Quotation (Invoice Advice)** (v02) — Pre-invoice quotation/advice documents.
4. **SOP Document - Unposted with Comments (SQL)** (v02) — Unposted (draft/open) SOP documents.
5. **Purchase Order - No Rollup (SQL)** (v01) — Purchase order documents without rollup aggregation.

Supporting assets:
- Logos: `citi_corp_logo.gif` (Citibank), `cps-logo.gif` (CPS — Card Processing Solutions), `NorthLane_cmyk_blacklogo.jpg` (NorthLane)
- Database index files: `ASI12312.dat` / `ASI12312.idx` (Crystal Reports index files)
- Shortcut: `CitiPrepaidCanada - Shortcut.lnk` — Windows shortcut to a server/share path

## Key Entities
| Entity | Notes |
|---|---|
| SOP Document (Sales Order Processing) | Great Plains invoice/order document |
| Historical Posted SOP | Finalized, committed SOP records |
| Unposted SOP | Draft/in-progress orders |
| Purchase Order | Procurement document |
| SOP Rollup | Aggregated order lines |

## Business Rules
- Historical variants imply separation between posted (committed) and unposted (draft) transactions.
- Multiple versions (v01 through v05) indicate iterative refinement; only the highest version is likely current.
- SQL-suffix variants indicate data is sourced directly via SQL queries to Great Plains database rather than Crystal Reports ODBC drivers.
- Canadian operations context: reports include Canadian tax and billing rules (implied by the "can" designation and CitiPrepaidCanada branding).

## Data Flows
```
Microsoft Great Plains (SQL Server DB)
        |
    Crystal Reports (.rpt)
        |
    PDF/Print output → Client/Finance team
```

## Compliance Relevance
- Invoice documents may include client billing details, order amounts, and entity names — relevant to **SOC 1** financial reporting accuracy controls.
- If Canadian cardholder data appears in SOP documents, **PIPEDA** and **Quebec Law 25** privacy obligations apply.
- Logo assets show Citibank branding — if Citibank is still a program partner, PCI DSS program-level obligations may apply to invoice content.

## Risks (Business)
1. **Multiple conflicting versions** (v01–v05 + copies) — unclear which version is current; using an older version in production risks incorrect invoice formatting.
2. **Legacy Citibank and CPS logos** — Citi and CPS branding in assets may be stale; post-Onbe rebranding, NorthLane/Onbe logos should replace them.
3. **Windows `.lnk` shortcut file in repo** — points to a network path; this is an operational artifact that should not be in source control and may reveal internal network topology.
4. **Crystal Reports binary format** — `.rpt` files are binary; changes cannot be reviewed via standard code diff tooling.
5. **No README describing which version to use in production** — institutional knowledge risk.
