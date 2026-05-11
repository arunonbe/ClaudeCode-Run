# Business Analyst Report — dmt_WAPP

## Business Purpose
The Data Management Tool (DMT) is an Excel macro-enabled workbook (`Data Management Tool - Production.xlsm`) that serves as the internal operational front-end for data management activities at Onbe/Northlane. It provides business users with a structured, permission-controlled interface to retrieve and manipulate data stored in a back-end SQL database called **RiskDB**, without exposing raw database access. Importantly, **no data is persisted inside the Excel file itself** — all data loads at runtime via SQL queries gated by the user's Active Directory/firewall permissions.

## Capabilities
| Capability | Detail |
|---|---|
| Data Retrieval | SQL-driven data fetch from RiskDB based on user firewall role |
| Data Management | In-spreadsheet CRUD operations via VBA macros (code not in-repo — lives on RiskDB server) |
| Version Distribution | `DMT Production Copy Link.xlsm` auto-downloads the latest `Data Management Tool - Production.xlsm` from RiskDB so users always run the current version |
| OPTIC Integration | `OPTIC - Production.xlsm` and `OPTIC Production Copy Link.xlsm` mirror the same link-file pattern for the OPTIC tool (separate but co-hosted application) |

## Key Entities
- **User** — Internal Onbe employee with firewall permissions that define visible SQL data sets
- **RiskDB** — SQL Server back-end; both storage and distribution host for the `.xlsm` files
- **DMT Excel Application** — Stateless front-end; VBA macro layer connecting to SQL
- **OPTIC Application** — Co-resident tool following identical distribution pattern

## Business Rules
1. Users must have active firewall permissions to access RiskDB; data visibility is permission-scoped at the SQL layer.
2. The production `.xlsm` file must only be distributed via the link file (not emailed/manually copied) to ensure version consistency.
3. All business logic and VBA code lives server-side on RiskDB; the Git repository stores only the binary artefact for version history purposes.
4. No sensitive data (PAN, PII) is stored inside the Excel files.

## Business Flows
```
User Desktop
  └─ Runs DMT Production Copy Link.xlsm
       └─ Downloads latest Data Management Tool - Production.xlsm from RiskDB
            └─ Excel opens; VBA connects to RiskDB via SQL
                 └─ Data filtered by user's firewall permissions
                      └─ User performs data management actions → saved back to RiskDB
```

## Compliance Relevance
- **PCI DSS**: RiskDB likely hosts or queries payment-related data; firewall-based access control is the primary PCI control boundary. The spreadsheet surface area should be evaluated for scoping.
- **GLBA / SOC 2**: Internal tool accessing financial operations data — change management and access control procedures apply.
- **Audit Trail**: No explicit audit logging visible within this repository; audit dependency is entirely on RiskDB SQL Server auditing.

## Risks
| Risk | Severity | Notes |
|---|---|---|
| Binary `.xlsm` files in Git | High | Excel macro binaries are difficult to diff/review; malicious VBA could be introduced invisibly. Binary commit history is unreliable for change control. |
| VBA code not in source control | High | The actual application logic (VBA on RiskDB) is outside Git — no code review, no SDLC control visible here. |
| No automated tests | High | Zero test artefacts in the repository. |
| Single point of distribution | Medium | RiskDB outage blocks all DMT users simultaneously. |
| OPTIC app co-mingled | Low | OPTIC files in the same repo — unclear if OPTIC has a separate change-management cycle. |
| Confluence dependency | Low | Official documentation only at `northlane.atlassian.net` — rebrand/migration risk. |
