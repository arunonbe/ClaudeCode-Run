# DS_ETL_great-plains — Data Architect Report

## 1. Data Architecture Overview

`DS_ETL_great-plains` is a legacy SSIS ETL project containing 34 packages that form the **Great Plains (Microsoft Dynamics GP) integration layer** for the Onbe (formerly Wirecard/eCount/NorthLane) financial platform. The project uses the **old SQL Server 2008 R2 SSIS project format** (`ProductVersion 10.50.1600.1`), which predates the 2012 Project Deployment Model used by its companion `DS_ETL_finance-gp`.

| Attribute | Value |
|-----------|-------|
| Platform | SSIS — SQL Server 2008 R2 format (legacy package deployment model) |
| Project file format | `.dtproj` — pre-2012 format (no Project Deployment / SSISDB catalog) |
| Package count | 34 packages (`.dtsx`) |
| GP version | Microsoft Dynamics GP (Great Plains ERP) |
| Data direction | Bidirectional: reads from Onbe operational DBs; writes to GP ERP and financial targets |
| Key data sources | `ecountcore`, `ordersvc`, `jobsvc`, prepaid warehouse, FDR files, CubeReconciliation data |
| Key data targets | Microsoft Dynamics GP (GL, AR modules), CitiDirect bank, revenue share checks |

---

## 2. Package Inventory and Data Flows

### 2.1 ACH/Banking Packages

| Package | Source Data | Target | Data Elements |
|---------|------------|--------|---------------|
| `CitiDirectACH.dtsx` | Onbe fee/billing data | CitiDirect US ACH file | Routing number, account number, amount, company name — **NACHA regulated** |
| `CACitidirectACH.dtsx` | Canadian billing data | CitiDirect Canada ACH | Same as above for CAD |
| `CitidirectDrawdown.dtsx` | Onbe funding data | CitiDirect drawdown | Bank account funding amounts |
| `FeeInvoicingACH.dtsx` | Fee invoice data | ACH payment instruction | Client ACH debit for fees — **NACHA** |
| `FeeInvoicingDrawdown.dtsx` | Fee invoice data | Drawdown payment | Client fee collection via drawdown |

### 2.2 GL Export Packages (SOX-Critical)

| Package | Data Flow | Entity | Significance |
|---------|----------|--------|-------------|
| `SSIS_GLBatchE.dtsx` | Onbe East operational data → GP GL batch | East entity | **SOX** — posts journal entries to East legal entity GL |
| `SSIS_GLBatchBin.dtsx` | Binary-format GL batch | Unknown entity | **SOX** — binary GP import format (different from standard XML) |
| `SSIS_GLExportN.dtsx` | North entity operational data → GL | North entity | **SOX** |
| `SSIS_GLFLXCExport.dtsx` | FLXC (Flexible Chart of Accounts) data | GP FLXC format | **SOX** |
| `SSIS_GLTxExportN.dtsx` | Transaction-level GL data → North entity | North entity | **SOX** |

### 2.3 Reconciliation Packages

| Package | Data Flow | Significance |
|---------|----------|-------------|
| `SSIS_CubeReconcileE.dtsx` | East entity cube data → reconciliation | Financial reconciliation East entity |
| `SSIS_CubeReconcileN.dtsx` | North entity cube data → reconciliation | Financial reconciliation North entity |
| `SSIS_FDR.dtsx` | FDR (First Data Resources) settlement data → reconciliation | **PCI DSS scope** — Visa/Mastercard network settlement |

### 2.4 Sales Order / Invoicing Packages

| Package | Business Process |
|---------|----------------|
| `SOFeeAggregation.dtsx` | Aggregates fee records for invoicing |
| `SOFeeInvoicing.dtsx` | Creates Sales Orders in GP for client fees |
| `SOJobsvc.dtsx` | Job service billing → GP Sales Order |
| `SOJobsvc_Orig.dtsx` | Backup copy of SOJobsvc — committed to source control |
| `SOJobsvc_recompile.dtsx` | Recompile variant of SOJobsvc |
| `SOOrdersvc.dtsx` | Order service billing → GP Sales Order |
| `SOVoid.dtsx` | Sales Order void operations |

### 2.5 Special/Unique Packages

| Package | Business Process | Data Significance |
|---------|----------------|------------------|
| `SSIS_VSS.dtsx` | Visa Settlement Services data processing | **PCI DSS scope** — Visa network settlement data |
| `SSIS_MCS.dtsx` | MCS financial data | Management control services reporting |
| `SSIS_MCS_Summary.dtsx` | MCS summary reporting | Summary-level MCS |
| `CDW_P-DB06_DB06_P-DB08_DB08_0.dtsx` | Data Warehouse migration DB06 → DB08 | One-time migration artefact; production server names indicate CDE-adjacent systems |
| `Onus.dtsx` | OnUs internal settlement | Internal bank transfer |
| `PRD_CustomerBalance.dtsx` | Production customer balance data | **GLBA** — customer financial data |
| `ClientRefund.dtsx` | Client refund processing | Financial — client crediting |
| `RSCheck.dtsx` | Revenue share check generation | Financial |
| `PrepaidDigitalInvoice.dtsx` | Digital invoice generation for prepaid | Financial |
| `CPPLoopProcess.dtsx` | CPP client programme processing loop | Multi-client orchestration |

---

## 3. Sensitive Data Classification

| Data Category | Package(s) | Classification | Regulation |
|---|---|---|---|
| ACH routing/account numbers | `CitiDirectACH`, `CACitidirectACH`, `FeeInvoicingACH` | **HIGHLY SENSITIVE** — bank account data | NACHA, Reg E, GLBA |
| Visa settlement data | `SSIS_VSS` | **PCI DSS SCOPE** — network settlement records | PCI DSS Req 3, 10 |
| FDR settlement data | `SSIS_FDR` | **PCI DSS SCOPE** — First Data settlement records | PCI DSS Req 3, 10 |
| GL journal amounts | All `SSIS_GL*` packages | FINANCIAL — SOX-critical | SOX |
| Customer balance data | `PRD_CustomerBalance` | **GLBA** — customer financial data | GLBA |
| Client refund amounts | `ClientRefund` | FINANCIAL | GLBA |
| Revenue share amounts | `RSCheck` | FINANCIAL | SOX |
| Drawing/drawdown amounts | `CitidirectDrawdown`, `FeeInvoicingDrawdown` | FINANCIAL — bank | NACHA, Reg E |

---

## 4. Data Quality Concerns

- **Three versions of `SOJobsvc`**: `SOJobsvc.dtsx`, `SOJobsvc_Orig.dtsx`, `SOJobsvc_recompile.dtsx` — no mechanism to determine which is the canonical version. Running the wrong version would post incorrect Sales Orders to GP.
- **`CDW_P-DB06_DB06_P-DB08_DB08_0.dtsx`** — a one-time migration package committed to the active project. If executed by mistake, it would re-run a production data warehouse migration.
- No row-count or financial reconciliation assertions visible in the project configuration.
- The old 2008 R2 project format uses Package Deployment Model (no SSISDB catalog) — environment-specific configurations are stored in `.dtsConfig` files, which may contain sensitive data.

---

## 5. Database and System Dependencies

The packages connect to multiple SQL Server databases (specific connection strings are embedded in the `.dtsx` XML files — not visible without parsing the binary-encoded package bodies). Inferred dependencies based on package names and business context:

| System | Packages | Data Role |
|--------|---------|----------|
| `ecountcore` / `cbaseapp` SQL Server | `SOJobsvc`, `SOOrdersvc`, `CPPLoopProcess` | Source: job/order billing data |
| `jobsvc` SQL Server | `SOJobsvc` | Source: job service billing records |
| `ordersvc` SQL Server | `SOOrdersvc` | Source: order billing records |
| `prepaid_warehouse` SQL Server | `SSIS_CubeReconcile*`, `SSIS_GL*` | Source: prepaid warehouse reporting data |
| FDR flat files | `SSIS_FDR` | Source: First Data settlement files |
| Visa VSS files | `SSIS_VSS` | Source: Visa settlement files |
| CitiDirect API/file | `CitiDirectACH`, `CitidirectDrawdown` | Target: CitiDirect banking platform |
| Microsoft Dynamics GP SQL Server | All `SOFee*`, `SO*`, `SSIS_GL*` | Target: GP ERP |

---

## 6. Compliance Gaps

| Gap | Regulation | Severity |
|-----|-----------|----------|
| SSIS 2008 R2 format — EOL | Security best practice | CRITICAL |
| `SSIS_VSS` processes Visa settlement data in EOL infrastructure | PCI DSS | HIGH |
| `SSIS_FDR` processes First Data settlement data in EOL infrastructure | PCI DSS | HIGH |
| Three SOJobsvc versions — no canonical version indicator | SOX (change management) | HIGH |
| `CDW_P-DB06_DB06_P-DB08_DB08_0.dtsx` — migration package in active project | Data governance | MEDIUM |
| Package Deployment Model (no SSISDB) — config in .dtsConfig files | PCI DSS Req 8 (credential management) | MEDIUM |
| No financial reconciliation assertions in packages | SOX | MEDIUM |
