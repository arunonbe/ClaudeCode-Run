# Business Analyst View — DS_ETL_great-plains

## Repository Overview

**Repo path:** `E:\OnbeEast363\repos\DS_ETL_great-plains`
**Solution file:** `Great-Plains.sln`
**SSIS project:** `Great-Plains.dtproj` (older format — `ProductVersion 10.50.1600.1` = SQL Server 2008 R2)
**Git branch:** `development`
**README:** Placeholder (14 bytes)

This repository contains a **large collection of Great Plains (Microsoft Dynamics GP) integration SSIS packages**. Structurally, it is nearly identical to `DS_ETL_finance-gp`, sharing most package names. The critical difference is the SSIS project format version — this uses the older SQL Server 2008 R2 project format (`ProductVersion 10.50.1600.1`), while `DS_ETL_finance-gp` uses the 2012-era Project Deployment Model.

**Assessment:** `DS_ETL_great-plains` is most likely an **archived or legacy copy** of the GP ETL packages from the Wirecard/pre-Project Deployment era. It may serve a **different legal entity or region** (North/EMEAM/EMXN entities), or it may be the baseline from which `DS_ETL_finance-gp` was forked and modernised.

---

## Business Purpose

Same as `DS_ETL_finance-gp` — Great Plains ERP integration for:
1. **Client fee invoicing** (Sales Order invoicing, ACH/drawdown collection)
2. **GL journal entry generation** (GL Batch exports for financial statement posting)
3. **Settlement reconciliation** (FDR data, cube reconciliation)
4. **Banking fund movements** (CitiDirect ACH and drawdown)
5. **Client refunds and revenue share** (ClientRefund, RSCheck)

The presence of additional packages `SSIS_GLBatchBin`, `SSIS_GLExportN`, `SSIS_GLTxExportN`, `SSIS_GLFLXCExport`, `SSIS_MCS`, `SSIS_MCS_Summary`, `SSIS_VSS` — not present in `DS_ETL_finance-gp` — suggests this repo **additionally handles GL export variants** for the North and other entities, as well as MCS (Merchant/Management Control Services?) and VSS (Visa Settlement Services?) integrations.

---

## Packages and Business Processes

### Packages Shared with DS_ETL_finance-gp

The following packages appear in both repos (by name), suggesting they are variants for different entities or time periods:

| Package | Business Function |
|---|---|
| `CitiDirectACH.dtsx` | CitiDirect US ACH file generation |
| `CACitidirectACH.dtsx` | CitiDirect Canada ACH |
| `CitidirectDrawdown.dtsx` | CitiDirect drawdown fund movement |
| `ClientRefund.dtsx` | Client refund processing |
| `CPPLoopProcess.dtsx` | Client programme processing orchestrator |
| `FeeInvoicingACH.dtsx` | Fee invoicing via ACH |
| `FeeInvoicingDrawdown.dtsx` | Fee invoicing via drawdown |
| `Onus.dtsx` | OnUs internal settlement |
| `PRD_CustomerBalance.dtsx` | Production customer balance |
| `PrepaidDigitalInvoice.dtsx` | Digital invoice generation |
| `RSCheck.dtsx` | Revenue share checks |
| `SOFeeAggregation.dtsx` | Sales order fee aggregation |
| `SOFeeInvoicing.dtsx` | Sales order fee invoicing |
| `SOJobsvc.dtsx` | Job service invoice processing |
| `SOOrdersvc.dtsx` | Order service invoice processing |
| `SOVoid.dtsx` | Sales order void |
| `SSIS_CubeReconcileN.dtsx` | Cube reconciliation — North entity |
| `SSIS_FDR.dtsx` | FDR settlement reconciliation |
| `SSIS_GLBatchE.dtsx` | GL Batch Export — East entity |

### Packages Unique to DS_ETL_great-plains

| Package | Business Function | Significance |
|---|---|---|
| `CDW_P-DB06_DB06_P-DB08_DB08_0.dtsx` | Data Warehouse transfer DB06→DB08 | Infrastructure data movement — server migration or CDW replication |
| `SSIS_CubeReconcileE.dtsx` | Cube reconciliation — East entity | Parallel to CubeReconcileN for East entity |
| `SSIS_GLBatchBin.dtsx` | GL Batch Binary export | Binary-format GL batch (for specific GP import method?) |
| `SSIS_GLExportN.dtsx` | GL Export — North entity | GL data export for North/North America entity |
| `SSIS_GLFLXCExport.dtsx` | GL FLXC Export | GL Flexible Chart of Accounts export (GP FLXC format) |
| `SSIS_GLTxExportN.dtsx` | GL Transaction Export — North | Transaction-level GL export |
| `SSIS_MCS.dtsx` | MCS (Management Control Services?) | MCS financial data processing |
| `SSIS_MCS_Summary.dtsx` | MCS Summary | Summary-level MCS reporting |
| `SSIS_VSS.dtsx` | VSS (Visa Settlement Services) | Visa network settlement data processing |
| `SOJobsvc_Orig.dtsx` | SOJobsvc original backup | **Backup copy committed to repo — should not be in version control** |
| `SOJobsvc_recompile.dtsx` | SOJobsvc recompile variant | **Alternative version — suggests ad-hoc development practices** |

---

## Notable Findings

### SOJobsvc Variants (3 versions)
The presence of `SOJobsvc.dtsx`, `SOJobsvc_Orig.dtsx`, and `SOJobsvc_recompile.dtsx` in the same repository is a significant concern. This suggests:
1. A developer created a backup copy (`_Orig`) before modifying the package
2. A recompile variant was created (`_recompile`) — perhaps to fix a deployment issue
3. All three versions were committed to git as active files

In a proper git workflow, the original version would be preserved in git history, not as a parallel file. This indicates the team was not confident using git for version history and instead used file naming as a version control substitute.

### `CDW_P-DB06_DB06_P-DB08_DB08_0.dtsx` — Data Warehouse Migration Package
This package's name indicates it moves data from a server `P-DB06_DB06` to `P-DB08_DB08`. The `P-` prefix suggests production servers. This appears to be a **one-time data migration package** that was not cleaned up after the migration. It should not be deployed to the active package catalog.

### Visa Settlement Services (`SSIS_VSS.dtsx`)
VSS is Visa's settlement and reconciliation service. This package processes Visa network settlement data — this is **PCI DSS scope** data (Visa transaction records, interchange, settlement amounts).

---

## Data Flows

Same as DS_ETL_finance-gp plus:
- Visa settlement data → `SSIS_VSS` → GL reconciliation
- MCS data → `SSIS_MCS` / `SSIS_MCS_Summary` → reporting
- GL data → `SSIS_GLExportN`, `SSIS_GLTxExportN` → GP North entity

---

## Schedule / Frequency

Same as DS_ETL_finance-gp — daily for ACH/settlement, monthly for invoicing/GL batch.

The unique packages (`SSIS_VSS`, `SSIS_MCS`) would also run on their respective settlement cycles:
- `SSIS_VSS` — daily or per-Visa settlement cycle (typically daily)
- `SSIS_MCS` — monthly or per-reporting period

---

## Regulatory Relevance

| Regulation | Package | Notes |
|---|---|---|
| **SOX** | `SSIS_GLBatchE`, `SSIS_GLBatchBin`, `SSIS_GLExportN`, `SSIS_GLFLXCExport`, `SSIS_GLTxExportN` | All GL export packages are SOX-critical financial reporting processes |
| **PCI DSS** | `SSIS_VSS`, `SSIS_FDR` | Visa settlement and FDR data contain network-level transaction data |
| **NACHA/Reg E** | CitiDirectACH, CACitidirectACH, FeeInvoicingACH | ACH NACHA file compliance |
| **GLBA** | `PRD_CustomerBalance`, `ClientRefund` | Customer financial data |
