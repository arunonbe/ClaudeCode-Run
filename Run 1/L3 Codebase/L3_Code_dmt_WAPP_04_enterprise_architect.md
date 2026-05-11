# Enterprise Architect Report — dmt_WAPP

## Platform Generation
**Generation 1 (Legacy)** — Excel-based desktop application with direct SQL connectivity. This is a classic Gen-1 fat-client tool pattern with no API layer, no containerisation, and no web delivery.

## Domain
**Internal Operations / Risk Data Management** — Internal Onbe tooling for data management and risk operations. Not customer-facing. Sits outside the Cardholder Data Environment (CDE) scope unless RiskDB contains or processes PAN data, in which case the Excel client falls within the CDE perimeter.

## Role in Enterprise Architecture
- Serves as the **UI layer** for operational data management on RiskDB.
- Acts as a **data distribution mechanism** via the link-file pattern.
- Has a sibling application, **OPTIC**, co-hosted in this same repository, suggesting a shared operational tooling domain.
- Referenced by the Northlane Confluence space (`northlane.atlassian.net`), indicating pre-Onbe-rebrand vintage.

## Dependencies
| Dependency | Type | Notes |
|---|---|---|
| RiskDB SQL Server | Hard runtime | All data and file distribution |
| Microsoft Excel | Hard runtime | Client-side execution environment |
| Active Directory / Firewall Rules | Hard security | Permission enforcement |
| dmt-web_WAPP | Successor/parallel | Web-based replacement under development (see separate repo) |
| Northlane Confluence | Documentation | Historical documentation host |

## Architectural Patterns
- **Fat Client / Smart Client**: All processing in Excel VBA on the user desktop.
- **Link File Distribution**: Self-updating desktop app via a bootstrap link file — a pre-DevOps pattern for version management.
- **Direct SQL Access**: No API gateway, no service layer.

## Status
**Active but strategically deprecated** — A web-based replacement (`dmt-web_WAPP`) is under development. The Excel tool is in production maintenance mode.

## Blockers to Modernisation
1. **VBA Logic Not Externalised**: Business rules embedded in binary macros must be re-implemented before retirement.
2. **RiskDB Schema Not Documented**: No schema artefacts in any repo; schema reverse-engineering required before migration.
3. **User Base Dependency**: Users depend on the self-update link-file UX; training and change management needed for web UI transition.
4. **OPTIC Application**: Co-resident OPTIC application must be separately analysed and migrated — it is not covered by dmt-web_WAPP.
5. **Unknown Permissions Model**: Firewall-based SQL row security has no equivalent documented for the web replacement.
