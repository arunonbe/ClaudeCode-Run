# DS_RPT_crystal-invoice-templates-us — Business Analyst View

## Business Purpose
A collection of **SAP Crystal Reports invoice templates** for the **United States operations** of eCount/NorthLane/CitiPrepaid. These reports generate customer-facing SOP (Sales Order Processing) invoice documents from Microsoft Great Plains for US-based clients, covering prepaid card program billing, purchase orders, and sales order processing.

## Capabilities
The repo contains 14+ Crystal Reports (`.rpt`) files:

1. **eCount Great Plains SOP Order Blank Paper** — Multiple versions (v02, v03, v04, v04 DynamicBank variant, v04 OldVersion). The primary invoice template series; "blank paper" indicates the report generates its own formatting without pre-printed stationery.
2. **eCount Great Plains SOP Order Short Form** (v03) — Condensed invoice for shorter order presentations.
3. **SOP Document - Historical with Comments (SQL)** — V02 (copy/backup), V03, V04 (original), V04 (LennyCopy), V05. Historical posted SOP documents with annotation support.
4. **SOP Document - Quotation (Invoice Advice)** (v1) — Pre-invoice quotation document.
5. **SOPDocument - Unposted with Comments (SQL)** — Draft/open order documents.
6. **PurchaseOrder - No Rollup (SQL)** — US purchase order document.

Supporting assets: `citi_corp_logo.gif`, `cps-logo.gif`, `NorthLane_cmyk_blacklogo.jpg`, `ASI12312.dat`/`.idx`

## Key Entities
| Entity | Notes |
|---|---|
| SOP Document (Sales Order Processing) | Great Plains invoice/order |
| Historical Posted SOP | Finalized, committed SOP records |
| Unposted SOP | Draft/in-progress orders |
| Purchase Order | US procurement document |
| eCount Prepaid Program | DynamicBank variant suggests bank-branded template |

## Business Rules
- "Blank paper" variants allow the report to render without special pre-printed invoice stationery — important for flexibility across clients.
- "DynamicBank" variant in v04 suggests a bank-co-branded version of the invoice that dynamically swaps bank partner branding.
- "LennyCopy" label on a V04 variant indicates an individual developer's personal copy was committed to the repo — not a controlled version.
- SQL-suffix filenames indicate direct SQL queries to Great Plains rather than Crystal Reports ODBC.
- Historical vs Unposted separation mirrors the Canadian templates; US operations follow the same GP SOP workflow.

## Data Flows
```
Microsoft Great Plains (SQL Server DB — US Entity)
        |
    Crystal Reports (.rpt)
        |
    PDF/Print output → Client/Finance team (US)
```

## Compliance Relevance
- Invoice documents contain client billing details and order amounts — relevant to **SOC 1** financial accuracy and **GAAP** compliance for revenue recognition.
- US operations: customer PII (names, addresses) on invoices is subject to **GLBA** and **CCPA** (for California clients).
- DynamicBank variant may include bank partner branding — subject to bank partner contractual obligations.

## Risks (Business)
1. **"LennyCopy" version in repo** (`SOP Document - Historical with Comments(SQL) V04 - LennyCopy.rpt`) — a personal copy of a report committed to source control; creates version confusion and is not a controlled artefact.
2. **OldVersion variant committed** (`eCount Great Plains SOP Order Blank Paper v04_OldVersion.rpt`) — obsolete version present alongside current; risk of production deployment of wrong version.
3. **Multiple V04 variants** (Original, LennyCopy, OldVersion, DynamicBank) for the same base report — four parallel versions of the same report type with no clear deprecation.
4. **Legacy branding** — Citibank and CPS logos present; post-Onbe rebranding required.
5. **Crystal cache files** — `ASI12312.dat`/`.idx` in repo may contain stale data.
