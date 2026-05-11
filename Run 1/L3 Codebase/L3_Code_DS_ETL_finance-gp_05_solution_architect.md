# Solution Architect View — DS_ETL_finance-gp

## Repository Overview

**Repo path:** `E:\OnbeEast363\repos\DS_ETL_finance-gp`
**Package count:** 18
**Connection manager count:** 10 (`.conmgr` files)
**Total repo size:** ~3.7 MB (excluding .git)

---

## Complete Object / Package Inventory

| Package | Size (bytes) | Purpose | Creator Domain | Key Connections |
|---|---|---|---|---|
| `SSIS_FDR.dtsx` | 720,574 | FDR (First Data) settlement reconciliation | (inferred — largest pkg) | cf_report, FDR files |
| `PRD_CustomerBalance.dtsx` | 412,589 | Production customer balance extraction | — | ATLYS_E, cf_report |
| `Onus.dtsx` | 397,110 | OnUs internal settlement processing | — | ATLYS_E, cf_report |
| `ClientRefund.dtsx` | 367,569 | Client refund processing | — | cf_report, GP databases |
| `SOFeeInvoicing.dtsx` | 313,497 | Sales Order fee invoice generation | `CB_OFFICE\MButola` | Core, GP |
| `SOJobsvc.dtsx` | 313,404 | Job service invoice processing | — | Core, GP |
| `SOOrdersvc.dtsx` | 311,478 | Order service invoice processing | — | Core, GP |
| `SOVoid.dtsx` | 232,582 | Sales Order void/reversal | — | Core, GP |
| `SSIS_GLBatchE.dtsx` | 223,599 | GL Batch Export — East/US entity | — | cf_report → GP |
| `CPPLoopProcess.dtsx` | 85,927 | CPP orchestration loop master | — | SSISConfigurations/Banker |
| `SSIS_CubeReconcileN.dtsx` | 83,950 | Cube reconciliation — North entity | — | ATLYS_RvCR |
| `CitiDirectACH.dtsx` | 69,390 | CitiDirect US ACH file generation | — | ECNT GP, cf_report |
| `FeeInvoicingDrawdown.dtsx` | 72,796 | Fee invoicing via drawdown | — | Core, ECNT GP |
| `FeeInvoicingACH.dtsx` | 72,310 | Fee invoicing via ACH | — | Core, ECNT GP |
| `PrepaidDigitalInvoice.dtsx` | 48,874 | Digital invoice for prepaid programmes | `NAM\gc48614` | cf_report |
| `RSCheck.dtsx` | 60,940 | Revenue share check processing | — | RSServer |
| `SOFeeAggregation.dtsx` | 31,466 | Fee aggregation per billing period | `CB_OFFICE\MButola` | Core, Banker |
| `CACitidirectACH.dtsx` | 6,896 | Canada CitiDirect ACH | — | ECAN GP |

---

## Connection Manager Inventory (Full)

| File | DTSID | Server | Catalog | Type | Auth | Credential Issue |
|---|---|---|---|---|---|---|
| `ATLYS_E.conmgr` | `{F611719E-...}` | `q-db03.nam.wirecard.sys,2232\db03` | `ATLYS_E` | OLEDB SQLNCLI11 | SSPI | None |
| `ATLYS_RvCR.conmgr` | `{...}` | `q-db03.nam.wirecard.sys,2232\db03` | `ATLYS_RvCR` | OLEDB SQLNCLI11 | SSPI | None |
| `Banker.conmgr` | (inferred) | `q-db03` | `Banker` | OLEDB SQLNCLI11 | SSPI | None |
| `cf_report.conmgr` | (inferred) | `q-db03.nam.wirecard.sys,2232\db03` | `cf_report` | OLEDB SQLNCLI11 | SSPI | None |
| `Core.conmgr` | `{4B449B7E-...}` | `q-db02.nam.wirecard.sys,2232\db02` | `Ecountcore` | OLEDB SQLNCLI11.1 | SSPI | None |
| `ECAN GP.conmgr` | `{1BED7AEC-...}` | `q-db03.nam.wirecard.sys,2232\db03` | `ECAN` | OLEDB SQLNCLI11.1 | SSPI | None |
| `ECNT GP.conmgr` | (inferred) | `q-db03` | `ECNT` | OLEDB SQLNCLI11 | SSPI | None |
| `RSServer.conmgr` | (inferred) | — | `RS` | OLEDB | SSPI | None |
| `SSISConfigurations.conmgr` | `{4D5EAD08-...}` | `q-db03.nam.wirecard.sys,2232\db03` | `Banker` | OLEDB SQLNCLI11 | SSPI | None |
| `SMTP Server.conmgr` | — | — | — | SMTP | — | No TLS visible |

---

## Security Vulnerabilities

### 1. SSIS Package Deployment Model with Configuration Tables — Untracked Configuration

**Severity: HIGH**

The `SSISConfigurations.conmgr` and the `DTS:EnableConfig="True"` setting in `SOFeeAggregation.dtsx` (line 9) indicate the older SSIS Package Deployment Model with configuration tables. The `Banker.dbo.SSISJobConfigurations` table contains runtime parameter values (server names, file paths, job types) that are not stored in version control.

This means:
- Production environment parameters can be changed without a code deployment or git commit
- Audit trail for configuration changes depends entirely on database audit logging
- Developers may make changes to configuration without peer review

**Remediation:** Migrate to Project Deployment Model with SSIS catalog environments. Store all runtime parameters in version-controlled deployment scripts.

### 2. Hardcoded Local File Path

**File:** `PrepaidDigitalInvoice.dtsx`, line 27
```
<DTS:Property DTS:DataType="8" DTS:Name="ParameterValue">D:\Jobs_Files\Outbound\</DTS:Property>
```

**Severity: Medium**
A local drive path is hardcoded as the default parameter value. This means the package can only execute successfully on a server where `D:\Jobs_Files\Outbound\` exists. It cannot run from an arbitrary execution host.

**Remediation:** Replace with a UNC path or a project-level parameter that resolves to an environment-appropriate path.

### 3. Application Name Leakage in Connection Strings

**File:** `ATLYS_E.conmgr`, line 8:
```
Application Name=SSIS-Onus-{F611719E-...}ppamwdcUIgp1A1\ppamwdcUIgp1A1.ATLYS_E;
```

**File:** `ECAN GP.conmgr`, line 8:
```
Application Name=SSIS-CitidirectDrawdown-{...}PPAMWDCUIGP1A1\PPAMWDCUIGP1A1.ECNT.gplain;
```

The `Application Name` in connection strings contains machine names (`ppamwdcUIgp1A1`, `PPAMWDCUIGP1A1`) and package names, committed to the git repository. These are production machine names (`ppamwdc*` prefix). While this information is embedded by SSDT automatically, it should be sanitised before committing to git as it exposes internal production server naming conventions.

**Severity: Low**

### 4. No TLS Enforcement on SQL Connections

All `.conmgr` files use `Integrated Security=SSPI` without `Encrypt=True`. This applies to connections carrying:
- ACH routing information
- GL journal amounts
- Customer balance data

**Severity: High** for connections carrying financial and potentially account data.

### 5. SSIS_FDR.dtsx — Potential PCI DSS Data Handling Risk

**Severity: High (pending full inspection)**

The `SSIS_FDR.dtsx` package processes First Data Resources settlement data. FDR settlement files may contain masked PANs, transaction amounts, and cardholder billing data. Without full inspection of this 720 KB package, it is unclear whether:
- PAN data is stored in intermediate SQL tables without masking
- Settlement records are written to unencrypted files
- Audit logging of FDR data access is in place

**Remediation:** Conduct a full PCI DSS data flow analysis of `SSIS_FDR.dtsx` as a priority item.

---

## Technical Debt Summary

| Item | Severity |
|---|---|
| 13-year-old packages (SOFeeAggregation created 2011) | High |
| Package Deployment Model with config tables | High |
| No CI/CD pipeline | Critical |
| SSIS_FDR.dtsx — 720 KB single package, unreviewed for PCI compliance | Critical |
| SSIS_GLBatchE.dtsx — SOX-critical, no automated regression tests | Critical |
| Hardcoded local path in PrepaidDigitalInvoice | Medium |
| No TLS enforcement on financial data connections | High |
| Package overlap with DS_ETL_great-plains (14 duplicate package names) | High |
| Machine name leakage in Application Name properties | Low |

---

## Remediation Priority

| Priority | Action |
|---|---|
| 1 (Critical) | Full PCI DSS review of `SSIS_FDR.dtsx` — trace all data paths for PANs and transaction data |
| 2 (Critical) | Implement CI/CD pipeline with automated `.ispac` deployment and parameter validation |
| 3 (High) | Migrate from Package Deployment Model to Project Deployment Model; version-control all environment parameters |
| 4 (High) | Add `Encrypt=True` to all SQL connection strings, especially those carrying financial data |
| 5 (High) | Resolve duplication with DS_ETL_great-plains — consolidate or formally document the divergence |
| 6 (Medium) | Replace hardcoded `D:\Jobs_Files\Outbound\` path with parameterised UNC path |
| 7 (Medium) | Sanitise Application Name values in connection manager files before git commits |
| 8 (Low) | Document `Banker.dbo.SSISJobConfigurations` schema in this repository |
