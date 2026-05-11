# Enterprise Architect Report: DS_DB_banker

## Platform Generation Classification

**Generation: Gen-1 (eCount / Citi Legacy) — FINANCIAL ORDER MANAGEMENT LAYER**

`banker` is a Gen-1 platform database with clear indicators:

1. **Great Plains ERP integration**: Core business logic depends on GP sales orders, GP customer mapping (`CitiPrepaidMapping`, `rm00101`), and GP company databases (`ecnt`, `ecan`)
2. **ATLYS_E dependency**: `so.gp_dbs` references `Atlys_E..vPrgPrefixes` for program-to-GP database routing
3. **eCount platform programs**: Program identifiers (`program_id` CHAR(8)) and program/promo structure are the Gen-1 eCount program model
4. **FDR processor data**: `banker_get_unsettled_funds` queries `BankerAllSOView` which wraps FDR/GP settlement data
5. **SSIS-based ETL**: `SSISConfigurations` and `SSISJobConfigurations` indicate SQL Server Integration Services for data movement — Gen-1 ETL tooling
6. **SQL Server 2016 target**: Consistent with other Gen-1 databases in this family

---

## Role in Payments Architecture

`banker` sits at the **financial authorization and invoicing layer** between the order management systems and Great Plains ERP:

```
eCount Core (Gen-1 card platform)
        |
        +-- Card orders → cf_report.so.ordersvc_get_orders → na_ordersvc_get_orders (synonym)
        |
        v
banker (THIS DATABASE — fund reservation + sales order automation)
  ├── Fund reservation: banker_reserved_source (tracks what's committed)
  ├── Settlement determination: banker_get_unsettled_funds (queries BankerAllSOView)
  ├── Sales order automation (so schema):
  │   ├── Fee aggregation: so.aggregate_core / so.aggregate_items
  │   ├── Fee invoicing: so.fee_invoicing_* procedures
  │   ├── Order lifecycle: so.order_status → so.order_detail
  │   └── Item processing: so.item_* procedures (plastics, reloads, ACH, etc.)
  ├── Balance tracking: so.PrepaidCustomerBalanceHistory (daily snapshots)
  └── SSIS config: SSISConfigurations (drives batch ETL jobs)
        |
        v
Great Plains ERP (ecnt, ecan GP company databases)
  ├── Receives GP sales orders (via SOA SSIS packages)
  ├── Provides BankerAllSOView + BankerPayment (settlement confirmation)
  └── Provides customer + fiscal period data (rm00101, SY40100, CitiPrepaidMapping)
        |
        v
Finance / Operations teams (balance reports, invoice status, fee aggregation reports)
```

The critical architectural role of `banker` is that it is the **financial pre-authorization layer**: before a GP sales order is created, `banker` ensures the funds are reserved and available. After GP processes the order, `banker` queries back through `BankerAllSOView` to confirm settlement. This creates a circular dependency between `banker` and Great Plains that must be carefully managed during any ERP migration.

---

## Geographic Scope

| Attribute | Value |
|---|---|
| Region | Global (this `banker` variant) — routes to both NA (`na_ordersvc_*`) and international (`intl_ordersvc_*`) |
| GP coverage | `ecnt` (US/ECNT) and `ecan` (Canada) GP company databases (per `so.gp_dbs`) |
| Currency | USD and CAD primary; CPGBP (British pounds) variant exists (`PrepaidCaptureDailyBalances_ForMovingCompany_International_CPGBP`) |
| Regulatory jurisdiction | US (NACHA, Reg E, SOX) + Canada (PIPEDA) + UK (CPGBP variant) |

---

## Dependencies

### Upstream (data sources)

| Dependency | Type | Risk |
|---|---|---|
| `BankerAllSOView` | External view (not defined in repo) | **Critical** — all settlement determination depends on this view |
| `BankerPayment` | External view (not defined in repo) | **Critical** — all payment retrieval depends on this view |
| `REPORTINGDBSERVER.cf_report.so.ordersvc_get_orders` | Synonym → remote SP | **Critical** — all order service data flows through this |
| `ATLYS_E..vPrgPrefixes` | Cross-DB view | **High** — GP database routing depends on this |
| Great Plains ERP (`ecnt`, `ecan`) | Linked server cross-DB | **Critical** — fee invoicing and customer mapping |
| `banker_na` database | Sibling database | **Medium** — `banker_na` is a specialized NA variant with additional capabilities |

### Downstream (consumers)

| Dependency | Type |
|---|---|
| Sales Order Automation SSIS packages | Consume `so` schema objects, read `SSISConfigurations` |
| Finance reporting applications | Consume `rpt_*` stored procedures |
| `banker_na` database | NA-specific variant shares the same core schema pattern |
| FortiDB DAM | Database activity monitoring |

### Critical Undocumented Dependencies

**`BankerAllSOView` and `BankerPayment`** are referenced throughout `banker_get_unsettled_funds.sql` (lines 66–80) and `banker_get_payments.sql` (lines 27–41) but are not defined anywhere in this repository. These are the most critical external dependencies in the entire database. Without them, the fund settlement determination system is completely non-functional. Their definitions, ownership, and CDE classification must be documented.

---

## Migration Complexity Assessment

| Factor | Assessment | Score |
|---|---|---|
| Schema complexity | Medium (multi-schema but focused domain) | 3/5 |
| Business logic density | High (fee invoicing, settlement determination, customer mapping) | 4/5 |
| Cross-database dependencies | Very High (GP ERP, ATLYS_E, REPORTINGDBSERVER, undefined external views) | 5/5 |
| GP ERP coupling | Very High (direct GP table queries, GP customer model embedded in SQL) | 5/5 |
| Gen-3 conceptual gap | Very High (SQL-based invoicing automation → modern billing service) | 5/5 |
| **Overall migration complexity** | **VERY HIGH** | |

**Key Gen-3 migration blockers:**

1. **`BankerAllSOView` and `BankerPayment` must be replaced first**: These undocumented external views are the foundation of fund settlement. Before `banker` can be migrated, a Gen-3 settlement confirmation API must replace these GP-embedded views.

2. **GP invoice creation must be replaced**: The Sales Order Automation system (`so` schema) creates GP invoices by inserting records into GP tables via SSIS packages. Gen-3 requires replacing this with an ERP API or billing service. Microsoft Dynamics 365 Business Central (or equivalent) must expose an invoice creation API.

3. **GP customer model is embedded in SQL**: `fee_invoicing_get_customers` directly queries `CitiPrepaidMapping`, `rm00101`, and `SY40100` GP tables via dynamic SQL. This business knowledge must be extracted and represented in a Gen-3 customer/billing service.

4. **Partition function is outdated**: The `monthly_partition` function covers 2013–2016 only, suggesting historical data management is already a concern. Gen-3 migration must include a data archival strategy.

5. **SSIS job dependencies**: The SSIS ETL jobs that consume this database's schema are outside this repository. Any schema change to `SSISConfigurations` or `so.*` tables requires coordinated SSIS package updates.

---

## Architectural Observations

1. **Multi-schema design is sound**: The use of `so` (Sales Order), `onus` (On-Us), and `dbo` (Banker core) schemas within a single database is a reasonable Gen-1 namespace approach. In Gen-3, these would likely become separate microservices (billing service, on-us processing service, fund management service).

2. **Sales Order Automation was well-engineered for its era**: The `so` schema procedures have detailed headers with author names, project context, revision history, and known bugs. `ordersvc_get_orders.sql` has author (Zach VanderVeen, 2013), project (Sales Order Automation), revision history, and JIRA references. This level of documentation is above average for Gen-1 SQL code.

3. **Debug tables in production are technical debt, not an architecture concern**: The `Nick_Logging_JVC_*` tables are not part of the architecture — they are development artifacts. However, their presence in the production SSDT project means they are deployed to production.

4. **`REPORTINGDBSERVER` alias abstracts environment differences**: Using a server alias for the reporting server is a positive architectural practice — it enables the synonym to point to different servers in different environments without code changes.

5. **International migration is partially complete**: The commented-out `intl_ordersvc_get_orders` call in `ordersvc_get_orders.sql` (line 69) with the comment "do not need this after migration" indicates that international order processing was moved to a separate path during a migration. The `intl_*` synonyms still exist but appear unused.
