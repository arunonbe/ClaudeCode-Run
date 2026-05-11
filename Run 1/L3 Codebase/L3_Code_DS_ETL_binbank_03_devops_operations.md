# DevOps & Operations Report — DS_ETL_binbank

## Repository Identity

**Repository:** DS_ETL_binbank  
**Deployment Model:** SSIS Project Deployment (`.ispac`) to SSIS Catalog  
**CI/CD Pipeline:** None detected  
**Operational Criticality:** HIGH — generates NACHA ACH settlement files; failures directly impact bank funding

---

## Build and Deployment Model

### Solution Structure
```
BINBANK.sln              ← Visual Studio solution
BINBANK.dtproj           ← SSIS project file (70 KB)
BINBANK.database         ← SSAS database stub
Project.params           ← Project parameters (minimal — only 91 bytes)
cf_report.conmgr         ← Project-level connection manager
nacha_file_process.dtsx  ← NACHA file generation
nacha_load_source.dtsx   ← Source data loading
nacha_print_file.dtsx    ← NACHA/EFA file output (631 KB — most complex)
program_balance_by_bank.dtsx ← Balance reporting
sunrise_transaction_code_export.dtsx ← Sunrise recon export
```

### Project Parameters
File: `Project.params` (91 bytes — minimal)
The project parameters file is nearly empty, suggesting most configuration is embedded in the packages themselves rather than externalised as project parameters. This is an anti-pattern for production deployments where environment-specific values need to be overridden without redeploying packages.

---

## NACHA Processing Pipeline Operations

### nacha_load_source.dtsx — Prerequisite
Must execute before `nacha_file_process.dtsx`. Loads source transactions into the NACHA staging area in `cf_report`. If this package fails, the downstream NACHA file generation will either fail or produce empty/incomplete files.

### nacha_file_process.dtsx — Core Processing
**Parameter:** `bank_name` (required) — specifies which bank's NACHA files to generate. Default value: `MB` (Metabank).

**Operational implications:**
- The package must be executed **once per bank** — if Onbe processes for multiple banks (Fifth Third, Sunrise, Metabank), the package must be executed multiple times with different `bank_name` values
- Missing bank configurations (tracked by `missing_config_count` variable) indicate configuration data gaps in `cf_report` that would cause file generation failures
- The `status_id` and `file_id` variables track processing state, suggesting the package is designed to be idempotent for re-runs

### nacha_print_file.dtsx — Output Generation
Produces the final NACHA and EFA files with timestamped filenames:
- `C:\ETL\Out\FifthThird\temp\53-ach-daily-recon<YYYYMMDD-hhmmss>.txt`
- `C:\ETL\Out\FifthThird\temp\EFA53-ach-daily-recon<YYYYMMDD-hhmmss>.txt`

**Post-processing assumption:** After the file is written, a separate process (SFTP job, Managed File Transfer system, or manual step) must transmit the file to Fifth Third Bank's ACH submission endpoint. This transmission step is not in this repository. If it fails silently, NACHA files accumulate on disk but are never submitted — causing funding failures for cardholders.

---

## Schedule and Timing

NACHA ACH files have strict submission deadlines governed by NACHA Operating Rules:
- **Standard ACH:** Must be submitted to the RDFI by the settlement date (typically the day before)
- **Same-Day ACH:** Must be submitted within specific windows (before 10:30 AM ET and 2:45 PM ET)

The BINBANK pipeline likely runs on a **daily schedule** with tight timing constraints. A package failure at 3 AM that is not detected until business hours could miss the ACH submission window, causing delayed cardholder funding. No alerting or failure-notification mechanism is visible in this repository.

---

## Environment Configuration

The design-time connection string points to `qc-az-db03.nam.wirecard.sys\qi_db03` (QC environment). Production must use a different connection string, presumably injected via SSIS Catalog environment parameters. The `CM.cf_report.Password` project parameter suggests there may be environments using SQL authentication rather than Windows authentication.

---

## Output File Management

NACHA and EFA output files are written to `C:\ETL\Out\FifthThird\temp\`. Operational concerns:
- **No archival logic visible** — unlike the Cardtronics ETL which has an `ArchiveFolder`, the BINBANK pipeline does not document file archival or purge procedures
- **Temp folder naming** — files written to a `\temp\` directory may suggest temporary storage before transmission; a process to move/delete files after successful submission is needed
- **File accumulation risk** — if files are not purged, the temp directory fills over time, eventually causing write failures

---

## Operational Risk Assessment

| Risk | Severity | Description |
|---|---|---|
| No error alerting/notification visible | CRITICAL | NACHA file failures may not be detected until banking partners report discrepancies |
| File transmission to bank not in scope | HIGH | Gap between file generation and ACH submission is invisible in this repo |
| Output files in unencrypted temp directory | HIGH | NACHA files contain routing/account numbers on unprotected local disk |
| Single `bank_name` per execution | HIGH | Multi-bank environments require multiple executions; missing one bank = missing ACH |
| EncryptSensitiveWithUserKey protection level | MEDIUM | Same deployment risk as Cardtronics ETL |
| QC server in design-time connection | MEDIUM | Confirms production vs. QC environment divergence |
| No file purge/archival process documented | MEDIUM | File accumulation over time |
| Minimal Project.params | MEDIUM | Configuration hardcoded in packages |
| SQLNCLI11.1 deprecated driver | LOW | Replacement needed for SQL Server 2019+ |
