# DS_DP_db04 — DevOps & Operations Report

## Repository Activity Summary

DB04 is the **highest-volume repository** in the DS_DP set with approximately 130 SQL scripts covering October 2019 to May 2023. The change rate reveals two distinct operational phases:

| Period | Approximate Script Count | Dominant Activity |
|---|---|---|
| Oct 2019 – Dec 2020 | ~30 scripts | Core schema, security, permissions, infrastructure |
| Jan 2021 – May 2023 | ~100 scripts | Content management (xcontent skins, copy tags, notifications) |

The post-2021 shift to content-heavy changes reflects DB04's role as the portal content management node — a near-continuous stream of client onboarding and content update activities.

---

## Deployment Patterns

### xcontent Skin Deployments
The xcontent skin scripts follow a naming convention indicating a separate versioning track:
```
YYYYMMDD_xcontent{version}_DB04_cbaseapp_Create_skin.sql
```
or
```
YYYYMMDD_xcontent_{version}_{suffix}_DB04_cbaseapp_createskin_cbaseapp.sql
```

These scripts are deployed when a new xcontent version is released. The high frequency (30+ skin deployments over 2 years) suggests these are **automated or near-automated** content release deployments — yet they appear as individual SQL scripts in the repo rather than in a pipeline.

**Anomaly:** Multiple scripts with the same xcontent version number on different dates (e.g., `xcontent1.0.24` appears on 2022-01-08, 2022-06-09, 2022-06-23, 2022-07-06). This suggests:
1. Skin scripts were being re-applied due to errors or re-deployments
2. Different program skins were deployed under the same xcontent version
3. Deployment tracking was insufficient

### Copy Tag Deployments
Copy tag scripts are ticket-driven, with each business request generating 1–5 SQL files. The deployment cadence accelerated in 2022–2023 for T-Mobile, Zoetis, and automotive luxury programs.

---

## Index Maintenance Jobs

### `DBMP User Databases -- Index and stats reorg (custom)` (and Integrity Check)
- **Source:** `20200212_NAMDATASVC-1879_DB04 Index and stats reorg and Integrity check jobs.sql`
- **Steps:** Uses `IndexOptimize_AgentWrapper` procedure (from `IndexOptimize_AgentWrapper.sql` — Ola Hallengren-based)
- **Schedule:** Daily midnight (Index reorg), Weekly Saturday evening (Integrity check)
- **Disabled on:** `C-` prefix servers (cold standby)
- **Source of `MaintenanceSolution_20191201213232.sql`:** Ola Hallengren's complete SQL Server maintenance solution, deployed in December 2019. This is the base for all index/backup maintenance across the DS_DP nodes.

### Old Jobs Disabled
`20200212_NAMDATASVC-1879_DB04 Disable Old Jobs.sql` — legacy jobs from pre-NAMDATASVC-1879 era were disabled. This cleanup indicates a maintenance tooling refresh in early 2020 that was applied to DB04, DB05, and DB06 simultaneously.

---

## Environment Configuration

```
Production server: P-DB04 (inferred)
QA proxy role:     q-db04.nam.wirecard.sys\db04,2232 (confirmed via DB07 SSIS Finance project config)
Cold standby:      C-DB04 (jobs disabled via @@SERVERNAME LIKE 'C%')
```

DB04's dual role as QA proxy for DB02 workloads means **QA deployments to DB04 must not conflict with production content operations**. This creates an operational segregation concern — the same SQL Server instance serves both QA card processing tests and production portal content.

---

## Change Management by Ticket System

| Ticket prefix | Count | Era |
|---|---|---|
| NATS-XXXXX | 5 | 2019 |
| NAMDATASVC-XXXX | 7 | 2019–2020 |
| WDNAMCBTS-XXX | 5 | 2020 |
| SQ-XXXX | 20 | 2020–2022 |
| Unnamed / date-only | ~100 | 2021–2023 |

The 2022–2023 scripts lack consistent ticket references, suggesting a **looser change management process** for content changes compared to the earlier infrastructure changes. This is a concern for PCI DSS Requirement 6.5 (change management) which requires all changes to be tracked.

---

## Backup and Recovery

- **Always On / Mirroring:** DB04 participates in the `-ha` pattern (inferred from cluster)
- **Archive files:** No separate archive database observed for `cbaseapp` (unlike DB02's `EcountCore_Process_Archive`)
- **Skin/copy tag versioning:** The Git repository itself functions as a change history, but individual SQL script changes (UPDATE statements) have no rollback unless a reverse script is created

**Critical gap:** For content changes (copy tag updates, skin creation), no rollback scripts are provided. If a copy tag update is deployed incorrectly to production, it must be manually identified and corrected.

---

## Operational Observations

1. **High noise, low structure** — The 2022–2023 content scripts lack consistent ticket references and some have unusual date formats (e.g., `20232009_` = YYYYDDMM format, which is incorrect). This creates a **date sorting anomaly**.

2. **Date format anomaly** — Several 2023 scripts use `YYYYDDMM` instead of `YYYYMMDD`:
   - `20231505_xcontent_1.0.35_DB04_createskin_cbaseapp.sql` — date `20231505` is invalid (month 15)
   - `20231610_DB04_createskin_cbaseapp.sql` — date `20231610` (month 16)
   - `20232009_DB04_...` — date `20232009` (month 20)
   - `20232108_DB04_...` — date `20232108` (month 21)
   - `20232407_DB04_...` — date `20232407` (month 24)
   These appear to be `YYYYDDMM` format errors (day and month swapped). This indicates **date prefix discipline broke down** in the 2023 content deployment phase.

3. **No automated skin deployment pipeline** — 30+ xcontent releases as individual SQL scripts in 2 years suggests a mature content release process that could benefit significantly from automation.

4. **`PS_TECHAPI` user** — `20210423-NATS-11158_Create_PS_TECHAPI_user_permissions.sql` creates a new technical API user in DB04. The nature and permissions of this user should be reviewed for least-privilege compliance.
