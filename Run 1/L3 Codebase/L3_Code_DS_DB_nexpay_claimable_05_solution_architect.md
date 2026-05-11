# DS_DB_nexpay_claimable — Solution Architect Report

## 1. Technical Debt Inventory

| Debt Item | Location | Severity | Remediation |
|-----------|----------|----------|-------------|
| `SELECT p.*` wildcard in claimable_payment view | `claimable_payment.sql` line 5 | **HIGH** | Replace with explicit column list |
| `SELECT *` wildcard in modality/status views | `claimable_payment_modality.sql` line 3, `claimable_payment_status.sql` line 3 | **MEDIUM** | Replace with explicit column lists |
| No SSDT project file (`.sqlproj`) | Repo root | **MEDIUM** | Create SSDT project for CI/CD integration |
| No CI/CD pipeline | Repo root | **MEDIUM** | Add GitLab CI pipeline for view validation and deployment |
| Cross-database view coupling to EcountCore | All 4 views | **MEDIUM** | Long-term: migrate to dedicated recipient domain service |
| NOLOCK on security-relevant reads | All 4 views | **LOW** | Audit NOLOCK usage for each view's use case |
| No DeltaSql migration history | Repo root | **LOW** | Low priority given no tables, but useful for change tracking |

## 2. Security Vulnerability Assessment

### 2.1 HIGH — Wildcard Column Exposure in `claimable_payment`

**Finding**: `claimable_payment.sql` line 5: `SELECT p.*`  
**Impact**: Any new column added to `EcountCore..claimable_payment` is automatically exposed to `nexpay-claim-code-svc` without review. If a PAN, routing number, or other sensitive column is added to `claimable_payment` in EcountCore, it would be immediately exposed to the microservice layer without a code review or PCI assessment.  
**Remediation**:
```sql
-- Replace: SELECT p.*, r.first_name, r.middle_name, r.last_name
-- With explicit columns:
CREATE VIEW [dbo].[claimable_payment] AS
SELECT 
    p.id,
    p.owner_id,
    p.claim_code,          -- document: payment claim token
    p.amount,              -- document: disbursement amount
    p.currency,            -- document: currency code
    p.status_id,           -- document: status reference
    p.modality_id,         -- document: selected payment modality
    p.created_at,          -- document: creation timestamp
    p.updated_at,          -- document: last update timestamp
    p.expiry_date,         -- document: claim expiry date
    r.first_name,          -- PII: recipient first name
    r.middle_name,         -- PII: recipient middle name
    r.last_name            -- PII: recipient last name
FROM EcountCore..claimable_payment p WITH (NOLOCK)
INNER JOIN EcountCore..core_member m WITH (NOLOCK) ON p.owner_id = m.id
INNER JOIN EcountCore..core_registration_basic r WITH (NOLOCK) ON m.registration_id = r.id
```
(Exact column names should be verified against EcountCore schema.)

### 2.2 MEDIUM — NOLOCK Dirty Read Risk on Payment Status

**Finding**: All views use `WITH (NOLOCK)`. For `claimable_payment`, reading a payment's status under NOLOCK could return a stale or uncommitted status value.  
**Impact**: If `nexpay-claim-code-svc` makes a payment execution decision based on a stale status value (e.g., payment status shows "PENDING" when it has actually been cancelled), this could result in a duplicate payment or erroneous execution.  
**Remediation**: For `claimable_payment` view, consider removing NOLOCK or using READ COMMITTED SNAPSHOT ISOLATION (RCSI) if EcountCore supports it. For `claimable_payment_modality` and `claimable_payment_status` (reference data), NOLOCK is acceptable.

### 2.3 LOW — No Column-Level Security

**Finding**: No column-level security (CLS) or row-level security (RLS) applied to views.  
**Impact**: The `nexpay-claim-code-svc` service account has access to all columns in all views, including all recipient PII. If additional services are granted access in the future, all PII would be exposed.  
**Remediation**: Implement SQL Server Column-Level Security on `recipient_registration` to restrict access to email/phone columns to authorised service accounts only.

## 3. All Database Objects with Purpose

### Views — Complete Catalogue

| View | File | Purpose | PII Flag |
|------|------|---------|----------|
| `claimable_payment` | `dbo/Views/claimable_payment.sql` | Payment records + recipient name for claim-code service | **HIGH — name + payment data** |
| `recipient_registration` | `dbo/Views/recipient_registration.sql` | Full recipient profile: name, emails, phones, address | **CRITICAL — full PII profile** |
| `claimable_payment_modality` | `dbo/Views/claimable_payment_modality.sql` | Payment modality reference (ACH, card, check, etc.) | No |
| `claimable_payment_status` | `dbo/Views/claimable_payment_status.sql` | Payment status reference codes | No |

## 4. View Query Pattern Analysis

### 4.1 `recipient_registration` — JOIN Performance
The `recipient_registration` view performs 7 joins (1 INNER + 1 INNER + 3 LEFT OUTER on extended_phone table aliased three times). This is a complex view for a microservice to execute on every claim request. Under high load (many concurrent claim portal sessions), this view query could become a performance bottleneck.

**Optimisation options**:
1. Ensure covering indexes on join keys in EcountCore: `core_member.registration_id`, `core_registration.registration1_id`, `core_registration.registration2_id`, `core_registration_extended_address.member_id`, `core_registration_extended_phone.member_id`
2. Consider materialising frequently-accessed recipient profiles in `nexpay-recipient-profile-svc`'s own data store (event-sourced from EcountCore changes)

### 4.2 `claimable_payment` — Index Dependency
The INNER JOIN on `owner_id = m.id` and `registration_id = r.id` must be supported by indexes in EcountCore:
- `claimable_payment.owner_id` must have an index
- `core_member.registration_id` must have an index
- `core_registration_basic.id` is presumed to be the primary key

Without these indexes, every claim lookup causes a full scan of EcountCore tables.

## 5. Remediation Priority Matrix

| Priority | Item | Owner | Effort |
|----------|------|-------|--------|
| P1 (This sprint) | Confirm claim_code token format — PCI scope assessment | Security/Architecture | 2 hours |
| P1 (This sprint) | Replace `SELECT p.*` with explicit column list | Dev | 2 hours |
| P2 (Q3) | Create SSDT `.sqlproj` for CI/CD integration | Dev/DevOps | 1 day |
| P2 (Q3) | Add CI/CD pipeline with view validation | DevOps | 2 days |
| P2 (Q3) | Remove NOLOCK from `claimable_payment` or enable RCSI on EcountCore | DBA | 1 day |
| P2 (Q3) | Replace `SELECT *` in modality/status views with explicit lists | Dev | 1 hour |
| P3 (Next cycle) | Implement column-level security on recipient_registration | DBA/Security | 1 day |
| P4 (Roadmap) | Migrate recipient data from EcountCore to nexpay-recipient-profile-svc | Architecture | 3–6 months |

## 6. Summary Risk Score

| Category | Score (1–5) |
|----------|------------|
| Schema risk | 1 — 4 views, no tables, simple |
| PII exposure | 4 — Full recipient profile in recipient_registration |
| CDE scope risk | 3 — Requires investigation of claim_code token format |
| Operational maturity | 4 — Best-documented, clean design |
| Architectural currency | 4 — Modern microservices pattern, cloud-ready target |

**Overall Risk: MEDIUM** — The primary risk is PII breadth in `recipient_registration` and the wildcard SELECT in `claimable_payment`. Remediation is straightforward given the small codebase. This is the lowest-risk database in the analysis set.
