# DS_RPT_crystal-invoice-templates-us — Solution Architect View

## Technical Architecture
- **Technology**: SAP Crystal Reports (version indeterminate from binary alone)
- **Data source**: Microsoft Great Plains SQL Server (US entity), direct SQL queries embedded in `.rpt`
- **Output**: PDF / printed invoice documents
- **Repo contents**: 14+ `.rpt` binary files, 2 Crystal cache files, 3 image assets
- **No application code** — pure report template artefacts

## API Surface
None. On-demand Crystal Reports runtime rendering.

## Security Posture

### Authentication
- Same risk profile as Canadian repo: connection type (Windows vs SQL auth) embedded in binary `.rpt` files.
- Cannot confirm without IDE inspection whether SQL credentials are embedded.
- **Potential PCI DSS Req 8.3.1 violation** if any `.rpt` stores a hardcoded SQL username/password.

### Secrets / Credentials
- Risk identical to Canadian repo: Crystal Reports `.rpt` files can store SQL credentials internally.
- **Action required**: Open all `.rpt` files in Crystal Reports IDE and confirm data source connection type.

### Crypto
- No encryption configuration visible.
- Cache files unencrypted binary.

### CVEs / Library Risk
- Same SAP Crystal Reports CVE risk profile as Canadian repo.
- `LennyCopy` and `OldVersion` variants may have been built against an older Crystal Reports version — potentially lower patch level than the current production version.

## Technical Debt
| Item | Severity | Evidence |
|---|---|---|
| Unknown Crystal Reports version | High | Binary files — no version indicator |
| Potential embedded SQL credentials | High | Crystal Reports design pattern |
| LennyCopy personal variant in source control | High | `SOP Document - Historical with Comments(SQL) V04 - LennyCopy.rpt` |
| OldVersion variant in active repo | High | `eCount Great Plains SOP Order Blank Paper v04_OldVersion.rpt` |
| 4 variants of V04 with no deprecation label | Medium | V04 Original, LennyCopy, OldVersion, DynamicBank |
| Crystal cache files in source control | Medium | `ASI12312.dat`, `ASI12312.idx` |
| Legacy branding assets | Low | `citi_corp_logo.gif`, `cps-logo.gif` |
| No README or version registry | Low | README contains only the repo name |

## Gen-3 Migration Requirements
1. Perform Crystal Reports IDE audit of all `.rpt` files — extract SQL, field mappings, and confirm auth type.
2. Immediately rotate any embedded SQL credentials found.
3. Consolidate V04 variants: identify and tag the current production version; archive or delete `LennyCopy` and `OldVersion`.
4. Remove `ASI12312.dat`/`.idx` from source control; add to `.gitignore`.
5. Replace Crystal Reports with modern paginated reporting (SSRS, Power BI Paginated Reports, or invoice-specific service).
6. Replace Great Plains SQL dependency with modern data layer.
7. Update all branding to current Onbe brand guidelines.
8. For DynamicBank variant: document which bank partners require this format; negotiate format modernization with partners.

## Code-Level Risks (File References)
| Risk | File |
|---|---|
| Personal/informal variant in production repo | `SOP Document - Historical with Comments(SQL) V04 - LennyCopy.rpt` |
| Explicitly labelled obsolete version | `eCount Great Plains SOP Order Blank Paper v04_OldVersion.rpt` |
| Potential embedded credentials | All `.rpt` files — requires IDE inspection |
| Stale cached data | `ASI12312.dat`, `ASI12312.idx` |
| Legacy branding | `citi_corp_logo.gif`, `cps-logo.gif` |
