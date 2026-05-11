# DS_DB_ecountcore_process — Business Analyst View

## Repository Overview

`DS_DB_ecountcore_process` is an SSDT SQL Server Database Project (`.sqlproj`, targeting SQL Server 2016 `Sql130DatabaseSchemaProvider`) that defines the schema for the `Ecountcore_Process` (or `Ecountcore_Process_SS`) database. This database serves as the **staging, process-tracking, and intermediate processing layer** for the Onbe prepaid card platform. It is the operational hub between raw inbound data files from card processors and banks, and the authoritative EcountCore database.

---

## Business Purpose

`Ecountcore_Process` handles the **file-based integration** and **batch processing staging** functions for multiple card processor and financial institution interfaces:

1. **FDR (First Data Resources) File Processing** — Ingesting and processing multiple FDR report files:
   - DD031 (Settlement/transaction detail file) — `fdr_process_dd031_*` tables
   - DCAF (Daily Card Activity File) — `fdr_process_dcaf_*` tables (auth data, CHD cardholder data, ticket data)
   - NACHA files from FDR — `fdr_process_nacha_file`, `fdr_process_nacha_file_switch`
   - ATM/ACH STAR network files — `fdr_process_atmach_star_file`
   - DebitACH files — `fdr_process_debitach_file`
   - Report files (CD011, CD052, CD061) — card status and balance reports
   - US address validation files — `fdr_process_report_us_address_validation`
   - Auth master file — `fdr_auth_master_file`

2. **Citi NAOT Card Processing** — Managing Citi NAOT card shipping status and address update workflows:
   - `citi_naot_plastic_shipping_*` — card shipment tracking
   - `citi_naot_return_mail_*` — returned mail processing
   - `citi_naot_address_update_*` — address correction processing
   - `citi_naot_exception_*` — exception handling
   - NACHA file processing — `citi_process_nacha_file`

3. **Fiserv Card Processing** — Managing Fiserv card shipping and status:
   - `tbl_Fiserv_Card_Ship_*` tables — shipping status, on-hold cards, import records
   - `FiServ_Cards_Status_Posting` and `FiServ_Cards_Status_Prepare` procedures

4. **Arroweye Card Fulfilment** — Managing Arroweye (card personalisation bureau) order and shipment data:
   - `arroweye_order_confirmation_report_*` — order confirmations
   - `arroweye_ship_confirmation_report_*` — shipment confirmations
   - `arroweye_return_mail_report_*` — returned cards

5. **ALTO/PACS Batch Processing** — Processing ALTO (ACH/load file processor) and PACS bulk card load files:
   - `alto_pacs_process_*` tables and procedures
   - `alto_arucs_*` tables — ARUCS (ACH return/unwind) processing

6. **Paypoint Encashment** — Processing Paypoint cash withdrawal settlement files:
   - `paypoint_encashment_settlement_file*` tables
   - `paypoint_call_audit_log` — call audit trail
   - `paypoint_site_file` — Paypoint site data

7. **IVR Card Activation** — Staging IVR (Interactive Voice Response) card activation requests:
   - `ivr_card_activation_stage`, `ivr_card_activation_processed`
   - `ivr_card_activation_update` procedure

8. **SMOTS Programme Processing** — SMOTS (specific card product) account status synchronisation:
   - `smots_account_status`, `smots_daily_count`, `smots_fp_orig_msg`
   - Account status sync and fast payment processing

9. **IEFT / WorldLink International Processing** — International EFT via Citi WorldLink:
   - FX rate files — `ieft_worldlink_process_fxrate_file`
   - FX rejects — `ieft_worldlink_process_fx_rejects_file`
   - Payment outcoming/incoming files — `ieft_worldlink_process_poc_file`, `por_file`
   - CitiConnect reject/return files — `ieft_citiconnect_process_reject_return_file`

10. **ACH Secure Addenda** — Processing secure ACH addenda records:
    - `batch_process_secureaddenda_data` — stores addenda pending batch processing

11. **Refund Processing** — Managing refund queue for ATM fee refunds:
    - `core_process_refund_atm_fees`, `core_process_refund_atm_fees_control`
    - `refund_process_queue`, `refund_process` procedure

12. **NACHA (Citi) / Block Code Management** — Payment NACHA status and DDA block code management:
    - `core_process_dda_blockcode_file`
    - `core_profile_dda_payment_nacha_status`, `core_profile_nacha_status_code`

---

## Regulatory Relevance

### PCI DSS
The `Ecountcore_Process` database is within PCI DSS CDE scope because it:
- Contains card-level data in `fdr_process_dcaf_chd_data` (Cardholder Data from FDR DCAF file)
- Stores `cvv_in` field in `fdr_process_dcaf_auth_data` (CVV input from FDR authorisation data)
- References card numbers (through `fdr_process_dd031_data_stage` before purge)
- Contains DDA numbers (account identifiers) in multiple tables

The `cvv_in` column in `fdr_process_dcaf_auth_data` is a **Critical PCI DSS finding** — if this stores the CVV input from authorisation requests, it must not be retained post-authorisation (PCI DSS Requirement 3.3.1).

### NACHA / Reg E
The NACHA file processing tables (`fdr_process_nacha_file`, `citi_process_nacha_file`) track NACHA file ingestion for settlement and return processing. The `core_profile_nacha_status_code` table stores NACHA return reason codes (R01, R02, etc.). These are critical for Reg E dispute resolution and NACHA compliance.

### OFAC / AML
The `fdr_process_dd031_import` procedure actively uses card hashing to link FDR transaction data to EcountCore accounts, supporting AML transaction monitoring data quality.

---

## Key Business Observations

1. This database is the **operational intermediary** — it processes inbound data, validates and maps it to EcountCore accounts, then feeds results to EcountCore for posting.
2. The "switch" table pattern (`*_switch` tables alongside primary processing tables) is used for partition switching operations — data is staged in a primary table, then partition-switched to an archive.
3. Multiple card processor interfaces are unified through this single staging database, making it a critical integration point.
4. The database is referenced by the AML Mantas ETL (`AMLMantasETLNAM.dtsx`) as `Ecountcore_Process_SS`, confirming it feeds the AML compliance system.
