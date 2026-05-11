# Enterprise Architect Report — DS_DB_GP_ecnt

## 1. Platform Generation Classification

**Generation: Gen-1 (eCount / Citi Legacy) — Great Plains ERP US Primary Company Database**

Evidence:
- **Microsoft Dynamics GP standard database**: Hundreds of GP-standard tables (`GL`, `RM`, `PM`, `SOP`, `POP`, `UPR`, `FA`) — Microsoft Dynamics GP is the Gen-1 ERP platform used across Onbe's corporate and card program financial operations
- **`CompatibilityMode=90`** (SQL Server 2005): GP databases are maintained at the compatibility level supported by the installed GP version; GP 2015/2016 typically runs on SQL 2012-2016 with older compat levels
- **Citi Direct integration**: `RSM_CitiDirect_ACH_WithBank`, `RSM_CitiDirect_Drawdown_WithBank` — Citi Direct is a Citi-era (Gen-1) banking integration for ACH and wire drawdown
- **`PUID` references**: Procedure comments reference PUID (Physical Unique Identifier) — a Citi-era cardholder identifier
- **`CitiPrepaid*` procedures**: `CitiPrepaidONUS_RevCSA_INSERT`, `CitiPrepaid_ZeroTotalSOBatch` — named procedures confirm Gen-1 CitiPrepaid platform integration
- **RSM naming convention**: `RSM_*` prefix for stored procedures is RSM (consulting firm) naming convention from the Gen-1 deployment
- **Banker functions** (2009 author `ACHEN` per `banker_get_required_deposit_date.sql`): Core Banker functions authored in 2009 — early Gen-1 implementation period
- **`ecan` and `ecnt`** GP company databases: ECAN (Canada) and ECNT (US Central) are the two primary GP company databases in the Gen-1 eCount/Northlane architecture

**Generation assessment**: Gen-1 with active Gen-2 maintenance (Wirecard/Northlane era modifications visible in `RSM_CitiDirect_*` procedures modified 2017-2019). ECNT has not been architecturally replaced and continues in active operational use.

---

## 2. Business Domain

**Domain**: ERP Financial Ledger / Corporate Finance / Program Financial Management

ECNT is the **primary financial ledger** for Onbe's US Central operations. It records all financial transactions for the US domestic prepaid card program portfolio against the ERP system of record. Business domains served:

- **Accounts Receivable**: Program sponsor billing, invoice management, credit limit administration
- **Accounts Payable**: Vendor payments, ACH/check disbursements, refund processing
- **General Ledger**: Journal entries, period-end close, financial reporting
- **Payroll**: US employee payroll processing (UPR module)
- **Sales Order Processing**: Program card order invoicing automation
- **Fixed Assets**: US asset base management
- **Banker SVC**: Real-time fund availability for prepaid card program authorisations
- **Citi Direct Banking**: ACH origination and wire drawdown to bank partners
- **Compliance**: Missing refund tracking (Reg E compliance)

---

## 3. Role in the Enterprise Architecture

```
GP Finance Team ──────────────────────► ECNT (invoices, payments, GL journal entries)
                                              │
                           ┌──────────────────┤
                           │                  │
Banker API (real-time) ◄───┤         Finance WebService ◄── AR/payment views
  Banker_available_balance  │
                           │
                           ├──► DS_ETL_finance-gp ──► Data Warehouse
                           │
                           ├──► Citi Direct (ACH origination, wire drawdown)
                           │
                           ├──► Meridian Bank (reconciliation via VRFMERIDIAN)
                           │
                           └──► Atlys (program financial data via ATLYS_APP_GRP)
                                Accounting Workflow (finance approvals)
                                VW_MISSING_REFUNDS ──► Compliance team
```

ECNT occupies the **financial system of record** position in the Gen-1 architecture. Every US prepaid card program has a corresponding GP customer record in ECNT, and the Banker SVC queries ECNT directly to verify fund availability before authorising card loads.

---

## 4. Dependencies

### Upstream (data sources)
| Dependency | Type | Coupling |
|---|---|---|
| GP Finance Team | Human/UI | Finance staff enter invoices, payments, journal entries via GP client |
| Order Service / Job Service | Application | Creates GP sales orders via SOP insert procedures |
| Accounting Workflow | Application | Finance approvals drive payment creation |
| Citi Direct | External banking | ACH and wire drawdown instructions originate from ECNT procedures |

### Downstream (consumers)
| Dependency | Type | Notes |
|---|---|---|
| Banker API | Critical real-time | `Banker_available_balance` is a synchronous, latency-sensitive call from the card authorisation path |
| Finance WebService | Business intelligence | AR views, SOPDETAILVIEW consumed for reporting |
| Atlys (`ATLYS_APP_GRP`) | Reporting | Atlys reads ECNT for program financial analytics |
| DS_ETL_finance-gp | ETL | Extracts all GP tables for data warehouse |
| DS_ETL_great-plains | ETL | Secondary GP export ETL |
| Accounting Workflow | Application | Reads financial status from ECNT |

---

## 5. Integration Patterns

| Pattern | Implementation | Notes |
|---|---|---|
| Direct GP table access | Banker procedures read `rm00103`, `GL10000`, etc. directly | No abstraction layer between Banker API and GP tables |
| Stored procedure API | All Onbe custom business logic exposed as `dbo.*` procedures | Consistent with GP custom development pattern |
| Email-based integration | `RSM_CitiDirect_ACH_WithBank` sends email notifications to bank partners | Email recipient addresses embedded in procedure body |
| SSIS-based ETL extraction | `DS_ETL_finance-gp` and `DS_ETL_great-plains` extract all tables | Pull-based, scheduled ETL |
| Named user direct access | 80+ individual login accounts access ECNT directly | Standard GP client access pattern |

---

## 6. Geographic Scope

| Attribute | Value |
|---|---|
| Primary region | US Central / primary US operations |
| GP company databases | `ecnt` (US) + `ecan` (Canada) — both GP companies share the same SQL instance family |
| Currency | USD primary; multi-currency GP configuration implied |
| Regulatory jurisdiction | US (NACHA, Reg E, SOX, GLBA, IRS payroll) |
| Bank partners | Citi Direct, Meridian Bank |

---

## 7. Strategic Status

**Status: Core Gen-1 System — Long Migration Timeline**

ECNT cannot be migrated or decommissioned without:
1. A replacement ERP or billing system (Microsoft Dynamics 365 Business Central, or equivalent)
2. Migration of the Banker SVC dependency (real-time fund availability)
3. Migration of Citi Direct banking integration
4. Migration of all US program customer records
5. Finance team training and change management
6. SOX ITGC audit coverage for the replacement system

The `RSM_CitiDirect_*` procedures were actively modified through 2019 (Wirecard era), confirming ECNT is in production use and not being actively decommissioned.

---

## 8. Migration Complexity and Blockers

**Complexity: VERY HIGH**

| Factor | Assessment |
|---|---|
| GP ERP replacement | Requires full ERP evaluation, selection, and implementation project — multi-year |
| Banker SVC real-time coupling | `Banker_available_balance` is in the card authorisation path — must be replaced with zero-downtime |
| Payroll data migration | US employee payroll records must be migrated to replacement payroll system (ADP, Workday, etc.) |
| Citi Direct banking integration | ACH and wire drawdown integrations must be replicated in new platform |
| AR/AP lifecycle migration | All open invoices, payments, and credit memos must be migrated or reconciled before cutover |
| 80+ named user access | All individual GP users must be migrated to the replacement ERP with access review |
| DS_ETL dependency | Finance and reporting ETL pipelines must be updated for new ERP data model |
| SOX financial reporting continuity | Financial reports generated from ECNT must be replicated and validated in new system before audit period |
| Missing refund compliance | `VW_MISSING_REFUNDS` functionality must be replicated before cutover — Reg E obligation |

**Migration blockers:**
1. GP ERP replacement is a separate, major programme — not a database migration
2. Banker SVC replacement requires a new Fund Management Service with sub-second latency
3. SOX ITGC must cover the new ERP from day one of financial periods — mid-year migration creates audit risk
4. Employee PII (payroll) migration requires privacy impact assessment under GLBA
