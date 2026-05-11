# DS_DB_GP_two — Solution Architect Report

## 1. Technical Debt Inventory

| Debt Item | Severity | Remediation |
|-----------|----------|-------------|
| SQL 2008 compatibility level | CRITICAL | Upgrade to SQL 2019+ (compat 150) |
| TDE not enabled | HIGH | Enable TDE |
| Undefined entity identity (README = "two") | HIGH | Document entity name, active/historical status |
| No CI/CD pipeline committed | HIGH | Add pipeline YAML / Jenkinsfile |
| No change tracking / CDC | HIGH | Enable CDC on PII tables |
| ANSI_NULLS / QuotedIdentifier disabled | MEDIUM | Enable after regression testing |
| No DeltaSql migration folder | MEDIUM | Implement per-ticket migration scripts |
| 250 custom views on GP tables | MEDIUM | Audit and migrate to BI layer |
| ReadCommittedSnapshot disabled | MEDIUM | Enable RCSI |
| VardecimalStorageFormatOn | LOW | Disable; use row compression |

## 2. Security Vulnerability Assessment

### 2.1 HIGH — TDE Not Enabled
Same finding as GP_EMXN. Employee SSNs (`UPR00100.SOCSCNUM`), dates of birth, and vendor tax IDs stored unencrypted at rest. Enable TDE immediately.

### 2.2 HIGH — No CDC or Audit Trail
`IsChangeTrackingOn=False`. No record of data access or modification on PII tables. Enable SQL Server Audit targeting `UPR00100`, `PM00200`, `RM00101`, `SY01200` (email).

### 2.3 HIGH — Entity Identity Unknown
**Critical governance finding**: The entity this database represents is not documented anywhere in the repository. Without knowing whether GP_two is an active, dormant, or legacy entity:
- Retention policies cannot be correctly applied
- Regulatory jurisdiction cannot be confirmed
- Data subject rights requests cannot be properly scoped
- The team responsible for this database cannot be identified

**Remediation**: Query the GP system table `SY01500` (Company Setup) against the live database to retrieve the company name, and commit this information to the README.

### 2.4 MEDIUM — Custom Views on Vendor-Owned Tables
250 views built on top of GP's vendor-owned schema. GP upgrades or patches that modify underlying table structures may silently break views. There is no automated view validation in the pipeline.

**Remediation**: Add a post-deployment view validation step to the CI pipeline. Long-term: migrate reporting views to a warehouse layer.

## 3. All Database Objects — Key Objects with Purpose

### Tables (1,015 total)

Same GP module structure as GP_EMXN. Key sensitive tables:

| Table | Purpose | PII Flag |
|-------|---------|----------|
| `UPR00100` | Employee master (SSN, DOB, demographics) | **CRITICAL** |
| `PM00200` | Vendor master (Tax ID, phone, address) | **HIGH** |
| `RM00101` | Customer master (phone, address) | **MEDIUM** |
| `SY01200` | Internet/email for all master records | **HIGH (email)** |
| `GL20000` | Posted GL transactions | Financial |
| `UPR10100` | Payroll transactions | Financial/PII |
| `SOP10100` | Sales order headers | Financial |
| `POP10100` | Purchase order headers | Financial |

### Views (250 total — by category)

| Category | Count (approx) | Notes |
|----------|---------------|-------|
| Standard GP system views | ~143 | Same as GP_EMXN |
| Custom Onbe views | ~107 | Additional reporting views unique to GP_two |

The 107 additional custom views represent bespoke reporting logic. These views must be:
1. Documented with business purpose
2. Reviewed for PII data exposure
3. Assessed for GP upgrade fragility

Critical PII-exposing views (same as EMXN):
- `Employees`, `EmployeeSummary` — Employee PII
- `PayrollTransactions`, `PayrollCheckAndDistributionHistory` — Payroll data
- `Customers`, `CustomerAddress` — Customer PII
- `Vendors`, `VendorAddress` — Vendor data

### Stored Procedures (15,923 total — by category)

| Category | Count (approx) | Purpose |
|----------|---------------|---------|
| `zDP_*` auto-generated | ~11,500 | GP CRUD data providers |
| eConnect API (`taCreate*`) | ~500 | Transaction API |
| Analytical Accounting (`aag*`) | ~200 | Cost allocation |
| Cash Management (`cm*`) | ~150 | Bank reconciliation |
| Custom Onbe procedures | ~50 | Non-standard GP additions |
| Other GP built-in | ~3,523 | Various GP module SPs |

### Functions (193 total)

All `DYN_FUNC_*` — identical to GP_EMXN. Read-only GP decode functions. No PII exposure risk.

## 4. Remediation Priority Matrix

| Priority | Item | Owner | Effort |
|----------|------|-------|--------|
| P1 (Immediate) | Enable TDE | DBA/Security | 1 day + testing |
| P1 (Immediate) | Document entity identity (query SY01500) | Finance/DBA | 1 hour |
| P1 (Immediate) | Enable SQL Server Audit on PII tables | DBA | 2 days |
| P2 (Q3) | SQL Server compat upgrade (100 → 150) | DBA + GP team | 4–6 weeks |
| P2 (Q3) | Enable RCSI | DBA | 1 day |
| P2 (Q3) | Audit and document 250 custom views | Dev/Architect | 3 weeks |
| P3 (Next cycle) | Migrate custom reporting views to warehouse | Dev/BI | 2–3 months |
| P3 (Next cycle) | Implement CI/CD pipeline | DevOps | 2 weeks |
| P3 (Next cycle) | Enable CDC on PII tables | DBA | 1 week |
| P4 (Roadmap) | Enable ANSI settings with regression testing | Dev | 6+ months |
| P4 (Roadmap) | Assess GP upgrade to D365 Business Central | Architecture | 3 months planning |

## 5. Comparison with GP_EMXN — Action Delta

GP_two is already ahead of GP_EMXN on security governance (no individual named logins). The additional actions specific to GP_two are:
1. **Entity identity documentation** — unique to GP_two
2. **250-view audit** — larger scope than EMXN's 143 views
3. **Confirm FortiDB coverage** — not evidenced in GP_two security (unlike EMXN)

## 6. Summary Risk Score

| Category | Score (1–5) |
|----------|------------|
| Data sensitivity | 5 — SSN, DOB, tax IDs |
| Security posture | 3 — Better than EMXN (no named logins), but TDE off, no audit |
| Operational maturity | 2 — No CI/CD, no migration scripts |
| Entity governance | 1 — Entity identity undocumented |
| Architectural currency | 1 — SQL 2008 compat, GP legacy stack |

**Overall Risk: HIGH** — Entity identity must be resolved, and TDE enabled, before next compliance review.
