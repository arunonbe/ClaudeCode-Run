# Data Architect Analysis — DS_DB_ATL_atlys_fc_nus (atlys_fc_nus)

## Database Configuration (from atlys_fc_nus.sqlproj)

| Property | Value |
|---|---|
| Compatibility mode | 90 (SQL Server 2005) |
| Default collation | SQL_Latin1_General_CP1_CI_AS |
| Recovery model | BULK_LOGGED |
| Page verify | CHECKSUM |
| Snapshot isolation | OFF |
| Read committed snapshot | OFF |
| Encryption at rest (TDE) | `<IsEncryptionOn>False</IsEncryptionOn>` — **NOT ENABLED** |
| Parameterisation | SIMPLE |
| Trustworthy | False |
| Change tracking | OFF |

These settings are **identical** to `atlys_fc_nca`. Both databases share the same configuration template, consistent with being forks of a common baseline.

---

## Schema Identity

`atlys_fc_nus` has an **identical table and view set** to `atlys_fc_nca`, confirmed by comparing the `<Build>` include lists in both `.sqlproj` files. The following analysis documents the schema as it applies to the US database, noting any US-specific data characteristics.

---

## Tables

### cursforecast
All 107 columns identical to `atlys_fc_nca`. The key US-specific data characteristic:
- `country_code VARCHAR(4)` — will be `'US'` for US programs (vs. `'CA'` for Canadian programs in the NCA instance).
- `bin VARCHAR(7)` — US BINs from Visa, Mastercard US-issued ranges. **CDE-adjacent.**
- `unclaimed_keep` / `unclaimed_months` — US state escheatment modelling; financial and legal significance is higher in the US due to state AG enforcement of unclaimed property statutes.
- `dorm_wait` — US Reg E-governed threshold: must be ≥12 months before the first dormancy fee to comply with 12 CFR 1005.20(d).

**Trigger:** `trg_exclude` — same change log trigger as NCA.

### tblForecast_data
Identical to NCA. Monthly forecast revenue by program and line code. `notes TEXT NULL` — deprecated data type.

**Sensitive fields:**
- `updated_by VARCHAR(15)` — PII (staff identifier)
- `notes TEXT` — may contain client-specific or negotiation information

### tblIssuance
Identical to NCA. Monthly issuance volumes. US programs likely include higher average load amounts for healthcare reimbursement (FSA/HSA), insurance disbursement, and payroll card use cases.

### tblPlastics / tblPlasticsDPhysical / tblPlasticsDVirtual
Physical and virtual card production volumes. The presence of `vPlasticsDPhysical` and `vPlasticsDVirtual` views in the NUS project (`atlys_fc_nus.sqlproj` Build items) is significant: the US market has a higher proportion of virtual-card programmes (single-use digital cards for healthcare, insurance, rebates) than other markets. These virtual programmes do not incur plastic production costs but do generate issuance and maintenance fee revenue.

### tblSpend
Spend volumes by transaction type. US-specific spend types include ATM withdrawals (`util_atm`) and ACH transfers (`util_ach`) — both Reg E-governed.

### tblCommissions
Sales rep commission records. US-based sales reps with commission agreements tied to US programme revenues.

### tblAmort_Tables_1 / tblAmort_Tables_2
Dormancy recognition schedule tables. These tables may have **different configured values in the US instance** compared to NCA, reflecting US-specific Reg E dormancy timing constraints. The amortisation schedules should align with the disclosed fee schedules on product packaging for US Reg E compliance.

### tblControls
Period control dates. US fiscal year end dates and forecast version dates for US reporting.

### tblForecast_Version / tblForecastChangeLog / tblForecast_Fees
Identical schema to NCA. Change log automatically populated by trigger.

### tblDash_data / tblPrgDflt / tblCosts
Identical to NCA.

---

## Views

**Identical view set to `atlys_fc_nca`.** Selected US-notable views:

| View | US Business Relevance |
|---|---|
| vPlasticsDPhysical / vPlasticsDVirtual | Physical vs. virtual card split — US has high virtual card proportion |
| vFirst12Revenue / vFirst12Revenue1 | First-year revenue projections — key metric for US client pricing |
| vRevenueFVD | FVD revenue — US Reg E defines limits on when FVD income can be recognised |
| vsfdc_extract | Salesforce CRM extract for US pipeline management |
| vControls1 / vControlsRev | Period control — US fiscal year settings |

---

## Functions

**Identical to `atlys_fc_nca`:** Single function `sys_prg_info` defined in the database. All other functions consumed via cross-database calls to `ATLYS_E.dbo.*`.

---

## Stored Procedures

**Identical stored procedure set to `atlys_fc_nca`.** Full list documented in the NCA data architect analysis. All 80+ procedures are present.

The NUS-specific variant of note:
- `sys_calc_dormancy` — contains the same server-name detection logic (`@@SERVERNAME` prefix check) as NCA. For the US database, this procedure must correctly model US Reg E dormancy fee timing.

---

## Sensitive Data Fields — Summary

| Field | Table | Classification | PCI / Regulatory Flag |
|---|---|---|---|
| `bin` | cursforecast | BIN data | CDE-adjacent |
| `card_type` | cursforecast | Card network type | CDE-adjacent |
| `cust_name` | cursforecast | Client business name | PII / GLBA |
| `unclaimed_keep` / `unclaimed_months` | cursforecast | Escheatment modelling | Legal / financial |
| `dorm_wait` | cursforecast | Reg E dormancy threshold | Regulatory |
| `notes` | cursforecast / tblForecast_data | Free-text | May contain PII |
| `updated_by`, `approved_by` | cursforecast | Staff names | PII |
| `comm_amt` | tblCommissions | Compensation amounts | Financial |

---

## PCI DSS CDE Scope Assessment

**Same assessment as `atlys_fc_nca`:** Connected-system scope. BIN data in `cursforecast.bin`. No full PANs or SAD. However, the US database handles programmes that may include healthcare FSA/HSA cards, which are subject to additional IRS regulations. The presence of health-related card programmes does not directly expand PCI scope, but does add HIPAA considerations if any cardholder health data were ever stored (none observed in this schema).

**Assessment: Connected-system CDE scope. BIN data present. No PAN/SAD found.**

---

## Encryption at Rest

**Not enabled.** Identical finding to `atlys_fc_nca`. All financial forecast data, fee rates, BIN data, and commission amounts stored in plaintext database files and backups.

---

## Data Retention

No retention or purge procedures visible. Same finding as `atlys_fc_nca`. The `tblForecastChangeLog` and `tblCommissions` tables will accumulate indefinitely.

**US-specific retention consideration:** Under GLBA, Onbe must retain records of customer financial transactions and account information for appropriate periods. The fee forecast and commission data in this database may be subject to GLBA record retention requirements. Additionally, state unclaimed property audit requirements may necessitate retention of breakage/escheatment modelling records for multiple years.
