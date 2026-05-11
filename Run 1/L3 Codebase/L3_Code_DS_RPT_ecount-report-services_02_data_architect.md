# DS_RPT_ecount-report-services — Data Architect View

## Data Sources (from .rds files)
| Data Source Name | Server | Database | Used By |
|---|---|---|---|
| cf_report | Q-LIS-DB03,2231 | cf_report | Most folders (primary report DB) |
| cf_report (QA/Azure) | qc-az-db03.nam.wirecard.sys\qi_db03 | cf_report | Finance, RiskDB folders |
| CF_Report_Prod | p-db06.nam.wirecard.sys\db06,2431 | cf_report | External Report.Exception Reports |
| ECNT | q-db04.nam.wirecard.sys,2232\db04 | ECNT | Finance |
| ECAN | q-db03.nam.wirecard.sys\db03,2232 | ECAN | Finance.CANADA |
| EcountCore | q-db02.nam.wirecard.sys\db02,2232 | EcountCore | Risk |
| Cbaseapp | pc-db03,2231 | Cbaseapp | Risk |
| RiskDB | qc-az-db03.nam.wirecard.sys\qi_db03 | RiskDB | Finance, Internal |
| ecount_rollback | q-db02.nam.wirecard.sys\db02,2232 | ecountcore_rollback | Customer Service, Daily ACH |
| Prepaid_Warehouse | q-db03.nam.wirecard.sys\db03,2232 | Prepaid_Warehouse | Warehouse |
| RS2008 | q-db03.nam.wirecard.sys\db03,2232 | RS2008 | IT.Reports Monitoring |
| Dev.rds | (unknown — separate dev source) | (unknown) | External Report.Client Custom Reports |
| Banker.rds | (Finance project only) | (unknown) | Finance |

**Note:** All `.rds` connection files in the repo point to QA/dev servers (`q-db0x`, `qc-az-db03`) except `CF_Report_Prod` which points to production (`p-db06`). Production connection overrides are managed at the SSRS server level.

## Primary Database: cf_report
The `cf_report` database is the central reporting database for eCount. Based on report queries observed in RDL files:
- `t_Images` — stores report logo images (Image_ID, Image_JPEG blob, Image_Desc)
- `reportconfig` — report configuration (id, type='copyright', description)
- Stored procedures: `rpt_Repetitive_Fees` (Compliance), `dbo.sys_interface` (referenced in ETL), others
- DDA numbers referenced in Cardholder Activity reports (`dda_number` field in Repetitive Fees Report)

## Sensitive Data in Reports
| Data Type | Report(s) | Sensitivity | Regulation |
|---|---|---|---|
| Masked card number (`Masked_card_number`) | Cardholder Archived Transactions | PCI DSS — masked only, acceptable | PCI DSS Req 3.4 |
| DDA number | Repetitive Fees, Paycard Cardholder DDA Profile, PUID and DDA Lookup | Bank account reference — sensitive | GLBA |
| Cardholder first/last name | Multiple customer service reports | PII | CCPA, GLBA |
| PIN change/selection status | PIN Change Report, PIN Selection Status | PCI DSS SAD area — must not log full PIN | PCI DSS Req 3.3 |
| ACH transaction details (amount, routing) | ACH Detail Reports | NACHA / Reg E sensitive | NACHA, Reg E |
| Check details (check numbers, amounts) | Check Details Reports | Financial | GLBA |
| Email address | (referenced in notification flows) | PII | CCPA |
| Transaction amounts | Most financial reports | Financial | SOC 1 |
| Interchange rebate data | Secured Reports | Confidential financial | SOC 1 |
| Bank account number (last 4 visible) | Paycard Cardholder DDA Profile | PCI adjacent (bank not card) | GLBA |

**Key Finding**: `Masked_card_number` is used in Cardholder Archived Transactions — the report explicitly checks the BIN prefix to render the correct issuer disclosure. This confirms the report renders near-PCI-scope data (masked PANs). **Full PANs must never appear in any cf_report stored procedure output.**

## Encryption
- All `.rds` files use `IntegratedSecurity=true` — Windows authentication, no embedded SQL passwords.
- Transport encryption between SSRS server and SQL Server depends on SQL Server TLS configuration — not visible in repo.
- `t_Images` stores JPEG logo data as binary blobs in `cf_report` — no PII risk.
- Report output (PDF/HTML) — no encryption at rest configuration in repo; depends on SSRS server settings.

## Data Flow
```
cf_report DB (p-db06 production / q-db03 dev)
EcountCore DB (q-db02)
Prepaid_Warehouse DB (q-db03)
EcountCore_rollback DB (q-db02)
ECNT / ECAN / RiskDB / Cbaseapp
        |
    SSRS Report Server (RDL execution)
        |
    Report output: HTML portal / PDF / Excel / CSV
        |
    End users: Internal staff, Client-facing (External Reports)
```

## Compliance Gaps
1. **`.rds` files point to QA servers** — if production SSRS server is not properly overriding these, reports could run against QA data.
2. **`CF_Report_Prod.rds` on p-db06** — one production-pointing data source file committed to repo in the Exception Reports folder; confirms production server identity is disclosed in source control.
3. **`ecountcore_rollback` database as a report source** (`ecount_rollback.rds`) — rollback databases should not be routine report sources; data may be inconsistent.
4. **No PAN masking enforcement at the reporting layer** — if a stored procedure in `cf_report` returns a full card number, the RDL will render it; reliance on the SP to mask is a single point of failure.
5. **Secured Reports folder** — `Interchange Rebate` and financial reports with sensitive totals; SSRS folder-level security must be verified separately (not visible in source).
6. **Retired Reports in active solution** — retired report definitions are still in the SSRS solution; they should be removed to reduce the attack surface.
