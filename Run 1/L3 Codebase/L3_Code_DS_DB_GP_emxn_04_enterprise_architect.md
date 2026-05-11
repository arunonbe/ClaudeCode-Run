# DS_DB_GP_emxn — Enterprise Architect Report

## 1. Platform Generation Assessment

`DS_DB_GP_emxn` is a **Generation 1 (Legacy ERP)** system on Onbe's platform. It represents a Microsoft Dynamics GP (formerly Great Plains) installation that pre-dates Onbe's microservices era. The database runs at SQL Server 2008 compatibility level (compat 100), indicating the schema was likely created and last structurally redesigned between 2008 and 2012. Onbe's newer services (jobsvc, ordersvc, notificationsvc, nexpay) run at SQL Server 2016–2019 compatibility levels.

## 2. Role in Onbe's Architecture

### 2.1 Position in the Platform Stack

```
┌────────────────────────────────────────────────────────────────────┐
│                     ONBE PLATFORM (East)                           │
├──────────────────────┬─────────────────────────────────────────────┤
│  BACK-OFFICE ERP     │  CORE PAYMENTS PLATFORM                     │
│  (Generation 1)      │  (Generation 2/3)                           │
│                      │                                             │
│  DS_DB_GP_emxn  ─────┼──► DS_ETL_finance-gp                       │
│  DS_DB_GP_two        │    DS_ETL_great-plains                      │
│  DS_DB_GP_EAST       │    DS_DB_prepaid_warehouse                  │
│  DS_DB_GP_ecan       │                                             │
│  DS_DB_GP_ecnt       │  [jobsvc] [ordersvc] [notificationsvc]      │
│  DS_DB_GP_emeam      │  [nexpay_claimable] [ecountcore]            │
└──────────────────────┴─────────────────────────────────────────────┘
```

GP EMXN sits entirely in the **back-office ERP tier**. It is not in the critical payment processing path (no prepaid card issuance, no ACH processing) but receives financial journal entries that represent the accounting results of payment operations processed upstream.

### 2.2 Entity Scope
EMXN represents the **Mexico legal entity** within Onbe's multi-entity GP deployment. Other GP entities:
- `GP_EAST` — Onbe East US entity (primary)
- `GP_two` — Second US entity or shared services entity
- `GP_ecan` — ECount Canada
- `GP_ecnt` — ECount entity
- `GP_emeam` — ECount EMEA (Europe, Middle East, Africa)
- `GP_emxn` — **ECount Mexico (this repo)**

Each GP database is a separate SQL Server database with identical schema structure but different data, linked via GP's intercompany framework.

## 3. Upstream and Downstream Dependencies

### 3.1 Upstream (feeds into EMXN)
| System | Data Flow | Mechanism |
|--------|-----------|-----------|
| Onbe EcountCore | Financial settlement journals | Manual GP entry or eConnect API |
| Accounts Payable team | Vendor invoices | Manual GP input |
| Payroll system | Payroll journal entries | GP UPR module or integration |
| Treasury | Bank reconciliation data | GP CM module |

### 3.2 Downstream (EMXN feeds out)
| System | Data Flow | Mechanism |
|--------|-----------|-----------|
| `DS_ETL_finance-gp` | Financial data extraction | Talend/SSIS ETL reading GP tables |
| `DS_ETL_great-plains` | Full GP extract to ODS/warehouse | Scheduled ETL |
| `DS_DB_prepaid_warehouse` | Aggregated financial KPIs | Via warehouse ETL |
| Reporting (Crystal Reports) | Invoice and financial reports | `DS_RPT_crystal-invoice-templates-us` |
| External auditors | Financial statements | Ad-hoc SQL/SSRS reports |

## 4. Integration Architecture

### 4.1 eConnect API
GP exposes the `taCreate*` stored procedures as the **eConnect API** layer — an XML-over-SP integration mechanism that allows external systems to post transactions into GP without bypassing business rules. The presence of `TA_DATE` and `TA_DBNAME` defaults confirms eConnect is enabled.

### 4.2 Analytical Accounting Integration
The `aag*` stored procedures (Analytical Accounting) allow dimensional cost allocation that feeds downstream BI tools. This is relevant for multi-entity cost reallocation between EMXN and other Onbe GP entities.

### 4.3 Service Management Integration
The `ASI*` and `SVC*` tables/views suggest field service or contract management integration — possibly tied to hardware (POS devices, card terminals) deployed in Mexico.

## 5. Technical Standards Compliance

| Standard | Status | Notes |
|----------|--------|-------|
| SQL Server version | Non-compliant | Compat 100 = SQL 2008 EOL |
| TDE at rest encryption | Non-compliant | `IsEncryptionOn=False` |
| Change tracking / CDC | Non-compliant | Not enabled |
| Named individual logins | Non-compliant | ~200 personal SQL logins |
| SSDT project structure | Compliant | Proper SSDT `.sqlproj` format |
| Source control | Compliant | GitLab managed |
| Secrets in code | Compliant | No credentials committed |

## 6. Migration Complexity Assessment

### 6.1 Complexity Score: VERY HIGH

| Dimension | Score | Rationale |
|-----------|-------|-----------|
| Schema size | 5/5 | 1,078 tables, 16,594 SPs, 193 functions |
| Vendor lock-in | 5/5 | Microsoft Dynamics GP proprietary schema |
| PII sensitivity | 4/5 | SSNs, DOBs, tax IDs present |
| Integration surface | 3/5 | ETL feeds, eConnect API, reporting |
| Data volume risk | 3/5 | Years of financial history |
| Business criticality | 4/5 | Financial ERP for Mexico entity |

### 6.2 Migration Scenarios

**Option A: Upgrade GP to Dynamics 365 Business Central**
- Estimated effort: 18–24 months
- Risk: Data migration of 1,078 tables; custom SPs must be rewritten
- Benefit: Modern SaaS ERP; resolves SQL 2008 EOL risk

**Option B: SQL Server upgrade (in-place or new server)**
- Estimated effort: 3–6 months
- Risk: GP app certification required for higher SQL Server versions
- Benefit: Resolves immediate EOL and TDE gap

**Option C: Retain as-is with mitigations**
- Estimated effort: 1–2 months (TDE, SQL upgrade)
- Risk: Continued technical debt; GP licensing costs
- Benefit: Minimal operational disruption

## 7. Relationship to NexPay / New Platform

GP EMXN has **no direct integration** with the NexPay microservices platform (`nexpay-*` repos). The architectural boundary is clean:
- NexPay handles real-time payment processing for claimable payments, card issuance, and recipient orchestration.
- GP handles ex-post financial accounting, payroll, and vendor management.
- The connection is via ETL pipelines that extract settlement totals from EcountCore → post to GP as journal entries.

This clean separation is architecturally sound and should be preserved during any modernisation effort.

## 8. Regulatory Architecture Considerations

Given EMXN is a Mexico-entity database:
- **CFDI (Comprobante Fiscal Digital por Internet)**: Mexican electronic invoicing mandate; GP may generate CFDI XML files that reference invoice data stored in `SOP10100`. Compliance with SAT requirements for digital invoicing must be validated.
- **DIOT (Declaración Informativa de Operaciones con Terceros)**: Monthly VAT reporting to SAT uses AP data from `PM10000` and `PM20000` tables.
- **Cross-border data transfer**: If EMXN data (especially employee PII in `UPR00100`) is processed on US infrastructure, LFPDPPP cross-border transfer provisions apply.
