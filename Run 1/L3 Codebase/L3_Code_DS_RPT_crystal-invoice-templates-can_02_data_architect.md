# DS_RPT_crystal-invoice-templates-can — Data Architect View

## Data Stores
- **Microsoft Great Plains (Dynamics GP)** — primary data source for all SOP and Purchase Order reports. Access is via Crystal Reports SQL queries directly to the GP database.
- No connection strings are visible in the `.rpt` binary files without a Crystal Reports reader; the SQL-suffix in filenames implies embedded SQL queries.
- The `ASI12312.dat` / `ASI12312.idx` files are Crystal Reports index/data cache files — they may contain cached result data from a previous report execution.

## Schema / Tables Accessed
- Crystal Reports `.rpt` files are binary; exact table names cannot be extracted without running the reports in a Crystal Reports IDE.
- Based on report names and Great Plains context, likely tables include:
  - `SOP10100` / `SOP10200` — Great Plains SOP header/line tables
  - `SOP30200` / `SOP30300` — Historical SOP header/line tables
  - `POP10100` / `POP10110` — Purchase Order header/line tables
  - `RM00101` — Receivables customer master
  - Canadian tax tables (if Canadian tax rules embedded)

## Sensitive Data Assessment
| Data Type | Likely Present | Risk Level |
|---|---|---|
| Customer/client names | Yes (billing entity names) | PII — PIPEDA/Quebec Law 25 |
| Order amounts / totals | Yes | Financial — SOC 1 scope |
| Invoice numbers / SOP numbers | Yes | Operational identifier |
| Customer addresses | Possible (invoice header) | PII |
| Credit card numbers on invoices | Unlikely | N/A for invoice docs |
| Canadian tax IDs (GST/HST) | Possible | Regulatory |

- Crystal Reports cache files (`ASI12312.dat`) may contain previously rendered report data, including any PII present in the report output.

## Encryption
- Crystal Reports `.rpt` files may have password protection configured within Crystal Reports (not detectable from filename alone).
- No transport encryption configuration visible in the repo (reports are run locally or via a report server — configuration not present here).
- Cache files (`ASI12312.dat`) — binary, unknown if encrypted.

## Data Flow
```
Great Plains SQL Server (GP DB — Canadian entity)
        |
    Crystal Reports Runtime (SAP Crystal Reports)
        |
    SOP Invoice / PO Document (PDF or Print)
        |
    Client / Finance recipient
```

## Data Quality / Retention
- Multiple report versions (v01–v05) without a version registry create ambiguity about which version produces the authoritative invoice.
- No data transformation logic visible (reports are read-only against GP).
- Crystal cache files in the repo introduce a risk of stale cached data being used instead of live DB queries.
- No data retention policy for rendered invoices visible in this repo.

## Compliance Gaps
1. **Crystal Reports cache files in source control** — `ASI12312.dat` / `.idx` may contain previously queried financial or PII data; these should not be committed to version control.
2. **Binary `.rpt` format** — no automated PII scanning can be performed; manual review in Crystal Reports IDE required to audit data fields.
3. **No data masking** — if customer PII (names, addresses) appears in invoice output, no masking or redaction controls are visible.
4. **Multiple unretired versions** — v01–v05 without explicit deprecation labelling creates audit ambiguity.
5. **Windows .lnk file** — reveals internal UNC/server path; potential information disclosure if repo is ever made public or shared.
