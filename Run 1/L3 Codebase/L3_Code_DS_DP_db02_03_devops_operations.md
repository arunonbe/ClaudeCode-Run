# DS_DP_db02 — DevOps & Operations Report

## Repository Structure

Like all DS_DP_db* repositories, DB02 contains **no CI/CD pipeline files**. It is a flat collection of 65+ SQL scripts with a naming convention of `YYYYMMDD_TICKET_Description.sql`. The README contains only "db02".

---

## Change Frequency and Activity Trends

DB02 has the **highest change velocity** of the six analyzed nodes:
- **2019:** 17 scripts (Oct–Dec)
- **2020:** 25 scripts (Jan–Dec)
- **2021:** 10 scripts (Jan–Jun)
- **2022:** 9 scripts (Mar–Dec)
- **2023:** 2 scripts (Feb)

The declining change rate from 2021 onward suggests the core schema stabilized post-Wirecard acquisition, with changes now primarily being data corrections and incremental feature additions (KYC, Same Day ACH).

---

## Environments

Evidence of multi-environment structure:

```
Production:   p-db02-ha.nam.wirecard.sys\db02
Dev/QA:       d-na-db02.nam.wirecard.sys\db02,2232
              q-db04.nam.wirecard.sys\db04,2232  (shared QA proxy)
Cold standby: C-DB02 (SQL Agent jobs disabled via @@SERVERNAME LIKE 'C%')
```

The HA suffix (`p-db02-ha`) confirms an Always On Availability Group or equivalent high-availability configuration for the production node. The `C-` prefix for cold standby is consistent across all DB nodes.

---

## SQL Agent Jobs

### `DBMP User Databases -- Index and stats reorg (custom)`
- **Source:** `20200212_NAMDATASVC-1880_DB02 Index and stats reorg and Integrity check jobs.sql` (note: this file name is from DB05/DB06 pattern; equivalent exists on DB02 via `20200428_NAMDATASVC-2132`)
- **Schedule:** Daily at midnight (00:30)
- **Steps:**
  1. `IndexOptimize_AgentWrapper` — fragmentation-based reorganize/rebuild
  2. Statistics update (`UPDATE STATISTICS ALL`, modified stats only)
- **Runtime windows:** 00:00–05:00 (150 min), 05:00–07:00 (until 7 AM), business hours (15 min)

### `DBMP User Databases -- Integrity Check (custom)`
- **Schedule:** Weekly Saturday at 21:00
- **Action:** `DatabaseIntegrityCheck` on ALL_DATABASES, physical-only, 9-hour time limit

### `DBMP - DBAdmin - Cleanup Audit_blocked_ip_user`
- **Source:** `20200917_WDNAMCBTS-517_003_...sql` (shared script, deployed to all nodes)
- **Schedule:** Weekly Saturday at 05:00
- **Action:** Delete blocked-IP audit records older than 90 days

### `Z_application_Prune repository file`
- **Note:** This job is specific to DB01 (Repositorysvc). DB02 may have equivalent archival jobs not yet visible in its scripts.

---

## Deployment Approach

### Script Execution Order
DB02 scripts must be applied in chronological order. Key dependencies identified:

1. Source/facility tables must be populated before transaction code scripts that reference them
2. The `kyc_tracker_status` reference table must be created before `kyc_tracker` (which FK-references it implicitly)
3. The IVR backfill sequence must run in order: `BACKFILL-001` (create staging table) → `BACKFILL-002` (process records)

**There is no enforced ordering mechanism** — this is a manual DBA responsibility.

### High-Profile Change Event: SQ-3087 IVR Backfill (June 2021)
The IVR activation backfill was a **major data migration event** processing 21.5 million records across 4 years (2018–2021). The backfill ran in 10,000-record batches with error recovery (records returned to `ivr_card_activation_stage_backfill` on failure). This type of large-batch operation requires:
- Careful coordination with the application team to avoid duplicate processing
- Monitoring of tempdb growth during execution
- Log space management (minimally-logged operations not guaranteed)

---

## TempDB Configuration
DB02 had TempDB files added in January 2020 (`NAMDATASVC-1454`):
- Production server: `modify` existing files (already had tempdb files)
- Cold-standby: `add` new tempdb files (different starting configuration)
- Evidence: `20200124_NAMDATASVC-1454_C-DB02 add tempdb files.sql` and `20200124_NAMDATASVC-1454_P-DB02 modify tempdb files.sql`

This dual-script pattern (one for C-DB02, one for P-DB02) is the only DB node to have separate environment-specific TempDB scripts, suggesting the cold-standby had a different initial TempDB configuration from production.

---

## Data Archival Strategy

DB02 uses a dedicated `EcountCore_Process_Archive` database for archiving aged process records. Evidence:
- `20200902_WDNAMCBTS-357_DB02 Add file to Ecountcore_Process_Archive database.sql` — adds a new data file to the archive database

This is more sophisticated than DB01's pattern (which uses a `_rollback` shadow). The separate `EcountCore_Process_Archive` database represents an active archival strategy for high-volume process data.

---

## Email and Alerting

```sql
-- From SQ-1114 email migration script, line 17-27
IF @@SERVERNAME LIKE '%DB06%' OR @@SERVERNAME LIKE '%DB07%'
BEGIN
    -- DB06 and DB07 also have a 'NAMDS' operator
END
```

DB02 uses `DataServicesGroup-Operator` only (not the `NAMDS` operator used on DB06/DB07). Alert notifications go to the updated `northlane.com` domain email addresses.

---

## Backup and Recovery Evidence

- **HA:** `p-db02-ha` suffix confirms Always On AG (High Availability)
- **Archive DB:** `EcountCore_Process_Archive` — separate database for aged data
- **Rollback databases:** `Repositorysvc_rollback` (shared pattern)
- **Script-level rollback:** Most DML scripts include a commented `--rollback` at the end, enabling manual reversal

---

## Operational Risk Observations

1. **No CI/CD pipeline** — 65+ manual scripts with no enforcement of ordering
2. **Largest node by change volume** — highest operational risk from manual deployments
3. **IVR backfill volume** — 21.5M records processed manually; future similar operations need automation
4. **Cross-database dependencies** — EcountCore scripts insert into tables referenced by `EcountIds` and `cf_report` (DB06), creating deployment coupling
5. **`EXEC @SQL`** dynamic SQL used in the `security_audit_device_user_data` partition migration (DB04 pattern also present) — not observed directly in DB02 but the trigger-with-EXEC AS sa pattern is shared
6. **Archival file addition** (WDNAMCBTS-357) — adding data files to archive DB without documented capacity planning
