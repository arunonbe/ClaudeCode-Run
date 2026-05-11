# Enterprise Architect Report: DS_DB_ATL_atlys_rv_nca_r

## Platform Generation Classification

**Generation: Gen-1 (eCount / Citi Legacy)**

This database is firmly rooted in the Gen-1 eCount platform architecture. Evidence:

1. **eCount table prefixes**: Source tables use the `tblEC_*` naming convention (tblEC_Iss, tblEC_Txns, tblEC_Accts) consistent with the eCount core platform.
2. **Great Plains ERP integration**: Cross-database references to `ECAN_R.dbo.RM00101`, `SOP10102`, and `GL00100` are the Great Plains Dynamics GP ERP tables used in the legacy eCount financial operations model. The `ECAN_R` database name suggests the NCA (North America excluding Canada) regional GP company.
3. **FDR processor references**: `tblfdrcosts` references First Data Resources (FDR), the legacy card processor used in the eCount era before the Northlane/Wirecard transition.
4. **Atlys application platform**: The Atlys web application (`atlys_WAPP`) is a Gen-1/Gen-2 financial reporting tool specific to Onbe's legacy platform.
5. **Naming convention**: The `DS_DB_ATL_` prefix places this squarely in the Atlys database family, a Gen-1 financial reporting subsystem.

---

## Role in Payments Architecture

This database serves as a **non-transactional financial reporting and analytics component**. It does not participate in the payment authorization or settlement critical path. Its role:

```
Payment Processing Layer (Gen-1 eCount core, FDR processor)
        |
        v
eCount Core operational tables (tblIssuance, revenue, tblSpend, etc.)
        |
        v
atlys_rv_nca_r (THIS DATABASE) - View layer for NCA region rollback reporting
        |
        v
Atlys Web Application (atlys_WAPP) - Finance team reporting and GP analysis
        |
        v
Finance/Operations users
```

The `_r` (rollback/reversal) designation means this database is the **standby schema** for the primary `atlys_rv_nca` database. During deployments or hotfixes to the primary, the Atlys application can be pointed at `atlys_rv_nca_r` to maintain reporting continuity. This is a manually-managed blue-green pattern at the database level.

---

## Geographic Scope

| Attribute | Value |
|---|---|
| Region | NCA — North America excluding Canada |
| GP company code | ECAN (Canada appears to be separate; NCA uses ECAN_R for reporting reads) |
| Currency | USD implied (NCA Americas) |
| Regulatory jurisdiction | US (NACHA, Reg E, OFAC applicable) |

The NCA variant is distinct from:
- `atlys_rv_nus` / `atlys_rv_nus_r` — US variant (different GP company, slightly different data scope)
- `atlys_rvcr` — Global/credit revenue variant with full stored procedure set
- `atlys_rv_nca` — Primary (non-rollback) NCA database

---

## Dependencies

### Upstream (data sources)
| Dependency | Type | Risk |
|---|---|---|
| `atlys_rv_nca` (primary sibling) | Same-instance DB | High — all base tables live here |
| `ECAN_R` (Great Plains NCA) | Linked server | High — partner revenue and program master |
| `ATLYS_Rv_NUS_R` (US sibling) | Cross-database | Medium — GL mapping table |

### Downstream (consumers)
| Dependency | Type |
|---|---|
| `atlys_WAPP` (Atlys web app) | Application consumer via ATLYS_E stored procedures |
| Finance reporting users | Direct query access |

### Lateral (peer databases)
| Database | Relationship |
|---|---|
| `ATLYS_E` (Atlys Engine) | Provides `sys_chkuser`, `sys_cinfo` access control functions referenced in the rvcr stored procedures |
| `atlys_rv_nca` | Primary counterpart |
| `atlys_rv_nus_r` | US rollback sibling; provides `tblGLLinks` |

---

## Migration Complexity Assessment

| Factor | Assessment |
|---|---|
| Schema complexity | Low (13 views, no tables) |
| Cross-database dependencies | High (3 external databases) |
| Data volume | Not applicable (view-only) |
| Application coupling | Medium (Atlys app must be updated to use new view names if migrated) |
| Gen-3 migration blockers | Great Plains ERP integration; FDR cost model; eCount table structure |

**Migration to Gen-3 (Onbe/Azure)**: This database would need to be replaced with an Azure-native reporting layer (e.g., Azure Synapse Analytics, Azure SQL views, or a reporting microservice) that can replicate the GP financial data integration via modern API or ETL patterns. The FDR cost tables and eCount operational tables would need equivalent replacements in the Gen-3 data model.

The primary migration risk is the **Great Plains ERP dependency**: `ECAN_R` linked server queries are tightly coupled to the legacy GP Dynamics financial system. Any GP replacement or cloud migration would break these views.

---

## Architectural Observations

1. **Rollback pattern**: The `_r` twin-database pattern for blue-green deployments is a pragmatic workaround for the lack of zero-downtime deployment in SQL Server SSDT projects. It works but creates maintenance overhead (two sets of objects to keep in sync).

2. **Cross-database coupling**: References to `ATLYS_Rv_NUS_R.dbo.tblGLLinks` in an NCA database indicate shared GL configuration between US and NCA regions. This is a design smell — regional databases should ideally maintain independent configuration tables, or the GL configuration should be centralized in a shared reference database.

3. **View-only architecture**: The decision to make this database view-only is architecturally sound for a rollback variant — it minimizes deployment risk and keeps all stateful data in the primary database.

4. **Linked server risk**: All cross-database joins run over linked server connections. In high-load reporting scenarios, these can become performance bottlenecks and single points of failure.
