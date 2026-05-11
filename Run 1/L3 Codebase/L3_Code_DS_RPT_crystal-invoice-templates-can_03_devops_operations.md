# DS_RPT_crystal-invoice-templates-can — DevOps / Operations View

## Build Process
- **No build process.** Crystal Reports `.rpt` files are binary design-time artefacts produced and modified in the SAP Crystal Reports IDE (or SAP Crystal Reports for Visual Studio).
- No solution file, project file, or build script present.
- No CI/CD pipeline, no automated test, no linting.

## Deployment Method
- Reports are deployed by copying `.rpt` files to a Crystal Reports Runtime Server or directly to the machine running the Crystal Reports runtime.
- No deployment scripts present in this repo.
- The Windows shortcut file (`CitiPrepaidCanada - Shortcut.lnk`) suggests reports were historically accessed from a shared network folder rather than a formal report server.

## Configuration Management
- Crystal Reports embed their data source connection information within the `.rpt` file (DSN or direct SQL connection settings).
- No environment-specific configuration files present; connection info is baked into each `.rpt` binary.
- Logo/image assets (`citi_corp_logo.gif`, `cps-logo.gif`, `NorthLane_cmyk_blacklogo.jpg`) are embedded by reference or value in the `.rpt` files; they must be present alongside the reports at runtime.

## Observability
- No logging, monitoring, or alerting configuration.
- Crystal Reports runtime errors are surfaced to the end user running the report; no server-side log aggregation visible.
- No job scheduling — these are on-demand reports run by Finance/Operations staff.

## Infrastructure Dependencies
| Dependency | Purpose | Risk if Unavailable |
|---|---|---|
| SAP Crystal Reports Runtime | Report rendering engine | Reports cannot be opened/run |
| Microsoft Great Plains (GP) SQL Server | Data source | Reports return no data |
| Network share (implied by .lnk) | Report file storage | Reports inaccessible to users |
| Logo image files (GIFs, JPG) | Report branding | Reports render without logos |

## Operational Risks
1. **No version control for binary format** — changes to `.rpt` files cannot be reviewed or diff'd; rollback requires restoring a previous file from source control.
2. **Multiple versions without documentation** — v01 through v05 coexist; wrong version deployed = incorrect invoice format.
3. **Stale logos** — Citibank and CPS logos are legacy; if reports are still being sent to clients, incorrect branding may cause confusion or contractual issues.
4. **Crystal cache files committed** — `ASI12312.dat` / `.idx` may produce stale query results if Crystal Reports uses cached data instead of live queries.
5. **No owner identified** — no commit history analyzed; no README author. If the Crystal Reports IDE license is not renewed, no one can modify the reports.

## CI/CD Assessment
- **No CI/CD pipeline.** No `.github`, `.gitlab-ci.yml`, `Jenkinsfile`, or Azure DevOps pipeline present.
- This repo functions purely as a file-system backup / version archive for binary report files.
- Recommended: At minimum, implement a change log or naming convention to identify the current production version of each report type.
