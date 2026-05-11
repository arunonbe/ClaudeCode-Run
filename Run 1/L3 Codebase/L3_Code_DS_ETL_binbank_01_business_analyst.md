# Business Analyst Report — DS_ETL_binbank

## Repository Identity

**Repository:** DS_ETL_binbank  
**Classification:** ETL Pipeline — BIN-to-Bank Mapping and NACHA File Generation  
**Technology:** Microsoft SQL Server Integration Services (SSIS) — SQL Server 2012 (11.0.7001.0)  
**Package count:** 5 SSIS packages  
**Project created:** April 2020 (WIRECARD\van.nguyen2 on workstation PF0VELTW)

---

## Business Purpose

DS_ETL_binbank (project name "BINBANK") is an SSIS project that performs two related but distinct functions:

1. **NACHA ACH file generation** — Produces NACHA-format ACH (Automated Clearing House) files and EFA (Early Funding Arrangement) reconciliation files for settlement with issuing banks. The README states: "This project contains the SSIS packages that deliver content to our major banks. NACHA files. Daily Network Recon."

2. **Program balance reporting by bank** — Aggregates prepaid card program balances by issuing bank for financial reporting.

3. **Sunrise transaction code export** — Exports transaction codes relevant to Sunrise Banks (a major prepaid issuing bank partner) for reconciliation purposes.

The pipeline bridges Onbe's card processing platform (`cf_report` database) with issuing bank settlement requirements, generating the ACH files that trigger fund movements between Onbe and its banking partners.

---

## NACHA ACH Background

NACHA (National Automated Clearing House Association) governs the ACH network. NACHA-format files are structured flat files with specific field positions and record types that banks use for batch settlement. In Onbe's context, ACH files are generated to:
- Fund prepaid card accounts (direct load)
- Reconcile daily network transactions
- Handle returns and adjustments

The `bank_name` parameter (default value `MB` in `nacha_file_process.dtsx`) indicates **Metabank** as one of the configured banks. Metabank (now Meta Financial Group / Pathward) is a major prepaid card issuer that works with program managers like Onbe. Multiple banks are supported through parameterisation.

---

## Key Business Processes

### 1. NACHA File Process (`nacha_file_process.dtsx`)
- **Purpose:** Processes queued NACHA file records from the `cf_report` database and generates NACHA-format output files for ACH submission
- **Input:** `nacha_configurations` (object variable — list of bank configurations) and `queued_files` (files to process) from `cf_report`
- **Parameter:** `bank_name` — the name of the bank to generate files for (default: `MB` = Metabank)
- **Tracking variables:** `file_id`, `missing_config_count`, `source_load_count`, `status_id`
- **Output:** NACHA ACH file for the specified bank

### 2. NACHA Load Source (`nacha_load_source.dtsx`)
- **Purpose:** Loads source transaction data from upstream systems into the NACHA processing staging area in `cf_report`

### 3. NACHA Print File (`nacha_print_file.dtsx`)
- **Purpose:** Produces the final formatted NACHA file and EFA (Early Funding Arrangement) reconciliation file
- **Outputs:**
  - NACHA file: `C:\ETL\Out\FifthThird\temp\53-ach-daily-recon<timestamp>.txt` (Fifth Third Bank)
  - EFA file: `C:\ETL\Out\FifthThird\temp\EFA53-ach-daily-recon<timestamp>.txt`
- **Bank partner visible:** Fifth Third Bank (53) — a major commercial bank

### 4. Program Balance by Bank (`program_balance_by_bank.dtsx`)
- **Purpose:** Aggregates prepaid card program balances by issuing bank for financial reporting and reconciliation reporting

### 5. Sunrise Transaction Code Export (`sunrise_transaction_code_export.dtsx`)
- **Purpose:** Exports transaction codes specific to Sunrise Banks for their reconciliation processes

---

## Bank Partners Identified

From the design-time connection strings and file paths, the following banking partners are in scope:

| Bank | Evidence | Role |
|---|---|---|
| Metabank (MB) | `bank_name` parameter default value `MB` | Issuing bank — NACHA files |
| Fifth Third Bank (53) | Output path `C:\ETL\Out\FifthThird\temp\53-ach-daily-recon*.txt` | Bank — NACHA/EFA files |
| Sunrise Banks | `sunrise_transaction_code_export.dtsx` name | Issuing bank — transaction code reconciliation |

The pipeline is parameterised to support multiple banks through the `bank_name` parameter in `nacha_file_process.dtsx`.

---

## Data Flow Summary

```
[cf_report database] ← [Upstream transaction processing (Ecountcore, etc.)]
         ↓
[nacha_load_source.dtsx] — loads source transactions into NACHA staging
         ↓
[nacha_file_process.dtsx — parameterised by bank_name]
         ↓
[nacha_print_file.dtsx] → [C:\ETL\Out\<BankName>\temp\<bank>-ach-daily-recon.txt]
                        → [C:\ETL\Out\<BankName>\temp\EFA<bank>-ach-daily-recon.txt]
         ↓
[bank ACH submission / SFTP to bank]

[program_balance_by_bank.dtsx] ← [cf_report] → [financial reports]
[sunrise_transaction_code_export.dtsx] → [Sunrise reconciliation files]
```

---

## Regulatory Relevance

### NACHA Operating Rules — CRITICAL
This pipeline **directly generates ACH files** submitted to the ACH network. NACHA Operating Rules impose strict requirements on:
- File format compliance (94-character fixed-width records, specific header/control record formats)
- Same-day ACH vs. standard ACH timing
- Return handling and exception processing
- Participant identification (ODFIs, RDFIs, routing numbers)
- File balancing (total debit = total credit)

NACHA violations can result in fines, suspension from the ACH network, or forced remediation. The integrity of this ETL pipeline directly affects Onbe's NACHA compliance.

### PCI DSS
ACH transaction data for prepaid card funding may include account numbers (routing + account). If `cf_report` tables contain routing numbers or bank account numbers linked to cardholders, this data is subject to PCI DSS Req 3 (stored data protection) and Req 4 (transmission protection).

The NACHA output files themselves contain:
- Bank routing numbers (9-digit ABA numbers)
- Account numbers (at the transaction entry level)
- Individual names or company names
- Transaction amounts

**NACHA output files are highly sensitive and constitute financial data that requires encrypted transmission to banking partners.** The file delivery mechanism (SFTP to bank) is not visible in this repository.

### Reg E
ACH transactions for prepaid cardholders are Reg E-regulated. Errors in NACHA file generation that cause incorrect fund movements create Reg E liability and require error correction procedures.
