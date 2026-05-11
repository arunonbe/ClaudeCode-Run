# Business Analyst View — DS_CCP_ccp-report-services

## Business Purpose
The CCP-Report-Services project is a SQL Server Reporting Services (SSRS 2017) solution that provides operational, financial, compliance, and management reporting for the CCP prepaid card program. It delivers reports to multiple internal business audiences including Finance, Client Services, Fraud/Risk, Admin, Analytics, and external BIN bank partners. Reports draw from three data sources: the ODS (operational real-time), the DWH (Oracle data warehouse for historical/analytical data), and WIRED (SQL Server reporting database with cached views and parameter lookup functions).

## Report Catalog by Business Audience
### Finance
| Report | Business Purpose |
|--------|----------------|
| `FIS - Client Daily Fee Summary.rdl` | Daily fee summary by financial institution and date range; filters by Bank parameter |
| `FIS - Processor Settlement.rdl` | FIS processor settlement detail |
| `Program Balance Report.rdl` | Program-level balance from `cache_pbr` (brand/promotion/virtual corporate account/balance) |
| `Program Balance Report Plus Fee.rdl` | Program balance including fee data |

### BIN Banks
| Report | Business Purpose |
|--------|----------------|
| `Network Settlement Report.rdl` | Network settlement by date, system, type, code, amounts, fees, association; uses `dbo.RptNetworkSettlementReport` stored procedure |

### Client Services — Exception
| Report | Business Purpose |
|--------|----------------|
| `Aggregate Spending with Total Dollars.rdl` | Spending aggregates with dollar totals |
| `Cardholder Account Management.rdl` | Cardholder inventory: Partner User ID, Ecount ID, Account Status, Create/Modify/Expire dates, last 4 digits of card, card expiration, cardholder info, PUD fields, activity/last-activity date, role, activation status. Uses Oracle DWH stored procedure `PKG_NAM_CLIE_CAM_DATA.GET_DATA` |

### Client Services — Operations
| Report | Business Purpose |
|--------|----------------|
| `Aggregate Spending.rdl` | Client-level spending aggregates |
| `Card Ship Date.rdl` | Card shipment dates |
| `RAPID Undeliverable Cards Report.rdl` | Cards that could not be delivered (return-to-sender / address issues) |

### Fraud
| Report | Business Purpose |
|--------|----------------|
| `Unposted Transactions.rdl` | Unposted (pending/authorization-only) transactions for fraud monitoring; uses `rpt_Unposted_Transactions` stored procedure on ODS; includes Card Number, Transaction Code, Amount, Date/Time, Transaction ID |

### Home (Management / Admin)
| Report | Business Purpose |
|--------|----------------|
| `Report Catalog.rdl` | Master list of all available reports |
| `Subscription Requests.rdl` | Report subscription management |
| `Subscription Status.rdl` | Status of scheduled report subscriptions |

## Key Business Entities in Reports
- **Program / Brand / Promotion** — prepaid card program hierarchy
- **Cardholder** — account holder with status, dates, card details, PUD fields
- **Transaction** — posted and unposted payments with amounts, dates, codes
- **Settlement** — network and processor settlement with amounts by association
- **Fee** — daily fees by institution and client
- **Balance** — program-level posted, pending, and available balances
- **Virtual Corporate Account** — funding account linked to program/promotion

## Business Rules / Report Parameters
- Most reports accept `Frequency` parameter drawn from `vw_param_Frequencies` (WIRED) supporting: Daily, Weekly, Bi-Weekly, Last 6 Weeks, Past 2/3/7/14/30/60 days, Next 30 Days, MTD, Monthly, Past 6 Months, YTD, Life of Program, Quarterly, Custom (with explicit start/end dates).
- `Program Balance Report` filters by `brand_name` against `[WIRED].[dbo].[cache_pbr]`.
- `Cardholder Account Management` filters by Brand, Loading Number Prefix, Date Type, Start/End Date, Activity Threshold.
- `Network Settlement Report` filters by Date, Frequency, Bank, Report type.
- `Unposted Transactions` filters by Date range.

## Compliance Relevance
- `Cardholder Account Management` includes last-4 digits of card, expiration date, cardholder PII — subject to PCI DSS Requirement 7 (access control) and GLBA.
- `Unposted Transactions` includes full `Card Number` field via `rpt_Unposted_Transactions` stored procedure — **confirmed CDE scope.**
- Finance reports support SOC 1 financial controls (program balance, settlement reconciliation).
- Network Settlement Report supports NACHA reconciliation.

## Risks
- Reports expose Card Number via the `Unposted Transactions` report — access control on the SSRS server is critical.
- Reports are subscribed and scheduled (`Subscription Requests`, `Subscription Status`) — if subscription email lists are not maintained, PII/CDE data could be sent to stale recipients.
- DWH (`Munich DWH_Dev.rds`) data source reference suggests a dev/non-production alias may be in use for some reports.
