# Business Analyst Report — optic_WAPP

## Business Purpose

`optic_WAPP` is a version-controlled repository hosting an Excel-based internal business application called OPTIC (Operations/Planning/Tracking/Intelligence/Control — exact acronym expansion unconfirmed). Based on the README, OPTIC is a data management tool (DMT) that serves as an Excel macro-enabled front-end (`.xlsm`) connected to a SQL backend called "RiskDB." The repository contains two files:

1. **`OPTIC - Production.xlsm`** — The production Excel application file containing VBA macro code. It stores no data internally except the VBA front-end logic. All data is loaded dynamically via SQL queries based on the user's firewall permissions (role-based data access control enforced at the database level).

2. **`OPTIC Production Copy Link.xlsm`** — A user-facing launcher file. Users run this from their desktop; it downloads the latest production copy of the OPTIC application directly from the RiskDB server and opens it, ensuring all users always run the current version without requiring manual distribution.

The Confluence documentation is hosted at `northlane.atlassian.net` (Northlane/Gen-2 era infrastructure), and the development contacts (`Pat.Brown@onbe.com`, `Micheal.Gevaryahu@onbe.com`) are Onbe employees, indicating this is a legacy Gen-2 tool still in active operational use by the business.

## Capabilities

- **Data visualization and reporting:** Connects to RiskDB SQL backend to retrieve and display operational risk, processing, or management data based on user role/permissions.
- **Role-based data access:** Data returned to each user is filtered by their SQL-level firewall/permission configuration — users see only data they are authorized to access.
- **Automated version distribution:** The link file pattern ensures zero-touch version deployment — a new version of OPTIC is published to the server and all users automatically receive it on next launch without IT intervention.
- **VBA-based application logic:** Business rules, data transformation, and UI logic are implemented in Excel VBA macros.

## Client/Cardholder Impact

OPTIC is an internal business application used by Onbe operations staff, not directly by cardholders or clients. However, the data it displays from RiskDB may include:
- Payment processing metrics and risk indicators
- Operational data related to card programs, disbursements, or settlement
- Potentially sensitive business-to-client data that could inform risk decisions affecting cardholders

## Business Rules in Code

Business rules are encoded in VBA macros within the `.xlsm` files, which cannot be inspected through standard source code analysis tools. Key observable rules:
- Data access is enforced at the database level, not in the application layer — SQL firewall permissions gate what data each user sees. This means the VBA application has no application-layer authorization logic.
- The link file pulls the production copy from the RiskDB server — the server path is presumably hardcoded or configured in the link file's VBA.

## Regulatory Obligations

- **GLBA Safeguards Rule:** If RiskDB contains financial customer data, access to that data via OPTIC must be subject to appropriate access controls, audit logging, and authorized user management.
- **PCI DSS Req 7 (Least Privilege):** Data access enforced by SQL firewall permissions is an appropriate least-privilege control, but its effectiveness depends on the database permission model being correctly maintained.
- **PCI DSS Req 8 (Authentication):** User access to OPTIC and RiskDB must be through individually authenticated accounts, not shared credentials.
- **SOC 1/SOC 2 (User Access Reviews):** Regular reviews of who has access to OPTIC/RiskDB and at what permission level are required under SOC controls.

## Key Business Risks

- **Macro-enabled Excel application:** `.xlsm` files present a significant security risk in a corporate environment. Excel macros can execute arbitrary code on the user's machine. If the OPTIC file is compromised (e.g., through a man-in-the-middle attack on the file download from RiskDB), malicious VBA could be distributed to all users automatically.
- **VBA code is not in source control in a reviewable format:** The `.xlsm` files are binary Office documents. Git cannot meaningfully diff VBA code inside them. This means there is no effective code review process, no diff history, and no way to detect unauthorized VBA changes through standard SDLC controls.
- **Single-server distribution mechanism:** The link file downloads the application from a specific server path. A compromised or unavailable RiskDB server would disrupt all users' access to OPTIC.
- **No visible test coverage:** VBA applications have limited unit testing capabilities; business logic errors may only surface through manual testing.
- **Gen-2 legacy tool:** The Northlane Confluence page indicates this is Gen-2 era infrastructure. Its long-term supportability under the Onbe Gen-3 platform roadmap is unclear.
