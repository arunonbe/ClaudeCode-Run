# DS_DB_GP_EAST — Solution Architect View

## 1. Repository Status Summary

`DS_DB_GP_EAST` is a **near-empty stub repository** containing only a `README.md`. No SQL source objects, SSDT project files, security scripts, or pipeline definitions are present.

This analysis covers:
- The security and technical risks arising from the **absence of source control** for this database.
- Projected risks based on the pattern established by sibling repos (ECAN, ECNT, EMEAM).

---

## 2. Security Vulnerabilities (Arising from Empty Repository)

### 2.1 CRITICAL — Schema Not Under Source Control

**Risk**: If the production EAST GP database contains custom stored procedures, views, or security grants, those objects exist in production with no audit trail in source control. This means:
- There is no way to detect unauthorised changes to the production database.
- There is no baseline against which a security audit can compare the current state.
- Recovery from a destructive event (ransomware, accidental drop, corrupt migration) requires rebuilding from scratch.

### 2.2 HIGH — Unknown Security Configuration

Based on the sibling repositories (ECAN, ECNT), GP company databases typically contain:
- SQL Authentication logins with **plaintext passwords** committed to `Security/` scripts.
- Individual user login scripts for all GP users.
- Role membership grants.

If the production EAST database has the same patterns and they are not under source control, the credential management risk is present but invisible — potentially worse than ECAN/ECNT where the credentials are at least documented (even if insecurely).

### 2.3 MEDIUM — False Coverage in Repository Register

The repository appears in `repos_actual.txt` as an active repository. Automated security scanners or audit tools may mark it as "covered" when it contains no actual schema. This creates a false sense of compliance coverage.

---

## 3. Technical Debt Register

| ID | Debt Item | Severity |
|----|-----------|----------|
| TD-1 | No SQL objects committed — production database not in source control | Critical |
| TD-2 | No SSDT project file — no repeatable build/deploy mechanism | Critical |
| TD-3 | No CI/CD pipeline | High |
| TD-4 | No security scripts — login/role state unknown | High |
| TD-5 | No ownership documentation | Medium |
| TD-6 | One-line README provides insufficient context | Low |

---

## 4. All Object Names

**None present in source control.**

---

## 5. Remediation Priority

| Priority | Item | Action |
|----------|------|--------|
| P0 | TD-1 — No objects in source control | Connect to production EAST database; extract all custom objects using SSDT Schema Compare; commit to this repo |
| P0 | TD-2 — No SSDT project | Create `.sqlproj` modelled on `ecan.sqlproj`; organise under `dbo/Functions`, `dbo/Stored Procedures`, `dbo/Tables`, `dbo/Views`, `Security/` |
| P1 | TD-3 — No CI/CD | Extend existing GP pipeline pattern (if one exists from ECAN/ECNT) to cover EAST |
| P1 | TD-4 — No security scripts | Extract and commit all logins, role memberships, and grants; apply same credential management improvements as recommended for ECAN/ECNT (Windows Auth, no plaintext passwords) |
| P2 | TD-5 — No ownership | Add CODEOWNERS file; update README with team, contact, database server, and environment details |
| P3 | TD-6 — Minimal README | Expand README to cover: purpose, deployment targets, dependencies, change management process |

---

## 6. Projected Security Findings (If Populated Per Sibling Pattern)

When the EAST database schema is extracted and committed, the following findings from the ECAN/ECNT pattern are expected to apply:

| Finding | Expected Severity |
|---------|------------------|
| Plaintext SQL Authentication passwords in Security scripts | Critical |
| `amAutoGrant`-style dynamic SQL | High |
| Individual named user login scripts | Medium |
| Broad `DYNGRP` role membership | Medium |
| No column-level encryption on financial data | Low |

These should be remediated at the same time as the source-control gap is closed, rather than committing known-vulnerable patterns from production.
