# DS_DP_db04 — Data Architect Report

## Database Instances and Schemas on DB04

### `cbaseapp` (Content Base Application — Primary Schema)

**Tables confirmed from DDL and DML scripts:**

| Table | Purpose | Sensitive Fields | Flag |
|---|---|---|---|
| `dbo.security_audit_device_user_data` | Cardholder device/login audit — partitioned | `sec_usr_data_id`, `eventDateTime`, `device_type_id`, `device_browser`, `device_os`, `device_model`, `device_geography`, `login_type` | `device_geography` — location data (CCPA); `login_type` — auth method |
| `dbo.security_audit_device_user_data_switch` | Partition switch staging for above | Same schema as above | CDE-adjacent — cardholder session data |
| `dbo.biocatch_api_audit` | BioCatch behavioral biometrics scoring log | `username`, `csid`, `activity_type`, `bcstatus`, `error_description`, `score`, `risk_factors`, `genuine_factors`, `data_points` | `username` — cardholder identifier; `score` — fraud score; `risk_factors` — behavioral biometric data (**CCPA: biometrics flag**); `data_points` (varchar 8000) — potentially large behavioral dataset |
| `dbo.inquiry_types_category` | CSA inquiry category lookup | `inquiry_type_category_desc`, `visible`, `inquiry_type_category_code` | Reference data |
| `dbo.Inquiry_types` | CSA inquiry type lookup | `Inquiry_Type`, `Inquiry_Desc`, `inquiry_type_category`, `visible` | Reference data |
| `dbo.inquiry_type_activity_xref` | Inquiry-to-activity mapping | `activity`, `inquiry_type`, `monetary` | Reference data |
| `dbo.security_role` | Portal security roles | `name` — role identifier (e.g., `ROLE_FILE_VIEW`) | Access control configuration |
| `dbo.affiliate_fieldname` / `dbo.affiliate_field_lookup` | Affiliate portal field configuration | Field names for KYC, password validation, contact us, FAQ, disclosures | Configuration data — KYC field spec |
| `dbo.cbaseapp_process_partition_control` | Partition management metadata | `online_months`, `process_order`, `enabled` | DBA operations table |

**Content tables (large volume, copy tag driven):**
| Table | Purpose |
|---|---|
| Copy tag tables (inferred) | Localized UI strings per program/locale/skin |
| Skin tables (inferred) | Brand visual theme definitions |
| Notification template tables | US + Canada notification message templates |
| `dbo.op_message` (inferred) | OnePortal message content (updated in login message script) |

---

### Partition Architecture — `cbaseapp` Security Audit Tables

**Partition function:** `cbaseapp_process_monthly_partition` — monthly boundary
**Partition scheme:** `cbaseapp_process_monthly_scheme` — maps to `[PRIMARY]` filegroup
**Source files:**
- `20191018_NAMDATASVC-1388_01-CbaseappAddPartitions.sql` — adds partition boundaries dynamically
- `20191018_NAMDATASVC-1388_02-Partition_security_audit_device_user_data.sql` — re-creates PK as partitioned clustered index on `(sec_usr_data_id, eventDateTime, device_type_id)` using `cbaseapp_process_monthly_scheme([eventDateTime])`
- `20191018_NAMDATASVC-1388-03-CREATE-security_audit_device_user_data_switch.sql` — creates the non-partitioned switch staging table
- `20191018_NAMDATASVC-1388-04-COLUMN-cbaseapp_process_partition_control.sql` — adds `process_order` and `enabled` columns to control table
- `20191018_NAMDATASVC-1388-05-INSERT-cbaseapp_process_partition_control.sql` — inserts initial partition control rows
- `20191018_NAMDATASVC-1388-06-ALTER-cbaseapp_process_partition_maintain.sql` — alters partition maintenance procedure

**Partition granularity:** Monthly. Boundary values are dynamically computed based on `online_months` from the control table.

**Key observation:** The monthly partition approach enables efficient archival of aged security audit data — old partitions can be switched out and archived without full table scans.

---

### `EcountCore` (Shared schema with DB02)

DB04 also hosts EcountCore (per the `20191009_NATS-5257_Payment_table_update_expiration_date.sql` reference to updating a `Payment` table). The QA proxy role (DB04 = QA for DB02 workloads) confirms the EcountCore schema is present. However, DB04-specific EcountCore changes are minimal — suggesting DB04's EcountCore instance is primarily a QA/read replica rather than an active processing node.

---

## Sensitive Data Field Inventory

| Field | Table | Database | Sensitivity | Flag |
|---|---|---|---|---|
| `device_geography` | `security_audit_device_user_data` | `cbaseapp` | HIGH | Location data — CCPA biometric-adjacent |
| `data_points` (varchar 8000) | `biocatch_api_audit` | `cbaseapp` | HIGH | **Behavioral biometrics data — CCPA Sec 1798.140(b) "biometric information"** |
| `risk_factors` | `biocatch_api_audit` | `cbaseapp` | HIGH | Behavioral biometric indicators |
| `genuine_factors` | `biocatch_api_audit` | `cbaseapp` | MEDIUM | Behavioral affirmative markers |
| `username` | `biocatch_api_audit` | `cbaseapp` | MEDIUM | Cardholder portal username |
| `csid` | `biocatch_api_audit` | `cbaseapp` | MEDIUM | Customer session ID — links to cardholder session |
| `login_type` | `security_audit_device_user_data` | `cbaseapp` | MEDIUM | Authentication method |
| `device_browser` / `device_os` / `device_model` | `security_audit_device_user_data` | `cbaseapp` | LOW-MEDIUM | Device fingerprinting data |

### BioCatch Data — Special Regulatory Note
The `biocatch_api_audit.data_points` column (varchar 8000) stores BioCatch behavioral biometric data. Under CCPA Section 1798.140(b), biometric information (including behavioral patterns used to establish personal identity) is a category of sensitive personal information. California residents whose data is stored here have expanded rights. This table requires:
1. Data minimization review — is all 8KB of `data_points` necessary?
2. Retention policy — no TTL/cleanup job visible for this table
3. Privacy notice update — must disclose collection of biometric data
4. Separate consent workflow if California cardholders are served on this node

---

## PCI DSS CDE Scope

DB04 is **in-scope for PCI DSS** because:
1. `security_audit_device_user_data` captures cardholder session authentication events — in-scope under PCI DSS Req 10 (audit logging)
2. DB04 hosts (or QA-proxies) EcountCore, placing it in the CDE network segment
3. The `cbaseapp` portal backend processes cardholder authentication sessions directly

However, DB04 is at the **perimeter of the CDE** rather than its core (unlike DB02 which holds actual card account data). The copy tag content and skin definitions themselves are not cardholder data.

---

## Schema Design Observations

### xcontent Versioning Pattern
The xcontent skin deployment scripts (`xcontent1.0.XX_DB04_cbaseapp_createskin_cbaseapp.sql`) follow a sequential version number pattern from 1.0.12 to 1.0.35. There are **gaps and overlaps** in the version numbering visible in the file list:
- Both `1.0.24` and `1.0.24_01` appear on different dates
- Versions 1.0.28, 1.0.32, 1.0.33 are not consistently sequential

This suggests a **multi-branch or parallel development** of xcontent skins that was not cleanly serialized before deployment. Schema drift or conflicting skin definitions could result.

### Copy Tag Structure
The `affiliate_fieldname` and `affiliate_field_lookup` tables form a key-value pair system for per-affiliate portal field configuration. The pattern of inserting `affiliate_fieldname` before `affiliate_field_lookup` is consistent across KYC (SQ-5183), password validation (SQ-4674), and Western Union (2023) scripts — indicating a well-established extensibility pattern.

### Comparison with DB02 Schema
- DB04 uses `cbaseapp_process_monthly_partition` (monthly) while DB02 uses unnamed row-compression on partition 1 for `fdr_process_dcaf_*` tables
- DB04's partition control is externalized in `cbaseapp_process_partition_control` table — DB02 does not have a visible equivalent control table
- Both share `EcountCore` schema structure but DB04 appears to be a lower-write instance of it

### Dynamic SQL in Partition Management
File `20191018_NAMDATASVC-1388_02-Partition_security_audit_device_user_data.sql`, line 40–44:
```sql
DECLARE @sql VARCHAR(MAX);
...
SET @sql = 'ALTER TABLE [dbo].[security_audit_device_user_data] DROP CONSTRAINT [' + @index_name + '];'
EXEC (@SQL);
```
Dynamic SQL is used to drop the PK constraint by dynamically constructing the constraint name. This is a security-code quality flag. While the index name is sourced from `sys.indexes` (catalog view, not user input), the use of unparameterized EXEC provides a potential attack surface if the pattern is reused with less-controlled inputs.

---

## Data Retention Concerns

1. **`biocatch_api_audit`** — No cleanup/archival job observed. This table may grow unbounded.
2. **Copy tag tables** — Historical copy tags may not be purged; multiple xcontent versions likely accumulate.
3. **`security_audit_device_user_data`** — Monthly partitioning enables archival, but no script shows old partition removal/switching-out. The archival half of the partition maintenance lifecycle appears incomplete in the repository.
