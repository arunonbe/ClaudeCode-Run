# DS_DB_GP_two — Enterprise Architect Report

## 1. Platform Generation Assessment

`DS_DB_GP_two` is a **Generation 1 (Legacy ERP)** system. It is structurally and technically equivalent to `DS_DB_GP_emxn` — both use the full Microsoft Dynamics GP schema at SQL Server 2008 compatibility. The "two" naming is ambiguous; it most likely indicates:

- **A second Onbe legal entity** in the US (common pattern: an operating company and a holding company, or a second business line)
- **An acquired entity**: If Onbe acquired another company that used GP, the acquired GP database may have been retained as "two"
- **A historical database**: Retained for reporting and compliance, but not actively processing new transactions

Without access to active GP configuration files (which would reveal the company name), the exact entity cannot be confirmed from schema analysis alone.

## 2. Role in Onbe's Architecture

GP_two occupies the same tier as all GP databases — **back-office ERP**, not in the payment processing critical path:

```
GP Family (Back-Office ERP Tier)
├── DS_DB_GP_EAST      — Primary US entity
├── DS_DB_GP_two       — Second entity (this repo)
├── DS_DB_GP_ecan      — Canada entity
├── DS_DB_GP_ecnt      — ECount entity
├── DS_DB_GP_emeam     — EMEA entity
└── DS_DB_GP_emxn      — Mexico entity
         ↓ (all feed via ETL)
DS_ETL_finance-gp / DS_ETL_great-plains
         ↓
DS_DB_prepaid_warehouse (reporting/analytics)
```

## 3. Differentiating Characteristics vs GP_EMXN

| Dimension | GP_EMXN | GP_two | Significance |
|-----------|---------|--------|-------------|
| Security model | ~200 named users | ~10 groups only | GP_two has better access governance |
| Tables2 count | 78 | 15 | GP_EMXN has more custom extensions |
| View count | 143 | 250 | GP_two has heavier custom reporting layer |
| SP count | 16,594 | 15,923 | Slightly smaller — fewer custom SPs |
| Entity type | Mexico legal entity | Unknown second entity | Entity clarification needed |

The 250 views in GP_two (vs 143 in EMXN) represent a meaningful investment in custom reporting. This suggests GP_two is actively consumed by finance/BI teams and may be the primary reporting-facing GP entity.

## 4. Integration Dependencies

### 4.1 Upstream Feeds
- Manual AP/GL entry by finance team
- eConnect API for automated transaction posting from Onbe systems
- GP intercompany framework for cross-entity journal entries

### 4.2 Downstream Consumers
| System | Purpose |
|--------|---------|
| `DS_ETL_great-plains` | Full extract to ODS/warehouse |
| `DS_ETL_finance-gp` | Finance-specific extraction pipeline |
| Crystal Reports (`DS_RPT_crystal-invoice-templates-us`) | US invoice and report rendering |
| `DS_DB_prepaid_warehouse` | Aggregated financial data for analytics |
| HP SiteScope (`NAM_sitescope_AD`) | Availability monitoring |

### 4.3 GP Intercompany Integration
GP supports intercompany transactions where GP_two may post entries against GP_EAST (or other entities). This creates data dependencies across GP databases. Any migration of GP_two must account for intercompany journal linkages.

## 5. Custom Reporting Architecture

The 250 views (107 more than GP_EMXN) suggest a custom reporting layer was developed specifically for GP_two. This is an architectural anti-pattern for GP — custom views on GP tables are fragile because GP upgrades may change underlying table structures, breaking the views silently. 

Recommendation: Document all 250 views, identify which are standard GP views versus Onbe-custom, and migrate custom reporting logic to a proper BI layer (e.g., `DS_DB_prepaid_warehouse` or a dedicated SSRS/Power BI layer).

## 6. Migration Complexity

### 6.1 Complexity Score: VERY HIGH (same as GP_EMXN)

| Dimension | Score | Rationale |
|-----------|-------|-----------|
| Schema size | 5/5 | 1,015 tables, 15,923 SPs, 250 views |
| Vendor lock-in | 5/5 | Dynamics GP proprietary schema |
| PII sensitivity | 4/5 | SSNs, DOBs, tax IDs |
| Custom reporting | 4/5 | 250 views — more than EMXN |
| Integration surface | 3/5 | ETL feeds, eConnect, reporting |
| Entity clarity | 2/5 | Entity identity not documented |

### 6.2 Entity Identity Risk
The **biggest architectural risk** for GP_two is the undefined entity name. Before any migration or modernisation planning:
1. Identify the legal entity name associated with GP_two by examining GP configuration tables (`SY00000`, `SY01500`) or contacting the Finance/Accounting team.
2. Determine whether GP_two is still actively transacting or read-only (historical).
3. Understand the intercompany relationship with GP_EAST and other GP entities.

## 7. Relationship to Payment Platform

GP_two has no direct relationship with NexPay microservices. Its only connection to the payment platform is through ETL pipelines that aggregate settlement financial data into GP as accounting entries. This separation is architecturally correct and should be maintained.

## 8. Regulatory Architecture

Same US regulatory framework as GP_EMXN for US-domiciled entities:
- **IRS**: W-2 (payroll), 1099 (vendor payments), corporate tax records
- **SOX-equivalent**: Financial data integrity controls (SOC 1)
- **GLBA**: If consumer financial data is processed
- **FLSA / DOL**: Payroll records retention (employee data in UPR tables)

If GP_two is actually an acquired foreign entity, additional international regulations may apply (analogous to EMXN's LFPDPPP obligations). This requires entity identity clarification.
