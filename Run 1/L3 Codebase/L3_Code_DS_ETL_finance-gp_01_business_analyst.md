# Business Analyst View — DS_ETL_finance-gp

## Repository Overview

**Repo path:** `E:\OnbeEast363\repos\DS_ETL_finance-gp`
**Solution file:** `finance-gp.sln`
**SSIS project:** `finance-gp.dtproj`
**Git branch:** `development`
**README:** Minimal — placeholder only (16 bytes)

This is the **largest and most complex** of the six repositories, with 18 SSIS packages totalling approximately 3.4 MB of package XML. It acts as the **ERP integration bridge** between Onbe's card programme financial data and the Microsoft Dynamics GP (Great Plains) accounting system. It handles fee invoicing, ACH fund movements, client programme reconciliation, GL batch exports, and multi-currency processing.

---

## Business Purpose

Microsoft Dynamics GP is Onbe's general ledger and accounts payable system. For every billing cycle, Onbe must:
1. Calculate fees owed by clients (programme fees, transaction fees, interchange)
2. Generate invoices and collect payment via ACH or drawdown
3. Post journal entries to GP's general ledger
4. Reconcile the cardholder liability ledger (balance sheet) against GP

This repository automates all the steps from financial calculation through ERP posting. It is the **financial backbone** of client billing and GL reconciliation.

---

## Packages and Business Processes

### `CPPLoopProcess.dtsx` (85,927 bytes)
**Business process:** Client Programme Processing (CPP) loop orchestrator. This is likely a master control package that iterates through client programme processing jobs. The package reads job configuration from `Banker.dbo.SSISJobConfigurations` (seen in `SOFeeAggregation.dtsx` parameter `ProcessId`) and runs child packages (SOFeeAggregation, SOFeeInvoicing, etc.) for each configured client or billing period.

**Key design pattern:** Parameterised loop process — `ProcessId`, `JobType`, `EndDate` parameters are passed from `CPPLoopProcess` down to child packages. This is the same "loop master" pattern seen in enterprise SSIS frameworks.

### `SOFeeAggregation.dtsx` (31,466 bytes)
**Business process:** Sales Order (SO) Fee Aggregation. Aggregates fee charges for client sales orders across a billing period. Parameters: `EndDate`, `JobType` (31), `ProcessId`, `StartDate`. Reads from `Ecountcore` (order/transaction data), aggregates fee totals, writes results to intermediate staging tables. Execution is logged to `\\q-na-stk01.nam.wirecard.sys\GP_Files\SOAFeeAggregation.log` (dtsx line 31).

### `SOFeeInvoicing.dtsx` (313,497 bytes)
**Business process:** Sales Order Fee Invoicing. The largest invoicing package. Takes aggregated fee data and generates formal invoices in GP format. Creates AP/AR entries in Great Plains. Contains the fee-to-GL-account mapping business rules.

### `SOJobsvc.dtsx` (313,404 bytes)
**Business process:** Sales Order Job Service invoice processing. Handles job service fees (similar to SOFeeInvoicing but for job/service type billing).

### `SOOrdersvc.dtsx` (311,478 bytes)
**Business process:** Sales Order Order Service processing. Handles order service fees.

### `SOVoid.dtsx` (232,582 bytes)
**Business process:** Sales Order Void processing. Handles reversal and voiding of previously generated invoices or transactions. Critical for credit memos and billing corrections.

### `CitiDirectACH.dtsx` (69,390 bytes)
**Business process:** Citi Direct ACH payment processing. Generates ACH debit files or initiates ACH fund movements via Citibank's CitiDirect platform. Used for collecting client fees via ACH or initiating cardholder refunds. Connects to ECNT GP database (Great Plains company for the ECNT entity).

### `CACitidirectACH.dtsx` (6,896 bytes)
**Business process:** Canada CitiDirect ACH processing — the Canadian-entity variant of `CitiDirectACH.dtsx`.

### `CitidirectDrawdown.dtsx` (65,174 bytes)
**Business process:** Citi Direct Drawdown. Drawdown transactions are wholesale fund movements from client trust accounts to cover cardholder loads. Uses ECAN GP database (Canadian entity) and ECNT GP database (US entity).

### `FeeInvoicingACH.dtsx` (72,310 bytes)
**Business process:** Fee invoicing via ACH. Generates ACH files for fee collections from clients. Reads fee invoice data and formats it for ACH NACHA file output.

### `FeeInvoicingDrawdown.dtsx` (72,796 bytes)
**Business process:** Fee invoicing via drawdown. Same as FeeInvoicingACH but for drawdown payment method clients.

### `ClientRefund.dtsx` (367,569 bytes)
**Business process:** Client Refund processing. Handles refunds to clients — a revenue-impacting process. Second largest package. Likely involves credit memos in GP and ACH/wire return instructions.

### `Onus.dtsx` (397,110 bytes)
**Business process:** OnUs (On-Us) settlement processing. OnUs refers to transactions where both the issuer and acquirer are the same institution (Onbe). The OnUs settlement process reconciles these internal transactions and posts the appropriate GL entries. This is the second largest package. Connects to `ATLYS_E` (Atlys East/US entity database) and `cf_report`.

### `PRD_CustomerBalance.dtsx` (412,589 bytes)
**Business process:** Production Customer Balance extraction/reporting. The **largest package** in the repository. Extracts detailed customer (cardholder) balance data for production reporting, likely feeding both banking partner reports and internal controls. The `PRD_` prefix indicates production-specific logic.

### `PrepaidDigitalInvoice.dtsx` (48,874 bytes)
**Business process:** Prepaid Digital Invoice generation. Creates digital invoices for prepaid card programmes. Output path `D:\Jobs_Files\Outbound\` (dtsx line 27 — hardcoded local path).

### `RSCheck.dtsx` (60,940 bytes)
**Business process:** Revenue Share (RS) Check processing. Handles revenue share payments to partners or distribution networks. `RSServer.conmgr` points to an RS server.

### `SSIS_FDR.dtsx` (720,574 bytes)
**Business process:** First Data Resources (FDR) processing. The **single largest package in the entire six-repo set** at 720 KB. FDR is a card processing network/processor. This package processes FDR settlement data — likely ingesting FDR settlement files, reconciling against Onbe's internal records, and posting GL entries.

### `SSIS_GLBatchE.dtsx` (223,599 bytes)
**Business process:** GL Batch Export for the East/US entity. Generates GL batch files for import into Great Plains. This is a SOX-relevant process — the GL batch drives the financial statements.

### `SSIS_CubeReconcileN.dtsx` (83,950 bytes)
**Business process:** Cube Reconciliation for North entity. Reconciles OLAP cube data against transactional data — a financial accuracy control.

---

## Data Flows (High-Level)

```
Ecountcore (orders/transactions)
ATLYS_E (Atlys card programme)
cf_report (financial reporting)
ECAN GP / ECNT GP / Dynamics GP
        |
        v
[finance-gp SSIS packages]
   Fee aggregation, invoicing, ACH, drawdown, GL batch
        |
   +----+------+----------+----------+
   v           v          v          v
[Great Plains] [ACH files] [FDR recon] [GP file share]
  (journal      (NACHA      (settlement  (\\stk01\GP_Files)
   entries)      files)      files)
```

---

## Schedule / Frequency

- **Daily:** CitiDirectACH, CitidirectDrawdown, FeeInvoicingACH, FeeInvoicingDrawdown — ACH files must be submitted by specific bank cut-off times
- **Monthly:** SOFeeAggregation → SOFeeInvoicing → GLBatchE — billing cycle drives monthly fee invoice and GL posting
- **On-demand/settlement cycle:** SSIS_FDR, Onus — driven by FDR settlement file availability (typically daily from processor)
- **Monthly/on-demand:** PRD_CustomerBalance, ClientRefund, RSCheck

---

## Business Rules Encoded

| Rule | Package | Detail |
|---|---|---|
| Billing period parameterisation | SOFeeAggregation, SOFeeInvoicing | `EndDate`, `StartDate`, `JobType` drive which period is processed |
| Entity segmentation (US/Canada) | CitiDirectACH vs CACitidirectACH | Separate packages per legal entity |
| GP company database routing | ECAN GP vs ECNT GP | ECAN = Canadian entity, ECNT = US entity |
| Security protocol enforcement | Project.params `SecurityProtocol=3072` | Forces TLS 1.2 for network connections (`3072 = Tls12`) |

---

## Regulatory Relevance

- **SOX:** GL batch export (`SSIS_GLBatchE`) feeds the general ledger. This is a SOX Sarbanes-Oxley in-scope financial process
- **NACHA/Reg E:** ACH file generation (CitiDirectACH, FeeInvoicingACH) must comply with NACHA formatting rules and Reg E consumer protection requirements
- **PCI DSS:** FDR settlement data handling — FDR files may contain cardholder-level transaction detail including masked PANs
- **GLBA:** Customer balance data in `PRD_CustomerBalance.dtsx` is non-public personal financial information
