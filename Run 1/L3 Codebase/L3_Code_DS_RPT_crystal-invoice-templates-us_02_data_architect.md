# DS_RPT_crystal-invoice-templates-us — Data Architect View

## Data Stores
- **Microsoft Great Plains (Dynamics GP) — US Entity**: Primary data source. Crystal Reports SQL queries read from GP SOP and PO tables directly.
- Crystal Reports cache files (`ASI12312.dat`/`.idx`) are local-execution artefacts present in the repo.

## Schema / Tables Accessed (Inferred)
Crystal Reports `.rpt` files are binary; exact tables cannot be extracted without IDE inspection. Based on US Great Plains SOP/PO context, expected tables:
- `SOP10100`, `SOP10200` — Open SOP header/line
- `SOP30200`, `SOP30300` — Historical SOP header/line
- `POP10100`, `POP10110` — Purchase Order header/line
- `RM00101` — Customer master
- Possible `IV00101` — Item master (for line-item descriptions)

## Sensitive Data Assessment
| Data Type | Likely Present | Risk Level |
|---|---|---|
| Client/company names | Yes | PII (CCPA if California clients) |
| Order amounts and totals | Yes | Financial — SOC 1 scope |
| Invoice/SOP numbers | Yes | Operational identifiers |
| Billing addresses | Possible | PII |
| Tax identifiers (TIN/EIN) | Possible | Regulatory sensitive |
| DDA/bank account numbers | Unlikely in SOP invoices | Low |
| Card numbers | Unlikely in GP invoice context | Low |

- The "eCount Great Plains SOP" naming confirms this is the eCount (prepaid card) operational billing layer.
- "DynamicBank" variant may include bank partner information (bank name, possibly BIN-level data).

## Encryption
- Connection details embedded in `.rpt` binary — encryption type unknown without IDE inspection.
- Cache files in repo — binary, unencrypted.
- No transport-layer encryption configuration in repo.

## Data Flow
```
Great Plains SQL Server (US Entity)
        |
    Crystal Reports Runtime
        |
    Invoice document (PDF or print)
        |
    Client / Finance / AR team
```

## Data Quality / Retention
- 4+ variants of V04 (`Original`, `LennyCopy`, `OldVersion`, `DynamicBank`) create ambiguity about the authoritative production version.
- No data validation or transformation logic visible (read-only reports against GP).
- Crystal cache files may produce stale data if run without refreshing from live DB.

## Compliance Gaps
1. **Crystal cache files in source control** — same risk as Canadian repo; may contain previously queried PII or financial data.
2. **Binary `.rpt` format** — PII scanning and DLP controls cannot be applied automatically.
3. **`LennyCopy` variant** — named after an individual developer; this should not be in a production source control repository; represents an internal person's name committed to a shared repo (minor PII/privacy consideration).
4. **Potential embedded SQL credentials** — cannot confirm without IDE inspection.
5. **No masking of client PII** in invoice output — names and addresses rendered in plaintext.
