# DS_DP_db06 — DevOps & Operations Report

## Repository Structure — Unique Features

DB06 is the **only DS_DP repository containing non-SQL files**:
- `20200805-namdatasvc-2320-deploy_ps_delete_rm_subscriptions_csv.ps1` — PowerShell script
- `20200805-namdatasvc-2320_subscriptions_to_delete.csv` — CSV data file
- `20200909_wdnamcbts-490_change_subscription_owners.ps1` — PowerShell script  
- `20200909_wdnamcbts-490_subs_owner_change.txt` — Text file (subscription owner changes)

These PowerShell files interact with **SQL Server Reporting Services (SSRS)** — specifically deleting and updating report subscription ownership. This confirms DB06 hosts not just the `cf_report` database but also an SSRS instance serving compliance and finance reports to business users.

---

## Change History and Activity

DB06's change history is primarily concentrated in 2019–2021:

| Period | Scripts | Dominant Activity |
|---|---|---|
| Nov 2019 – Dec 2019 | 5 | Data cleanup, program additions |
| Jan 2020 – Mar 2020 | 10 | Schema changes, job creation, data migration |
| Apr 2020 – Sep 2020 | 8 | Program adds, NACHA mapping, permissions |
| Oct 2020 – Dec 2020 | 8 | SQ-series: tcode updates, email migration, permissions |
| Jan 2021 – Jul 2021 | 10 | NACHA Same Day ACH expansion, user sync |

No changes after July 2021 in the repository — a 4-year gap to analysis date.

---

## SQL Server Reporting Services (SSRS) Operations

### PowerShell: Delete Report Subscriptions (`NAMDATASVC-2320`)
- **File:** `20200805-namdatasvc-2320-deploy_ps_delete_rm_subscriptions_csv.ps1`
- **Data:** `20200805-namdatasvc-2320_subscriptions_to_delete.csv` — list of subscription IDs to delete
- **Operation:** Deletes specific SSRS report subscriptions via PowerShell SSRS API
- **Business context:** Mass cleanup of old report subscriptions (likely legacy wirecard.com email recipients being cleaned up during brand transition)

### PowerShell: Change Subscription Owners (`WDNAMCBTS-490`)
- **File:** `20200909_wdnamcbts-490_change_subscription_owners.ps1`
- **Data:** `20200909_wdnamcbts-490_subs_owner_change.txt` — owner change mappings
- **Operation:** Updates SSRS subscription ownership from old to new owners
- **Business context:** Subscription ownership transfer following Wirecard → NorthLane personnel changes

**SSRS Operational Significance:** DB06 appears to host or connect to an SSRS instance that distributes compliance and finance reports to business users. The subscription management operations confirm automated report delivery was in use.

---

## SQL Agent Jobs Deployed

### `Monthly Negative Balance Writeoff Preparation`
- **Source:** `20200114_NAMDATASVC-1074_DB06 Create job for Monthly Negative Balance Writeoff Prepa.sql`
- **Schedule:** Monthly
- **Purpose:** Prepares data for the monthly negative balance writeoff process (accounts that are negative and uncollectable)
- **Business function:** Credit loss management for prepaid card programs

### Index Maintenance and Integrity Check
- **Source:** `20200212_NAMDATASVC-1880_DB06 Index and stats reorg and Integrity check jobs.sql`
- **Same pattern as DB04/DB05:** Daily index maintenance + weekly integrity check
- Disabled on `C-` servers

### `STARsf` Transaction Code Export
- **Source:** `20201013_NATS-9461 P-DB07 add job schedule and ha to SSIS-DB06-Sunrise_TCodeExport.sql` (in DB07 repo)
- Job `SSIS-DB06-Sunrise_TCodeExport` runs on DB07 and reads from DB06 data
- **Schedule:** Configured on DB07 to run at COB

### `SQLAgentJobAlerts`
- Same proactive monitoring job as DB07 (30-minute interval monitoring for cancelled SQL Agent jobs)
- Not directly in DB06 repo but referenced via shared pattern

### Business User Sync Job
- **Source:** `20210609_SQ-501_create_job_sync_business_users.sql`
- **Purpose:** Calls `uspSyncBusinessUsers` to sync AD group membership to `master.BusinessUsers`
- **Schedule:** Likely periodic (daily or hourly) — exact schedule not visible in the available script

---

## Reporting Subscription Management

DB06 hosts SSRS subscriptions for:
- **EcountIds** (transaction dimensions) — referenced in DB06 reporting cross-database queries
- **Recon files** — Daily reconciliation file subscriptions
- **Exception reports** — Account management exception lists
- **STARsf monthly** — STAR network reports

Report delivery email addresses were updated from `wirecard.com` to `northlane.com` domain (`SQ-315`, November 2020) and `NorthLane` → organizational emails.

---

## Multi-Environment Deployment

Standard environment handling via `@@SERVERNAME LIKE 'C%'` pattern.

Additionally, DB06 is referenced from DB07 for:
- `CM.Vendor.ServerName = p-db06-ha.nam.wirecard.sys\db06` — SSIS package connection
- SSIS jobs referencing `SSIS-DB06-Sunrise_TCodeExport` — DB07 runs against DB06 data

This means **DB06 must be online before DB07 SSIS jobs can run** — a deployment order dependency.

---

## Change Management Notes

DB06's early scripts show good ticket discipline (NAMDATASVC-*, WDNAMCBTS-*, SQ-* all consistent). The post-2021 inactivity is similar to DB05 but less concerning since DB06's core schema (NACHA, BINBANK, IVR) was likely stable by mid-2021.

**No changes for 4 years:** Like DB05 and DB07 (which also stop around 2021), this suggests either:
1. DB06's reporting schema stabilized after Same Day ACH rollout
2. Changes are being made through alternate channels (direct DBA access not captured in Git)
3. The reporting layer migrated to a new platform not captured in these repositories

---

## Operational Risk Observations

1. **SSRS credentials in PowerShell scripts** — The PS1 files may contain SSRS service account credentials or connection strings. These should be reviewed for hardcoded secrets.
2. **`xp_logininfo` in `uspSyncBusinessUsers`** — This extended stored procedure requires the SQL Server service account to have AD read permissions. Configuration changes to the service account or AD OU structure could break user sync.
3. **`ecountcore_ss` linked server** — Reports depend on this linked server being current. Replication lag would produce stale reporting data, which could affect NACHA file accuracy.
4. **No backup scripts** — DB06's `cf_report` and `Vendor` databases have no visible backup jobs in the repository. Given NACHA file history and IVR call logs are housed here, backup coverage must be confirmed.
