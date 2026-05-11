# Enterprise Architect Report — DS_DB_ATL_atlys_fccr

## 1. Platform Generation Classification

**Generation: Gen-1.5 / Gen-2 Boundary — Wirecard-era Atlys Financial Modelling Tool**

Evidence:
- **Wirecard-era product**: Atlys is the revenue forecasting and fee-calculation platform built during the Wirecard/NAM acquisition period. The `ATLYS_APP_GRP` role (`NAM\PPA_PRD_ATLYS` service account) and the `NAM_PPA_PRD_ATLYS` login confirm this is a Wirecard NAM production service
- **SQL 2005 compatibility level** (`CompatibilityMode=90`): Atlys was originally built for SQL Server 2005/2008 era — predating many Onbe/Northlane services. The project uses the `Sql100DatabaseSchemaProvider` (SQL 2008 toolchain) but targets compatibility 90, indicating it was designed for an older SQL Server environment and never fully modernized
- **APAC CPP variant present** (`NAM_PROD_CPP_APAC.sql`): The APAC CPP login is unique to this variant among the fccr/nca/nus databases, confirming this database serves programs that span North America and Asia-Pacific geographic scope
- **Salesforce CRM integration**: The bidirectional Salesforce integration (`sys_sf_import`, `sys_sf_upload`) is a Wirecard-era/NAM-era capability representing the integration of the deals pipeline CRM with the financial modelling tool
- **`fccr` variant = Credit Fee Calculation**: The `fccr` database handles credit-type card program fee modelling, which is distinct from the standard prepaid NCA/NUS variants; credit programs were a Wirecard NAM product expansion

**Generation assessment**: Gen-2 (Wirecard/Northlane). Built during the Wirecard NAM operational period, this is not a Gen-1 eCount/Citi legacy product (it has no FDR/Citi transaction processing) but it predates the Gen-3 Onbe cloud-native architecture.

---

## 2. Business Domain

**Domain**: Financial Planning and Analysis (FP&A) / Revenue Intelligence

`atlys_fccr` sits in the **Atlys platform** — Onbe's internal financial modelling and revenue forecasting tool for prepaid and credit card programs. The Atlys platform is used by:
- Finance teams for revenue forecasting and variance analysis
- Sales/BD teams for deal modelling (via Salesforce integration)
- Operations teams for issuance, plastics, and commission reporting

The `fccr` variant specifically models **credit-type card programs** — distinct from prepaid debit programs modelled in the NCA/NUS variants.

---

## 3. Role in the Enterprise Architecture

```
Salesforce CRM (deal pipeline)
        │
        │  sys_sf_import (inbound deal data)
        ▼
atlys_fccr (THIS DATABASE)
  ├── Credit program fee models
  ├── Revenue/commission forecasting
  ├── Deferred revenue management
  ├── Issuance/plastics pipeline forecasting
  └── Dashboard/variance reporting
        │
        │  sys_sf_upload (outbound revenue forecasts)
        ▼
Salesforce CRM (deal economics updated)

        │
        ▼
Atlys Web Application (atlys_WAPP) — reporting UI
        │
        ▼
Finance team (revenue forecasting, planning)
```

This database is a **read-heavy reporting and modelling service**. It does not process card transactions, cardholder records, or payment authorisations. Its outputs are financial forecasts and revenue reports consumed by internal teams and fed back to Salesforce for deal management.

---

## 4. Dependencies

### Upstream
| Dependency | Type | Notes |
|---|---|---|
| Salesforce CRM | External integration | Bidirectional: Atlys imports Salesforce opportunity data and uploads revenue forecasts back |
| `cursforecast` / Atlys shared program master | Implied database | Core program master data referenced by stored procedures but not defined in this repo — likely in a shared Atlys infrastructure database |
| Atlys NCA / NUS databases | Sibling databases | Share the same stored procedure architecture; fccr is the credit variant |

### Downstream
| Dependency | Type | Notes |
|---|---|---|
| `atlys_WAPP` (Atlys web application) | Consumer | Primary Atlys UI reads from this database via `ATLYS_APP_GRP` role |
| Finance web service (`NAM_PPA_PRD_FinSVC`) | Consumer | Finance reporting service reads Atlys data |
| Salesforce CRM | Consumer | `sys_sf_upload` feeds revenue cross-tab data back to Salesforce |

---

## 5. Integration Patterns

| Pattern | Implementation |
|---|---|
| Stored procedure API | All business logic exposed as parameterised stored procedures; no direct table access by consumers |
| Database role-based access control | `ATLYS_APP_GRP` role controls application access; separate roles for production support, security scanning, and monitoring |
| Polling-based Salesforce import | `sys_sf_import` reads from `Salesforce_to_Atlys` staging table — import is ETL-mediated, not event-driven |
| Pull-based reporting | Atlys UI calls stored procedures on demand; no push/notification mechanism |

---

## 6. Strategic Status

**Status: Legacy / Ongoing Use — Decommission timeline unclear**

`atlys_fccr` serves an active business function (credit program revenue forecasting) but runs on a SQL Server 2005-compatible database with no CI/CD, no modern encryption, and Wirecard-branded infrastructure references. Key strategic questions:

1. **Is credit program revenue modelling moving to a Gen-3 tool?** If Onbe's Gen-3 FP&A strategy includes a modern BI/analytics platform (Power BI, Tableau, Adaptive Insights), `atlys_fccr` would be a migration target.

2. **Salesforce integration ownership**: The bidirectional Salesforce connection (`sys_sf_import`/`sys_sf_upload`) represents significant integration investment. Migrating this to Gen-3 requires Salesforce API integration work in addition to database migration.

3. **Credit vs. prepaid program separation**: The existence of `fccr` (credit) alongside `fc_nca`/`fc_nus` (prepaid) suggests the Atlys platform was purpose-built for two product lines. Any Gen-3 replacement must support both.

---

## 7. Migration Complexity and Blockers

**Complexity: MEDIUM**

| Factor | Assessment |
|---|---|
| Schema size | Small (2 tables + views) — data model is lightweight |
| Stored procedure volume | 78 stored procedures — significant but focused on reporting; no transaction processing |
| Cross-database dependencies | Moderate — depends on Atlys shared program master (undefined in repo) |
| Salesforce integration | Bidirectional integration requires Salesforce API work in Gen-3 |
| Regulatory sensitivity | No PCI CDE scope; ASC 606 revenue recognition logic in stored procedures |
| Compatibility mode upgrade | SQL 2005 compat mode (90) must be upgraded before any SQL 2016+ syntax is used |

**Migration blockers**:
1. **Atlys program master database** (`cursforecast` table host) must be identified and included in the migration scope
2. **Salesforce bidirectional integration** must be replanned using Salesforce REST/Bulk API before the stored procedure integration can be retired
3. **78 stored procedures** contain cross-tab reporting logic that must be validated for accuracy against the Gen-3 replacement
4. **Finance team dependency**: Revenue forecasting is a business-critical function; migration requires Finance team sign-off and parallel running during transition
