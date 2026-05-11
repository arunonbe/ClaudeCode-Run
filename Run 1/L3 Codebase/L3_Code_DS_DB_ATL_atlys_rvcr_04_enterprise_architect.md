# Enterprise Architect Report: DS_DB_ATL_atlys_rvcr

## Platform Generation Classification

**Generation: Gen-1 (eCount / Citi Legacy) — ROUTER/DISPATCHER LAYER**

`atlys_rvcr` is the global application-tier entry point for the Gen-1 Atlys financial reporting platform. All characteristics confirm Gen-1 classification:

1. **ATLYS_E access control**: Calls `ATLYS_E.dbo.sys_chkuser` and `sys_chkuserrights` — the Gen-1 Atlys authentication framework
2. **eCount platform staging tables**: `tblEC_*` session-scoped tables hold eCount transaction, issuance, account, and order service data
3. **FDR processor integration**: `tblFDR_*` tables, `tblSettle`, `tblInterface` manage FDR settlement file data
4. **Great Plains ERP**: GL batch routing (`sys_glbatch`, `sys_glbatch_complete`) targets GP company databases
5. **Router architecture**: Every SP routes calls to company-specific databases (`atlys_rv_nus`, NCA, and others) via `ATLYS_E.dbo.sys_cinfo` — a Gen-1 multi-tenant dispatch pattern
6. **SQL Server 2016 target**: SSDT project targets `Sql130DatabaseSchemaProvider`, confirming long-lived legacy infrastructure

---

## Role in Payments Architecture

`atlys_rvcr` occupies the **application gateway layer** of the Atlys Gen-1 financial reporting stack. It does not hold the authoritative financial data but controls access to all company-specific financial databases:

```
Atlys WAPP (web application)
        |
        v
atlys_rvcr (THIS DATABASE — global application gateway)
  ├── Authentication: ATLYS_E.dbo.sys_chkuser / sys_chkuserrights
  ├── Company routing: ATLYS_E.dbo.sys_cinfo → company DB name
  ├── Region routing: ATLYS_E.dbo.sys_regioncinfo → iterate all companies
  ├── Shared settlement data: tblSettle, tblFDR_* (FDR-sourced)
  ├── eCount staging: tblEC_* (session-scoped landing zones)
  ├── Job scheduling: tblJobs + sys_jobrun (drives automated collection)
  └── Comparison metrics: tblCompareBuckets, tblCompareMetrics*
        |
        +── atlys_rv_nus (US company database — primary)
        +── atlys_rv_nca (NCA company database)
        +── atlys_rv_[other regional databases]
        |
        v
Great Plains ERP (GL posting via GL batch router)
        |
        v
Finance / Operations / Sales teams (via Atlys WAPP)
```

The critical architectural characteristic of `atlys_rvcr` is that it is the **sole entry point** for the Atlys WAPP. All financial reporting requests — regardless of company or region — are authenticated and dispatched through this database. This creates a hub-and-spoke dependency model with `atlys_rvcr` as the hub.

---

## Geographic Scope

| Attribute | Value |
|---|---|
| Region | Global (CR = Credit Revenue, multi-region aggregator) |
| Company scope | All companies: NUS (US), NCA (Canada), and others |
| Currency | Multi-currency (USD, CAD, and others via regional databases) |
| Regulatory jurisdiction | Multi-jurisdictional: US (NACHA, Reg E, OFAC), Canada (PIPEDA, Quebec Law 25) |
| Processor | FDR (First Data Resources) — Gen-1 processor |

---

## Dependencies

### Upstream (data sources)

| Dependency | Type | Risk |
|---|---|---|
| `ATLYS_E` | Same-instance DB | **Critical** — access control for every stored procedure call; single point of failure |
| Company-specific databases (`atlys_rv_nus`, `atlys_rv_nca`, others) | Same-instance cross-DB | **Critical** — all report data is sourced from these databases |
| FDR settlement file import | ETL/batch → `tblFDR_*`, `tblSettle` | **High** — source of settlement and cost data |
| eCount company databases | ETL → `tblEC_*` via `sys_import_txn` | **High** — source of transaction staging data |
| Great Plains ERP | Linked server | **Medium** — GL batch destination; bank recon source |

### Downstream (consumers)

| Dependency | Type |
|---|---|
| `atlys_WAPP` | Primary consumer of all stored procedures and views |
| Finance team | Direct database access via `Prod_Support_*` roles |
| Automated job scheduler (`sys_jobrun`) | Self-referential: drives automated balance reconciliation and GL collection |
| FortiDB DAM | Database activity monitoring |

### Critical Dependency: ATLYS_E

Every single stored procedure in `atlys_rvcr` begins with a call to `ATLYS_E.dbo.sys_chkuser` (or bypasses this check only if the caller is the `dbo` user). This means:

1. `ATLYS_E` availability is a prerequisite for `atlys_rvcr` availability
2. `ATLYS_E` schema changes to `sys_chkuser`, `sys_chkuserrights`, `sys_cinfo`, or `sys_regioncinfo` require coordinated testing with `atlys_rvcr`
3. The `ATLYS_E` database is not defined in this repository — it must be documented and tracked separately

---

## Multi-Tenancy Architecture

The `atlys_rvcr` database implements a **routing-based multi-tenancy model**:

- `@ctype = 'C'` (Company): Route to a single company database, execute the equivalent stored procedure there, return results
- `@ctype = 'R'` (Region): Iterate through all companies in the region (via `ATLYS_E.dbo.sys_regioncinfo`), execute the SP in each company database, INSERT results into a local temp table, return the aggregated set

This pattern is implemented uniformly across all ~45 stored procedures. The region iteration uses a cursor or WHILE loop over the `sys_regioncinfo` result set. This architecture is effective for the Gen-1 context but introduces significant latency for multi-region reports, as each company database is queried serially.

---

## Migration Complexity Assessment

| Factor | Assessment | Score |
|---|---|---|
| Schema complexity | Low-Medium (45 SPs, 20 functions, 35 views — all routing logic) | 2/5 |
| Business logic density | Low (logic is in company-specific DBs; rvcr mostly routes) | 2/5 |
| Cross-database dependencies | Very High (ATLYS_E + all company DBs + eCount + FDR + GP) | 5/5 |
| Routing pattern migration | High (must redesign multi-tenancy for Gen-3 service mesh) | 4/5 |
| Gen-3 conceptual gap | Very High (from SQL routing to API gateway / service mesh) | 5/5 |
| **Overall migration complexity** | **HIGH** | |

**Key Gen-3 migration considerations:**

1. **ATLYS_E replacement**: The ATLYS_E access control framework must be replaced with a Gen-3 identity/authorization service (OAuth2/OIDC + RBAC) before `atlys_rvcr` can be decommissioned. This is a prerequisite for migrating all Atlys databases.

2. **Multi-tenancy redesign**: The `@ctype = 'C'/'R'` routing pattern embedded in SQL stored procedures must be redesigned as an API gateway routing layer or service mesh configuration in Gen-3.

3. **Session-scoped staging tables**: The `tblEC_*` session-scoped permanent tables pattern must be replaced with proper message queue or event streaming patterns in Gen-3.

4. **Job scheduling**: The `tblJobs` + `sys_jobrun` SQL-based scheduler must be replaced with a modern job orchestration platform (e.g., Kubernetes CronJob, AWS EventBridge Scheduler, Apache Airflow).

5. **Settlement data migration**: `tblSettle` and `tblFDR_*` tables contain historical settlement data that must be migrated or archived before decommissioning. The FDR processor integration itself is also a Gen-3 migration target.

6. **FDR processor replacement**: FDR is a Gen-1 processor. Gen-3 migration requires replacing FDR with a modern processor (Galileo, Marqeta, or others). This directly impacts `tblFDR_*`, `tblInterface`, `sys_fdr`, and related objects.

---

## Architectural Observations

1. **Uniform routing pattern**: The consistency with which every stored procedure implements the same routing pattern is architecturally intentional. This was a deliberate design decision to centralize multi-tenancy routing in SQL. While technically sound for its era, it creates SQL-layer coupling that is antithetical to microservices architecture.

2. **`dbo` bypass is a feature, not a bug**: The access control bypass for `dbo` is clearly an intentional design choice to enable automated deployments and DBA operations. However, it is a permanent exception to PCI DSS-required access controls that must be addressed.

3. **Comparison metrics tables**: `tblCompareBuckets`, `tblCompareMetrics`, `tblCompareMetrics2`, `tblCompareMetricsComponents`, `tblCompareMetricsMap` represent a configuration data layer for the Atlys reporting UI. These tables are maintained by users (or configuration procedures) and drive what metrics are displayed in period comparison reports. This configuration layer must be preserved or migrated to a Gen-3 configuration service.

4. **FortiDB monitoring as a compensating control**: The presence of `FortiDBRptRole.sql` and FortiDB DAM confirms that database activity monitoring is a compensating control for the broad access permissions granted to `Prod_Support_*` roles. This compensating control must be carried forward to any Gen-3 architecture.
