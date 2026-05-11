# DS_DB_ecountcore_process_archive — Business Analyst View

## Repository Overview

`DS_DB_ecountcore_process_archive` is a Git repository (main branch) containing SQL migration scripts organised by date and story number, defining the schema for the `Ecountcore_Process_Archive` database. Unlike the other repositories in this set, it uses a **numbered migration script approach** rather than SSDT object scripts — each change set is a dated folder containing numbered SQL files. The initial base schema was deployed on 2021-08-23 (US565).

---

## Business Purpose

The `Ecountcore_Process_Archive` database is the **long-term archive for processed EcountCore staging data**. When data in `Ecountcore_Process` exceeds its online retention period (controlled by `ecountcore_process_partition_control.online_months`), it is partition-switched to this archive database rather than being deleted.

The business functions served are:

1. **Regulatory Data Retention** — Payment transaction records, NACHA files, FDR settlement data, and card shipping records must be retained for regulatory purposes:
   - PCI DSS Requirement 9.4.7 — cardholder data storage must follow defined retention policy and be securely deleted after retention period
   - NACHA rules require ACH transaction records to be retained for at least 2 years
   - Reg E requires transaction records for 24 months for dispute resolution purposes
   - State tax/unclaimed property laws may require records for 5-7 years

2. **Operational History and Investigation** — Archived processing records support:
   - Cardholder dispute investigations (Reg E, card network chargebacks)
   - Reconciliation of historical settlements
   - AML investigation support (Oracle Mantas investigations)
   - Fraud investigation (linking historical transaction patterns)

3. **Audit Support** — PCI DSS QSA assessments, SOC 1/SOC 2 audits, and NACHA audits may require access to historical processing records.

4. **FDR Settlement History** — Historical FDR DCAF, DD031, and ATM/ACH STAR data enables retrospective settlement analysis and dispute handling for aged transactions.

---

## Data Archived

The archive mirrors the same table structures as `Ecountcore_Process` for the following high-volume tables:

| Archived Table | Business Data |
|---|---|
| `citi_process_nacha_file` | Citi NACHA payment file records — ACH history |
| `fdr_process_atmach_star_file` | FDR ATM/ACH STAR network transaction records |
| `fdr_process_dcaf_auth_data` | **FDR DCAF authorisation data** — includes `cvv_in` field (**CRITICAL PCI finding carries over from process DB**) |
| `fdr_process_dcaf_chd_data` | **FDR cardholder data file** — highest sensitivity |
| `fdr_process_dcaf_ticket_data` | FDR transaction ticket data |
| `fdr_process_debitach_file` | FDR Debit ACH file records |
| `fdr_process_nacha_file` | FDR NACHA file records |
| `fdr_process_report_cd_011` | FDR card status reports |
| `fdr_process_report_cd_052` | FDR balance reports |
| `fdr_process_report_cd_061` | FDR activity reports |
| `fdr_process_report_us_address_validation` | US address validation — **PII** |
| `fdvs_process_ivr_capture_file_data` | IVR capture data |
| `ecountcore_process_archive_partition_control` | Partition configuration |

All tables use the same `ecountcore_process_archive_monthly_partition` partition function with `ecountcore_process_archive_scheme`.

---

## Retention Policy

The archive database uses the same partition-based retention architecture as `Ecountcore_Process`. The `ecountcore_process_archive_partition_control.online_months` value determines how long archived data is retained in the archive database before final deletion.

The initial data migration (`20210824-US565` change set) includes a DML script `005_dml_archive_retention_online_months.sql` that sets the retention period — the specific values are in that script (not reviewed here but should be confirmed against legal/compliance retention requirements).

---

## Regulatory Relevance

### PCI DSS
The archive database contains data migrated from `Ecountcore_Process`, including:
- `fdr_process_dcaf_auth_data` with `cvv_in` column — **this CVV violation is preserved into the archive**
- `fdr_process_dcaf_chd_data` — FDR cardholder data
- All the same PCI scope concerns apply to the archive database

Under PCI DSS Requirement 3.2, cardholder data must not be retained beyond what is needed for business or legal requirements. The archive database must have documented, enforced retention periods with secure deletion at expiry.

### NACHA / Reg E
Archived NACHA files (`fdr_process_nacha_file`, `citi_process_nacha_file`) support the 2-year NACHA record retention requirement and Reg E dispute handling.

### SOC 1 / SOC 2
The archive database is relevant to SOC 1 audits (controls over financial reporting) as it contains settlement and payment processing records. SOC 2 Type II audits would assess the availability and security of archived records.

---

## Key Observations for Business

1. The archive was created in August 2021 (`20210823-Initial-Base`) and had its first bug-fix change set the following day (`20210824-US565-Fix-monthly-database-archive`), suggesting rapid iteration during initial deployment.
2. The migration folder naming convention (`YYYYMMDD-USXXX-description`) is the most mature change management approach across all six repositories — a numbered, dated, story-linked migration pattern.
3. The archive database is essential for compliance — losing it would eliminate the ability to respond to historical disputes, audits, or regulatory inquiries.
4. The CVV violation in the source database (`Ecountcore_Process`) is reproduced here — any CVV values in `fdr_process_dcaf_auth_data.cvv_in` would have been archived into this database.
