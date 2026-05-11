# DS_DP_db05 — Enterprise Architect Report

## Platform Position

DB05 occupies an **undefined position** in the DS_DP cluster architecture based on repository evidence alone. Its sequential numbering places it between:
- **DB04** — portal content management and QA processing node
- **DB06** — reporting, BINBANK management, and NACHA extract node

The absence of application-specific scripts while all other infrastructure scripts are present is the defining characteristic of DB05 in this analysis.

---

## Technology Stack

| Attribute | Value |
|---|---|
| Database engine | Microsoft SQL Server (version unknown) |
| Instance name pattern | `P-DB05` (inferred from naming convention) |
| Maintenance framework | Ola Hallengren SQL Server Maintenance Solution (deployed February 2020) |
| HA mechanism | Unknown (no direct evidence; cold-standby pattern likely given other nodes) |
| Last documented change | December 2020 |

---

## Architectural Hypotheses

### Hypothesis A: Decommissioned Node (Most Likely)
The absence of any changes since December 2020 — coinciding with the Wirecard acquisition closure — suggests DB05 may have been decommissioned as part of post-acquisition infrastructure consolidation. 

Evidence supporting this:
- The maintenance job scripts deployed in February 2020 contain `CASE WHEN @@SERVERNAME LIKE 'C%' THEN 0 ELSE 1 END` — if the server was later repurposed as a cold-standby (C-DB05), all jobs would have been disabled
- The absence of db03 from the repository (likely decommissioned) creates a precedent for node retirement
- The 2020 date range aligns with the Wirecard acquisition by NorthLane (which resulted in infrastructure rationalization)

### Hypothesis B: Warm Standby / Read Replica
DB05 may function as an **Always On readable secondary** or log-shipping target for one of the active nodes. In this architecture:
- All data arrives via replication/log shipping — no direct application writes
- DBA changes are minimal (only infrastructure changes needed)
- The repository captures only changes that cannot be replicated (agent jobs, server-level objects)

This would explain why DB05 has exactly the same infrastructure scripts as other nodes but no application scripts.

### Hypothesis C: Legacy Partition Host
DB05 may have been a **historical partition node** for a specific card program cohort that was migrated to another node (DB02 or DB04) during the 2019–2020 modernization. After migration, DB05 received only infrastructure maintenance but no new application deployments.

---

## DS_DP Cluster Topology (Updated View with DB05)

```
┌──────────────────────────────────────────────────────────────┐
│              DS_DP Database Cluster                          │
│                                                              │
│  DB01 ── General services (Repositorysvc, Ordersvc, Jobsvc)│
│  DB02 ── Core card processing (EcountCore, EcountCore_Process)│
│  [DB03 ── DECOMMISSIONED]                                   │
│  DB04 ── Portal content + QA proxy (cbaseapp, EcountCore QA)│
│  DB05 ── UNKNOWN / POSSIBLY DECOMMISSIONED                  │
│  DB06 ── Reporting + NACHA + IVR logs (cf_report, Vendor)  │
│  DB07 ── ETL orchestration (SSISDB, SSIS packages)         │
│                                                              │
│  [DB08 ── Referenced in SSIS configs, not in this analysis] │
│  [DB15 ── Listed in repo_list.txt, not in this analysis]   │
└──────────────────────────────────────────────────────────────┘
```

The gap between db03 (absent) and db05 (sparse) suggests a **progressive decommissioning** of earlier nodes as the platform evolved, with db02, db04, db06, and db07 emerging as the active functional nodes.

---

## Dependencies

### Inbound
- Unknown — no application writes documented

### Outbound
- `DataServicesGroup-Operator` email distribution — SQL Agent alerts
- Index maintenance logs (written to `CommandLog` table in `master`)

### Shared with Other Nodes
- Server-level trigger `TR_check_ip_address_functional_user` — network access control
- `IndexOptimize_AgentWrapper` — maintenance wrapper
- `Ola Hallengren` maintenance solution

---

## Migration Complexity

| Factor | Assessment |
|---|---|
| Known schema complexity | LOW (no application schema confirmed) |
| Unknown schema risk | HIGH (unknown databases may exist on server) |
| Dependencies on other nodes | UNKNOWN |
| Decommission risk | LOW (if already inactive) |
| PCI scope determination | REQUIRED before any migration/decommission action |

---

## Enterprise Architecture Concerns

1. **Undocumented node** — A database server in a PCI Level 1 environment with no documented business function creates compliance risk. PCI DSS Requirement 2.1 mandates a system inventory of all in-scope components.

2. **Consistency gap** — If DB05 is actively serving traffic, it represents a node whose schema state is unknown to the engineering team — a significant operational risk.

3. **db03 precedent** — The complete absence of db03 from the repository suggests prior decommissioning was not fully documented. DB05's ambiguous state may follow the same pattern.

4. **DB08 and DB15** — Two additional DS_DP nodes (DB08, DB15) are referenced in the `repo_list.txt` but not included in this analysis. DB08 is referenced in SSIS configurations on DB07 and appears to host `ATLYS_FcCR` (an Atlys financial reporting database). The full DS_DP cluster includes at least nodes DB01–DB08 and DB15.

---

## Strategic Recommendations

1. **Immediately determine server status** — Is DB05 a running server? Query the network topology/DNS to confirm.
2. **If running:** Execute full database inventory and PCI scope assessment
3. **If decommissioned:** Document formally, remove from production network, archive repository with decommission date
4. **Update cluster documentation** — The DS_DP cluster topology document must account for all numbered nodes including DB03 (decommissioned) and DB05 (status unknown)
5. **Consider consolidation** — If DB05 is idle, its allocated resources (compute, storage, licenses) should be evaluated for reallocation
