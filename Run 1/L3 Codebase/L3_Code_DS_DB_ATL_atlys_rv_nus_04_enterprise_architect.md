# Enterprise Architect Report: DS_DB_ATL_atlys_rv_nus

## Platform Generation Classification

**Generation: Gen-1 (eCount / Citi Legacy) — PRIMARY FINANCIAL DATABASE**

This is the **central Gen-1 financial operations database** for US prepaid card programs. All characteristics confirm Gen-1 classification:

1. **eCount platform tables**: `tblEC_Accts`, `tblEC_Iss`, `tblEC_Ordersvc1-4`, `tblEC_Txns` — all eCount-sourced staging data
2. **FDR processor integration**: `tblFDR_*`, `tblfdr`, `tblfdrcosts` — First Data Resources settlement data
3. **Great Plains ERP**: GL batch integration, cross-database views to GP company databases (`ECAN_R`, US GP companies)
4. **Atlys application**: `ATLYS_E` access control, `ATLYS_APP_GRP` application role, `NAM\PPA_PRD_ATLYS` service account
5. **Revenue replication**: `NOT FOR REPLICATION` flags on identity columns confirm SQL Server replication is active
6. **Scale**: 270+ views and 120+ functions indicate organic growth over many years — characteristic of a long-lived Gen-1 system

---

## Role in Payments Architecture

This database is the **financial hub** of the Gen-1 Atlys platform — it does not process payments directly but receives financial results from the payment processing layer:

```
FDR Processor (Gen-1 card processing)
        |
        +-- Settlement files → tblFDR_*, tblSettle, tblSettleDtl
        
eCount Core (Gen-1 card platform)
        |
        +-- Load events → tblIssuance
        +-- Transaction events → tblSpend, tblfdr
        +-- Order events → tblEC_Ordersvc1-4
        |
        v
atlys_rv_nus (THIS DATABASE — primary US financial database)
  ├── Revenue recognition (revenue table + trg_revenue)
  ├── GL batch processing (tblGLBatch → GP ERP)
  ├── Settlement reconciliation (tblSettle + sys_bank_reconcile)
  ├── Deferred revenue / customer liability (tblDefRev, tblFVD)
  ├── Commission calculation (tblCommissions)
  ├── Sweep breakage (tblSweepBreakage)
  └── Audit trail (tblAuditLog)
        |
        +── atlys_rv_nus_r (rollback sibling reads tblGLLinks)
        +── atlys_rv_nca, atlys_rv_nca_r (read tblGLLinks via cross-DB)
        |
        v
Great Plains ERP (GL posting via tblGLBatch)
        |
        v
Atlys WAPP (finance dashboards, GP analysis, bank recon)
        |
        v
Finance / Operations / Sales teams
```

---

## Geographic Scope

| Attribute | Value |
|---|---|
| Region | NUS — North America United States |
| GP company | US Great Plains company |
| Currency | USD primary (some multi-currency in settlement) |
| Regulatory jurisdiction | US federal (NACHA, Reg E, OFAC, state escheatment laws) |
| Processor | FDR (First Data Resources) |

---

## Dependencies

### Upstream (data sources)
| Dependency | Type | Risk |
|---|---|---|
| eCount Core operational database | Same-instance DB or linked server | Critical — source of all issuance, spend, and transaction data |
| FDR settlement file import process | ETL/batch | Critical — source of settlement and cost data |
| Great Plains ERP (US company) | Linked server | High — partner revenue, GL validation |
| `ATLYS_E` (Atlys Engine) | Same-instance DB | Critical — access control for all stored procedures |

### Downstream (consumers)
| Dependency | Type |
|---|---|
| `atlys_rv_nus_r` | Reads `tblGLLinks` (rollback sibling) |
| `atlys_rv_nca`, `atlys_rv_nca_r` | Read `tblGLLinks` via cross-database join |
| `atlys_WAPP` | Primary consumer of all SPs and views |
| Great Plains ERP | Receives GL batch postings |
| Finance team | Direct database access (Prod_Support roles) |
| FortiDB DAM | Database activity monitoring |

### SQL Server Replication
The `NOT FOR REPLICATION` markers indicate a **publisher** role in SQL Server replication. The replicated tables (`revenue`, `tblAuditLog`, `tblAuditDetails`) likely have subscribers — potentially a reporting replica or disaster recovery standby. The subscriber database(s) are not visible from this codebase.

---

## Migration Complexity Assessment

| Factor | Assessment | Score |
|---|---|---|
| Schema complexity | Very High (270 views, 120 functions, 95 tables) | 5/5 |
| Business logic density | Very High (trigger on revenue, complex stored procedures) | 5/5 |
| Cross-database dependencies | High (ATLYS_E, GP ERP, NCA databases read tblGLLinks) | 4/5 |
| Replication topology | High (active replication, subscriber databases) | 4/5 |
| Gen-3 conceptual gap | Very High (eCount → modern microservices) | 5/5 |
| **Overall migration complexity** | **VERY HIGH** | |

**Key Gen-3 migration blockers:**

1. **Revenue trigger logic**: The `trg_revenue` trigger embeds complex business logic for GL classification. This must be replicated in the Gen-3 revenue service. Risk of revenue misclassification during migration.

2. **270+ views with complex joins**: Many views (especially the `vEC_BR_*` series with 100+ variants) represent deeply embedded business knowledge. Rewriting in a modern analytics layer requires comprehensive functional testing.

3. **tblGLLinks shared dependency**: Three regional databases read this table. Any migration that moves this database must maintain backward compatibility or simultaneously migrate all dependent databases.

4. **FDR processor integration**: FDR is being replaced as part of Gen-3. The `tblFDR_*` and cost calculation logic must be rebuilt for the new processor (likely Galileo/Marqeta/etc.) before this database can be decommissioned.

5. **Great Plains ERP**: GP Dynamics is being replaced or cloud-migrated. Revenue partner data flows and GL batch posting must be re-implemented against the new ERP.

6. **SQL Server replication**: Subscriber databases must be identified and either migrated simultaneously or decoupled before the publisher is decommissioned.

---

## Architectural Observations

1. **Organic growth pattern**: 270+ views and multiple versioned table names (`tblGLMap_new`, `tblGLMap_new_new`) indicate a database that has grown organically over 10+ years without architectural refactoring. This is a classic Gen-1 "big bang" database.

2. **Business logic in the database**: The `trg_revenue` trigger and 120+ table-valued functions embed significant business logic in the database layer. Gen-3 migration should extract this to a revenue classification service.

3. **Shared configuration ownership**: Owning `tblGLLinks` while also being a rollback-capable database is architecturally conflicted. The GL configuration should be separated into an independent configuration service.

4. **FortiDB monitoring**: The presence of `FortiDBRptRole` indicates active database activity monitoring — a positive security control.
