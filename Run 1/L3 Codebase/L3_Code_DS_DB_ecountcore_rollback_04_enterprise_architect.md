# Enterprise Architect Report — DS_DB_ecountcore_rollback

## 1. Platform Generation Classification

**Generation: Gen-1 (eCount / Citi Legacy) — Archive, Rollback, and Compliance Database**

Evidence:
- **Historical snapshots from 2002**: Tables named `affiliate_2201_balance_off_jwu_20020830`, `fdr_process_nacha_file_jwu_20020419` — these are earliest-era eCount records, predating the Citi formal integration
- **DBA naming conventions**: Tables named `*_jwu_YYYYMMDD` (JWu = DBA name) confirm Gen-1 era manual DBA snapshot practices
- **Mellon Bank references**: `mellon_process_check_file_rollback_20041201` — Mellon Bank (now PNC) was an early banking partner; these records are from the 2004-era platform
- **Citi-era data**: Tables like `citi_profile_network_atms_backup`, `PUID UPDATE`, `Qwest PUID Update-20030327` — Qwest and PUID (Physical Unique Identifier) are Citi-era constructs
- **SQL Server 2016 target (Sql130)**: The SSDT project targets SQL 2016, indicating the operational procedures were updated/maintained into the Wirecard/Northlane era while the underlying data remains Gen-1
- **`archive_fdaj_commit_this` authored 2020** (Van Nguyen, 2020-02-11): The active archive management layer was written in 2020 — confirming ongoing maintenance into the Onbe period
- **`monitor_autoach_failure` authored 2004** (JWu): Monitoring procedures originated in the Gen-1 period
- **GENTRAN schema**: IBM Sterling Gentran EDI is a Gen-1 era integration technology; presence of `GENTRAN.app_process_activation_extract` confirms Gen-1 EDI integration heritage

**Classification**: This is a Gen-1 database that has been **actively maintained into the Onbe era** (2020+ procedures) without architectural migration. It is a unique hybrid — the data is from 2002-2013, but the operational procedures serving live business functions (archive management, escheatment, monitoring) are current.

---

## 2. Business Domain

**Domain**: Data Governance / Platform Operations / Compliance

`Ecountcore_rollback` serves multiple concurrent business functions that are difficult to separate:

1. **Archive management service** — live component managing the lifecycle of `ecountcore.fdr_dda_account_journal` (FDAJ) records
2. **Compliance service** — escheatment eligibility determination for state unclaimed property filings
3. **Operations monitoring** — ACH failure detection, card creation monitoring, settlement verification
4. **Historical research workspace** — 2002-2013 snapshots available for regulatory investigations and data reconstructions

---

## 3. Role in the Enterprise Architecture

```
ecountcore (Gen-1 core)
  fdr_dda_account_journal (primary transaction table)
        │
        │  archive_fdaj_commit_this (FDAJ lifecycle management)
        ▼
Ecountcore_rollback (THIS DATABASE)
  ├── fdr_dda_account_journal_archive (archived FDAJ records)
  ├── archive_ctrl_fdaj (archive control state)
  ├── Historical rollback tables (2002-2013 snapshots)
  ├── Escheatment functions (cross-call to ecountcore)
  ├── Monitoring SPs (cross-call to ecountcore)
  └── GENTRAN EDI integration
        │
        ├── SQL Agent jobs (scheduled monitoring + archival)
        ├── State regulators (escheatment NAUPA filings — via cf_report)
        └── Operations team (monitoring alerts)
```

**Critical coupling**: `archive_fdaj_commit_this` directly modifies `ecountcore.dbo.fdr_dda_account_journal` — disabling its update trigger to delete records. This means `Ecountcore_rollback` has **write access to the primary transaction table of the core payments platform**. This is an unusually tight coupling between an archive database and the core platform.

---

## 4. Dependencies

### Upstream
| Dependency | Type | Coupling |
|---|---|---|
| `ecountcore` | Direct cross-DB call + DDL | **Critical** — archive procedures read and delete from `ecountcore.fdr_dda_account_journal`; escheatment functions call `ecountcore.dbo.app_func_*` |
| SQL Agent (job scheduler) | Infrastructure | Monitoring and archival procedures are called from SQL Agent jobs |

### Downstream
| Dependency | Type | Notes |
|---|---|---|
| State regulators (unclaimed property offices) | Compliance output | Escheatment functions support NAUPA filing preparation (via cf_report) |
| Operations team | Internal | Monitoring procedures generate operational alerts |
| DBA team | Internal | Historical rollback tables used for incident response |

---

## 5. Integration Patterns

| Pattern | Implementation |
|---|---|
| Cross-database function calls | `ecountcore.dbo.app_func_*` functions called directly from rollback DB functions |
| Cross-database DDL | `archive_fdaj_commit_this` disables/enables ecountcore triggers |
| Batch archival with commit checkpointing | Transactions committed per batch to avoid table locks; control state persisted in `archive_ctrl_fdaj` |
| Table-type parameters | `archive_fdaj_commit_this(@DDA_Table AS ArchiveDDATableType READONLY)` — uses SQL Server table-valued parameters for DDA list passing |
| Trigger-aware delete | Archive procedure explicitly disables the historical-adjustment-blocking trigger before batch deletes — tight awareness of ecountcore trigger architecture |

---

## 6. Strategic Status

**Status: Active Gen-1 Component — Cannot Be Decommissioned Without ecountcore Migration**

`Ecountcore_rollback` cannot be decommissioned in isolation because:

1. **FDAJ archival is a live operational requirement**: `ecountcore.fdr_dda_account_journal` grows continuously. Without the archival procedures in this database, FDAJ will grow indefinitely, creating a storage and performance risk.

2. **Escheatment compliance is active**: State unclaimed property reporting (30+ US states) depends on the escheatment functions in this database.

3. **Monitoring procedures are operational**: ACH failure monitoring and settlement verification procedures run on scheduled intervals.

4. **Historical data is potentially required for regulatory investigations**: 20 years of ACH/NACHA records may be subject to regulatory hold or e-discovery requests.

---

## 7. Migration Complexity and Blockers

**Complexity: VERY HIGH**

| Factor | Assessment |
|---|---|
| Cross-database DDL coupling | Archive procedures disable triggers in ecountcore — cannot be migrated without simultaneous ecountcore migration |
| Active compliance service | Escheatment functions must remain available during any migration; downtime is not acceptable during escheatment processing periods (typically September-November annually) |
| 200+ table deployment | Historical tables in SSDT project bloat DACPAC and create deployment complexity |
| PCI compliance blockers | `allfreedomcard` plaintext PAN and CVV parameter storage must be remediated before migration |
| Historical data disposition | 2002-2013 data must be classified as: (a) required for regulatory hold, (b) subject to CCPA/right-to-erasure, or (c) safe to purge — before migration |
| GENTRAN EDI | IBM Sterling Gentran is a legacy EDI platform; migration requires EDI platform modernisation as a parallel workstream |

**Migration blockers:**
1. `allfreedomcard` PAN table must be assessed, data purged, and table removed before any cloud migration
2. CVV storage in `fdr_card_account_detail` (via `fdr_card_account_create`) must be remediated
3. FDAJ archival must be redesigned in the Gen-3 architecture before ecountcore can be migrated
4. Historical data (2002-2013) disposition must be formally documented and approved by Legal/Compliance before deletion
5. Escheatment compliance functions must be replicated in Gen-3 before the rollback DB can be decommissioned
