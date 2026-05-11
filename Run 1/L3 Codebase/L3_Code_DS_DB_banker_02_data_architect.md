# Data Architect Report: DS_DB_banker

## Overview

The `banker` SSDT database project contains approximately 20 `dbo` tables, 50 `dbo` stored procedures, 5 `dbo` functions, 10 `so` schema tables, 50 `so` schema stored procedures, 3 `so` views, 2 `onus` schema tables, 1 `onus` stored procedure, and a `Storage` partition function/scheme. The database serves as the fund reservation and sales order automation layer for Onbe's Gen-1 prepaid card platform.

---

## Complete Database Object Inventory

### Tables — dbo schema (~20)

| Table | Purpose | Key Fields |
|---|---|---|
| `banker_approval_notification` | Fund approval workflow notifications | Program/promo, notification state |
| `banker_approval_notification_comment` | Comments on approval notifications | FK to notification |
| `banker_available_funds_rule` | Program/promo fund availability flags | `program_id`, `promotion_id`, availability flag |
| `banker_default_promo_exception_program` | Exception programs for default promo routing | Program config |
| `banker_group_amt_mapping` | Group-level amount mapping config | Group, amount thresholds |
| `banker_mult_sos` | Multiple sales order tracking (global only) | SO references |
| `banker_preset_funds_config` | Preset fund configuration | Program, preset amounts |
| `banker_program_datasource` | Maps program expressions to data source names | `program_expr`, `datasource_name` |
| `banker_reserved_source` | Core fund reservation ledger | PK: `(program_id, promotion_id, source_prefix, source_id, ref_source_id)`; `action`, `action_amount` BIGINT, `updated_by`, `update_date` |
| `banker_reserved_source_log` | Audit log of reservation changes | Same key fields + timestamps |
| `banker_temp_unsettled_sources` | Temporary working table for unsettled source analysis | Program/promo/source |
| `client_refund_process_status` | Client refund processing state machine | Process lifecycle |
| `client_refund_program_status` | Program-level refund status | Program state |
| `cpp_loop_process_status` | CPP batch loop processing state | `id`, `start_dt`, `end_dt` — FK target for `so.order_status` |
| `fee_aggregation_core_5_24_2018` | Date-stamped backup of fee aggregation core | Historical backup — orphaned |
| `fee_aggregation_items_5_24_2018` | Date-stamped backup of fee aggregation items | Historical backup — orphaned |
| `Nick_Logging_JVC_Orders` | Developer debug logging table (named after developer) | `order_status_id`, `order_id`, `order_src`, `run_date`, `is_test` |
| `Nick_Logging_JVC_Order_Details` | Developer debug logging detail (named after developer) | Order detail fields |
| `reporting_server_check` | Server availability check state | Server check timestamps |
| `SSISConfigurations` | SSIS package configuration key-value store | `ConfigurationFilter`, `ConfiguredValue`, `PackagePath`, `ConfiguredValueType`, `ModifiedDate` (auto-updated by trigger) |
| `SSISJobConfigurations` | SSIS job configuration | Job config |
| `SSISJobConfigurations_backup` | Backup of SSIS job config — orphaned | Historical backup |

### Tables — so schema (~10)

| Table | Purpose | Key Fields |
|---|---|---|
| `fee_aggregation_core` | Fee aggregation core results | Program, promo, customer, run_date, amounts |
| `fee_aggregation_day_status` | Daily aggregation run status | `id`, `run_date`, step state |
| `fee_aggregation_fee_type` | Fee type reference | Fee type definitions |
| `fee_aggregation_items` | Item-level fee aggregation | `program`, `promo`, `fee_customer`, `is_test`, amounts |
| `fee_aggregation_items_and_stored_procs` | Mapping of items to aggregation procedures | Configuration |
| `fee_aggregation_program_status` | Program-level aggregation status | `program`, `promo`, `day_id`, `step` |
| `fee_invoicing_customer_status` | Customer invoice creation state | `fee_customer`, `period_id`, `step`, `aggregation_failed`, `attempt_count`, `attempts_exceeded` |
| `fee_invoicing_period_status` | Invoice period state | `id`, `start_dt`, `end_dt`, period lifecycle |
| `fees_and_items` | Fee and item cross-reference | Mapping config |
| `FWSAuditTable` | Financial web service audit trail | Audit fields |
| `items_to_actions` | Maps items to processing actions | Config |
| `order_detail` | Sales order line items | `program`, `promo`, `quantity`, `amount`, `item_code`; FK to `so.order_status` |
| `order_status` | Sales order processing state machine | `id`, `process_id` (FK to `cpp_loop_process_status`), `customer_id`, `step`, `attempt_count`, `attempts_exceeded`, `last_run_dt` (auto-updated by trigger) |
| `PrepaidCustomerBalanceHistory` | Daily credit line snapshots | `CreditLimit`, `InvoiceTotals`, `PaymentTotals`, `SalesOrderTotals`, `CreditTotals`, `CustomerBalance` (all MONEY type) |
| `PrepaidCustomerBalanceHistory_Backup` | Backup copy — orphaned | Historical backup |
| `PrepaidCustomerBalanceHistory_ForMovingCompany` | Balance history for program migrations | Migration-specific fields |
| `void_status` | Void processing status | Void lifecycle state |

### Tables — onus schema (2)

| Table | Purpose |
|---|---|
| `onus.program_status` | OnUS transaction processing state by program |
| `onus.item_detail` | OnUS item detail records |

### Views (1)

| View | Schema | Purpose |
|---|---|---|
| `gp_dbs` | `so` | Maps GP server/database names to program prefixes; queries `Atlys_E..vPrgPrefixes`; filters to `ecnt` and `ecan` GP databases |

### Synonyms (10)

| Synonym | Schema | Points To | Purpose |
|---|---|---|---|
| `na_ordersvc_get_orders` | `dbo` | `[REPORTINGDBSERVER].[cf_report].[so].[ordersvc_get_orders]` | NA order service data source |
| `na_jobsvc_get_orders` | `dbo` | `[REPORTINGDBSERVER].[cf_report].[so].[jobsvc_get_orders]` | NA job service data source |
| `na_ordersvc_get_fvd_for_order_xml` | `dbo` | `[REPORTINGDBSERVER].[cf_report].[so].[ordersvc_get_fvd_for_order_xml]` | NA FVD XML data |
| `na_jobsvc_get_fvd_for_order_xml` | `dbo` | `[REPORTINGDBSERVER].[cf_report].[so].[jobsvc_get_fvd_for_order_xml]` | NA job FVD XML |
| `na_void_get_orders` | `dbo` | `[REPORTINGDBSERVER].[cf_report].[so].[void_get_orders]` | NA void order data |
| `intl_ordersvc_get_orders` | `dbo` | `[REPORTINGDBSERVER].[cf_report].[so].[ordersvc_get_orders]` | International order service (currently commented out in ordersvc_get_orders.sql line 69) |
| `intl_jobsvc_get_orders` | `dbo` | `[REPORTINGDBSERVER].[cf_report].[so].[jobsvc_get_orders]` | International job service |
| `intl_ordersvc_get_fvd_for_order_xml` | `dbo` | `[REPORTINGDBSERVER].[cf_report].[so].[ordersvc_get_fvd_for_order_xml]` | International FVD XML |
| `intl_jobsvc_get_fvd_for_order_xml` | `dbo` | `[REPORTINGDBSERVER].[cf_report].[so].[jobsvc_get_fvd_for_order_xml]` | International job FVD XML |
| `intl_void_get_orders` | `dbo` | `[REPORTINGDBSERVER].[cf_report].[so].[void_get_orders]` | International void data |

All `intl_*` synonyms currently appear to be unused after post-migration simplification (see `ordersvc_get_orders.sql` line 69 comment).

### Storage Objects

| Object | Type | Purpose |
|---|---|---|
| `monthly_partition` | Partition Function | RANGE RIGHT partition function with boundaries from 2013-01 through 2016-12 (48 monthly partitions) |
| `monthly_scheme` | Partition Scheme | Partition scheme referencing `monthly_partition` |

The partition function (`Storage/monthly_partition.sql`) covers 2013–2016 only. It is not extended beyond 2016, indicating it may not be actively used for current data or is stale.

### Triggers

| Trigger | Table | Purpose |
|---|---|---|
| `SSISConfigurations_timestamp_trigger` | `dbo.SSISConfigurations` | Updates `ModifiedDate` on any row UPDATE |
| `order_status_timestamp_trigger` | `so.order_status` | Updates `last_run_dt` on any row UPDATE |

---

## Sensitive Data Field Assessment

### PCI DSS Cardholder Data
No PANs, CVVs, track data, or PIN data found in this database's schema definition. The database works with **program/promotion identifiers and financial amounts** only, not cardholder-level data.

### Financial Data
| Field | Table | Sensitivity |
|---|---|---|
| `action_amount` (BIGINT) | `banker_reserved_source` | Client fund reservation amounts — financially sensitive |
| `CreditLimit`, `InvoiceTotals`, `PaymentTotals`, `SalesOrderTotals`, `CreditTotals`, `CustomerBalance` (MONEY) | `so.PrepaidCustomerBalanceHistory` | Client credit line and balance data — high financial sensitivity |
| `amount` | `so.order_detail` | Sales order line amounts — financially sensitive |
| `ConfiguredValue` (NVARCHAR 4000) | `dbo.SSISConfigurations` | May contain connection strings, server names, file paths — potential credential risk |

### SSIS Configuration Risk
`SSISConfigurations.ConfiguredValue` is defined as `NVARCHAR(4000)` and typically stores SSIS package configuration values which may include database connection strings, server addresses, and file system paths. This table should be reviewed to confirm it does not store plaintext credentials or sensitive configuration values that would constitute a PCI DSS finding.

### Debug Logging Tables
`Nick_Logging_JVC_Orders` and `Nick_Logging_JVC_Order_Details` contain `customer_id`, `order_id`, `order_file_name`, and `is_test` fields. These tables were created for developer debugging (named after the developer "Nick") and should be reviewed for retention and potential data leakage of order processing state.

---

## Referential Integrity

| Relationship | Type |
|---|---|
| `so.order_status.process_id` → `dbo.cpp_loop_process_status.id` | FK constraint |
| `so.order_detail` → `so.order_status` | FK constraint (implied by schema) |

Most `dbo` schema tables have no foreign key constraints. The `banker_reserved_source_log` is structurally a log of `banker_reserved_source` but has no FK to enforce this relationship.

## Encryption

No column-level encryption. TDE at instance level should be confirmed. The `SSISConfigurations` table is a particular concern given that it may hold connection strings that could benefit from cell-level encryption or a secrets management solution.

## PCI DSS CDE Scope

**REVIEW REQUIRED — CDE ADJACENCY.** The `BankerAllSOView` and `BankerPayment` external views (not defined in this repository) are sourced from Great Plains and may contain settlement data adjacent to the CDE. The synonym chain `na_ordersvc_get_orders` → `REPORTINGDBSERVER.cf_report` reaches an external system whose CDE classification must be independently verified. No PANs or SAD data are stored in this database's own tables.

## Data Retention

No purge procedures found. `PrepaidCustomerBalanceHistory` accumulates daily balance snapshots indefinitely. The orphaned backup tables (`fee_aggregation_core_5_24_2018`, `fee_aggregation_items_5_24_2018`, `SSISJobConfigurations_backup`, `PrepaidCustomerBalanceHistory_Backup`) represent unmanaged data accumulation with no defined lifecycle.
