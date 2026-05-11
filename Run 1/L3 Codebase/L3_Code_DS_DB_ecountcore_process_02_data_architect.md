# DS_DB_ecountcore_process — Data Architect View

## Database Overview

- **Database Name**: `Ecountcore_Process` (alias: `Ecountcore_Process_SS` as referenced by SSIS packages)
- **SQL Server Version**: SQL Server 2016 (`Sql130DatabaseSchemaProvider`)
- **Project Type**: SSDT SQL Server Database Project
- **Schema**: `dbo` (single schema)
- **Active Branch**: `development`
- **Object Counts**: 90+ tables, 40+ stored procedures, 4 functions, Storage (partition function + scheme)

---

## Complete Table Inventory (92 tables)

### ALTO / PACS Processing Tables

| Table | File | Key Columns | Sensitive Data |
|---|---|---|---|
| `alto_arucs_process_file` | `dbo/Tables/` | file_id, filename, status | None |
| `alto_arucs_process_status` | `dbo/Tables/` | status_id, name | None |
| `alto_arucs_profile_decline_reason_code` | `dbo/Tables/` | code, description | None |
| `alto_pacs_process_file` | `dbo/Tables/` | file_id, filename | None |
| `alto_pacs_process_profile_decline_reason_code` | `dbo/Tables/` | code, description | None |
| `alto_pacs_process_status` | `dbo/Tables/` | status_id, name | None |

### Arroweye Fulfilment Tables

| Table | File | Key Columns | Sensitive Data |
|---|---|---|---|
| `arroweye_order_confirmation_report` | `dbo/Tables/` | order data, cardholder info | **PII — cardholder name/address** |
| `arroweye_order_confirmation_report_status` | `dbo/Tables/` | Status codes | None |
| `arroweye_return_mail_report` | `dbo/Tables/` | returned card data | **PII — address** |
| `arroweye_return_mail_report_status` | `dbo/Tables/` | Status codes | None |
| `arroweye_ship_confirmation_report` | `dbo/Tables/` | shipment tracking | PII (name/address) |
| `arroweye_ship_confirmation_report_status` | `dbo/Tables/` | Status codes | None |

### Batch Process Tables

| Table | Key Columns | Sensitive Data |
|---|---|---|
| `batch_process_secureaddenda_data` | ACH addenda fields | ACH addenda — may contain bank account info |
| `cfg_Cards_Ship_Status_Files` | Config for card ship file processing | None |

### Citi NAOT Tables

| Table | Key Columns | Sensitive Data |
|---|---|---|
| `citi_naot_address_update_file` | address fields, card identifiers | **PII — cardholder address** |
| `citi_naot_address_update_status` | Status codes | None |
| `citi_naot_exception_file` | exception records | Card identifiers |
| `citi_naot_exception_status` | Status codes | None |
| `citi_naot_plastic_shipping_file` | Card shipping data | Card identifiers, **address** |
| `citi_naot_plastic_shipping_status` | Status codes | None |
| `citi_naot_return_mail_file` | Returned mail records | **PII — address** |
| `citi_naot_return_mail_status` | Status codes | None |
| `citi_process_nacha_file` | NACHA file records | **ACH routing/account numbers** |
| `citi_process_nacha_file_switch` | Partition switch staging | Same as above |
| `citi_process_nacha_file_system_audit` | Audit trail | Operational |

### Core Process Tables

| Table | Key Columns | Sensitive Data |
|---|---|---|
| `core_process_batch_secondary_card_issue` | Card issue batch records | Card identifiers |
| `core_process_card_ship_status_file` | Card shipping | Card identifiers |
| `core_process_dda_blockcode_file` | Block code changes | DDA numbers |
| `core_process_dda_blockcode_status` | Status | None |
| `core_process_refund_atm_fees` | ATM fee refunds | DDA numbers, amounts |
| `core_process_refund_atm_fees_control` | Control totals | Amounts |
| `core_profile_batch_secondary_card_issue_status` | Status codes | None |
| `core_profile_dda_payment_nacha_status` | NACHA status | Payment status |
| `core_profile_dda_payment_nacha_status_audit` | Audit log | Payment status history |
| `core_profile_nacha_status_code` | NACHA return codes (R01, R02...) | None — reference |
| `core_profile_program_payment_company` | Payment company config | None |
| `core_profile_program_payment_company_audit` | Audit | None |
| `ecountcore_process_partition_control` | Partition maintenance config | None |

### ECS (ECount Service) Tables

| Table | Key Columns | Sensitive Data |
|---|---|---|
| `ecs_encashment_settlement_file` | Settlement file records | Card/account data |
| `ecs_ivr_epmemo_details_record` | IVR EP memo details | Card/transaction data |
| `ecs_ivr_epmemo_details_status` | Status | None |

### FDR Processing Tables — CRITICAL PCI SCOPE

| Table | Key Columns | Sensitive Data | PCI Finding |
|---|---|---|---|
| `fdr_auth_master_file` | Card auth data, transaction codes | **Card data — PCI scope** | Confirm no PAN |
| `fdr_auth_master_file_process_run` | Process tracking | None | None |
| `fdr_auth_wallet_type` | Wallet type reference | None | None |
| `fdr_process_atmach_star_file` | ATM/ACH STAR network transactions | DDA numbers, amounts | Financial |
| `fdr_process_atmach_star_file_switch` | Partition switch staging | Same | Same |
| `fdr_process_atmach_star_update_audit` | Audit | Operational | None |
| `fdr_process_dcaf_auth_data` | **FDR Daily Card Activity — auth records** | **`cvv_in` CHAR(2) — CRITICAL** | **PCI DSS Req 3.3.1 violation if post-auth CVV stored** |
| `fdr_process_dcaf_auth_data_switch` | Partition switch | Same | Same |
| `fdr_process_dcaf_chd_data` | **FDR CHD (Cardholder Data) file** | **Cardholder data from FDR** | **PCI CDE — must assess all columns** |
| `fdr_process_dcaf_chd_data_switch` | Partition switch | Same | Same |
| `fdr_process_dcaf_maint_fee_open_auth_accounts` | Maintenance fee open auth | Account data | Financial |
| `fdr_process_dcaf_ticket_data` | Transaction ticket data | Transaction amounts, merchant | Financial |
| `fdr_process_dcaf_ticket_data_switch` | Partition switch | Same | Same |
| `fdr_process_dd031_data` | FDR DD031 settlement data | **`cvv` VARCHAR(3) — CRITICAL PCI** | **CVV stored post-authorisation** |
| `fdr_process_dd031_data_stage` | Staging for DD031 | card_number temporarily (purged in import proc) | **Transient PAN — must confirm purge** |
| `fdr_process_dd031_fees_prepost` | Fee pre-posting | Financial amounts | Financial |
| `fdr_process_dd031_file_status` | File processing status | None | None |
| `fdr_process_dd031_totals_stage` | Totals staging | Financial totals | Financial |
| `fdr_process_debitach_file` | Debit ACH file records | ACH data | **ACH routing/account** |
| `fdr_process_debitach_file_switch` | Partition switch | Same | Same |
| `fdr_process_debitach_update_audit` | Audit | Operational | None |
| `fdr_process_dmf_airline_data` | DMF airline data (special transaction type) | Transaction data | Financial |
| `fdr_process_dmf_status` | DMF status | None | None |
| `fdr_process_nacha_file` | NACHA file from FDR | **ACH routing/account numbers** | NACHA/Reg E scope |
| `fdr_process_nacha_file_switch` | Partition switch | Same | Same |
| `fdr_process_report_cd_011` | CD011 — card status report | Card identifiers | PCI scope |
| `fdr_process_report_cd_011_switch` | Partition switch | Same | Same |
| `fdr_process_report_cd_052` | CD052 — balance report | Account balances | Financial |
| `fdr_process_report_cd_052_switch` | Partition switch | Same | Same |
| `fdr_process_report_cd_061` | CD061 — activity report | Transaction data | Financial |
| `fdr_process_report_cd_061_switch` | Partition switch | Same | Same |
| `fdr_process_report_us_address_validation` | US address validation | **PII — cardholder addresses** | Privacy |
| `fdr_process_report_us_address_validation_switch` | Partition switch | Same | Same |
| `fdr_process_response` | FDR process response codes | None | None |
| `fdr_process_response_setting` | Response settings | None | None |
| `fdvs_process_ivr_capture_file_data` | IVR capture data from FDVS | Transaction data | Financial |
| `fdvs_process_ivr_capture_file_data_switch` | Partition switch | Same | Same |

### IEFT / WorldLink Tables

| Table | Key Columns | Sensitive Data |
|---|---|---|
| `ieft_citiconnect_process_reject_return_file` | Reject/return records | Payment data |
| `ieft_citiconnect_process_reject_return_status` | Status | None |
| `ieft_worldlink_process_fxrate_file` | FX rates | None — reference data |
| `ieft_worldlink_process_fxrate_status` | Status | None |
| `ieft_worldlink_process_fx_rejects_file` | FX rejects | Payment data |
| `ieft_worldlink_process_fx_status` | Status | None |
| `ieft_worldlink_process_poc_file` | Payment outcoming | **International payment data** |
| `ieft_worldlink_process_poc_status` | Status | None |
| `ieft_worldlink_process_por_file` | Payment incoming | **International payment data** |
| `ieft_worldlink_process_por_status` | Status | None |
| `international_atmach_transfers_file` | International ATM/ACH transfers | Cross-border payment data |

### IVR Tables

| Table | Key Columns | Sensitive Data |
|---|---|---|
| `ivr_card_activation_processed` | Processed activations | Card identifiers |
| `ivr_card_activation_stage` | Pending activations | Card identifiers |

### MQ Tables

| Table | Key Columns | Sensitive Data |
|---|---|---|
| `mq_back_out_msg` | Message queue back-out records | Message content |

### Paypoint Tables

| Table | Key Columns | Sensitive Data |
|---|---|---|
| `paypoint_advice_type` | Reference data | None |
| `paypoint_call_audit_log` | Call audit | Card/transaction data |
| `paypoint_call_type` | Reference data | None |
| `paypoint_encashment_settlement_file` | Settlement records | Financial amounts |
| `paypoint_encashment_settlement_file_event_type` | Event type ref | None |
| `paypoint_encashment_settlement_file_header_trailer` | File metadata | None |
| `paypoint_encashment_settlement_file_tx_source` | Transaction source ref | None |
| `paypoint_site_file` | Paypoint site data | Location data |

### Refund Queue Table

| Table | Key Columns | Sensitive Data |
|---|---|---|
| `refund_process_queue` | Refund pending records | DDA numbers, amounts |

### SMOTS Tables

| Table | Key Columns | Sensitive Data |
|---|---|---|
| `smots_account_status` | Account status sync | Account identifiers |
| `smots_daily_count` | Daily count tracking | Counts |
| `smots_fp_orig_msg` | Fast payment original message | Payment data |
| `smots_profile_fp_reject_cd` | Reject codes | None |

### Fiserv / NAOT Ship Status Tables

| Table | Key Columns | Sensitive Data |
|---|---|---|
| `tbl_Card_Ship_status_file_duplicates` | Duplicate tracking | Card identifiers |
| `tbl_Fiserv_Card_Ship_OnHold` | On-hold card shipments | Card identifiers |
| `tbl_Fiserv_Card_Ship_Statuses` | Shipment status | Card identifiers |
| `tbl_Fiserv_Card_Ship_status_file_import` | Import staging | Card identifiers |
| `tbl_NAOT_Card_Ship_OnHold` | On-hold NAOT shipments | Card identifiers |
| `tbl_NAOT_Card_Ship_Statuses` | NAOT shipment status | Card identifiers |
| `tbl_NAOT_Card_Ship_status_file_import` | Import staging | Card identifiers |

---

## Critical Sensitive Data Flags

| Field | Table | Classification | PCI/Regulatory Flag |
|---|---|---|---|
| `cvv_in` CHAR(2) | `fdr_process_dcaf_auth_data` | **CVV/SAD** | **CRITICAL: PCI DSS Req 3.3.1 — post-auth CVV must not be stored** |
| `cvv` VARCHAR(3) | `fdr_process_dd031_data` | **CVV/SAD** | **CRITICAL: PCI DSS Req 3.3.1** |
| `card_number` (in `fdr_process_dd031_data_stage` before purge) | `fdr_process_dd031_data_stage` | **PAN** | Transient — verify purge in `fdr_process_dd031_import` procedure |
| `dda_number` CHAR(16) | Multiple FDR/NAOT/Fiserv tables | Account number | PCI scope |
| Cardholder data columns | `fdr_process_dcaf_chd_data` | **PII/PAN/SAD** | **Full CDE assessment required** |
| Address fields | `citi_naot_address_update_file`, arroweye tables | PII | CCPA/GDPR |
| ACH routing/account | `fdr_process_nacha_file`, `citi_process_nacha_file` | Financial | NACHA scope |

---

## Partition Architecture

The database uses SQL Server **Table Partitioning** for high-volume FDR processing tables:

- **Partition Function**: `ecountcore_process_monthly_partition` (monthly ranges)
- **Partition Scheme**: `ecountcore_process_monthly_scheme`
- **Filegroup**: `ECP_FG1` — dedicated filegroup for partition storage
- **Control Table**: `ecountcore_process_partition_control`
- **Maintenance Procedure**: `ecountcore_process_partition_maintain` — splits future partitions and merges old empty ones

The "switch" tables (`*_switch`) are staging tables used for partition switch operations — data is loaded to the switch table, then atomically swapped into the main table's partition. This is a high-performance pattern for bulk data ingestion.

---

## Data Retention

The `ecountcore_process_partition_control` table stores `online_months` per table — the number of months of data to retain in the live database before archival. Data older than the retention period is moved to `ecountcore_process_archive` via partition switch.
