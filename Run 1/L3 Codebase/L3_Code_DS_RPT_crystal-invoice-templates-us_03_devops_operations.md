# DS_RPT_crystal-invoice-templates-us — DevOps / Operations View

## Build Process
- **No build process.** Crystal Reports `.rpt` files are binary design-time artefacts produced in the SAP Crystal Reports IDE.
- No solution file, project file, or build script present.
- No CI/CD pipeline.

## Deployment Method
- Reports deployed by copying `.rpt` files to a Crystal Reports Runtime server or the machine running the Crystal Reports runtime.
- No deployment scripts in this repo.
- No evidence of a report server (e.g., SAP Crystal Reports Server, SAP BusinessObjects) being used; distribution pattern is unclear.

## Configuration Management
- All data source connection settings are baked into the binary `.rpt` files.
- No environment-specific config files present.
- Logo assets (`citi_corp_logo.gif`, `cps-logo.gif`, `NorthLane_cmyk_blacklogo.jpg`) must be co-located with the reports or referenced by an absolute path.
- The `DynamicBank` variant name suggests the bank name/branding is parameterized at runtime (a Crystal Reports parameter or formula) — but this cannot be confirmed from file inspection alone.

## Observability
- No logging, monitoring, or alerting.
- Errors surface to end users running the report; no centralized error tracking.
- On-demand execution only; no scheduled job definitions in this repo.

## Infrastructure Dependencies
| Dependency | Purpose | Risk if Unavailable |
|---|---|---|
| SAP Crystal Reports Runtime | Report rendering | Reports cannot run |
| Microsoft Great Plains (US) | Data source | Empty reports |
| Logo image files | Branding | Reports without logos |

## Operational Risks
1. **`LennyCopy` variant** — a personal copy committed by a developer; if mistakenly deployed to production, the wrong invoice format is presented to clients.
2. **`OldVersion` variant** — explicitly named old version present in the same repo as the current version; risk of deployment confusion.
3. **Multiple V04 variants** — four variants of V04 require manual selection of the correct one for production deployment.
4. **Crystal cache files** (`ASI12312.dat`/`.idx`) — if present on the production server, Crystal Reports may serve cached data from a prior run instead of querying the live database.
5. **No version tagging or README** to identify the current production version.

## CI/CD Assessment
- **No CI/CD pipeline.** Repo is a binary file archive with no automation.
- Recommended minimum: add a `CURRENT_VERSION.txt` or README section identifying which `.rpt` file is the active production template for each document type.
