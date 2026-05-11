# DS_DB_banker_na — Solution Architect View

## Technical Architecture
- **Engine**: SQL Server (SSDT `Sql100DatabaseSchemaProvider`, SQL Server 2008 schema-level).
- **Project format**: SSDT `.sqlproj` / MSBuild DACPAC.
- **Schema**: Single `dbo` schema; approximately 20 tables, 30+ stored procedures, 7 synonyms, 2 views, multiple security role files.
- **Cross-database access pattern**:
  - Synonyms for `ecountcore_ss` objects (shallow abstraction with hardcoded server name in DDL).
  - Direct procedure call to external `banker_action_log` table in `jobsvc` database from `banker_insert_action_log`.
  - Synonym `syn_ItemPricePerContractPlusKit` for GP pricing.
- **SSIS configuration**: `SSISConfigurations` table (legacy SSIS package configuration model, pre-SSISDB).
- **Data types**: Amounts stored as `BIGINT` (integer cents) in reservation tables; `NUMERIC(10,2)` in the action log procedure parameters. This inconsistency between integer-cent storage and decimal procedure parameters is a conversion risk.

## API Surface
Stored procedures grouped by functional area:

| Group | Procedures |
|---|---|
| Banker funds | `banker_get_reserved_source(s)`, `banker_insert_action_log`, `banker_get_avialable_funds_rule_info` [sic], `banker_get_preset_funds_configs`, `banker_update_preset_funds_config(s)`, `banker_update_reserved_source`, `banker_delete_reserved_source(s)`, `banker_update_program_datasource`, `banker_delete_program_datasource` |
| Banker workflow | `banker_get_approval_notification_counter`, `banker_update_approval_notification`, `banker_update_email_status_info`, `banker_get_user_group_info`, `banker_get_user_group_amount_info`, `banker_get_user_info_by_group_name`, `banker_get_job_info`, `banker_get_jobsvc_job_info`, `banker_get_job_promotion_id`, `banker_insert_jobs_data` |
| Plastic processing | `ab_process_plastic_get_expiring_sp`, `ab_process_plastic_get_dates_sp`, `ab_process_plastic_foreach_loop_sp`, `ab_process_plastic_insert_status_sp`, `ab_process_plastic_update_status_sp`, `ab_process_plastic_invoice_sp`, `ab_process_plastic_gp_ItemPricePerContractPlusKit_sp`, `ab_process_plastic_set_synonyms_for_ssis_sp` |
| GP invoice | `gp_process_create_Invoice_sp` |
| ONUS | `onus_get_process_program_status`, `onus_item_price_per_contract`, `onus_process_foreach_loop` |
| Reporting | `rpt_Banker_Audit` |

Notable: `ab_process_plastic_set_synonyms_for_ssis_sp` — a procedure that dynamically sets synonyms, indicating the synonym targets are changed at runtime for different environments.

## Security Posture
- **No TDE** — fund balances and DDA-adjacent data stored at rest in plaintext.
- **No column encryption** — `banker_approval_notification.source_amount` (client float amounts) and manager names are in plaintext.
- **`SSISConfigurations` secrets exposure**: Connection strings are in a database table; any user with SELECT permission on this table can read server names and potentially credentials.
- **Hardcoded production server in synonyms**: Source control contains the production server name `ppamwdcudsql1c1\ppamwdcudsql1c1` — an operational security concern.
- **Security folder**: Contains 30+ manually maintained grant scripts covering PROD, UAT, emergency access (`emer_*`) logins, and role definitions. Emergency access accounts (`emer_ag60132`, `emer_rb27292`, etc.) committed to source control indicate a break-glass access pattern that should be managed through a PAM (Privileged Access Management) solution instead.
- **DDA numbers in result sets**: `ab_process_plastic_get_expiring_sp` returns `dda_number` in its SELECT list; any consumer of this procedure receives raw DDA numbers without masking.
- **`banker_get_avialable_funds_rule_info`** [typo in procedure name — "avialable"]: Naming inconsistency suggests no code review or naming convention enforcement was in place.

## Technical Debt
- **Typo in procedure name**: `banker_get_avialable_funds_rule_info` — "avialable" is misspelled; this is a breaking change if renamed, so it must be corrected carefully.
- **BIGINT vs NUMERIC parameter mismatch**: `banker_reserved_source.action_amount BIGINT` stores integer cents, while `banker_insert_action_log` parameters are `NUMERIC(10,2)`. The conversion between these two representations is not documented; a value of 1000000000 cents ($10M) would overflow `NUMERIC(10,2)` (max 99,999,999.99).
- **Hardcoded server name in synonyms**: `ab_process_plastic_set_synonyms_for_ssis_sp` suggests runtime synonym redefinition is used to work around this — an anti-pattern that introduces execution-time DDL operations.
- **Legacy SSIS configuration table**: The `SSISConfigurations` table is a deprecated SSIS pattern; maintaining it adds operational friction and a security surface for credential exposure.
- **`ab_process_plastic_foreach_loop_sp`**: A cursor-driven foreach loop in SQL Server is a performance anti-pattern for set-based operations; for large card populations approaching expiry, this will be slow.
- **No FK constraints between banker tables and program master**: `program_id` and `promotion_id` are unconstrained VARCHAR columns; orphaned or invalid records cannot be detected at the database layer.
- **`gp_process_econnect_*` staging tables**: No visible cleanup mechanism; successfully posted invoices remain in staging indefinitely.

## Gen-3 Migration Requirements
1. **Replace synonym pattern with service API**: Card account lookups (`fdr_card_account`, `core_device_ecard`) should be retrieved through a card-account microservice API rather than direct synonym-based cross-database reads.
2. **Migrate SSIS to modern pipeline**: Replace the legacy SSIS package configuration table with a modern pipeline tool (Azure Data Factory, Prefect, Airflow); eliminate `SSISConfigurations` table.
3. **Move secrets out of the database**: Connection strings and any credentials stored in `SSISConfigurations` must be moved to a secrets vault before migration.
4. **Standardise amount data type**: All monetary amounts should use `DECIMAL(19,4)` or `BIGINT` (integer cents) consistently; the current mixed `BIGINT`/`NUMERIC(10,2)` pattern must be resolved with a defined conversion standard.
5. **Extract approval workflow**: The notification and approval state in `banker_approval_notification` should be managed by a workflow service (e.g., Temporal, Conductor) rather than database tables; migrate in-flight approvals carefully.
6. **Manage emergency access via PAM**: Remove `emer_*` login grant scripts from source control; provision break-glass access through a PAM solution with time-bounded credentials and full audit trails.
7. **Replace foreach cursor proc**: `ab_process_plastic_foreach_loop_sp` should be refactored as a set-based query or replaced by batch processing in application code.
8. **Fix procedure name typo**: Rename `banker_get_avialable_funds_rule_info` to `banker_get_available_funds_rule_info` with an alias or wrapper during transition to avoid breaking existing callers.

## Code-Level Risks
- **`NUMERIC(10,2)` overflow for large fund balances**: The action log procedure accepts `@amount numeric(10,2)`, which has a maximum of 99,999,999.99. Programs with eight-digit dollar balances will silently truncate or error on insert.
- **`ab_process_plastic_foreach_loop_sp` cursor performance**: For a card portfolio of millions of expiring cards, a cursor-driven loop will perform orders of magnitude worse than a set-based approach.
- **`ab_process_plastic_set_synonyms_for_ssis_sp` runtime DDL**: Executing `CREATE SYNONYM` or `DROP SYNONYM` at runtime within a stored procedure requires elevated permissions (`ALTER` on schema) and is prone to race conditions if multiple processes attempt to set synonyms simultaneously.
- **No transaction wrapping in `banker_insert_action_log`**: The procedure inserts into `banker_action_log` with `RETURN @@error`; if the insert fails (e.g., due to a constraint violation), the error is returned but the calling transaction is not necessarily rolled back. This can result in banker actions that were performed but not logged.
- **Typo-sensitive API**: Any callers that reference `banker_get_avialable_funds_rule_info` by name will break if the typo is corrected; this must be tracked and coordinated across the Banker application codebase.
