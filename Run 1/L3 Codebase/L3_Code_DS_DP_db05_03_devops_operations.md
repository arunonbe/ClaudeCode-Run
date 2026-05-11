# DS_DP_db05 — DevOps & Operations Report

## Repository Activity Summary

DB05 is the **least active** repository in the DS_DP set:

| Metric | DB05 Value | Cluster Average |
|---|---|---|
| Total SQL scripts | 7 | ~52 |
| Date span | 10 months (Feb–Dec 2020) | 26 months |
| Most recent change | December 2020 | February 2023 |
| Application DDL/DML scripts | 0 | ~45 |
| Infrastructure scripts | 7 | ~7 |

The repository has had **no changes since December 2020**. This 4+ year gap (to analysis date of May 2026) is a significant operational concern.

---

## Change History

All 7 scripts are dated within a narrow 10-month window:

| Date | Script | Type |
|---|---|---|
| 2020-02-12 | NAMDATASVC-1880 — Disable Old Jobs | SQL Agent job management |
| 2020-02-12 | NAMDATASVC-1880 — Index and stats reorg and Integrity check jobs | SQL Agent job setup |
| 2020-08-21 | WDNAMCBTS-343 — Grant temporary view definition permissions | Permission management |
| 2020-11-13 | SQ-1114 — Update SQL agent operator and dbmail account | Email domain migration |
| 2020-11-17 | SQ-306 — Update SQL agent jobs for email alerts recipients | Email recipient update |
| 2020-12-01 | SQ-1448 — Revoke temporary view definition permissions | Permission revocation |

This pattern matches a **platform-wide infrastructure rollout** (all 6 nodes received the WDNAMCBTS-343 grant, SQ-1114 email update, SQ-1448 revoke, and NAMDATASVC-1880 maintenance jobs at approximately the same time). DB05 received only these shared runbook scripts and nothing else.

---

## SQL Agent Jobs Deployed on DB05

### `DBMP User Databases -- Index and stats reorg (custom)`
- **Source:** `20200212_NAMDATASVC-1880_DB05 Index and stats reorg and Integrity check jobs.sql`
- **Steps:**
  1. `IndexOptimize_AgentWrapper` via `sqlcmd -E -S $(ESCAPE_SQUOTE(SRVR))` (CmdExec subsystem)
  2. Statistics update
- **Schedule:** Daily at 00:30
- **Enabled:** Yes (unless server name starts with `C`)

### `DBMP User Databases -- Integrity Check (custom)`
- **Source:** Same file
- **Action:** `DatabaseIntegrityCheck @Databases = 'ALL_DATABASES', @PhysicalOnly = 'Y', @TimeLimit = 32400` (9 hours)
- **Schedule:** Weekly Saturday at 21:00
- **Enabled:** Yes (unless server name starts with `C`)

### Old Jobs Disabled
`20200212_NAMDATASVC-1880_DB05 Disable Old Jobs.sql` — pre-2020 legacy maintenance jobs were disabled. This is the same pattern as DB04 (NAMDATASVC-1879) and DB06 (NAMDATASVC-1880), confirming a simultaneous platform-wide maintenance job refresh in February 2020.

---

## Email and Alerting Configuration

- **Mail account:** `NoReply@northlane.com` (updated from wirecard.com via SQ-1114)
- **Operator:** `DataServicesGroup-Operator`
- **Jobs:** Both maintenance jobs alert on failure via `@notify_level_email=2`

Note: DB05 uses only `DataServicesGroup-Operator`. Unlike DB06 and DB07, it does not have the additional `NAMDS` operator.

---

## Deployment Model Observations

1. **No application deployment pipeline** — consistent with all other DS_DP nodes
2. **Purely infrastructure scripts** — DB05's repository never received application SQL scripts (unlike DB02 with 65+ application scripts)
3. **Shared runbook pattern** — The scripts are identical copies of scripts deployed to other nodes (SQ-1114, WDNAMCBTS-343, SQ-1448 appear in DB01–DB06 with only the node name changed in script content)

---

## Backup and Recovery

Based on the maintenance jobs deployed:
- **Integrity check:** Weekly Saturday DBCC CHECKDB (physical-only)
- **Index maintenance:** Daily defragmentation/rebuild
- **Backup:** No backup scripts are in the DB05 repository. Backups are either handled by a separate backup schedule not captured here or by the HA/replication mechanism.

**Recovery concern:** With no application-level archive database (unlike DB01's `_rollback` pattern or DB02's `EcountCore_Process_Archive`), point-in-time recovery for DB05 depends entirely on SQL Server native backup/restore and HA replication.

---

## Stale Instance Risk

The **4+ year absence of changes** (December 2020 to analysis date May 2026) creates operational risks:

1. **OS/SQL Server patch gap** — If DB05 is a running production server, it has received no documented database-level changes while security patches continue to be released. This does not mean it hasn't been patched at the OS level, but there is no evidence in the repo.

2. **Unknown current state** — The actual state of DB05's databases, jobs, and configuration in May 2026 is unknown. The repo reflects the state as of December 2020.

3. **Orphaned infrastructure** — If DB05 was decommissioned but remains in the repository, it should be explicitly marked as decommissioned (like db03 which is absent from the repo entirely) to avoid confusion during incident response.

4. **Undocumented dependencies** — Other services may still reference DB05 as a backup target or read replica without any repository evidence.

---

## Operational Recommendations

1. **Confirm server status** — Verify whether DB05 is currently a running server, decommissioned, or in standby
2. **Inventory databases** — If running, execute `sys.databases` catalog query to document all databases
3. **Review job status** — Confirm SQL Agent jobs deployed in February 2020 are still running and alerting correctly
4. **Update repository** — If DB05 is decommissioned, add a `DECOMMISSIONED.md` file to the repository to document its status
5. **Add to PCI inventory** — Ensure DB05 appears (as active or decommissioned) in the PCI DSS system inventory document
