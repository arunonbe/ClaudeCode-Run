# DS_DB_GP_EAST — Business Analyst View

## 1. Repository Identity

| Attribute | Value |
|-----------|-------|
| Repo name | DS_DB_GP_EAST |
| README content | "DYNAMICS GP ONLY - Houses a Collection of Modified Stored Procedures, Views (ECAN, ECNT, etc.)" |
| SQL project file | None found |
| SQL source files | None found (repository contains only `.git` folder and `README.md`) |
| Active branch | `main` |
| Git pack objects | Two pack files — a tiny pack (147 bytes content) and a small pack (869 bytes content), indicating extremely limited committed content |

---

## 2. Repository Status: SKELETON / NEAR-EMPTY

**This repository is effectively empty from a source-code perspective.** The only substantive file is the `README.md`. No SQL scripts, stored procedures, DDL, views, SSDT project files, or configuration files are present.

The README describes the intended purpose: to house a collection of **modified stored procedures and views** for Dynamics GP, specifically for the "EAST" regional variant affecting the ECAN, ECNT, and related company databases. However, these objects have either:
1. **Not yet been committed** to this repository (content may exist only on the database server), or
2. **Been committed and removed** at some point (the git pack structure suggests very minimal historical commits), or
3. **Intentionally deferred** — the repository was created as a placeholder for content that resides in the regional GP company repos (DS_DB_GP_ecan, DS_DB_GP_ecnt) directly.

---

## 3. Intended Business Purpose (Per README)

Based on the README description and the context of the GP multi-company architecture, `DS_DB_GP_EAST` is intended to hold:

- **Modified GP Stored Procedures** — customisations to standard Microsoft Dynamics GP stored procedures specific to the East region of Onbe's operations. These may include:
  - Regional budget management procedures
  - East-region-specific financial reconciliation queries
  - Banker SVC integration procedures tailored for EAST company data
  - Payroll or AR/AP procedures adjusted for East-region business rules

- **Modified GP Views** — custom views that aggregate or reshape GP data for East-region reporting, potentially cross-referencing ECAN and ECNT company data.

The "East" designation in Onbe's architecture typically refers to the broader US East operations as distinct from the Canada (ECAN), Central (ECNT), and EMEA (EMEAM) regions.

---

## 4. Regulatory Relevance (If Populated Per Intent)

If the repository were populated as described, it would be relevant to:

| Regulation | Relevance |
|------------|-----------|
| **SOX** | Any modified GP stored procedures affecting financial posting, AP/AR, or GL would be in-scope for SOX IT change management controls. |
| **PCI DSS** | Modified procedures accessing payment-related financial data (cardholder program invoices, Banker payments) would be connected-system scope. |
| **GLBA** | Any access to payroll or customer financial data would be GLBA-scoped. |

---

## 5. Data Flows (Projected)

If populated, DS_DB_GP_EAST would contain objects that execute within the GP company database (EAST company context) and would:
- Read from standard GP tables (GL, SOP, RM, POP series) in the EAST company database.
- Potentially expose views consumed by the Banker SVC or Finance WebService for the East region.
- Cross-reference ECAN and ECNT data (as suggested by the README reference to both).

---

## 6. Remediation / Action Required

1. **Determine whether custom procedures and views for the EAST region exist** in production but are not committed to source control. If so, extract and commit them using SSDT schema comparison.
2. **Clarify the intended scope** — if EAST-region customisations are already covered by the ECAN and ECNT repos, document this decision and either close this repo or populate it with a clear scope definition.
3. **Do not leave a registered repository empty** without documenting the rationale, as it creates confusion during incident response and audit reviews.
