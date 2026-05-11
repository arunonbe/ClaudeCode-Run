# DS_RPT_crystal-invoice-templates-us — Enterprise Architect View

## Platform Generation
**Gen-1** — SAP Crystal Reports binary templates, Microsoft Great Plains (legacy ERP). Identical generation classification to the Canadian equivalent repo.

## Business Domain
**Finance — Billing / Invoicing (US Operations)**
- Generates SOP invoice and purchase order documents for US prepaid card clients and programs.
- Serves: Finance, Accounts Receivable, Client Management (US).

## Architectural Role
**Client-facing invoice rendering** for US prepaid program billing. Occupies the same position as the Canadian repo but for US entity and US regulatory context.

```
[Great Plains / Dynamics GP — US Entity DB]
        |
    [Crystal Reports Runtime]
        |
    [PDF / Print — eCount SOP Invoice or PO]
        |
    [Client / Finance recipient (US)]
```

## Integration Patterns
- **Direct DB query** (Crystal Reports SQL to GP)
- **File-based distribution** (PDF/print; no API delivery)
- **Binary template monolith** — logic and layout inseparable

## Differentiators from Canadian Repo
| Aspect | US | Canada |
|---|---|---|
| Primary template name | eCount Great Plains SOP Order Blank Paper | Great Plains SOP Order Rollup |
| DynamicBank variant | Yes (v04) | No |
| Short Form variant | Yes (v03) | No |
| LennyCopy personal variant | Yes (V04) | No |
| Branding assets | Same (Citi, CPS, NorthLane) | Same |

## Strategic Status
- **Legacy / Sunset candidate** — same assessment as Canadian repo. Crystal Reports + Great Plains = Gen-1 stack.
- US operations likely represent the larger volume of invoice activity (primary market).
- DynamicBank variant suggests active client customization work was being done; unclear if this is still maintained.

## Migration Blockers
1. **Binary `.rpt` format** — must be opened in Crystal Reports IDE to extract SQL logic and field mappings.
2. **Great Plains dependency** — requires parallel GP decommission or migration.
3. **US billing/tax rules** — embedded US tax logic (if any) must be replicated in replacement system.
4. **Multiple V04 variants** — must determine which is production-current before migration.
5. **DynamicBank template** — if bank partners consume a specific invoice format, format changes require partner approval.
6. **No current owner** — assignment required before any migration or decommission.
