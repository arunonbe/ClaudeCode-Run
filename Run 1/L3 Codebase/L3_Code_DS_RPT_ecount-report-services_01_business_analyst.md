# DS_RPT_ecount-report-services — Business Analyst View

## Business Purpose
The central **SSRS (SQL Server Reporting Services) report library** for eCount — Wirecard North America's legacy prepaid card issuing platform. This project contains transactional, operational, compliance, finance, risk, and client-facing reports that support day-to-day operations of the prepaid card program. Reports span internal analytics, cardholder account activity, client-specific deliverables, ACH/payment processing, compliance monitoring, and financial reconciliation.

Per the README: "eCount is Wirecard North America's legacy issuing platform. The platform employs a collection of transactional reports written in SQL Server Reporting Services."

## Capabilities (Report Folders and Purposes)
| Folder | Business Function |
|---|---|
| Admin | Operational edits and admin-level reports (e.g., OP_Edits) |
| Analytics Reports | Analytical queries, revenue sharing, real-time credit line usage |
| Compliance | Regulatory compliance monitoring (e.g., Repetitive Fees Report for UDAAP/fee monitoring) |
| Customer Service | Balance transfer monitoring, IVR history/utilization, cardholder archived transactions, activation data |
| Customer-Specific Reports (Grifols, Maritz) | Client-dedicated custom report deliverables |
| Daily ACH Report | Daily ACH transaction reporting |
| External Report — Cardholder Activity | Cardholder-facing activity reports (ACH detail, card ship dates, issuance, payment details, PIN reports, DDA lookup, RAPID undeliverable cards, check details) |
| External Report — Client Activity | Client-level activity aggregations |
| External Report — Financial Reporting | Client financial statements |
| External Report — Exception Reports | Operational exception monitoring |
| External Report — BIN Reports | BIN-level program reporting |
| External Report — Administrative Reports | Client administrative reports |
| Finance | Internal financial reports (ATM fee credits, banker audit, revenue share) |
| Finance.CANADA | Canadian finance reports |
| Finance.Revenue Share | Revenue sharing reports |
| Internal Reports | Internal operational reports |
| IT / IT.Reports Monitoring | IT system and report server monitoring |
| Risk / Risk and Control | AML reports, risk monitoring |
| Secured Reports | Sensitive financial reports (aggregate spending with dollars, interchange rebate, location codes) |
| Vendor Management | Vendor-level reporting |
| Warehouse / Warehouse.DWH_reports | Data warehouse reports |
| Monthly Processing / Canada | Monthly cycle reports |

## Key Entities
| Entity | Reports |
|---|---|
| Cardholder / Member | Archived transactions, enrollment, activation, DDA profile, PIN, RAPID |
| Payment / Transaction | ACH detail, payment detail, reversal, check detail, utilization |
| Card / DDA | Ship date, activation status, DDA lookup, undeliverable cards |
| Program / BIN | Aggregate issuance, spending, BIN reports, location codes |
| Client | Client activity, custom reports (Grifols, Maritz, Subaru, TXU, Enservio) |
| Fee | Repetitive Fees (Compliance), ATM out-of-network fees, interchange rebate |
| IVR | IVR history, IVR utilization, IVR status |
| ACH / IEFT | ACH detail, daily ACH, merchant spend and ACH withdraw |
| Check | Check detail, refund checks, claimable payments |
| Revenue Share | Finance.Revenue Share reports |

## Business Rules
- Repetitive Fees Report (`Compliance\`) accepts `startdt`, `enddt`, `frequency`, `Threshold`, `defaultdays` — monitors for fee patterns that may indicate UDAAP violations.
- Cardholder Archived Transactions renders a Visa/Mastercard issuer disclosure based on the card BIN prefix (5 = Mastercard, other = Visa); issuer is Sunrise Banks N.A.
- Secured Reports are a separate SSRS folder with restricted access — `Interchange Rebate Report`, `Aggregate Spending with Total Dollars` are finance-sensitive.
- Canadian vs US separation is maintained via Finance.CANADA folder and separate data sources (ECAN, ECNT vs EcountCore).
- Customer-specific reports (Grifols, Maritz, Subaru, TXU) represent contractual reporting obligations.

## Compliance Relevance
- **Repetitive Fees Report** — direct UDAAP compliance monitoring tool.
- **ACH Detail Reports** — NACHA record-keeping support.
- **Cardholder Activity reports** — Reg E dispute support (transaction history for cardholders).
- **AML Reports (Risk folder)** — AML/CTF monitoring as required under BSA/FFIEC.
- **Interchange Rebate / Revenue Share** — SOC 1 financial accuracy.
- **PIN Change Report, PIN Selection Status** — PCI DSS PIN management audit.
- **PIPEDA/Quebec Law 25** — Canadian cardholder data in Finance.CANADA reports.

## Risks (Business)
1. **Wirecard North America attribution** — README explicitly states this is for "Wirecard North America's legacy issuing platform"; brand/entity must be updated.
2. **Retired Reports folder** — significant volume of retired/archived reports committed to the repo including BIN Migration archives, QBE, FluCare, Durbin — these increase repo size and create confusion.
3. **Client-specific reports for current clients** (Grifols, Maritz) — contractual delivery obligations; changes require client notification.
4. **Secured Reports access** — `Interchange Rebate` and financial reports must remain properly access-controlled on SSRS server.
5. **No SLA or retention policy** visible for report output.
