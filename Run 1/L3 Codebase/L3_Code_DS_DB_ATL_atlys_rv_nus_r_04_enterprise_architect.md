# Enterprise Architect Report: DS_DB_ATL_atlys_rv_nus_r

## Platform Generation Classification

**Generation: Gen-1 (eCount / Citi Legacy)**

Same generation as the NCA rollback. Evidence:
- eCount operational table naming (`tblissuance`, `tblfdrcosts`, `revenue`)
- Great Plains ERP integration via linked servers
- FDR (First Data Resources) processor cost model
- Atlys application platform
- `DS_DB_ATL_` repository prefix family

---

## Role in Payments Architecture

This database serves as:
1. **US rollback view layer** for the primary `atlys_rv_nus` database (blue-green deployment standby)
2. **Shared GL configuration host** — provides `tblGLLinks` to both US and NCA regional reporting databases

```
Great Plains ERP (US company ECNT/ECAN)
        |
        v
Partner revenue view (vRevenueT_Partner)
        |
eCount Core US (tblissuance, revenue, tblfdrcosts, etc.)
        |
        v
atlys_rv_nus_r (THIS DATABASE)
  - View layer (vRevenue, vIssuance, vCosts, etc.)
  - tblGLLinks (GL config — AUTHORITATIVE SOURCE)
        |
        +--- Read by atlys_rv_nca_r.vRevenueD (cross-DB)
        +--- Read by atlys_rv_nca.vRevenueD (cross-DB)
        |
        v
Atlys WAPP (via atlys_rvcr stored procedures)
```

---

## Geographic Scope

| Attribute | Value |
|---|---|
| Region | NUS — North America United States |
| GP company | US Great Plains company (distinct from ECAN_R for NCA) |
| Currency | USD |
| Regulatory jurisdiction | US federal (NACHA, Reg E, OFAC) |

---

## Dependencies

### Upstream (data sources)
| Dependency | Type | Risk |
|---|---|---|
| `atlys_rv_nus` primary sibling | Same-instance DB | High |
| US Great Plains ERP | Linked server | High — partner revenue |

### Downstream (consumers)
| Dependency | Type |
|---|---|
| `atlys_WAPP` (Atlys web app) | Application via ATLYS_E stored procedures |
| `atlys_rv_nca_r.vRevenueD` | Cross-database read of `tblGLLinks` |
| `atlys_rv_nca.vRevenueD` | Cross-database read of `tblGLLinks` |

### Lateral
| Database | Relationship |
|---|---|
| `ATLYS_E` | Provides access control functions |
| `atlys_rv_nus` | Primary counterpart |
| `atlys_rv_nca_r` | Reads `tblGLLinks` from this DB |

---

## Migration Complexity Assessment

| Factor | Assessment |
|---|---|
| Schema complexity | Low (12 views) |
| Cross-database dependencies | Medium (2 external) + reverse dependency from NCA |
| `tblGLLinks` migration impact | High — must coordinate with NCA databases |
| Gen-3 migration blockers | Same as NCA: GP ERP, FDR cost model, eCount tables |

**Additional Gen-3 migration complexity**: `tblGLLinks` must be migrated to a shared reference store (Azure SQL or config service) accessible by all regional reporting databases before either the US or NCA databases can be decommissioned. Migrating either regional database in isolation will break the other region's GL mapping.

---

## Architectural Observations

1. **Asymmetric dependency**: The NCA rollback database reads GL mapping from the US rollback database. This creates a geographic dependency that violates the principle of regional isolation. The US database becoming unavailable would break NCA reporting.

2. **Date normalization divergence**: The US and NCA schemas use different approaches to date period assignment (inline monthly formula vs. period table join). This makes it harder to join or compare data across regions and increases maintenance burden when business rules change.

3. **Shared config in rollback database**: Storing the authoritative `tblGLLinks` in a rollback database is architecturally fragile. The rollback database should ideally be a passive standby that mirrors its primary; instead, it is an active dependency for other databases.

4. **Rollback naming convention**: The `_r` convention is consistent across the Atlys family (`atlys_rv_nca_r`, `atlys_rv_nus_r`, `atlys_rvcr` where `cr` may denote "credit"). This naming aids operational management.
