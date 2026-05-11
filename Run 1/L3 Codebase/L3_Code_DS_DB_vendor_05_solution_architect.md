# DS_DB_vendor — Solution Architect Assessment

## 1. Critical Security and Compliance Findings

### 1.1 P0 CRITICAL: Full PAN Stored in Plaintext VARCHAR

**Finding:** `dbo/Tables/fdr_cardholder_master.sql` — `card_number CHAR(16)` stores the full 16-digit Primary Account Number in plaintext with no masking, truncation, tokenisation, or encryption. This is compounded by `GBBase/Tables/CustomerMaster.sql` — `CardNumber VARCHAR(100)` stores a full card number alongside the encrypted equivalent `ECN VARBINARY(256)`.

**Regulatory Basis:**
- PCI DSS v4.0.1 Requirement 3.4.1: "If disk-level or partition-level encryption is not used (rather than file-, column-, or field-level database encryption), then PAN must be rendered unreadable anywhere it is stored by using any of the following approaches: one-way hashes based on strong cryptography; truncation; index tokens with the pads being securely stored; strong cryptography."
- The presence of `card_number CHAR(16)` in plaintext means the Vendor database fails this requirement entirely.

**Impact:** Any account with `db_datareader` membership, `Vendor_Select` role membership, or `db_owner` membership can execute `SELECT card_number FROM dbo.fdr_cardholder_master` and retrieve full PANs in bulk. The 20+ members of `Vendor_Select` all have this access.

**Remediation (Priority: P0 — Immediate):**
1. Assess whether `fdr_cardholder_master` is actively queried with the `card_number` column. If not, truncate the column to store only the last 4 digits (BIN + last 4 is the maximum allowed under PCI DSS).
2. For `GBBase.CustomerMaster.CardNumber`: if `ECN VARBINARY(256)` is the encrypted equivalent, drop or mask the plaintext `CardNumber` column. If `CardNumber` is still required by calling services, replace with a tokenised reference.
3. Engage Compliance to assess whether a PCI DSS self-reporting obligation applies for this finding.

---

### 1.2 P0 CRITICAL: SSN Stored in Plaintext VARCHAR

**Finding:** `GBBase/Tables/CustomerMaster.sql` — `SSN VARCHAR(50)` stores the cardholder's Social Security Number in plaintext. Simultaneously, `ESN VARBINARY(256)` exists in the same row — an encrypted SSN that was presumably introduced as part of a data protection initiative, but the plaintext `SSN` column was never cleared.

**Regulatory Basis:**
- GLBA Safeguards Rule (16 CFR 314.4(c)): Requires administrative, technical, and physical safeguards to protect customer information. A plaintext SSN column directly accessible to 20+ service accounts fails this standard.
- CCPA 1798.81.5: Requires businesses to implement reasonable security procedures and practices for SSN and other specified categories of sensitive personal information.
- GDPR Article 9 (special categories) and Article 32: SSN is a government identifier requiring appropriate technical safeguards.
- While PCI DSS specifically governs cardholder data, SSN is classified as sensitive PII by every applicable US and international privacy regulation.

**Impact:** The `GBMap.DDA_Card_Account_Detail` view (`GBMap/Views/DDA_Card_Account_Detail.sql`, line 29: `,c.ssn`) exposes SSN to all `Vendor_Select` role members. This means every production service account — IVR, order management, scheduler, customer service web, ECAP — can retrieve cardholder SSN via a simple view query.

**Remediation (Priority: P0):**
1. Immediately restrict `GBMap.DDA_Card_Account_Detail` to exclude the `ssn` column, or replace with a masked version (last 4 only) for non-privileged callers.
2. Evaluate whether `GBBase.CustomerMaster.SSN` should be dropped in favour of `ESN VARBINARY(256)` only. Coordinate with the team managing ESN encryption to confirm the encryption key management approach.
3. If `ESN` uses a separately managed key (not co-located in the same database), this represents the correct architecture. The `SSN` column should be set to NULL and then dropped.
4. Verify with Compliance and Legal whether a data breach notification obligation applies under CCPA, GLBA, or state breach notification laws for the historical SSN exposure.

---

### 1.3 P0 CRITICAL: `uspNESSDailyExtract` WHERE Clause Bug — OFAC Screening Silent Failure

**Finding:** `GBLoads/Stored Procedures/uspNESSDailyExtract.sql`, line 43:
```sql
WHERE PICreated > @startdate AND PICreated > @enddate
```

The intended logic was to filter records created within the date range (`between @startdate and @enddate`). The second condition `PICreated > @enddate` where `@enddate = GETDATE()` (today's date) will never be true for any existing record — no record was created in the future. **This means the NESS daily extract produces zero rows and submits nothing to the NESS screening engine.**

**Regulatory Basis:**
- OFAC 31 CFR Part 501: Requires blocking of transactions involving SDN-listed parties. If the NESS extract is empty, newly enrolled cardholders are never screened against the SDN list.
- BSA Program requirements: An effective AML/sanctions compliance program must include screening of customer data against OFAC lists.

**Impact:** If this bug has been present in production, every cardholder onboarded since the bug was introduced has not been screened against OFAC/SDN lists through this procedure. The weekly extract (`uspNESSWeeklyExtract`) should be reviewed to determine if it contains the same bug.

**Remediation (Priority: P0 — Immediate):**
1. Fix the WHERE clause: `WHERE PICreated > @startdate AND PICreated <= @enddate`
2. Run a full retrospective NESS extract for all cardholders in `GBBase.CustomerMaster` to screen the entire population that may have been missed.
3. Engage Compliance immediately — if OFAC screening has been silently failing, this may constitute a material compliance failure requiring escalation to senior management, regulators, or the Board Risk Committee.
4. Verify `uspNESSWeeklyExtract` does not contain the same bug.

---

### 1.4 P1 HIGH: `db_owner` Granted to Service Account and Named Individual

**Finding:** `Security/RoleMemberships.sql` (lines 1–10): `db_owner` granted to `vendor`, `nam\jd62380`, and `NAM\PPA_PRD_ABAT`.

**Impacts:**
- `nam\jd62380` — if this is a named individual account, they may have left Onbe. Active `db_owner` for departed employees is a critical access control failure (PCI DSS Req 8.6).
- `NAM\PPA_PRD_ABAT` has both `db_owner` AND `db_datareader` — redundant and overprivileged.
- `db_owner` can disable audit traces, modify security roles, and bypass any stored procedure API access controls.

**Remediation (Priority: P1):**
1. Verify whether `jd62380` is an active employee. If not, immediately revoke database access.
2. Remove `db_owner` from `NAM\PPA_PRD_ABAT` and replace with minimum-necessary role membership.
3. Remove `db_owner` from the generic `vendor` login and replace with specific role grants.

---

### 1.5 P1 HIGH: `NAM\UAT` Account in Production `db_datareader`

**Finding:** `Security/RoleMemberships.sql` (line 45): `ALTER ROLE [db_datareader] ADD MEMBER [NAM\UAT]`.

A UAT (User Acceptance Testing) credential has read access to the production Vendor database. This UAT credential likely has access to the same Onbe Active Directory domain but is intended for non-production use.

**Impact:** If the UAT environment shares the `NAM\UAT` service principal with the production database, developers or testers running UAT workloads could inadvertently (or intentionally) query production cardholder data including SSN and PAN.

**Remediation (Priority: P1):**
1. Remove `NAM\UAT` from production `db_datareader` immediately.
2. If UAT testing requires access to realistic cardholder data, use anonymised/synthetic data — not production cardholder records.

---

### 1.6 P2 HIGH: DES Encryption Algorithm on GoogleBinKey

**Finding:** `Security/GoogleBinKey.sql`:
```sql
CREATE SYMMETRIC KEY [GoogleBinKey]
    WITH ALGORITHM = DES
    ENCRYPTION BY CERTIFICATE [GoogleBinCert];
```

DES (56-bit) has been cryptographically broken since the DES Cracker demonstration in 1998. PCI DSS v4.0.1 Requirement 3.6.1 prohibits the use of DES for PAN or sensitive data protection. The certificate `GoogleBinCert` expired in October 2012.

**Remediation (Priority: P2):**
1. Identify any data encrypted with `GoogleBinKey` — if any such data exists in the database, it should be treated as unencrypted.
2. Drop `GoogleBinKey` and `GoogleBinCert` from the database.
3. If Google BIN lookup functionality is still required, implement using AES-256 with a properly managed key.

---

## 2. All Database Objects — Complete Inventory

### 2.1 Tables — dbo Schema

| Table | PII Risk | Notes |
|---|---|---|
| `fdr_cardholder_master` | CRITICAL — full PAN CHAR(16) | No PK, no indexes |
| `fdr_import_cd_012` | High — SHA1 hashed card | SHA1 trigger positive control |
| `fdr_import_cd_014` / `cd_051` / `cd_063` / `bm_406` | Medium | FDR staging records |
| `fdr_import_dd_096` / `sd_091` | Medium | FDR staging records |
| `fdr_process_dcaf_chd_data_20090519` | High — DDA + card hash | Disabled indexes |
| `fdr_process_dcaf_chd_data_20061223` | High | Legacy 2006 table |
| `fdr_process_dcaf_auth_data_20090519/20061223` | High | Legacy auth data |
| `fdr_process_dcaf_ticket_data_*` | Medium | FDR ticket data |
| `fdr_process_report_*` | Medium | FDR report data |
| `fdr_process_debitach_file` | Medium | ACH debit file |
| `ness_hits` | CRITICAL — OFAC results with PII | BSA retention required |
| `IVR_CallLog` | High — ANI, DOB, partial card | Retention policy required |
| `IVR_CallLog_MenuChoices` | Low | Menu navigation only |
| `IVR_Fraud_Call_Log` | High | Fraud-flagged calls |
| `IVR_ArkadinData` | Medium | Conferencing data |
| `chargeback_process_queue` | High — DDA number | Reg E process data |
| `chargeback_process_status` | Low | Status tracking |
| `chargeback_rules` | Low | Reference data |
| `citishare_process_warehouse_file` | Low | Legacy CitiShare |
| `psx_card_package_usage_report` | Medium | Card package data |
| `fdr_token_log_file` | Medium | Token log |
| `ddl_log` | Low | DDL change log |
| `september.sql` / `sep_quality.sql` | Unknown | Ad-hoc tables — audit required |
| `RC_Contact_Log_Stg` | Medium | Contact log staging |

### 2.2 Tables — GBBase Schema

| Table | PII Risk | Notes |
|---|---|---|
| `CustomerMaster` | CRITICAL — SSN, PAN, full PII | CDC enabled |
| `AuthorizedTransactions` | HIGH — PAN plaintext + encrypted | Indexed by DDA |
| `PostedTransactions` | HIGH — PAN plaintext + encrypted | Indexed by DDA |
| `ReconVBase` | Medium | Reconciliation base |

### 2.3 Tables — GBLoads Schema

| Table | PII Risk | Notes |
|---|---|---|
| `Files` | Low | ETL file registry |
| `FileSteps` | Low | ETL step tracking |
| `lkSteps` | Low | Step reference |
| `Log` | Low | Load log |
| `tmpNESSTable` | HIGH — raw OFAC screen data | Staging only, truncated each load |

### 2.4 Stored Procedures

| Procedure | Schema | Purpose | Risk |
|---|---|---|---|
| `chargeback_process_begin` | dbo | Create chargeback process record | Low |
| `chargeback_process_service` | dbo | Core chargeback processing | High |
| `chargeback_process_callback` | dbo | Async callback handling | High |
| `chargeback_process_end` | dbo | Close chargeback process | Low |
| `monitor_autoach_failure` | dbo | ACH failure monitoring | Medium |
| `thankyou_get_shipping_report` | dbo | Rewards shipping report | Medium |
| `thankyou_get_shipping_report_daterange` | dbo | Date-range variant | Medium |
| `thankyou_get_shipping_report_new` | dbo | Current production variant | Medium |
| `thankyou_get_shipping_report_old_04242009` | dbo | Archived 2009 variant — should be dropped | Low |
| `usp_IVR_ArkadinData_INS` | dbo | IVR Arkadin data insert | Low |
| `usp_IVR_CallLog_Cleanup` | dbo | Purge old IVR records | Medium |
| `usp_IVR_CallLog_INS` | dbo | IVR call log insert | Medium |
| `usp_IVR_CallLog_INS_From_RC` | dbo | IVR call log from RC | Medium |
| `usp_IVR_CallLog_MenuChoices_INS` | dbo | IVR menu choice insert | Low |
| `usp_IVR_Fraud_Call_Log_INS` | dbo | Fraud call log insert | High |
| `uspNESSDailyExtract` | GBLoads | Daily OFAC extract — BUG | CRITICAL |
| `uspNESSWeeklyExtract` | GBLoads | Weekly OFAC extract — verify for same bug | CRITICAL |
| `uspUpdateCustomerMaster` | GBLoads | Apply FDR updates to CustomerMaster | High |
| `uspGetFileAction` | GBLoads | File action lookup | Low |
| `uspRollBack` | GBLoads | Rollback failed file load | Medium |
| `uspUpdateFile` / `uspUpdateFileStep` / `uspUpdateLog` | GBLoads | ETL control procedures | Low |

---

## 3. Remediation Priority Table

| Priority | Finding | Effort | Regulation |
|---|---|---|---|
| P0 | Fix `uspNESSDailyExtract` WHERE bug; run full retrospective NESS extract | Low (hours) + Very High (retro) | OFAC |
| P0 | Engage Compliance re: OFAC screening gap scope and regulatory notification | Low (immediate) | OFAC/BSA |
| P0 | Remove SSN from `GBMap.DDA_Card_Account_Detail` view | Low | GLBA/CCPA |
| P0 | Truncate `fdr_cardholder_master.card_number` to masked value | Low | PCI DSS Req 3.4 |
| P0 | Evaluate dropping `GBBase.CustomerMaster.SSN` (retain `ESN` only) | Medium | GLBA/CCPA/GDPR |
| P0 | Evaluate dropping / masking `GBBase.CustomerMaster.CardNumber` (retain `ECN` only) | Medium | PCI DSS Req 3.4 |
| P1 | Remove `db_owner` from service accounts and named individual | Low | PCI DSS Req 7.2 |
| P1 | Remove `NAM\UAT` from production `db_datareader` | Low | PCI DSS Req 6 |
| P1 | Verify `uspNESSWeeklyExtract` for same bug as daily extract | Low | OFAC |
| P1 | Define and enforce IVR DOB/ANI retention schedule | Low | GDPR Art 5(1)(e) |
| P2 | Drop `GoogleBinKey` / `GoogleBinCert` (DES + expired cert) | Low | PCI DSS Req 3.6.1 |
| P2 | Audit `september.sql`, `sep_quality.sql` for data; drop if empty | Low | Data governance |
| P2 | Drop `thankyou_get_shipping_report_old_04242009.sql` dead code | Low | Housekeeping |
| P2 | Implement CI/CD pipeline | Medium | PCI DSS Req 6 |
| P2 | Add PK and index to `fdr_cardholder_master` | Low | Performance |
| P3 | Separate GBBase, GBLoads, and IVR into distinct databases | Very High | Architecture |

---

## 4. Compliance Gap Summary

| Regulation | Gap | Severity |
|---|---|---|
| PCI DSS v4.0.1 Req 3.4 | Full PAN in `fdr_cardholder_master` and `CustomerMaster` — not rendered unreadable | Critical |
| GLBA Safeguards Rule | Plaintext SSN in `CustomerMaster` accessible to 20+ accounts | Critical |
| OFAC | `uspNESSDailyExtract` bug produces empty extract — OFAC screening silent failure | Critical |
| CCPA 1798.81.5 | Plaintext SSN without reasonable security measures | Critical |
| PCI DSS Req 7.2 | `db_owner` for service accounts — exceeds least privilege | High |
| PCI DSS Req 6 | UAT credential in production; no CI/CD | High |
| GDPR Art 32 | Plaintext SSN without appropriate technical measures | High |
| GDPR Art 5(1)(e) | IVR DOB retention — no enforced data minimisation | Medium |
| PCI DSS Req 3.6.1 | DES encryption on GoogleBinKey — weak/broken algorithm | Medium |
| BSA/OFAC | ness_hits disposition records require 5-year retention — no visible retention policy | Medium |
