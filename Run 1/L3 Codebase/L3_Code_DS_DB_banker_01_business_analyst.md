# Business Analyst Report: DS_DB_banker

## Repository Identity

| Field | Value |
|---|---|
| Repository name | DS_DB_banker |
| Full meaning | Banker — financial order management and fund reservation system |
| Database project type | SQL Server Data Tools (SSDT) `.sqlproj` |
| Source files | ~20 dbo tables, ~50 dbo stored procedures, ~5 dbo functions, ~10 so tables, ~50 so stored procedures, ~3 so views, `onus` schema, `Storage` partition objects, Security files |
| Special role | **Fund reservation and sales order automation** — acts as an authorization/budget management layer between client fund commitments and Great Plains invoicing |

---

## Business Purpose

The `banker` database is Onbe's **financial settlement and sales order automation platform** for the Gen-1 prepaid card business. It manages the lifecycle of client fund commitments from initial reservation through to Great Plains (GP) invoice creation and final settlement. The system serves two primary functions:

1. **Fund Reservation**: Tracks which client funds have been reserved for specific program/promotion/source combinations, prevents over-commitment, and enables financial operations to know exactly what is settled versus unsettled at any point in time.

2. **Sales Order Automation**: Automates the creation of GP sales orders and invoices for fee-based services (plastic card production, fee invoicing, order service items). The `so` schema drives the complete lifecycle of automated invoicing: order detection, fee aggregation, GP invoice generation, and print queue management.

The database name "banker" reflects its role as the financial gatekeeper — analogous to an investment banker who tracks funds in, funds committed, and funds settled.

---

## Business Processes Supported

### 1. Fund Reservation and Settlement Determination
`banker_reserved_source` and `banker_reserved_source_log` track the reservation state of funds per program/promotion/source combination. `banker_get_unsettled_funds` (452 lines) is the core settlement determination engine: it queries `BankerAllSOView` (an external view of GP sales orders) to calculate how much of a reserved source has been settled via GP invoices versus what remains unsettled. This function is the answer to "has this client payment cleared through GP?" for every prepaid program.

`banker_get_payments` queries `BankerAllSOView` and `BankerPayment` (both external GP-linked views) to retrieve payment application details for a given program and source.

### 2. Automated Sales Order Creation (Order Service)
The `so.ordersvc_get_orders` procedure (created 02/15/2013 by Zach VanderVeen) is the core of the Sales Order Automation (SOA) system. It:
- Retrieves active customers via `so.get_active_customers`
- Gets pending orders via `na_ordersvc_get_orders` synonym (pointing to `REPORTINGDBSERVER.cf_report.so.ordersvc_get_orders`)
- Maps orders to GP customer IDs for invoice creation
- Inserts results into `so.order_status` and `so.order_detail` tables
- Tracks processing state through multiple steps (step 1 = new, step 0 = complete)

The commented-out `intl_ordersvc_get_orders` call at line 69 documents a post-migration simplification: international orders were removed from this procedure after migration to separate processing.

### 3. Fee Invoicing and Aggregation
`so.fee_invoicing_*` procedures manage the fee invoicing lifecycle:
- `fee_invoicing_get_customers` (160 lines with cursors): identifies GP customers for fee invoice creation, handles complex mapping exceptions between plastic (P) and fee (F) accounts in GP, uses cursors over `so.gp_dbs` to query multiple GP company databases
- `fee_invoicing_get_customer_invoice`: retrieves invoice data for a specific customer in a period
- `fee_aggregation_*` tables and procedures: aggregate daily fee data by program/promo/customer before invoice creation
- `fee_invoicing_update_customer_status`, `fee_invoicing_update_period_status`: advance workflow state

### 4. Customer Balance Tracking and Reporting
`so.PrepaidCustomerBalanceHistory` stores daily snapshots of customer credit positions with fields: `CreditLimit`, `InvoiceTotals`, `PaymentTotals`, `SalesOrderTotals`, `CreditTotals`, `CustomerBalance`. `PrepaidCaptureDailyBalances` and its variants (`_ForMovingCompany`, `_ForMovingCompany_International`, `_ForMovingCompany_International_CPGBP`) capture these snapshots with different regional/currency configurations.

`rpt_Customer_Bal_History` and `rpt_Customer_Bal_History_Detail` provide reporting over this history. `rpt_Customer_Bal_History_with_Migration_Phases` is a variant for program migration scenarios.

### 5. On-Us (OnUS) Processing
The `onus` schema contains `program_status` and `item_detail` tables with `onus\get_process_program_status.sql`. On-us transactions are prepaid card transactions processed in-house (the bank's own network) rather than through an external processor. These require separate tracking and reporting.

### 6. Client Refund Processing
`client_refund_process_status`, `client_refund_program_status` tables and `client_refund_process_foreach_loop`, `client_refund_get_process_program_status` procedures manage the client refund workflow.

### 7. SSIS ETL Configuration
`SSISConfigurations` and `SSISJobConfigurations` store SSIS package configuration data with connection strings, server paths, and processing parameters. `SSISConfigurations_timestamp_trigger` (`SSISConfigurations.sql` lines 15–23) auto-updates `ModifiedDate` on any update to track when SSIS configurations last changed.

### 8. Reporting and Auditing
Multiple `rpt_*` procedures provide operational reporting: `rpt_Aggregation_Test_Items`, `rpt_CPMXN_Daily_Report` (Mexico peso daily report), `rpt_Customer_Bal_History*`, `rpt_OnUS_API_Payable`, `rpt_OnUS_Error`, `rpt_so_fee_aggregation_day_status`. These feed operational dashboards and financial monitoring.

---

## Data Stored and Processed

| Category | Tables/Schema |
|---|---|
| Fund reservation | `dbo.banker_reserved_source`, `dbo.banker_reserved_source_log`, `dbo.banker_temp_unsettled_sources` |
| Fund configuration | `dbo.banker_available_funds_rule`, `dbo.banker_preset_funds_config`, `dbo.banker_program_datasource`, `dbo.banker_group_amt_mapping` |
| Approval workflows | `dbo.banker_approval_notification`, `dbo.banker_approval_notification_comment` |
| Sales order status | `so.order_status`, `so.order_detail`, `so.void_status` |
| Fee aggregation | `so.fee_aggregation_core`, `so.fee_aggregation_items`, `so.fee_aggregation_day_status`, `so.fee_aggregation_program_status`, `so.fee_aggregation_fee_type` |
| Fee invoicing | `so.fee_invoicing_customer_status`, `so.fee_invoicing_period_status` |
| Customer balance history | `so.PrepaidCustomerBalanceHistory`, `so.PrepaidCustomerBalanceHistory_ForMovingCompany` |
| Processing status | `dbo.cpp_loop_process_status`, `dbo.client_refund_process_status`, `dbo.client_refund_program_status` |
| OnUS | `onus.program_status`, `onus.item_detail` |
| SSIS config | `dbo.SSISConfigurations`, `dbo.SSISJobConfigurations`, `dbo.SSISJobConfigurations_backup` |
| Debug/logging | `dbo.Nick_Logging_JVC_Orders`, `dbo.Nick_Logging_JVC_Order_Details` |
| Historical fee data | `dbo.fee_aggregation_core_5_24_2018`, `dbo.fee_aggregation_items_5_24_2018` (date-stamped backups) |

---

## Business Rules in SQL

1. **Fund reservation integrity**: `banker_reserved_source` PK is `(program_id, promotion_id, source_prefix, source_id, ref_source_id)` — the composite key prevents duplicate reservations for the same source reference.

2. **Settlement window**: `banker_get_unsettled_funds` uses `GETDATE() - 120` (line 44) as a voided original SO filler date — a 120-day lookback window for voided sales order analysis.

3. **Monday/Friday date adjustment**: `rpt_Customer_Bal_History` applies a special date window when run on Mondays (lines 47–58): uses `GETDATE() - 2` as start date to capture weekend data, consistent with the same business day rule in `atlys_rvcr.sys_jobrun`.

4. **GP customer mapping**: `fee_invoicing_get_customers` implements a three-pass remapping algorithm (lines 81–113) when GP customer accounts are inactive, deleted, or unmapped: first tries mapping P accounts to F accounts, then P to main P, then all to main F account. This embeds business logic for how Onbe maps fee invoices to GP customer hierarchies.

5. **FVD range pricing**: `so.ordersvc_get_orders` header comment references JIRA `SQ-1633` (2020-12-11): "Enhance FVD Ranges to allow for % pricing" — a documented business rule change for Face Value Discount percentage-based pricing.

---

## Regulatory Relevance

| Regulation | Relevance |
|---|---|
| **PCI DSS** | External dependencies on `BankerAllSOView` and `BankerPayment` may contain settlement data adjacent to the CDE. No PANs or CVVs found in this database. `REPORTINGDBSERVER` synonym targets must be assessed for CDE adjacency. |
| **SOX** | Fund reservation and GP sales order creation are financially significant automated processes. Changes to `banker_get_unsettled_funds` logic directly impact financial reporting accuracy. |
| **Reg E** | The prepaid card fee aggregation and invoicing process determines what fees are charged to programs and ultimately to cardholders. |
| **NACHA** | OnUS and ACH item processing items are referenced in `so.item_ach_withdrawal`, `so.item_samedayach_withdrawal`. |

---

## Integration with Services

- **Great Plains ERP** (via `BankerAllSOView`, `BankerPayment`, `so.gp_dbs`): Primary settlement data source and invoice destination
- **REPORTINGDBSERVER** (`cf_report` database): Source of order service data via `na_ordersvc_get_orders` synonym
- **ATLYS_E**: Referenced in `so.gp_dbs` view (`Atlys_E..vPrgPrefixes`) for GP database mapping
- **Sales Order Automation (SOA) SSIS packages**: Consume `so` schema objects and `SSISConfigurations` data
- **banker_na database**: NA variant; shares the same schema pattern but has additional plastic billing and GP eConnect invoice creation capabilities
