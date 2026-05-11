# DS_RPT_crystal-invoice-templates-can — Enterprise Architect View

## Platform Generation
**Gen-1** — SAP Crystal Reports (legacy reporting technology), directly connected to Microsoft Great Plains (legacy ERP). No API layer, no cloud component, no modern BI platform.

## Business Domain
**Finance — Billing / Invoicing (Canadian Operations)**
- Generates SOP invoice documents for Canadian prepaid card clients/programs.
- Serves: Finance, Accounts Receivable, and Client Management teams.
- Geographic scope: Canada (CitiPrepaid Canada, Canadian regulatory context).

## Architectural Role
**Point-of-record invoice rendering** — Crystal Reports templates that transform Great Plains SOP transaction data into printed or PDF invoice documents. These are the last-mile client-facing documents for Canadian billing.

```
[Great Plains / Dynamics GP — Canadian Entity DB]
        |
    [Crystal Reports Runtime]
        |
    [PDF / Print — SOP Invoice or PO Document]
        |
    [Client / Finance recipient]
```

## Integration Patterns
- **Direct DB query** (Crystal Reports SQL embedded in `.rpt`) — tightly coupled to GP schema
- **File-based distribution** (network share / email PDF) — no API or electronic delivery integration observed
- **Binary report template** — monolithic; logic and presentation are inseparable

## External System Dependencies
| System | Role |
|---|---|
| Microsoft Great Plains (Dynamics GP) | Sole data source |
| SAP Crystal Reports Runtime | Rendering engine |
| Network share (implied) | Report file access / delivery |
| Citibank (branding) | Legacy program partner |
| CPS / NorthLane / Onbe | Branding assets |

## Strategic Status
- **Legacy / Sunset candidate** — Crystal Reports is SAP end-of-mainstream-maintenance technology. Great Plains (Dynamics GP) is also a legacy ERP platform.
- Presence of Citibank and CPS logos suggests these reports predate the NorthLane era (pre-2019).
- NorthLane logo also present — reports were updated at some point for rebrand.
- If Onbe has migrated Canadian invoicing to a modern ERP or billing platform, these reports may already be obsolete.

## Migration Blockers
1. **Binary `.rpt` format** — no extract of business logic without Crystal Reports IDE; migration requires manual reverse-engineering of each report's SQL and layout.
2. **Great Plains dependency** — migration requires a corresponding GP-to-modern-ERP data migration.
3. **Canadian tax/regulatory logic** — any Canadian GST/HST/QST logic embedded in reports must be replicated in the replacement system.
4. **No current owner** — decommission or migration requires ownership assignment first.
5. **Client-facing format dependency** — if clients have contractual expectations of a specific invoice layout, changes require client notification and approval.
