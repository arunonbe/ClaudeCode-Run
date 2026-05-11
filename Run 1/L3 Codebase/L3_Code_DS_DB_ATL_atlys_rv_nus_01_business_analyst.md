# Business Analyst Report: DS_DB_ATL_atlys_rv_nus

## Repository Identity

| Field | Value |
|---|---|
| Repository name | DS_DB_ATL_atlys_rv_nus |
| Full meaning | Atlys Reward Value US (primary database) |
| Database project type | SQL Server Data Tools (SSDT) `.sqlproj` |
| Target SQL Server | SQL Server 2016 (`Sql130DatabaseSchemaProvider`) |
| Project file | `atlys_rv_nus.sqlproj` (102 KB — largest in the family) |
| Source files | ~95 tables, ~270+ views, ~80+ stored procedures, ~120+ functions, user-defined types, Security folder |

This is the **primary and most comprehensive US Atlys database** — the full operational and reporting database for the Atlys financial management platform covering US prepaid card programs. Unlike its rollback sibling (`atlys_rv_nus_r`), this database contains all tables, stored procedures, functions, views, and security definitions.

---

## Business Purpose

The Atlys RV NUS database serves as the **financial operations and reporting backbone** for US prepaid card programs managed on the eCount platform. It supports the following enterprise-level business functions:

1. **Revenue recognition and GL batch preparation** — tracking fee and revenue entries, mapping to Great Plains GL accounts, and generating GL batches for ERP posting
2. **Gross Profit analysis** — comprehensive program-level P&L reporting including revenue, costs, commissions, and deferred revenue
3. **Balance reconciliation** — bank/processor settlement reconciliation, FDR clearing and settlement file processing
4. **Customer liability tracking** — deferred revenue and float balance monitoring per program
5. **Sales commission calculation** — automated calculation of sales rep commissions based on revenue events
6. **Issuance, spend, and plastics tracking** — granular card production and usage reporting
7. **Audit trail** — complete audit logging of data changes and access
8. **Program configuration** — bank, BIN, card type, emboss vendor, and cost rate mappings

---

## Business Processes Supported

### Revenue Management
The `revenue` table (with trigger `trg_revenue`) is the central revenue ledger. The trigger auto-populates GL account codes, product classifications, and channel codes on insert/update based on program configuration tables (`vAffiliates`, `vProducts`, `tblProgramsBank`). This is a real-time revenue classification system.

Views `vRevenueT0`, `vRevenueT_Cardholder`, `vRevenueT_CardholderInterchange`, `vRevenueT_MaintFees`, `vRevenueT_Partner`, `vRevenueT_FVD`, and `vRevenueT_Issue` segment revenue by type, enabling detailed revenue type analysis.

### GL Batch Processing
The `tblGLBatch`, `tblGLBatchBin`, `tblGLBatchFeeTax` tables and `sys_glbatch`, `sys_glbatchbin`, `sys_glbatchfeetax`, `sys_glbatch_complete` procedures manage the GL batch lifecycle — from staging revenue/cost entries to marking batches as complete for Great Plains posting.

### Settlement and Bank Reconciliation
`tblSettle` and `tblSettleDtl` store FDR processor settlement data (net spend, interchange, pass-through fees, chargebacks, representments) by BIN/ICA and currency. The `sys_bank_reconcile*` procedures perform automated reconciliation against GP cash balances.

### Deferred Revenue (Customer Liability)
Views `vCustLiabilityT*`, `vDefRev*` and the `tblDefRev*` tables track the float (unexpired card balances) as a liability. The deferred revenue calculation is critical for financial reporting under revenue recognition accounting standards.

### Commission Calculation
`tblCommissions`, `tblCommissionsRates`, and the `sys_comm*` procedures automate sales rep commission calculation based on revenue entries and commission rate schedules.

### Sweep and Breakage
`tblSweepBreakage` and functions `sys_getSweepBreakageIssuance`, `sys_getSweepBreakageMonthly` calculate breakage income from unclaimed card balances subject to state escheatment rules.

### Audit and Compliance
`tblAuditLog`, `tblAuditDetails`, `tblAuditItems`, `tblAuditComments` provide a structured audit trail for GP-to-Atlys data reconciliation. `NOT FOR REPLICATION` flags on identity columns indicate this database participates in SQL Server replication.

---

## Data Stored and Processed

### Core Financial Tables

| Table | Contents |
|---|---|
| `revenue` | Revenue ledger with GL coding, product classification, commission amounts |
| `tblIssuance` | Card load/issuance amounts and counts by program and date |
| `tblSpend` | Transaction spend by type, quantity, and dollar amount |
| `tblCommissions` | Computed sales commissions with rate, amount, product |
| `tblSettle` | FDR settlement: net spend, interchange, chargebacks, ICA/BIN |
| `tblSettleDtl` | Settlement detail lines |
| `tblGLBatch` | GL batch entries for ERP posting |
| `tblGLLinks` | GL account to reporting line code mapping (shared with NCA databases) |
| `tblDefRev`, `tblDefRevSum` | Deferred revenue (customer liability float) |
| `tblFVD`, `tblFVD_Revenue` | Face Value Discount records and revenue |
| `tblSweepBreakage` | Breakage/escheatment calculation data |
| `tblBalReconcile` | Balance reconciliation records |
| `tblAuditLog`, `tblAuditDetails` | Audit trail for data changes |

### Program Configuration Tables

| Table | Contents |
|---|---|
| `tblProgramsBank` | Bank assignment per program with effective date ranges |
| `tblProgramsBin` | BIN assignments per program |
| `tblProgramsCardType` | Card type (Visa/MC/prepaid) per program |
| `tblProgramsEmboss` | Emboss vendor assignments |
| `tblGLMap`, `tblGLMapLog` | GL account mapping configuration and change log |
| `tblCostsRates` | FDR cost rate schedules by BIN |

### Processor Data Tables

| Table | Contents |
|---|---|
| `tblFDR_CD083`, `tblFDR_DD442` | FDR settlement report data (CD083 = clearing, DD442 = detail) |
| `tblFDR_SD090`, `tblFDR_SD091`, `tblFDR_SD902` | FDR summary settlement data |
| `tblfdr` | FDR raw transaction data |
| `tblfdrcosts` | Computed FDR cost breakdown by program/BIN/date |

---

## Business Rules in SQL

1. **Revenue GL auto-classification** (`revenue.sql` trigger `trg_revenue`, lines 47–74): On insert/update, revenue records are automatically assigned GL product, channel, and account number based on `vAffiliates` (program configuration), `vProducts` (product catalog), and `tblProgramsBank` (bank assignment). Visa and MC interchange items are assigned specific GL suffixes (`-01-` and `-02-` respectively).

2. **FDR cost allocation**: The `sys_fdr_calc` procedure computes per-program FDR processing costs based on transaction volumes and rates from `tblCostsRates`, applying BIN-level rate schedules.

3. **GL batch lifecycle**: GL batches move through states managed by `sys_glbatch` and `sys_glbatch_complete`. Only `dbo` users or users with 'Finance' rights can process GL batches (enforced via `ATLYS_E.dbo.sys_chkuserrights`).

4. **Bank reconciliation**: `sys_bank_reconcile` (and variants for sweep breakage, DD-AJ adjustments) compare FDR net spend against GP cash balance, flagging discrepancies.

5. **Deferred revenue calculation**: Customer liability is the sum of all issued card value minus all cardholder spend, adjusted for maintenance fees and escheatment events.

6. **Sweep breakage**: Breakage income is recognized when card balances become dormant beyond state-specific escheatment periods.

---

## Regulatory Relevance

| Regulation | Relevance |
|---|---|
| **PCI DSS** | `tblSettle` contains ICA/BIN (Bank Identification Number) data. BIN is not a PAN, but this data contributes to the cardholder data environment boundary assessment. No PANs, CVV, or track data found. |
| **NACHA** | ACH issuance tracked via `vIssuanceT_ACH`, `vIssuanceT_ACHSum`. ACH volumes flow into revenue reporting and commission calculations. |
| **Reg E** | Cardholder fee income (`vRevenueT_CardholderMaintFee`) and maintenance fee calculations are subject to Reg E disclosure requirements. |
| **State Escheatment (Unclaimed Property)** | Sweep/breakage tables (`tblSweepBreakage`) track expired balances for potential escheatment reporting obligations. |
| **SOX** | Revenue recognition, GL batch processing, and GL mapping changes (`tblGLMapLog`) are financially significant processes subject to SOX controls. |

---

## Data Flows

```
FDR Processor settlement files
        → tblFDR_*, tblfdrcosts, tblSettle, tblSettleDtl
        
eCount Core system events
        → tblIssuance (loads), tblSpend (transactions), tblPlastics (card production)
        → revenue table (triggered GL classification)
        
Great Plains ERP
        → tblGLBatch → sys_glbatch_complete → ERP posting
        → vRevenueT_Partner (SOP posted sales)
        
Atlys WAPP / Finance users
        ← sys_gp_details_cross_tab, sys_revenue, sys_bank_reconcile
        ← All reporting views
```

---

## Integration with Services

- **ATLYS_E**: Access control functions (`sys_chkuser`, `sys_chkuserrights`, `sys_cinfo`) used by all stored procedures
- **Great Plains ERP** (`ECAN_R` and US GP companies): Revenue partner data, GL posting integration, customer master
- **FDR (First Data Resources)**: Settlement data imported into `tblFDR_*` and `tblSettle` tables
- **Atlys WAPP**: Primary application consuming all stored procedures and views
- **atlys_rv_nus_r**: Rollback sibling that mirrors this database's view layer; reads `tblGLLinks` from here
