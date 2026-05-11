# Solution Architect Report — GP-RSM-Customization

## 1. Complete Class and Method Inventory

**The repository contains no source code.** The only file present is `README.md`:

```
README.md — "East Campus Dynamics GP .NET GP Addin. Originally in Dex, converted to .NET by Crestwood"
```

No classes, methods, interfaces, or other code artifacts are available for inventory. The class/method inventory cannot be completed until source code is recovered from the production GP server (`p-na-app31`) or from the Crestwood consulting team.

---

## 2. Security Vulnerability Assessment

### VULN-001 — CRITICAL: No Source Code in Version Control

**Location**: Entire repository

**Risk**: The complete absence of source code means:
- No code review process can gate changes to report generation and distribution logic
- Any attacker with access to the GP server (`p-na-app31`) could modify the deployed `.dll` without any detection via version control diffs
- SOX ITGC Change Management controls are unenforceable — no evidence of prior changes, reviews, or approvals
- PCI DSS Requirement 6.4.4 (change management for production systems) cannot be met for this component

**Remediation**:
1. Recover the source code from `p-na-app31` (decompile if necessary using tools like ILSpy or dotPeek)
2. Request original source code from Crestwood
3. Commit to this repository under a proper branch/PR workflow
4. Establish code review requirements before future deployments

Priority: **CRITICAL — IMMEDIATE ACTION**.

---

### VULN-002 — HIGH: No CI/CD Pipeline or Automated Build

**Location**: Repository root (no `.github/workflows/`, no `.gitlab-ci.yml`)

**Risk**: Without an automated build pipeline:
- Build reproducibility cannot be verified — the deployed binary may not match any recoverable source state
- No automated security scanning (SAST) runs against this codebase
- Deployment to production is entirely manual with no approval gates
- A developer or administrator can deploy directly to `p-na-app31` without any review or testing

**Remediation**: After source code recovery, add a GitHub Actions workflow that builds the GP Add-in against a reference GP DLL set and runs any unit tests. Add a manual approval gate for production deployment. Priority: **HIGH**.

---

### VULN-003 — HIGH: GP Add-in Runtime Credential Risk

**Location**: Deployed add-in on `p-na-app31` (source unknown)

**Risk**: GP .NET Add-ins run in the context of the Dynamics GP application. Depending on how the add-in was written:
- Database connection strings may be hardcoded in the `.dll` (consistent with patterns observed in `finance-webservice_API` `Web.config` which hardcodes SQL Server connection strings)
- Email distribution credentials (SMTP server, sender account) may be embedded in the assembly
- Any credentials hardcoded in the `.dll` are not rotatable without modifying and redeploying the binary

Without source code, the extent of credential hardcoding cannot be assessed.

**Remediation**: Decompile the deployed `.dll` and inspect for hardcoded credentials. If found, move to GP Application.config or Azure Key Vault integration. Priority: **HIGH**.

---

### VULN-004 — HIGH: No Change Management Controls

**Location**: Deployment process (no documented process)

**Risk**: Financial report generation systems are in scope for SOX ITGCs:
- **CC6.1 (Change Management)**: Changes to systems that affect financial reporting must be authorized, tested, and reviewed
- Without version control and an audit trail, there is no evidence that changes to the RSM customization followed SOX-compliant change management procedures
- An audit finding on this gap could result in a SOX material weakness for Onbe's financial reporting controls

**Remediation**: Establish a documented change management process (JIRA ticket + code review + QA sign-off + Controller approval for report logic changes) before the next modification to this system. Priority: **HIGH** (SOX compliance risk).

---

### VULN-005 — HIGH: Dynamics GP End-of-Life (September 30, 2029)

**Location**: Platform dependency — Dynamics GP

**Risk**: Microsoft will end support for Dynamics GP on September 30, 2029. After this date:
- No security patches will be released for the GP platform
- PCI DSS Requirement 6.3.3 (addressing known security vulnerabilities) cannot be met on an unsupported platform
- Any vulnerability discovered in GP post-EOL will remain unpatched, creating a persistent attack surface in the CDE if GP is within scope

**Remediation**: Include `GP-RSM-Customization` and `finance-webservice_API` in the Dynamics 365 Business Central migration roadmap. Priority: **HIGH** (timeline-driven — must complete before September 2029).

---

### VULN-006 — MEDIUM: Potential PCI DSS Exposure in Report Outputs

**Location**: Report output files and email distributions (content unknown)

**Risk**: GP reports generated from sales transaction data may inadvertently include account reference data. Standard GP SOP reports can include customer account numbers, invoice numbers, and program codes that, combined, could constitute sensitive cardholder data. Without seeing the report templates, PCI DSS Requirement 3.3 (masking of account data) compliance cannot be confirmed.

**Remediation**: Audit currently active RSM report templates. Confirm no report includes full PANs, full account numbers, or sensitive authentication data. Apply masking (first 6 / last 4) if card data appears. Priority: **MEDIUM**.

---

## 3. Technical Debt Summary

| Debt Item | Severity | Effort |
|---|---|---|
| No source code in repository | CRITICAL | MEDIUM — recovery + remediation |
| No CI/CD pipeline | HIGH | LOW (after code recovery) |
| Unknown credential handling in deployed binary | HIGH | MEDIUM — decompile + audit + refactor |
| No change management process | HIGH | LOW — process documentation |
| Dynamics GP EOL (Sept 2029) | HIGH | HIGH — platform migration |
| On-premise deployment model | MEDIUM | HIGH — cloud migration |
| No automated testing | MEDIUM | MEDIUM (after code recovery) |
| Manual deployment with no rollback | MEDIUM | LOW (after CI/CD added) |
| Potential PCI exposure in reports | MEDIUM | LOW — report template audit |

---

## 4. Remediation Priority Matrix

| Priority | Action | Owner |
|---|---|---|
| P1 — IMMEDIATE | Recover source code from `p-na-app31` or Crestwood | Dev + GP Admin |
| P1 — IMMEDIATE | Decompile deployed `.dll` and audit for hardcoded credentials | Security |
| P1 — Sprint 1 | Commit recovered source to repository; establish branch protection | Dev |
| P1 — Sprint 1 | Document change management process for GP Add-in deployments | Dev + Compliance |
| P2 — Sprint 2 | Add GitHub Actions build pipeline for GP Add-in | DevOps |
| P2 — Sprint 2 | Audit RSM report templates for PCI DSS compliance | Dev + Security |
| P3 — Q3 | Evaluate Power BI / Azure-native report generation as GP RSM replacement | Architecture |
| P4 — Roadmap | Dynamics GP → Dynamics 365 Business Central migration | Platform + Finance |
