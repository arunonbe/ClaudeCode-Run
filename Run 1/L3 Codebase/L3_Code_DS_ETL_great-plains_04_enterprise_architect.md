# DS_ETL_great-plains — Enterprise Architect Report

## 1. Platform Generation

| Attribute | Value |
|-----------|-------|
| Platform generation | Gen-1 (Pre-Wirecard / original eCount/NorthLane ERP integration) |
| Technology stack | SSIS 2008 R2 Package Deployment Model |
| SSIS version | `ProductVersion 10.50.1600.1` — SQL Server 2008 R2 |
| Relationship to sibling | Older/larger variant of `DS_ETL_finance-gp` (which uses SSIS 2012 Project Deployment Model) |
| Legal entity coverage | North + East entities; Canada + US; EMEAM-adjacent (inferred from package set) |

This is the **oldest SSIS project format** in the Data Services repository set — SQL Server 2008 R2 reached end of life in July 2019. The project predates both the Wirecard acquisition and the NorthLane rebranding, representing the original Great Plains ERP integration from the eCount/NorthLane era.

---

## 2. Business Domain

**Domain**: Finance and Accounting — ERP Integration  
**Subdomain**: General Ledger synchronisation, client fee invoicing, ACH fund movements, network settlement reconciliation

This pipeline is the **primary ERP bridge** between Onbe's operational payment processing systems and the Microsoft Dynamics GP accounting system. It supports the entire financial close process:

1. **Client invoicing** — Sales Order creation in GP for program fees.
2. **GL posting** — Journal entry export to GP for multiple legal entities (East, North, Canada).
3. **Bank fund movements** — CitiDirect ACH/drawdown for fee collection and client refunds.
4. **Network settlement** — Visa (VSS) and First Data (FDR) settlement reconciliation.
5. **Revenue share** — RSCheck revenue share check generation.

**Uniqueness vs. `DS_ETL_finance-gp`**: This repo contains 34 packages vs. the finance-gp repo's smaller set, including:
- Additional GL exports for the North entity (`SSIS_GLExportN`, `SSIS_GLTxExportN`)
- Visa Settlement Services (`SSIS_VSS`)
- MCS reporting (`SSIS_MCS`, `SSIS_MCS_Summary`)
- East entity cube reconciliation (`SSIS_CubeReconcileE`)
- Binary-format GL batch (`SSIS_GLBatchBin`)
- Data warehouse migration package (`CDW_P-DB06_DB06_P-DB08_DB08_0.dtsx`)

---

## 3. System Role in the Enterprise

| Role | Description |
|------|-------------|
| ERP integration hub | Sole mechanism for posting financial data to Microsoft Dynamics GP |
| ACH payment orchestrator | Generates CitiDirect ACH files for US and Canadian fee collection |
| GL publisher | Exports all journal entries for East and North legal entities |
| Settlement reconciliation | Reconciles Visa (VSS) and First Data (FDR) network settlement against operational data |
| Financial close enabler | Without this pipeline, the monthly financial close cannot complete |

This pipeline is **SOX-critical**: GL packages directly populate the general ledger of the legal entity that files financial statements with regulators.

---

## 4. Dependencies

### Upstream (reads from)
| System | Packages | Data |
|--------|---------|------|
| `ecountcore` / `cbaseapp` | `SOJobsvc`, `SOOrdersvc`, `CPPLoopProcess` | Job/order transaction data |
| `jobsvc` | `SOJobsvc` | Job service billing data |
| `ordersvc` | `SOOrdersvc` | Order service billing data |
| Prepaid Warehouse | `SSIS_CubeReconcile*`, `SSIS_GL*` | Financial reporting aggregates |
| FDR files | `SSIS_FDR` | First Data settlement files |
| Visa VSS files | `SSIS_VSS` | Visa settlement files |
| `DB06` data warehouse | `CDW_P-DB06_*` | One-time migration source |

### Downstream (writes to)
| System | Packages | Data Written |
|--------|---------|-------------|
| Microsoft Dynamics GP | `SOFee*`, `SO*`, `SSIS_GL*` | Sales orders, GL journal entries |
| CitiDirect (US) | `CitiDirectACH` | NACHA ACH file |
| CitiDirect (Canada) | `CACitidirectACH` | Canadian ACH file |
| CitiDirect Drawdown | `CitidirectDrawdown`, `FeeInvoicingDrawdown` | Drawdown payment instructions |
| `DB08` data warehouse | `CDW_P-DB06_*` | One-time migration target |

---

## 5. Integration Patterns

| Pattern | Where Used | Assessment |
|---------|-----------|------------|
| File-based ETL | FDR, VSS settlement files | Gen-1 flat file processing |
| SQL-to-SQL bulk copy | All GP-targeting packages | SSIS OLE DB source/destination |
| NACHA file generation | `CitiDirectACH`, `CACitidirectACH`, `FeeInvoicingACH` | File-based bank API integration |
| Drawdown instruction | `CitidirectDrawdown`, `FeeInvoicingDrawdown` | File or direct bank API |
| SSIS Package Deployment Model | Project-level deployment | Oldest SSIS deployment model |
| Manual version control | `SOJobsvc_Orig`, `SOJobsvc_recompile` | Developer-managed file copies replacing git branching |

---

## 6. Strategic Status

**Current status**: ACTIVE — assumed production-critical based on financial process dependency.

**Assessment**: This pipeline is **irreplaceable in the short term** because it is the only mechanism for GL posting to Microsoft Dynamics GP. However, it represents significant technical and compliance risk:

- SSIS 2008 R2 is 6+ years past EOL.
- Running PCI DSS–scoped data (VSS, FDR) through EOL infrastructure likely constitutes a PCI DSS compensating control gap.
- The SOJobsvc 3-version problem is an active SOX change management risk.

The parallel existence of `DS_ETL_finance-gp` (SSIS 2012 version) suggests a migration to the newer project format was in progress or planned. The strategic path is:
1. Consolidate to `DS_ETL_finance-gp` (newer format).
2. Migrate remaining unique packages (`SSIS_VSS`, `SSIS_MCS*`, `SSIS_GLExportN`, `SSIS_GLTxExportN`, `SSIS_CubeReconcileE`, `SSIS_GLBatchBin`) from this repo into the 2012-format project.
3. Decommission `DS_ETL_great-plains` after consolidation.
4. Long-term: replace SSIS with Spring Batch / Azure Data Factory as part of Gen-3 migration.

---

## 7. Migration Blockers

| Blocker | Detail |
|---------|--------|
| SOJobsvc 3-version ambiguity | Must determine canonical version before migrating — wrong version in production = SOX violation |
| `CDW_P-DB06_DB06_P-DB08_DB08_0.dtsx` | One-time migration package must be identified as completed or pending before decommission |
| GP ERP dependency | Microsoft Dynamics GP itself may be an EOL platform being replaced; GP migration must be co-ordinated |
| No source control for config | Connection strings embedded in packages; cannot migrate without first externalising configuration |
| VSS/FDR settlement formats | File formats from Visa and First Data are proprietary; any Gen-3 replacement requires re-implementation of parsers |
| PCI DSS scoping | VSS and FDR packages are PCI-adjacent; Gen-3 replacement requires formal QSA scoping before production cutover |
