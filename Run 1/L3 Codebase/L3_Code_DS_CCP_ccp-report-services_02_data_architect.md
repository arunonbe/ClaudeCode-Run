# Data Architect View — DS_CCP_ccp-report-services

## Data Sources
| Source | Type | Connection String | Auth | Used By |
|--------|------|------------------|------|---------|
| ODS | SQL Server | `Data Source=t-phl-db01;Initial Catalog=ODS` | Integrated Security (Windows) | Fraud, BIN Banks, Finance, Client Services |
| WIRED | SQL Server | `Data Source=t-phl-db01;Initial Catalog=WIRED` | Integrated Security (Windows) | Parameter lookups (frequencies), Program Balance Report, some report frames |
| DWH (prod) | Oracle | `DATA SOURCE=DWH_AWS_SSH` | (credentials on SSRS server) | Cardholder Account Management (DWH_Dev.rds alias used in dev) |
| Munich DWH_Dev | Oracle | Dev alias | Dev/QA only | Dev versions of DWH-backed reports |
| ReportServer | SSRS metadata | `Home\ReportServer.rds` | (SSRS built-in) | Home/admin reports |

## Schema: Key Stored Procedures and Tables
### ODS
| Object | Type | Used By |
|--------|------|---------|
| `rpt_Unposted_Transactions(@startdt, @enddt)` | Stored procedure | Unposted Transactions (Fraud) |
| `dbo.RptNetworkSettlementReport(@StartDate, @EndDate, @Frequency, @Bank, @Report)` | Stored procedure | Network Settlement Report (BIN Banks) |

### WIRED
| Object | Type | Used By |
|--------|------|---------|
| `vw_param_Frequencies` | View | All reports — date range parameter lookup |
| `[dbo].[cache_pbr]` | Table (cache) | Program Balance Report — columns: brand_name, promotion_id, virtual_corporate_account, corporate_client_name, Date, Document Name, QTY, Description, JOB, Status, Processed Invoices, Payments, Credits, Debits, Posted Balance, Pending Amount, Available Balance |

### DWH (Oracle)
| Object | Type | Used By |
|--------|------|---------|
| `PKG_NAM_CLIE_CAM_DATA.GET_DATA(P_BRAND_NAME, P_BRAND_AFFILIATE, P_START_DATE, P_END_DATE, P_DATE_TYPE, P_ACTIVITY_THRESHOLD)` | Oracle package procedure | Cardholder Account Management |

## Sensitive Data in Reports
| Report | Field | Classification | PCI DSS Scope |
|--------|-------|---------------|---------------|
| Unposted Transactions | `Card Number` | PAN | **YES — CDE** |
| Unposted Transactions | `Transaction Amount`, `Transaction Date`, `Transaction ID` | Financial | Partial |
| Cardholder Account Management | Last 4 digits of card, card expiration date | Truncated PAN | PCI DSS Req 3.4 (truncated = allowed) |
| Cardholder Account Management | Partner User ID, Ecount ID, Account Status, PUD fields | PII / operational | GLBA / CCPA |
| Program Balance Report | Posted Balance, Pending Amount, Available Balance | Financial | SOC 1 |
| FIS - Client Daily Fee Summary | Fee amounts by institution | Financial | NACHA |

## Report Folder Structure and Data Source Matrix
| Folder | Data Sources Used |
|--------|-----------------|
| Admin | ODS, DWH (prod + dev), WIRED |
| Analytics | (project file only; no RDL files present) |
| BIN Banks | ODS, WIRED |
| Client Custom | (project file only) |
| Client Services - Exception | ODS, DWH (dev), WIRED |
| Client Services - Operations | ODS, DWH (dev), WIRED |
| Finance | ODS, DWH (prod + dev), WIRED |
| Fraud | ODS, WIRED |
| Home | SSRS ReportServer metadata |
| Templates | ODS (template structure only) |
| UAT | (project file only) |
| Vendor Management | (project file only) |

## Data Quality / Architecture Notes
- `cache_pbr` in WIRED is a **cached/denormalised table** — its freshness depends on a separate cache-refresh process not visible in this repository.
- `vw_param_Frequencies` drives all date parameter dropdowns — if this view is stale or missing from WIRED, all parameterised reports break.
- `Munich DWH_Dev.rds` is a dev-only Oracle data source pointing to a dev/staging DWH; reports in some folders use this instead of the production DWH — **risk of dev data being shown if data source reference is not overridden at deploy time.**

## Compliance Gaps
1. **PCI DSS Req 3.4** — `rpt_Unposted_Transactions` returns full Card Number. The Fraud report must be access-controlled (need-to-know, role-based); confirm SSRS row-level security or folder-level permissions.
2. **PCI DSS Req 7** — No row-level security in SSRS reports; access is controlled only at the folder/item level on the SSRS server.
3. **PCI DSS Req 10** — No audit log of who ran the Unposted Transactions or Cardholder Account Management report.
4. **GLBA / CCPA** — Cardholder personal data (name, address, DOB proxies via PUD fields) is accessible via Cardholder Account Management report; data minimisation review recommended.
5. **Dev data source** — `Munich DWH_Dev.rds` used in Client Services Exception / Operations — if deployed to production without overriding to production DWH, reports expose dev/non-production data.
