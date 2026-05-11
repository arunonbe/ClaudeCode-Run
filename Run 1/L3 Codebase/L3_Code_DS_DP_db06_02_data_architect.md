# DS_DP_db06 — Data Architect Report

## Database Inventory on DB06

### `cf_report` (Compliance and Finance Reporting Database)

#### `dbo` schema tables:

| Table | Purpose | Sensitive Fields | Flag |
|---|---|---|---|
| `dbo.STARSf_Monthly` | STAR network SF (small fleet/fleet) monthly aggregates | `bin_ext` (varchar 9), `program_id` (varchar 8), `sys_prin_agent` (char 12) | `sys_prin_agent` — encoded BIN/principal/agent; `bin_ext` — extended BIN reference |
| `dbo.dim_transaction_type_12272016` | Transaction type dimension for daily recon | `source_id`, `source_name`, `facility_id`, `facility_name`, `t_code`, `transaction_group_*`, `CR/DR Flag`, `CR/DR Flag BIN Bank` | Transaction classification data — not directly sensitive but drives billing reporting |
| `dbo.t_Report_Exception_list` (inferred) | Program exception list for account management report | `program_id` — specific client programs | Program configuration data |
| `dbo.MaritimeATM_Terminal_ID` (inferred) | Maritime ATM terminal registry | Terminal IDs for vessel-based ATMs | Low sensitivity |
| `dbo.STARsf_Monthly` (loaded by SP) | Monthly STAR SF aggregate report | `accts` count, BIN data | Aggregate only — no individual cardholder data |

**`rpt_StarSF` Stored Procedure:**
- Created: `20200317_NAMDATASVC-1917_Create_STARsf_SProc_STARsf_Monthly_Table.sql`
- Accesses: `ecountcore_ss.dbo.fdr_card_account` (linked server to EcountCore secondary/snapshot)
- Accesses: `ecountcore_ss.dbo.fdr_card_account_detail`
- Accesses: `ecountcore_ss.dbo.fdr_dda_account_journal`
- Accesses: `ecountcore_ss.dbo.fdr_card_number_bins`
- **Flag:** This SP reads `fdr_card_account_detail` from a linked server (`ecountcore_ss`) — if `cv_code` is populated in that table (per VULN-01 in DB02 report), this reporting SP would access SAD (Sensitive Authentication Data) indirectly.

#### `BINBANK` schema tables:

| Table | Purpose | Sensitive Fields | Flag |
|---|---|---|---|
| `BINBANK.nacha_transaction_mapping` | Maps source_id to NACHA entries | `source_id`, ACH mapping fields | NACHA regulatory data |
| `BINBANK.nacha_bank_source` | Source config for NACHA extract | `source_id`, `enabled` flag | NACHA regulatory data |
| `BINBANK.TCode_Lookup` | Transaction code lookup for BIN Bank extract | `source_id`, `facility_id`, `t_code`, `description` | Used in cardholder statement descriptions |
| `BINBANK.[dim_transaction_type_12272016]` equivalent | Reporting dimension | Same as dbo equivalent | — |

---

### `Vendor` (IVR and Third-Party Data Database)

| Table | Purpose | Sensitive Fields | Flag |
|---|---|---|---|
| `dbo.IVR_CallLog` | All IVR call records | `id` (NUMERIC 19,0), `dda` (DDA number — 16 chars), `card_number` (full card number — see FLAG), `call_start` / `call_end` (datetime), `activation_status`, `activation_flag`, `balance_flag`, `card_type`, `pinchange_flag`, `RouterCallKey`, `trans_flag` | `dda` — account number; `card_number` — **CRITICAL FLAG: full card number field exists in IVR_CallLog** |
| `dbo.IVR_CallLog_STG` | Staging version of IVR_CallLog | Same columns | Same flags |
| `dbo.IVR_CallLog_MenuChoices` | Menu selections per IVR call | `id`, `call_id` (FK to IVR_CallLog), `order` | Low sensitivity |
| `dbo.IVR_CallLog_MenuChoices_STG` | Staging | Same | Same |
| `dbo.IVR_Fraud_Call_Log` | Fraud-flagged IVR calls | `id`, `calltime` | Fraud indicators |
| `dbo.IVR_Fraud_Call_Log_STG` | Staging | Same | — |

---

### CRITICAL FLAG: `card_number` in `Vendor.dbo.IVR_CallLog`

**Evidence:** `20210611-SQ-3087-BACKFILL-001-prepare backfill population.sql`, line 30:
```sql
, RIGHT(I.card_number, 4) AS card_number_last4
FROM REPORTINGDBSERVER.Vendor.dbo.IVR_CallLog AS I
```

The backfill script references `I.card_number` — a `card_number` column in `IVR_CallLog`. The script only uses `RIGHT(I.card_number, 4)` (last 4 digits), but the **full `card_number` column exists in the IVR_CallLog table**. 

IVR systems typically capture card numbers for authentication purposes. If this column stores full 16-digit card numbers (PAN) from IVR sessions:
- This is a **PCI DSS Requirement 3.2 violation** — PANs are being stored outside the CDE in a reporting/vendor database
- `Vendor.dbo.IVR_CallLog` would be explicitly within PCI DSS CDE scope
- Cardholder data would be present on DB06, a reporting node that may have wider access than DB02

**Immediate action required:** Confirm whether `card_number` in `IVR_CallLog` contains full PANs or only partial/masked values. If full PANs: P0 compliance violation.

---

### `ODS` (Operational Data Store — Transitional)

| Table | Purpose | Notes |
|---|---|---|
| `dbo.Billing_Audit` | Billing event audit | Migrated to `CCP` database (NAMDATASVC-1936) |
| `dbo.Billing_Detail` | Billing line items | Migrated to `CCP` database |
| `dbo.Billing_Events` | Fee type to event mapping | Migrated |
| `dbo.FVD_Deferred` | FVD (Financial Value Deposit?) deferred recognition | Migrated; financial revenue data |
| `dbo.FVD_Revenue` | FVD revenue entries | Migrated; financial revenue data |
| `dbo.package_execution` | ETL package execution log | Migrated; has trigger `TR_package_execution_U` |
| `dbo.package_execution_log` | Detailed package execution log | Migrated |

---

### `master` (Instance Administration)

| Object | Type | Source | Purpose |
|---|---|---|---|
| `dbo.uspSyncBusinessUsers` | Stored Procedure | `20210609_SQ-501_stored_proc_sync_users.sql` | AD group → SQL Server access sync using `xp_logininfo` |
| `dbo.BusinessUsers` | Table | `20210609_SQ-501_create_table_insert_groups.sql` | Business user registry (Logins) |
| `dbo.BusinessUserGroups` | Table | Same | AD group names + isLimited flag |
| `TR_check_ip_address_functional_user` | Server Trigger | Shared | IP-based logon control |
| `ValidIPAddress` | Table | Shared | IP allowlist |
| Ola Hallengren objects | Stored Procs + Tables | `MaintenanceSolution_20191201213232.sql` | Maintenance |

---

## Sensitive Data Field Summary

| Field | Table | Database | PCI/Regulatory Classification | Flag Level |
|---|---|---|---|---|
| `card_number` | `IVR_CallLog` | `Vendor` | **PAN — Full account number potential** | CRITICAL |
| `dda` | `IVR_CallLog` | `Vendor` | Account identifier | HIGH |
| `sys_prin_agent` | `STARSf_Monthly` | `cf_report` | BIN-derived program encoding | MEDIUM |
| `bin_ext` | `STARSf_Monthly` | `cf_report` | Extended BIN reference | MEDIUM |
| NACHA mapping data | `BINBANK.*` | `cf_report` | NACHA filing data | HIGH (regulatory) |
| Billing/revenue data | `ODS.*` / `CCP.*` | Multiple | Financial revenue recognition | HIGH (finance) |

---

## Linked Server and Cross-Database Architecture

DB06's `rpt_StarSF` SP uses the `ecountcore_ss` linked server alias — likely a SQL Server snapshot or secondary replica of EcountCore:

```sql
-- From rpt_StarSF SP, lines 72-80:
FROM ecountcore_ss.dbo.fdr_card_account AS a 
INNER JOIN ecountcore_ss.dbo.fdr_card_number_bins AS b ...
INNER JOIN ecountcore_ss.dbo.fdr_card_account_detail AS c ...
INNER JOIN ecountcore_ss.dbo.fdr_card_account_status AS d ...
```

The `_ss` suffix likely means "snapshot" or "secondary site" — DB06 reads from a replica of EcountCore rather than directly from DB02 (production). This is architecturally sound (reporting workloads isolated from OLTP) but the replica must receive:
1. The same PCI controls as DB02
2. Timely replication to ensure NACHA and reporting files reflect current data

---

## PCI DSS CDE Scope Assessment

DB06 is **in-scope for PCI DSS CDE** primarily because of:
1. `Vendor.dbo.IVR_CallLog.card_number` — potential PAN storage (requires immediate investigation)
2. `ecountcore_ss` linked server reads — brings DB06 into the CDE data flow
3. NACHA file generation — ACH file data constitutes financial account data regulated under Reg E

DB06 is at the **edge of the CDE** — it primarily aggregates and reports on data, but the `card_number` field in IVR_CallLog could make it a PAN storage node, which would elevate its PCI scope significantly.
