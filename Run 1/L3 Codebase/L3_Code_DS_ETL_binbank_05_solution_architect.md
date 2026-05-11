# Solution Architect Report — DS_ETL_binbank

## Repository Identity

**Repository:** DS_ETL_binbank  
**Risk Profile:** CRITICAL — NACHA ACH file generation pipeline; failures have immediate financial and regulatory consequences

---

## Complete Object Inventory

| Object | Type | Purpose |
|---|---|---|
| `nacha_file_process.dtsx` | SSIS Package | Core NACHA processing — reads configs and queued files from cf_report, generates NACHA content |
| `nacha_load_source.dtsx` | SSIS Package | Loads source transaction data into NACHA staging in cf_report |
| `nacha_print_file.dtsx` | SSIS Package (631 KB) | Formats and writes NACHA and EFA flat files to C:\ETL\Out\FifthThird\temp\ |
| `program_balance_by_bank.dtsx` | SSIS Package | Aggregates program balances by issuing bank for reporting |
| `sunrise_transaction_code_export.dtsx` | SSIS Package | Exports Sunrise Banks-specific transaction codes for reconciliation |
| `cf_report.conmgr` | Connection Manager | OLE DB to cf_report on qc-az-db03.nam.wirecard.sys\qi_db03 |
| `Project.params` | Parameters (minimal) | Nearly empty — configurations hardcoded in packages |
| `BINBANK.dtproj` | Project File | ProtectionLevel=EncryptSensitiveWithUserKey; Password parameter present |
| `BINBANK.database` | Database Definition | SSAS stub |
| `BINBANK.sln` | Solution File | Visual Studio solution |

---

## Security Vulnerabilities

### CRITICAL

**1. NACHA Output Files Written as Plaintext to Local Disk**  
File: `nacha_print_file.dtsx`, line 34  
```
C:\ETL\Out\FifthThird\temp\53-ach-daily-recon<timestamp>.txt
```
NACHA Entry Detail records (Type 6) contain bank routing numbers (9 digits), bank account numbers (up to 17 digits), transaction amounts, and individual names. These files are written **unencrypted to a local temp directory**. Any user or process with access to `C:\ETL\Out\FifthThird\temp\` can read complete ACH financial records. This violates:
- GLBA Safeguards Rule (unprotected financial data at rest)
- NACHA Operating Rules section on data security
- PCI DSS Req 3.5 (if account numbers are linked to card PANs)

**2. EncryptSensitiveWithUserKey — Contains `CM.cf_report.Password` Parameter**  
File: `BINBANK.dtproj`, line 74  
A `CM.cf_report.Password` project parameter exists — unlike the Cardtronics ETL, BINBANK has an explicit password parameter for the cf_report connection. Under `EncryptSensitiveWithUserKey`, this password is encrypted with the developer's DPAPI key. On a server, this password will be unreadable, likely causing the cf_report connection to fail with an authentication error.

**This is a different risk level from the Cardtronics ETL:** if the password parameter is actively used (i.e., a SQL authentication password is stored here), the package will fail on any server that is not the original developer's workstation.

**3. No SFTP/Secure Transmission in Pipeline**  
The pipeline generates NACHA files but does not transmit them to the bank. The transmission step is absent from the repository. If transmission is handled by a separate manual process or undocumented script, the risk of human error (wrong file, wrong destination, missed transmission) is high. Missed NACHA submissions have direct financial consequences (late cardholder funding) and NACHA compliance implications.

**4. QC Server (`qc-az-db03`) in Design-Time Connection**  
File: `cf_report.conmgr`, line 9  
The design-time connection points to the QC environment server. If the SSIS Catalog environment parameter for the production connection string is ever misconfigured, the production NACHA packages could silently run against the QC database, generating empty or test files that are transmitted to real banks.

### HIGH

**5. No File Balance Validation Visible**  
NACHA Operating Rules require that the total amount in Entry Detail records equals the batch totals in Batch Control records, and file totals in File Control records. The repository does not show explicit balance-check logic (though the internal package logic in `nacha_print_file.dtsx`'s 631 KB of XML may contain this). A missing balance check allows malformed NACHA files to be generated, which banks will reject, causing settlement failures.

**6. Missing Configuration Detection Without Alerting**  
Variable `missing_config_count` in `nacha_file_process.dtsx` tracks configurations missing from `cf_report`. There is no visible alerting mechanism on this variable. If a new bank is added without corresponding `cf_report` configuration, the package silently skips it with no notification to operations.

**7. Per-Bank Serial Execution — Multi-Bank Gap Risk**  
The `bank_name` parameter makes the package bank-specific. For multi-bank NACHA processing, each bank requires a separate execution. If one bank's job fails, other banks' jobs may still succeed. Operations must monitor each bank's job independently. There is no parent-level orchestrator visible in this repository that ensures all banks are processed each day.

### MEDIUM

**8. `nacha_print_file.dtsx` — No Temp File Cleanup**  
Output files are written to `\temp\` with timestamps. No cleanup/archival logic is visible. Files accumulate indefinitely, creating disk space risk and a growing archive of unencrypted financial data on local disk.

---

## Technical Debt Inventory

| Item | Debt Type | Priority |
|---|---|---|
| NACHA files in plaintext temp directory | Security | P1 |
| CM.cf_report.Password under EncryptSensitiveWithUserKey | Security/Operations | P1 |
| No SFTP transmission in pipeline | Architecture | P1 |
| QC server in design-time connection | Operations | P1 |
| No NACHA file balance validation visible | Compliance | P1 |
| No alerting on missing bank configurations | Operations | P2 |
| Per-bank serial execution — no orchestration | Architecture | P2 |
| No temp file cleanup | Operations | P2 |
| Minimal Project.params (configs in packages) | Architecture | P2 |
| SQL Server 2012 SSIS (EOL) | Lifecycle | P2 |
| SQLNCLI11.1 deprecated | Operations | P3 |

---

## Remediation Priorities

### Immediate (P1)
1. Implement file encryption or secure file path for NACHA/EFA output files. At minimum, ensure `C:\ETL\Out\` is accessible only to the SSIS service account and designated operations staff. Evaluate writing to an encrypted volume.
2. Change SSIS project protection level to `DontSaveSensitive`. Move `CM.cf_report.Password` to SSIS Catalog environment parameter. Confirm whether SQL authentication or Windows authentication is used in production and align accordingly.
3. Add SFTP transmission as a final step in the NACHA pipeline, or document and track the manual transmission process with confirmation logging.
4. Validate that the production SSIS Catalog environment correctly overrides the QC connection string.

### Short-Term (P2)
5. Implement file balance validation in NACHA print logic — verify that entry amounts sum to batch control totals, and batch totals sum to file control totals.
6. Add `missing_config_count > 0` alerting — send email or raise SQL Agent job failure if bank configurations are missing.
7. Create a daily orchestrator job that tracks all required bank NACHA executions and reports success/failure collectively.
8. Implement temp file archival and purge — move successfully transmitted files to a time-limited archive and purge files older than the regulatory retention period.

### Longer-Term (P3)
9. Evaluate integrating Managed File Transfer (MFT) solution (e.g., GoAnywhere, Axway) for NACHA file delivery, providing audit trails, encryption, and delivery confirmation.
10. Upgrade SSIS packages to SQL Server 2019/2022 format and migrate from SQLNCLI11.1 to MSOLEDBSQL.
11. Consider rewriting NACHA generation logic in a language with mature NACHA library support (Python `nacha` library, Java `ach4j`) to simplify compliance validation.
