# DS_DP_db02 — Data Architect Report

## Database Instances and Schemas on DB02

DB02 hosts multiple logical databases. The following are confirmed from scripts:

### `EcountCore` (Primary card account database)

**Tables with confirmed DDL or DML:**

| Table | Purpose | Sensitive Fields | Flag |
|---|---|---|---|
| `dbo.fdr_card_account` | Core card account record | `card_id` (int PK), `dda_number` (char 16), `card_type`, `sys_prin_agent` (char 12), `created` | `dda_number` — **PCI DSS: card account number surrogate / account linkage key**; `sys_prin_agent` — BIN/principal/agent encoding |
| `dbo.fdr_card_account_detail` | Card detail record | `card_id` (FK), `access_level`, `exp_date` (datetime), `cv_code` (nullable), `activation_code`, `statement_code`, `pin_selection_code`, `block_code`, `fdr_create_commit` | `exp_date` — PCI DSS SAD if combined with PAN; `cv_code` — **CRITICAL FLAG: CVV/CVC field present in schema** (nullable but column exists) |
| `dbo.fdr_card_account_registration` | Cardholder PII | `card_id` (FK), `created`, `first_name`, `middle_name`, `last_name`, `suffix_name`, `home_email`, `business_email`, `mobile_email`, `address1`, `address2`, `attention_line`, `company_name`, `city`, `state`, `postal`, `country`, `home_phone`, `business_phone`, `mobile_phone` | **ALL fields PII** — name, address, phone, email. CCPA/GLBA regulated. |
| `dbo.fdr_dda_account_registration` | DDA-linked cardholder PII | Same PII fields as above, keyed by `dda_number` | Same as above; note `dda_number` is used as a join key to the card account |
| `dbo.fdr_dda_account_journal` | Transaction journal | `id` (GUID), `created`, `dda_number` (char 16), `ticket_id`, `date`, `amount` (int, cents), `fee` (int), `facility` (smallint), `source` (smallint), `status`, `description` (merchant name+city+state), `card_id` | `dda_number` — account key; `amount` — transaction value; `description` — merchant transaction description containing merchant name and geographic data |
| `dbo.fdr_profile_transaction_source` | Transaction source dimension | `id`, `name`, `inline_fee`, `fee_source` | Configuration data; no cardholder data |
| `dbo.fdr_profile_transaction_facility` | Transaction facility dimension | `id`, `name` | Configuration data |
| `dbo.app_profile_escheatment_rules` | State dormancy rules | `state`, `dormancy_period`, `rule_set_id` | Regulatory configuration |
| `dbo.app_profile_dda_exclusions` | DDA ACH exclusion list | `dda_number` (implied), program/facility fields | `dda_number` — account key |
| `dbo.kyc_tracker` | KYC workflow state | `id` (GUID), `ref_id` (GUID), `kyc_portal_token_id` (GUID), `program_id` (char 8), `dda_number` (char 16), `card_last_four_number` (char 4), `status` (tinyint), `created`, `updated` | `dda_number` — account key; `card_last_four_number` — last-4 card digits (PCI DSS permitted element); `kyc_portal_token_id` — third-party KYC token |
| `dbo.kyc_tracker_status` | KYC status lookup | `id` (tinyint), `status` (char 25) | Reference data |
| `dbo.fdr_card_number_bins` | BIN registry | `sys` (prefix), `prin` (principal), `bin` (BIN number) | `bin` — card BIN (first 6 digits); per PCI DSS, BIN alone is not full PAN but is CDE-adjacent |
| `dbo.app_profile_promotion` | Program promotion config | Promotion-level settings | Low sensitivity |

**Filegroup:** `FDR_DATA` — KYC tables are explicitly placed on this named filegroup (`ON [FDR_DATA]` in kyc_tracker DDL, line 27 of `20220314_SQ-5175_DB02_kyc_tracker.sql`). This indicates intentional filegroup separation for the card data.

---

### `EcountCore_Process` (Transaction processing database)

**Tables confirmed from scripts:**

| Table | Purpose | Sensitive Fields | Flag |
|---|---|---|---|
| `dbo.fdr_process_dcaf_auth_data_switch` | Authorization data switch table (partitioned) | Authorization data | **HIGH — DCAF (Debit Card Authorization File) data is CDE core** |
| `dbo.fdr_process_dcaf_chd_data_switch` | Cardholder data switch table (partitioned) | Cardholder data | **CRITICAL — "chd" = Cardholder Data; this table is in the heart of the CDE** |
| `dbo.fdr_process_dcaf_ticket_data_switch` | Ticket data switch (partitioned) | Ticket/transaction IDs | HIGH — links auth to cardholder |
| `dbo.fdr_process_debitach_file_switch` | Debit/ACH file staging (partitioned) | ACH file data | NACHA-regulated |
| `dbo.fdvs_process_ivr_capture_file_data_switch` | IVR capture file data (partitioned) | IVR voice capture data | Contains DDA/card references |
| `dbo.ivr_card_activation_stage` | IVR activation staging | `dda_number` (char 16), `card_number_last4` (varchar 4), `activation_time` | Account activation events |
| `dbo.ivr_card_activation_stage_backfill` | Temporary backfill staging | Same fields | Created/dropped as part of SQ-3087 backfill |

**Partition scheme:** `EcountCore_Process` tables use row-level compression on partition 1. Evidence: `20191017-NAMDATASVC-102-resync_switch_table_compression.sql`. The `fdr_process_dcaf_*` tables are partitioned — consistent with DB04's monthly partition scheme pattern across the platform.

---

## Critical Sensitive Data Field Flags

| Field | Table | Database | PCI DSS Classification | Risk Level |
|---|---|---|---|---|
| `cv_code` | `fdr_card_account_detail` | `EcountCore` | **Sensitive Authentication Data (SAD)** | CRITICAL — storing CVV/CVC after authorization is a PCI DSS Req 3.2.1 violation |
| `dda_number` (char 16) | Multiple tables | `EcountCore` | Account number / PAN surrogate | HIGH — 16-character DDA number functions as an account identifier equivalent to PAN |
| `card_last_four_number` | `kyc_tracker` | `EcountCore` | Last 4 of PAN | LOW-MEDIUM — permitted by PCI DSS but must be protected in context |
| `exp_date` | `fdr_card_account_detail` | `EcountCore` | Card expiration — SAD | HIGH — combined with dda_number constitutes near-complete card data |
| `first_name`, `last_name`, `address*`, `email`, `phone` | `fdr_card_account_registration` | `EcountCore` | PII | HIGH — GLBA/CCPA regulated |
| `bin` | `fdr_card_number_bins` | `EcountCore` | BIN prefix data | MEDIUM — CDE-adjacent |
| DCAF auth/cardholder data | `fdr_process_dcaf_*_switch` | `EcountCore_Process` | Core CDE data | CRITICAL |

### CRITICAL FLAG: `cv_code` Column
The `fdr_card_account_detail` table contains a `cv_code` column (line 16 of the card account insert script `20200311_NATS-6935_insert_card_account_and_journal.sql`). The inserts in the script set `cv_code = null`, but the **column exists in the schema**. PCI DSS Requirement 3.2.1 prohibits storing SAD (CVV/CVC) after authorization under any circumstances. The existence of this column requires:
1. Immediate schema review to confirm whether this column ever contains non-null values in production
2. If non-null values exist, this is a P0 compliance violation requiring immediate remediation
3. The column should be removed from the schema entirely

---

## PCI DSS CDE Scope Assessment

DB02 is **unambiguously in the core CDE**:
- `fdr_process_dcaf_chd_data_switch` — Cardholder Data table explicitly named
- `fdr_process_dcaf_auth_data_switch` — Authorization data
- `fdr_card_account_detail.cv_code` — SAD field present in schema
- `fdr_card_account_registration` — Full cardholder PII
- `dda_number` — 16-character account number throughout all tables

All systems connecting to DB02 are within PCI DSS scope. Network segmentation, encryption in transit, and access controls are mandatory PCI requirements for this database node.

---

## Schema Design

### Partition Architecture
`EcountCore_Process` switch tables use **SQL Server table partitioning** with row compression. This is an efficient approach for high-volume transaction processing tables. The switch tables (e.g., `fdr_process_dcaf_auth_data_switch`) are likely used for partition switching — the standard SQL Server technique for efficient bulk data loading/archival without full table locks.

### Naming Conventions
- `fdr_*` prefix: First Data Resources heritage (FDR = First Data, the legacy card processor). This confirms the platform originated on First Data authorization infrastructure.
- `fdvs_*` prefix: FDR Voice Services — IVR-related data
- `core_profile_*` prefix: Application-level profile/configuration tables
- `app_profile_*` prefix: Program-level application settings

### Filegroup Strategy
The `FDR_DATA` filegroup for KYC tables suggests a deliberate data segregation strategy — KYC data may be on separate physical disks for encryption-at-rest scoping. This should be verified and documented as a PCI DSS Req 3.5 control.

---

## Data Flows

Based on script evidence, DB02 participates in the following data flows:

1. **Card issuance:** New cards → `fdr_card_account` + `fdr_card_account_detail` + `fdr_card_account_registration`
2. **Authorization processing:** Real-time auth data → `fdr_process_dcaf_auth_data_switch` (partitioned, high-volume)
3. **ACH disbursement:** Outbound ACH → `core_profile_dda_payment_nacha_status` → NACHA file extract (via DB06)
4. **IVR activation:** IVR call logs (Vendor DB on DB06) → `ivr_card_activation_stage` → processed via `ivr_card_activation_update` SP
5. **KYC verification:** KYC portal → `kyc_tracker` (insert/update via `kyc_status_insert_update` SP) → status tracking
6. **Escheatment:** Dormancy check against `app_profile_escheatment_rules` → escheatment queue management
