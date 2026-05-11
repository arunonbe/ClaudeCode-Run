# DS_RPT_crystal-invoice-templates-can — Solution Architect View

## Technical Architecture
- **Technology**: SAP Crystal Reports (version not determinable from binary `.rpt` files without IDE inspection)
- **Data source**: Microsoft Great Plains SQL Server (direct SQL queries embedded in `.rpt`)
- **Output**: Printed invoices and/or PDF documents
- **Repo contents**: 9 `.rpt` binary files, 2 Crystal cache files, 3 image assets, 1 Windows shortcut
- **No application code** — pure report template artefacts

## API Surface
None. Crystal Reports are rendered by the Crystal Reports runtime engine on demand by a user or calling application. No REST API, SOAP service, or programmatic interface defined in this repo.

## Security Posture

### Authentication
- Crystal Reports connect to the Great Plains database via connection settings embedded in each `.rpt` file.
- Connection type (Windows auth vs SQL auth) cannot be determined without opening the binary files in the Crystal Reports IDE.
- If SQL authentication is used, credentials may be embedded in the `.rpt` binary — this is a **significant PCI DSS concern** (Req 8.3.1 — default/embedded credentials prohibited).

### Secrets / Credentials
- Cannot be confirmed from outside the binary — Crystal Reports `.rpt` files can store DSN connection strings, SQL Server login credentials, or Windows auth settings internally.
- **Risk**: If any `.rpt` file stores a SQL username/password, those credentials are embedded in a binary committed to source control.
- Recommendation: Open each `.rpt` in Crystal Reports IDE and verify data source connection type before any distribution or migration.

### Crypto
- No transport encryption configuration visible in repo.
- Crystal cache files (`ASI12312.dat` / `.idx`) — binary format, content unknown; may contain previously queried financial data at rest without encryption.

### CVEs / Library Risk
- SAP Crystal Reports runtime has a history of high-severity CVEs (XML injection, RCE via malformed `.rpt` files).
- Without knowing the exact Crystal Reports version, specific CVE applicability cannot be determined.
- Crystal Reports for Visual Studio (SAP) reached end of mainstream support; security patches may not be available.

## Technical Debt
| Item | Severity | Evidence |
|---|---|---|
| Unknown Crystal Reports version | High | No version indicator in repo |
| Potential embedded SQL credentials in .rpt binary | High | Crystal Reports design pattern risk |
| Multiple versions without deprecation (v01–v05) | Medium | 9 .rpt files across 5 version levels |
| Crystal cache files (.dat/.idx) in source control | Medium | ASI12312.dat, ASI12312.idx present |
| Legacy Citibank/CPS logos | Low | citi_corp_logo.gif, cps-logo.gif |
| Windows .lnk file in repo | Low | CitiPrepaidCanada - Shortcut.lnk |
| Binary format — no diff/review capability | Low | Architectural constraint of Crystal Reports |

## Gen-3 Migration Requirements
1. Audit each `.rpt` file in Crystal Reports IDE to extract:
   - Data source connection type (Windows vs SQL auth)
   - Embedded SQL queries and parameters
   - All data fields rendered in output
2. If SQL credentials are embedded, rotate immediately.
3. Replace Crystal Reports with a modern reporting tool (SSRS, Power BI Paginated Reports, or a web-based invoice generation service).
4. Replace Great Plains SQL dependency with modern data layer (API or warehouse query).
5. Remove cache files from source control; add `.dat`/`.idx` to `.gitignore`.
6. Consolidate to a single current version per report type; archive or delete prior versions.
7. Update branding assets to current Onbe branding.

## Code-Level Risks (File References)
| Risk | File |
|---|---|
| Potential embedded SQL credentials | All `.rpt` files — requires IDE inspection |
| Stale cached query data | `ASI12312.dat`, `ASI12312.idx` |
| Internal network path disclosure | `CitiPrepaidCanada - Shortcut.lnk` |
| Obsolete branding | `citi_corp_logo.gif`, `cps-logo.gif` |
| Ambiguous current version | `SOP Document - Historical with Comments(SQL)_v01.rpt` through `_v05.rpt` |
