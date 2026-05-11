# DS_DP_db05 — Solution Architect Report

## Critical Issues

### ISSUE-01: Unknown Server Status — PCI DSS System Inventory Gap
- **Severity:** HIGH
- **PCI DSS Requirement:** 2.1 — All system components in scope must be identified and inventoried
- **Evidence:** Repository contains only 7 infrastructure scripts from 2020 with no application content, no schema documentation, and no change activity in 4+ years
- **Risk:** If DB05 is an active production server handling cardholder data with no documented schema or change management, it is a ghost system in the CDE — creating both security and audit risk. PCI QSA auditors will request system inventory documentation for all CDE nodes.
- **Remediation:** Execute immediate server status check; add to system inventory regardless of status (active, standby, or decommissioned)
- **Priority:** P1 — Compliance

### ISSUE-02: No Evidence of Application Data Handling
- **Severity:** MEDIUM (information gap, not confirmed vulnerability)
- **Evidence:** Zero application DDL/DML scripts in repository
- **Risk:** The absence of evidence is not evidence of absence. Unknown databases may contain cardholder data.
- **Remediation:** Full database catalog discovery on live server
- **Priority:** P1

### ISSUE-03: Maintenance Jobs May Be Stale
- **Severity:** MEDIUM
- **Evidence:** Maintenance jobs deployed February 2020; no evidence of updates or verification since then
- **Risk:** Ola Hallengren maintenance solution versions have evolved; the December 2019 version deployed on DB05 may miss improvements and bug fixes
- **Remediation:** Update Ola Hallengren solution to current version; verify jobs are still executing successfully
- **Priority:** P2

---

## Technical Debt Inventory

### TD-01: 4+ Year Change Silence
- No documented changes since December 2020
- Either the server is inactive (decommissioned) or changes are being made outside the Git repository
- Both scenarios represent technical debt: untracked changes are a PCI Req 6.5 violation
- Priority: P1

### TD-02: Same as Cluster-Wide Issues
The following technical debts are shared across all DS_DP nodes and apply to DB05:
- SQL Agent jobs owned by `sa` (instead of a service account) — P1
- IP-based trigger with `EXECUTE AS 'sa'` — P1
- No CI/CD pipeline — P1
- Inconsistent file naming dates — P3

---

## Object Inventory

### All Confirmed Objects (Complete for DB05)

#### `master` Database
| Object | Type | Source | Purpose |
|---|---|---|---|
| `IndexOptimize_AgentWrapper` | Stored Procedure | `IndexOptimize_AgentWrapper.sql` | Time-aware index maintenance (Ola Hallengren wrapper) |
| `DatabaseBackup` | Stored Procedure | `MaintenanceSolution_20191201213232.sql` | Backup orchestration |
| `DatabaseIntegrityCheck` | Stored Procedure | Same | Integrity check orchestration |
| `IndexOptimize` | Stored Procedure | Same | Index reorganize/rebuild |
| `CommandExecute` | Stored Procedure | Same | Command execution helper |
| `CommandLog` | Table | Same | Maintenance execution log |
| `TR_check_ip_address_functional_user` | Server Trigger | Implied (shared runbook) | IP-based logon control |
| `ValidIPAddress` | Table (existing) | Implied | IP allowlist |
| `usernames_functional_accounts` | Table (existing) | Implied | Functional account registry |

#### `msdb` Database
| Object | Type | Source | Purpose |
|---|---|---|---|
| `DBMP User Databases -- Index and stats reorg (custom)` | SQL Agent Job | `NAMDATASVC-1880` scripts | Daily index maintenance |
| `DBMP User Databases -- Integrity Check (custom)` | SQL Agent Job | Same | Weekly integrity check |
| Multiple disabled legacy jobs | SQL Agent Jobs | `NAMDATASVC-1880 Disable Old Jobs` | Disabled pre-2020 maintenance jobs |

#### Application databases — **UNKNOWN / NOT DOCUMENTED**

---

## Schema Consistency Comparison

DB05 is unique among the six nodes in having **no confirmed application schema**. This places it in a separate tier:

```
Tier 1 (Full application schema documented):
  DB02 — EcountCore (card processing)
  DB04 — cbaseapp (portal content)
  DB06 — cf_report, Vendor (reporting)
  DB07 — SSISDB (ETL orchestration)

Tier 2 (Partial application schema):
  DB01 — Repositorysvc, Ordersvc, Jobsvc (service databases)

Tier 3 (Infrastructure only, application unknown):
  DB05 — No confirmed application schema
```

---

## Remediation Priority Matrix

| Priority | Item | Effort | Impact |
|---|---|---|---|
| P1 | Confirm server status (running/decommissioned) | LOW | PCI compliance |
| P1 | Execute database catalog discovery if running | LOW | PCI inventory |
| P1 | Add DB05 to PCI DSS system inventory | LOW | Audit readiness |
| P2 | Update Ola Hallengren maintenance solution | LOW | Operational health |
| P2 | Verify SQL Agent job execution status | LOW | Operational |
| P3 | Formally document decommission if inactive | LOW | Documentation |

---

## Summary

DB05 represents the most significant **documentation and governance gap** in the DS_DP cluster. While technically it may be the simplest node (possibly decommissioned), the compliance risk of an **undocumented system in a PCI DSS Level 1 environment** cannot be understated. A QSA examiner encountering DB05 with no documentation would flag it as a finding. The recommended action is a 30-minute server status check and database catalog discovery to either document and scope it, or formally close the repository as decommissioned.
