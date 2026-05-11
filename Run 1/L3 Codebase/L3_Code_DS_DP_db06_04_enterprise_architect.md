# DS_DP_db06 — Enterprise Architect Report

## Platform Generation and Technology Stack

| Attribute | Value |
|---|---|
| Database engine | Microsoft SQL Server (named instance, port 2232, HA suffix) |
| Instance name | `p-db06-ha.nam.wirecard.sys\db06` |
| HA mechanism | Always On AG (`-ha` suffix) |
| Reporting platform | SQL Server Reporting Services (SSRS) — confirmed from PowerShell subscription management |
| ETL consumer | DB07 SSIS packages read from DB06 (Vendor, cf_report) |
| Linked server to | `ecountcore_ss` — EcountCore secondary/snapshot on DB02 |
| Linked server from | `DATAWAREHOUSEDBSERVER` — data warehouse inserts to DB06 via transaction code scripts |

---

## DB06 Architecture Role

DB06 occupies the **reporting and compliance layer** of the DS_DP platform:

```
┌──────────────────────────────────────────────────────────────────┐
│                    DB06 Architecture Role                         │
│                                                                   │
│  DB02 EcountCore ──► ecountcore_ss ──► cf_report.rpt_StarSF     │
│  (via linked server)                   (STAR network reports)    │
│                                                                   │
│  IVR System ──► Vendor.IVR_CallLog   (call logs + fraud)        │
│                                                                   │
│  ACH Processor ──► cf_report.BINBANK.nacha_* (NACHA mappings)   │
│                        ──► NACHA file extract (via DB07 SSIS)   │
│                                                                   │
│  ETL (DB07)    ──► cf_report (reads STARsf data, EschatData)   │
│                                                                   │
│  SSRS           ──► Business users (compliance, finance reports) │
│                                                                   │
│  AD (Active Directory) ──► BusinessUsers (SQL access control)   │
└──────────────────────────────────────────────────────────────────┘
```

---

## Dependencies

### Upstream (feeds DB06)
- **DB02 (EcountCore)** — Via `ecountcore_ss` snapshot/replica — card account and journal data
- **IVR platform** — Direct writes to `Vendor.IVR_CallLog`
- **NACHA processor / ACH network** — ACH settlement data drives NACHA mapping table updates
- **CCP system** — Billing data (formerly in ODS, now in CCP)
- **BINBANK team** — Direct updates to BINBANK transaction codes and NACHA mappings

### Downstream (DB06 feeds)
- **DB07 SSIS** — ETL packages read from DB06 (`CM.Vendor.ServerName`, `SSIS-DB06-Sunrise_TCodeExport`)
- **SSRS report subscriptions** — Automated distribution to business users
- **External NACHA file recipients** — Financial institution ACH files generated from DB06 mappings
- **Data warehouse** — Transaction type dimensions syndicated from DB06/DB02

### Cross-References with Other Nodes
| From | To | Data |
|---|---|---|
| DB06 `cf_report.BINBANK.TCode_Lookup` | DB02 `EcountCore` | Same script updates both (SQ-3539) |
| DB06 `cf_report.dim_transaction_type_12272016` | DB02 `EcountIds` | Transaction dimensions synchronized |
| DB06 `Vendor.IVR_CallLog` | DB02 `EcountCore_Process.ivr_card_activation_stage` | Activation backfill data flow |
| DB07 SSIS | DB06 `Vendor.IVR_CallLog` | ETL reads IVR call log |

---

## NACHA File Generation Architecture

DB06 is the **NACHA file orchestration hub**:

```
Card Account Data (DB02) ──► ecountcore_ss ──►
  cf_report.BINBANK.nacha_transaction_mapping ──►
    NACHA File Extract (SSIS on DB07) ──►
      Financial Institution (ACH receiver)
```

The mapping between transaction source codes and NACHA entries is managed in `cf_report.BINBANK`. When new transaction types are added (e.g., Same Day ACH in May 2021), both:
1. `EcountCore.fdr_profile_transaction_source` on DB02 (source definition)
2. `cf_report.BINBANK.nacha_transaction_mapping` on DB06 (ACH mapping)

...must be updated in the same deployment window. This **cross-node deployment coupling** is a significant operational risk — a partial deployment (DB02 without DB06 or vice versa) would produce incorrect NACHA files.

---

## Maritime ATM Specialty Architecture

DB06's role in Maritime ATM processing is architecturally notable:
- Terminal IDs for ship-based ATMs are maintained on DB06
- Cardtronics ATM files are processed through DB07 SSIS (`SSIS-DB06-MaritimeATM_DeviceDetail`, `SSIS-DB06-MaritimeATM_Partial*`)
- Exception reporting for maritime ATM programs feeds into `t_Report_Exception_list`

This suggests DB06 manages **niche card acceptance channels** (maritime, ATM networks) that require specialized transaction mapping not present on the core DB02 processing node.

---

## Migration Complexity

| Factor | Assessment |
|---|---|
| Schema complexity | MEDIUM-HIGH — multiple databases (`cf_report`, `Vendor`, `ODS`, `EcountIds`) with complex interdependencies |
| SSRS dependency | HIGH — SSRS subscriptions must be migrated alongside database |
| Linked server to ecountcore_ss | HIGH — replica/snapshot relationship must be maintained |
| DB07 SSIS dependency | HIGH — DB07 SSIS packages hardcode DB06 server names |
| NACHA coupling with DB02 | CRITICAL — DB06 and DB02 must be migrated in a coordinated window |
| IVR call log volume | HIGH — potentially hundreds of millions of IVR_CallLog records spanning multiple years |
| PowerShell scripts | LOW — SSRS management scripts are maintenance tools, not schema |

---

## Strategic Architecture Notes

1. **DB06 and DB07 are tightly coupled** — DB07 is the SSIS execution engine; DB06 is the data source. Any migration of either node must account for this coupling.

2. **NACHA dependency chain** — DB06 → DB07 SSIS → ACH file → financial institution. Disruption at any point in this chain could cause ACH file submission failures with regulatory consequences (NACHA fines, Reg E violations).

3. **SSRS as reporting platform** — SSRS is aging technology. The business reporting layer on DB06 is a candidate for modernization to Power BI or Tableau, which would reduce DB06's footprint but require data modeling effort.

4. **`ecountcore_ss` snapshot strategy** — Using a snapshot/replica for reporting workloads is architecturally sound, but the snapshot must be kept current. Snapshot age should be monitored and included in SLA metrics.

5. **AD integration via `xp_logininfo`** — The business user sync using the extended stored procedure `xp_logininfo` represents an aging pattern. Modern identity integration would use Azure AD or LDAP-based provisioning rather than extended SPs.
