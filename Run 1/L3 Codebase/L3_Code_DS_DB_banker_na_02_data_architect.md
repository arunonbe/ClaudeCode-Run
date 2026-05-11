# DS_DB_banker_na — Data Architect View

## Data Stores
- **Primary database**: `banker_na` — SQL Server SSDT project targeting `Sql100DatabaseSchemaProvider` (SQL Server 2008 schema), compatibility mode from project settings, collation `SQL_Latin1_General_CP1_CI_AS`.
- **Linked cross-database dependencies**:
  - `ecountcore_ss` on `ppamwdcudsql1c1\ppamwdcudsql1c1` — referenced via synonyms for `fdr_card_account`, `core_device_ecard`, and `app_service_card_expiration_queue`. This is the core card-account database.
  - `jobsvc` — referenced in `banker_insert_action_log` (the procedure comments say "insert into the jobsvc_test database"); the `banker_action_log` table itself is not defined in the SSDT project, implying it resides in another database.
  - `syn_job_action` and `syn_job_action_detail_register_user` reference the job-service database.
  - GP (`Dynamics GP`) via `syn_ItemPricePerContractPlusKit` and SSIS eConnect integration.
- **SSIS configuration store**: `SSISConfigurations` table stores SSIS package runtime configuration, including connection strings.

## Schema & Tables
All objects in schema `dbo`. Table groups:

| Group | Tables | Purpose |
|---|---|---|
| Banker funds state | `banker_available_funds_rule`, `banker_preset_funds_config`, `banker_reserved_source`, `banker_reserved_source_log`, `banker_temp_unsettled_sources`, `banker_group_amt_mapping` | Funds reservation and rule configuration |
| Banker workflow | `banker_approval_notification`, `banker_approval_notification_comment`, `banker_program_datasource`, `banker_default_promo_exception_program` | Approval and program configuration |
| Plastic processing | `ab_process_plastic_processing`, `ab_process_plastic_status`, `ab_process_plastic_connections`, `ab_process_plastic_price`, `ab_process_plastic_finance_mapping` | Card expiry and re-issue lifecycle |
| GP invoice staging | `gp_process_econnect_invoice`, `gp_process_econnect_invoice_component`, `gp_process_econnect_invoice_line_insert`, `gp_process_econnect_reference` | GP billing staging tables |
| ONUS processing | `onus_process_status`, `onus_program_status` | ONUS batch job tracking |
| SSIS config | `SSISConfigurations` | SSIS runtime configuration |

**Synonyms** (cross-database references abstracted as local objects):
- `syn_fdr_card_account` → `ecountcore_ss.dbo.fdr_card_account`
- `syn_fdr_card_account_detail` → `ecountcore_ss.dbo.fdr_card_account_detail`
- `syn_core_device_ecard` → `ecountcore_ss.dbo.core_device_ecard`
- `syn_app_service_card_expiration_queue` → `ecountcore_ss.dbo.app_service_card_expiration_queue`
- `syn_ab_process_plastic_finance_mapping` → (self-referential or cross-db)
- `syn_ItemPricePerContractPlusKit` → GP pricing table
- `syn_job_action`, `syn_job_action_detail_register_user` → job service database

**Views** (2 visible):
- `ab_process_plastic_account_vw` — joins card account data from `ecountcore_ss` for expiry processing
- `ab_process_plastic_expiring_vw` — filters cards due for expiry within a requested date range

## Sensitive Data Handling
- **DDA numbers**: `ab_process_plastic_get_expiring_sp` selects `dda_number` from `ab_process_plastic_expiring_vw`; DDA numbers are Demand Deposit Account numbers — sensitive financial account identifiers under Reg E and potentially PCI DSS if they are associated with prepaid card DDA accounts.
- **Member IDs**: `member_id` is selected from the account view in the expiry proc. Depending on what `member_id` resolves to in `ecountcore_ss`, this could be a cardholder identifier.
- **Manager names**: `program_mgr_full_name`, `relation_mgr_full_name` in `banker_approval_notification` — personal names.
- **`action_performed_by`** (in `banker_action_log`): Up to `VARCHAR(200)`, potentially a full name or employee identifier.
- **`SSISConfigurations.ConfiguredValue`**: Connection string values potentially containing server names, database names, or credentials.
- **No card numbers, CVV, PIN, or track data** are stored in tables defined within this SSDT project.

## Encryption & Protection
- **No TDE** configured in the SSDT project (`IsEncryptionOn` not explicitly set to True).
- **No column-level encryption** on DDA numbers, amounts, or personal name fields.
- **`SSISConfigurations`** stores `ConfiguredValue NVARCHAR(255)` in plaintext — if connection strings include passwords or connection tokens, this is a secrets exposure risk.
- Synonym definitions hardcode the server name `ppamwdcudsql1c1\ppamwdcudsql1c1` — exposing production server topology in source control.

## Data Flow
```
External card processor (FDR) / ecountcore_ss
    ↓ (via synonyms)
ab_process_plastic_expiring_vw / ab_process_plastic_account_vw
    ↓
ab_process_plastic_get_expiring_sp
    → ab_process_plastic_processing (status tracking)
    → ab_process_plastic_update_status_sp (error handling)
    → GP eConnect invoice staging tables
        ↓
        gp_process_create_Invoice_sp → gp_process_econnect_invoice*
            ↓
            SSIS eConnect package → Dynamics GP

Banker service (application)
    → banker_reserved_source (INSERT/UPDATE via banker_insert/update/delete procs)
    → banker_approval_notification (INSERT via approval notification procs)
    → banker_action_log (INSERT via banker_insert_action_log — in jobsvc db via synonym)

SSIS packages read SSISConfigurations for runtime configuration.
```

## Data Quality & Retention
- **`banker_temp_unsettled_sources`**: A staging/transient table; no evidence of automated cleanup procedure in the SSDT project. If rows accumulate, this becomes stale state.
- **`banker_reserved_source_log`**: An append-only log table with no visible purge logic; will grow unbounded.
- **No data retention policy** defined in the SSDT project for any table.
- **`ab_process_plastic_status`** tracks plastic processing with status codes; no archival or purge for completed records is visible.
- **NULL-able `num_promos_in_source`** in `banker_reserved_source` means the number of promotions sharing a source is not always known; queries relying on this for allocation calculations must handle NULLs explicitly.
- **`gp_process_econnect_*` staging tables**: If GP integration fails mid-flight, staged invoice rows may remain permanently in these tables; no dead-letter or retry logic is visible in the SSDT project.

## Compliance Gaps
- **DDA number processing without masking**: DDA numbers are selected and passed to downstream processes without any masking or tokenisation; they appear in plain text in procedure output sets and SSIS data flows.
- **Secrets in `SSISConfigurations`**: Connection strings in a database table are a common PCI DSS and GLBA compliance gap — credentials should be managed in a secrets vault (Azure Key Vault, HashiCorp Vault), not in a database table.
- **Hardcoded production server name in synonyms**: Server names committed to source control expose production infrastructure topology; this violates security-by-obscurity expectations and makes environment parity (dev/UAT/prod) structurally impossible without synonym redefinition.
- **No audit of funds reservation changes**: `banker_reserved_source_log` exists, but there is no verified trigger or procedure ensuring that every change to `banker_reserved_source` is captured in the log — an SSIS or ad-hoc UPDATE would bypass it.
- **`banker_action_log` in external database**: The audit trail for banker actions is stored in the `jobsvc` database (not `banker_na`); this creates a cross-database audit dependency that is harder to protect and backup consistently.
- **No TDE or column encryption**: Amounts representing client fund balances and DDA numbers are at rest unencrypted.
