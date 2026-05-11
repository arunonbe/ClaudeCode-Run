# DS_DP_db02 — Enterprise Architect Report

## Platform Generation and Technology Stack

| Attribute | Value |
|---|---|
| Database engine | Microsoft SQL Server (version unknown from scripts; named instance port 2232) |
| Instance name pattern | `p-db02-ha.nam.wirecard.sys\db02` |
| HA mechanism | Always On Availability Group (inferred from `-ha` suffix) |
| Storage | `FDR_DATA` named filegroup — dedicated filegroup for card data |
| Connectivity | TCP/IP, port 2232, SQLNCLI11 |
| Platform heritage | First Data Resources (FDR) — all core tables use `fdr_` prefix |

---

## DB02 in the Payments Architecture

DB02 is the **central card processing engine** in the Onbe prepaid card platform. It sits at the intersection of:
- Card issuance and account management
- Real-time debit authorization (DCAF)
- ACH/DDA payment processing
- KYC compliance
- IVR self-service card activation

```
┌────────────────────────────────────────────────────────────────┐
│                    DB02 Architecture Role                       │
│                                                                │
│   Card Issuance         EcountCore                            │
│   ─────────────►  fdr_card_account                            │
│                   fdr_card_account_detail  (CDE CORE)         │
│                   fdr_card_account_registration               │
│                                                                │
│   Auth Processing       EcountCore_Process                    │
│   ─────────────►  fdr_process_dcaf_auth_data_switch (PART.)  │
│                   fdr_process_dcaf_chd_data_switch   (PART.)  │
│                   fdr_process_debitach_file_switch   (PART.)  │
│                                                                │
│   KYC Portal     ◄─►  kyc_tracker (EcountCore)               │
│   IVR System     ◄─►  ivr_card_activation_stage              │
│   NACHA Rail     ◄─►  core_profile_dda_payment_nacha_status  │
│                                                                │
│   ──────────────────────────────────────────────────          │
│   Reporting         ──►  DB06 (cf_report)                    │
│   Data Warehouse    ──►  DB07 SSIS ──► Prepaid_Warehouse      │
│   KYC Portal        ──►  External KYC system                  │
└────────────────────────────────────────────────────────────────┘
```

---

## Dependencies

### Downstream (DB02 feeds)
- **DB06 `cf_report`** — `fdr_profile_transaction_source/facility` tables in EcountCore are referenced by DB06 reporting stored procedures (see DB06 `STARsf` report using `ecountcore_ss.dbo.*`)
- **DB07 SSIS (ETL project)** — SSIS package `ETL` on DB07 uses DB02 as a source (`CM.Ecountcore_Process.ServerName = p-db02-ha.nam.wirecard.sys\db02`)
- **Prepaid_Warehouse** — Transaction type dimension `dim_transaction_type` inserts cascade to the data warehouse (SQ-3539 script, line 180)
- **`EcountIds`** — Dimension table `dim_transaction_type` in `EcountIds` DB is updated alongside EcountCore (SQ-3539, line 151)
- **`DATAWAREHOUSEDBSERVER`** — Explicit linked server reference for warehouse inserts

### Upstream (writes to DB02)
- **Card enrollment APIs** — Write to `fdr_card_account_registration`
- **Authorization processor** (FDR/First Data) — Feeds `fdr_process_dcaf_*` tables
- **Online portal (OnePortal/OP)** — ACH withdraw orders → `fdr_dda_account_journal`
- **CSA (Customer Service Agent)** — Payment orders → journal entries
- **KYC portal** — Status updates → `kyc_tracker`
- **IVR system** (Vendor DB on DB06) — Activation events → `ivr_card_activation_stage`
- **NACHA ACH processor** — Returns → `core_profile_dda_payment_nacha_status`

---

## Cross-Instance Linked Server Dependencies

DB02 scripts reference the following remote servers:
| Server alias | Database | Context |
|---|---|---|
| `REPORTINGDBSERVER` | `Vendor` | IVR backfill reads from `Vendor.dbo.IVR_CallLog` |
| `DATAWAREHOUSEDBSERVER` | `Prepaid_Warehouse` | Transaction type dimension sync |
| DB06 via alias | `EcountIds` | Transaction type dimension sync |

These linked server dependencies mean **DB02 cannot be migrated in isolation** — all linked server endpoints must be updated simultaneously or the ETL/reporting chain breaks.

---

## FDR Platform Heritage

The `fdr_` prefix throughout EcountCore is a significant architectural marker. First Data Resources (now Fiserv) was the card authorization network provider. The `fdr_` prefix tables represent the **data model inherited from FDR's card management system**, indicating Onbe's platform was originally built on FDR's infrastructure and subsequently in-housed. This has implications:
1. The data model may follow FDR specifications that are undocumented within Onbe's own codebase
2. Any move away from FDR authorization would require schema migration, not just endpoint changes
3. FDR-format data (sys_prin_agent, BIN structure) is embedded throughout all node schemas

---

## Migration Complexity

| Factor | Assessment |
|---|---|
| Schema complexity | VERY HIGH — core CDE tables, partitioned process tables, KYC tables |
| Downstream dependencies | CRITICAL — DB06 reporting, DB07 ETL, data warehouse all depend on DB02 |
| Linked server dependencies | HIGH — `REPORTINGDBSERVER`, `DATAWAREHOUSEDBSERVER` must coordinate |
| HA migration | MEDIUM — already on Always On AG (`-ha` suffix) |
| PCI compliance during migration | CRITICAL — maintaining CDE controls during migration window |
| `cv_code` field review | BLOCKING — must be resolved before any migration/audit |
| Data volume | CRITICAL — 21.5M IVR activation records alone; full table volumes unknown but presumed hundreds of millions for core card tables |

---

## Strategic Architecture Notes

1. **DB02 is the anchor node** — all other nodes in the DS_DP cluster are either feeding DB02 (auth data), reading from DB02 (reporting), or being orchestrated through DB07 based on DB02 data.

2. **FDR model lock-in** — The `fdr_` prefix naming and `sys_prin_agent` field encoding tie the schema directly to First Data's proprietary card management data model. Modernizing the schema requires understanding FDR's field encoding specifications.

3. **EcountCore vs EcountCore_Process** — The separation of static account data (`EcountCore`) from high-velocity process data (`EcountCore_Process`) is architecturally sound — it allows different performance tuning, backup, and retention strategies for each.

4. **DCAF tables as CDE boundary** — The `fdr_process_dcaf_chd_data_switch` table represents the innermost CDE boundary. Network controls, encryption, and access auditing must be tightest around this table cluster.
