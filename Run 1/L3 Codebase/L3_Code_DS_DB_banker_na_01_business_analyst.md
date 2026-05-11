# DS_DB_banker_na — Business Analyst View

## Business Purpose
`banker_na` is the **funds management and program financing database** for the North America (NA) region. It tracks the lifecycle of client program funding: how much money is available, how it is reserved against promotions/orders, approval workflows for funding operations, the rules that govern when funds can be released, and the status of plastic card manufacturing and shipment orders. It also manages SSIS-driven data-processing connections for card-reissuance (expiry processing) and the invoicing interface to Great Plains (Dynamics GP) for card-manufacturing billing.

## Business Capabilities
- **Funds reservation and release**: records the current state of reserved funds per program/promotion, the source of those funds, and the action taken on them (reserve, release, adjust).
- **Available-funds rule configuration**: governs whether a given program/promotion has available-funds calculation turned on or off.
- **Preset funds configuration**: stores fixed-ratio and base-amount configurations for automatic fund pre-loading.
- **Group amount mapping**: maps user groups to funding amounts for approval-tier purposes.
- **Approval notification workflow**: tracks pending approval notifications for funding actions, including notification counts, banker level, and responsible managers.
- **Action logging**: persists a full audit trail of every banker action (reserve, release, credit, adjustment) with balance snapshot data.
- **Plastic card expiry processing**: identifies cards approaching expiration, drives re-issue workflows, and records processing status and invoicing data.
- **GP invoice creation**: generates eConnect-formatted invoice records for card-manufacturing billing into Dynamics GP.
- **ONUS process management**: tracks ONUS (on-us card) job processing status and program status for batch reconciliation.
- **SSIS configuration**: stores runtime connection strings and configuration values for SSIS packages that drive expiry and billing ETL.

## Business Entities
| Entity | Table(s) | Description |
|---|---|---|
| Available funds rule | `banker_available_funds_rule` | On/off flag per program/promotion |
| Preset funds config | `banker_preset_funds_config` | Ratio and base-amount for auto-load |
| Reserved source | `banker_reserved_source` | Current reserved-funds state per program/promo/source |
| Reserved source log | `banker_reserved_source_log` | Historical log of reserved-source changes |
| Group amount mapping | `banker_group_amt_mapping` | User-group to amount tier mapping |
| Program datasource | `banker_program_datasource` | SSIS datasource name per program |
| Approval notification | `banker_approval_notification` | Pending approval alerts with manager names and amounts |
| Approval notification comment | `banker_approval_notification_comment` | Comments on approval notifications |
| Default promo exception | `banker_default_promo_exception_program` | Programs exempt from default promotion rules |
| Temp unsettled sources | `banker_temp_unsettled_sources` | Transient staging for unsettled fund sources |
| Action log | `banker_action_log` (referenced in proc, not in visible tables DDL — likely in a synonym-linked database) | Full audit of every banker action |
| Plastic processing | `ab_process_plastic_processing`, `ab_process_plastic_status`, `ab_process_plastic_connections`, `ab_process_plastic_price`, `ab_process_plastic_finance_mapping` | Card expiry re-issue processing lifecycle |
| GP eConnect invoice | `gp_process_econnect_invoice`, `gp_process_econnect_invoice_component`, `gp_process_econnect_invoice_line_insert`, `gp_process_econnect_reference` | GP billing integration staging |
| ONUS process | `onus_process_status`, `onus_program_status` | ONUS batch job tracking |
| SSIS configuration | `SSISConfigurations` | SSIS runtime configuration store |

## Business Rules & Validations
- A program/promotion combination can have available-funds calculation toggled on or off (`banker_available_funds_rule.on_off_flag BIT`).
- `banker_preset_funds_config.preset_ratio` is a `TINYINT` (0-255), representing a percentage ratio; any value above 100 would be arithmetically invalid but is not constrained at the database level.
- `banker_reserved_source.action_amount` is `BIGINT`, representing amounts in the smallest currency unit (cents); the field `num_promos_in_source` is nullable, allowing partial source configurations.
- `banker_approval_notification.notification_sent_counter` is `TINYINT`; a counter reset or overflow could cause duplicate approval sends.
- `banker_approval_notification.source_amount` is `BIGINT` (cents); the `currency_symbol` column stores the symbol as `VARCHAR(50)`, accommodating multi-currency programs.
- Plastic expiry processing (`ab_process_plastic_get_expiring_sp`) selects cards within a requested date range; it joins the expiry view (`ab_process_plastic_expiring_vw`) against an account view (`ab_process_plastic_account_vw`) on DDA number and member ID, then records any errors via `ab_process_plastic_update_status_sp`.
- GP invoice generation (`gp_process_create_Invoice_sp`) creates eConnect-formatted invoice records; the `gp_process_econnect_reference` table tracks reference identifiers to avoid duplicate invoice creation.

## Business Flows
1. **Fund reservation**: When a client or system reserves funds for a promotion, a row is inserted into `banker_reserved_source`; balance data (posted balance, free funds, reserved funds, 1/2/3 day totals) is logged to `banker_action_log` via `banker_insert_action_log`.
2. **Approval workflow**: Large fund movements trigger an approval notification via `banker_approval_notification`; the workflow tracks notification counter and banker level until approved or expired.
3. **Card expiry re-issue**: A scheduled SSIS job calls `ab_process_plastic_get_expiring_sp` with a date range, retrieves expiring cards from the linked `ecountcore_ss` database via synonyms, and drives re-issue processing with status updates.
4. **GP invoice**: `gp_process_create_Invoice_sp` populates `gp_process_econnect_invoice*` tables; an external SSIS package then submits these to GP via eConnect.
5. **ONUS reconciliation**: `onus_process_foreach_loop` iterates over program statuses and updates `onus_process_status` and `onus_program_status`.

## Compliance & Regulatory Concerns
- **`banker_reserved_source`** stores financial amounts (`action_amount BIGINT`, representing cents) and program/promotion identifiers. These amounts are not PAN data, but they represent client fund balances — regulated as payment float under bank program agreements and relevant to Reg E and GLBA safeguards.
- **Approval notification stores full manager names** (`program_mgr_full_name`, `relation_mgr_full_name` — `VARCHAR(50)`): PII subject to GLBA/CCPA if stored beyond operational necessity.
- **`banker_insert_action_log` comment**: "Created by i-Flex" (2008-10-22) — the system records `action_performed_by VARCHAR(200)`, which may contain user identifiers subject to access review under SOX/GLBA.
- **DDA number in expiry processing**: The `ab_process_plastic_expiring_vw` and `ab_process_plastic_account_vw` views join on `dda_number` — a Demand Deposit Account number, which is sensitive financial account data under Reg E and PCI DSS scope (if associated with card accounts).
- **SSIS `SSISConfigurations` table**: Stores connection strings (`ConfiguredValue NVARCHAR(255)`) and package paths; if connection strings contain database credentials or server names, this is a secrets-management risk.
- **Synonyms reference `ppamwdcudsql1c1\ppamwdcudsql1c1.ecountcore_ss`**: A hardcoded SQL Server instance name in synonym definitions is an infrastructure disclosure risk and a brittle configuration pattern.

## Business Risks
- **Duplicate approval notifications**: The `notification_sent_counter TINYINT` field with no database-enforced uniqueness constraint means that concurrent processes could send duplicate approval notifications, violating segregation-of-duties controls.
- **No referential integrity between `banker_reserved_source` and core card tables**: The `program_id` and `promotion_id` columns are plain VARCHAR; there is no foreign key to a program master, meaning orphaned reservation records are possible.
- **Hardcoded server name in synonyms**: `syn_fdr_card_account`, `syn_core_device_ecard` etc. all reference `[ppamwdcudsql1c1\ppamwdcudsql1c1].[ecountcore_ss].[dbo].*` — any server rename or failover will break the plastic processing workflow immediately.
- **`BIGINT` amounts**: All monetary amounts are stored as integer cent values. If the calling application passes decimal values or uses incorrect conversion, silent rounding errors will corrupt fund balances.
- **No constraint on `preset_ratio`**: A misconfigured ratio above 100 would cause over-allocation of funds; no database-level guard exists.
