# Data Architect Report: DS_DB_ATL_atlys_rv_nus

## Overview

This is the **primary and most comprehensive database** in the Atlys RV family. It contains the full schema for the US Atlys financial reporting platform, including tables, views, stored procedures, functions, user-defined types, and security definitions. The `.sqlproj` file is 102 KB, indicating a very large number of included objects.

---

## Complete Database Object Inventory

### Tables (~95 defined)

#### Financial Core Tables
| Table | Purpose | Sensitive Fields |
|---|---|---|
| `revenue` | Central revenue ledger with GL classification trigger | `amount`, `comm_amt`, `gl_acct_num` — financial |
| `tblIssuance` | Program load amounts and card counts | `amount`, `num_issued` — financial |
| `tblSpend` | Transaction spend by type | `dollars` — financial |
| `tblCommissions` | Sales rep commission records | `comm_rate`, `comm_amt` — financial |
| `tblCommissionsRates` | Commission rate schedules | Rate configuration |
| `tblCommissions1` | Commission variant (alternate calc) | Financial |
| `tblAffiliateComm` | Affiliate commission records | Financial |

#### Settlement and GL Tables
| Table | Purpose | Sensitive Fields |
|---|---|---|
| `tblSettle` | FDR processor settlement (net spend, interchange, chargebacks, ICA/BIN) | `ICA_BIN` — BIN data; financial amounts |
| `tblSettleDtl` | Settlement detail lines | Financial |
| `tblGLBatch` | GL batch entries for ERP posting | GL account numbers |
| `tblGLBatchBin` | GL batch by BIN | BIN reference — financial |
| `tblGLBatchFeeTax` | GL batch fee/tax entries | Financial |
| `tblGLBatchRecon` | GL batch reconciliation | Financial |
| `tblGLBatchReconCompareReports` | GL batch comparison | Financial |
| `tblGLBatchReconDtlTypes` | Reconciliation detail types | Configuration |
| `tblGLLinks` | **GL account to line code mapping** (shared with NCA databases) | Financial config — HIGH value |
| `tblGLMap`, `tblGLMapLog` | GL account mapping and change log | Audit — `tblGLMapLog` tracks changes |
| `tblGLCashBal` | GL cash balance records | Financial |
| `tblGLCDs` | GL certificate of deposit records | Financial |
| `tblGLEntry`, `tblGLEntryIDs` | GL journal entries | Financial |
| `tblGL` | GL account data | Financial |

#### Processor Data Tables
| Table | Purpose | Sensitive Fields |
|---|---|---|
| `tblfdr` | FDR raw transaction data | Transaction data |
| `tblfdrcosts` | Computed FDR cost breakdown | Financial |
| `tblfdrcosts_copy` | Backup copy of fdrcosts | Financial |
| `tblFDR_CD083` | FDR CD083 clearing report data | Clearing amounts |
| `tblFDR_DD442` | FDR DD442 detail report | Transaction counts/rates |
| `tblFDR_SD090` | FDR SD090 summary settlement | Settlement amounts |
| `tblFDR_SD091` | FDR SD091 summary settlement variant | Settlement amounts |
| `tblFDR_SD902` | FDR SD902 summary report | Settlement amounts |

#### Deferred Revenue / Customer Liability Tables
| Table | Purpose |
|---|---|
| `tblDefRev` | Deferred revenue entries |
| `tblDefRevAdj` | Deferred revenue adjustments |
| `tblDefRevSum` | Deferred revenue summary |
| `tblFVD` | Face Value Discount records |
| `tblFVD_DefFVD` | FVD deferred records |
| `tblFVD_Rev` | FVD revenue records |
| `tblFVD_Revenue` | FVD revenue (for reporting) |
| `tblSweepBreakage` | Breakage/escheatment data |

#### Program Configuration Tables
| Table | Purpose |
|---|---|
| `tblProgramsBank` | Bank per program with date ranges |
| `tblProgramsBin` | BIN per program |
| `tblProgramsCardType` | Card network (Visa/MC) per program |
| `tblProgramsEmboss` | Emboss vendor per program |
| `tblCostsRates` | FDR cost rates by BIN/category |
| `tblCostsAlloc`, `tblCostsAllocLog` | Cost allocation results and log |
| `tblCostsAllocMethod` | Cost allocation methodology config |
| `tblCostsAllocMethodExtVendorRates` | External vendor rate table |
| `tblCostsAllocMethodExtVendorRatesLog` | Vendor rate change log |
| `tblProducts` | Product catalog |
| `tblProgramCompPlan`, `tblProgramCompPlan1` | Compensation plan definitions |
| `tblProgramCompPlanFees` | Fee schedules per plan |

#### Production Tables
| Table | Purpose |
|---|---|
| `tblPlastics` | Physical card production counts |
| `tblCoreEmboss` | Emboss job records with vendor |
| `tblCoreEmbossAdjust` | Emboss adjustment records |
| `tblCoreVirtual` | Virtual card counts |
| `tblStockCosts` | Card stock cost records |

#### Operational / Utility Tables
| Table | Purpose |
|---|---|
| `tblBalReconcile` | Balance reconciliation records |
| `tblBalReconcile_RFDates` | Reconciliation roll-forward dates |
| `tblBalReconcile_Types` | Reconciliation type reference |
| `tblBankRecon_CCPmts` | Bank rec: credit card payments |
| `tblcalldata` | Customer service call data |
| `tblcscall_detail` | CS call detail records |
| `tblCubeMap` | Cube/SSAS metric mapping |
| `tblDefRev`, `tblDefRevAdj`, `tblDefRevSum` | Deferred revenue |
| `tblDurbin` | Durbin Amendment (interchange cap) data |
| `tblEC_Accts`, `tblEC_Iss`, `tblEC_Ordersvc1-4`, `tblEC_Txns` | eCount staging tables (temp/ETL) |
| `tblFileMap` | File import mapping configuration |
| `tblInterface`, `tblInterfaceXLS` | Data interface/import staging |
| `tblMetrics` | Performance metrics |
| `tblNegBal`, `tblNegBal_FeeCodes` | Negative balance tracking |
| `tblPeriods` | Reporting period calendar |
| `tblgprecords` | GP cost records (CS, IVR, Telco) |
| `tblGP_lines`, `tblGP_lines062019` | GP transaction line data |
| `tblUsageType` | Card usage type reference |
| `tblAuditLog`, `tblAuditDetails`, `tblAuditItems`, `tblAuditComments` | Audit trail |
| `tblAuditArchiveLog`, `tblAuditArchiveDetails`, `tblAuditArchiveComments` | Archived audit records |
| `tblAudit_FVD0` | FVD audit snapshot |
| `tblBalReconcile_RFDates` | Roll-forward date tracking |

### Triggers (1 confirmed)

| Trigger | Table | File | Purpose |
|---|---|---|---|
| `trg_revenue` | `revenue` | `revenue.sql` lines 47–74 | Auto-populates GL codes, product/channel classification, and first-issue flag on INSERT/UPDATE |

### Views (~270 defined)

The view inventory is extensive. Key categories:

**Financial Reporting Views:**
`vRevenue`, `vRevenueD`, `vRevenueDSum`, `vRevenueSum`, `vRevenueSumM`, `vRevenueT`, `vRevenueT0`, `vRevenueT_700`, `vRevenueT_Cardholder`, `vRevenueT_CardholderImport`, `vRevenueT_CardholderInterchange`, `vRevenueT_CardholderMaintFee`, `vRevenueT_CardholderSum`, `vRevenueT_FVD`, `vRevenueT_Issue`, `vRevenueT_MaintFees`, `vRevenueT_Partner`

**GP / Cost Analysis Views:**
`vGP`, `vGP_nc`, `vGP_t`, `vGPRecords`, `vGP_ItemPrg`, `vGP_lines`, `vCosts`, `vCostsSum`, `vCostsAllocMethod`, `vStockCosts`, `vStockInventory`

**FDR / Settlement Views:**
`vFDR`, `vFDRCosts`, `vFDRT_AccountsOnFile`, `vFDRT_SettledTransactions`, `vFDR_CD083`, `vFDR_DD442`, `vFDR_SD090`, `vFDR_SD091`, `vFDR_SD902`, `vSettle`, `vSettleDtl`

**Balance Reconciliation Views:**
`vBalReconcile_Rollforward`, `vBalReconcile_Rollforward0`, `vBalReconcile_Compare`, `vBalReconcileBin_Rollforward`, `vGLCash`, `vGLCashBal`, `vGLBal`, `vGLTxBal`, `vTB`

**Deferred Revenue / Float Views:**
`vDefRev`, `vDefRevAdj`, `vDefRevBal`, `vDefRevLTD`, `vDefRevSum`, `vCustLiabilityT`, `vCustLiabilityT_Details`, `vCustLiabilityT_LTD`, `vFVD`, `vFVDSum`, `vSweepBreakage`, `vSweepBreakageFC`

**Commission Views:**
`vCommissions`, `vCommissionsT`, `vCommissionsP`, `vCommissionsRates`, `vAffiliateComm`

**GL Views:**
`vGL`, `vGLAccts`, `vGLBatch`, `vGLBatchBin`, `vGLBatchFeeTax`, `vGLBatchRecon`, `vGLLinks`, `vGLMap`, `vGLMapLog`, `vGLSum`, `vGLTx`, `vGLFVD`, `vGLCustL`

**Audit Views:**
`vAuditLog`, `vAuditDetails`, `vAuditItems`, `vAuditSum`, `vAuditSummary`, `vAuditArchiveComments`, `vAuditArchiveDetails`, `vAudit_GP`, `vAudit_Issuance`

**eCount Balance Reconciliation Views:**
`vEC_BR_1_*` through `vEC_BR_17_*` (100+ views) — detailed reconciliation views comparing eCount core balance data against Atlys financial records at various join stages

**Issuance / Spend / Plastics:**
`vIssuance`, `vIssuanceD`, `vIssuanceSumM`, `vIssuanceT`, `vIssuanceT_ACH`, `vPlastics`, `vPlasticsD`, `vSpend`, `vSpendD`, `vSpendSum`, `vSpendT`

### Stored Procedures (~80)

Full list:
`sys_audit`, `sys_bal_reconcile`, `sys_bank_dates`, `sys_bank_reconcile`, `sys_bank_reconcile_ddaj`, `sys_bank_reconcile_sweep_breakage_detail`, `sys_bank_reconcile_sweep_breakage_fc_detai`, `sys_bank_reconcile_sweep_breakage_fc_summary`, `sys_bank_reconcile_sweep_breakage_summary`, `sys_comm`, `sys_comm_calc`, `sys_comm_type_cross_tab`, `sys_compare`, `sys_compare_by_month`, `sys_costs_rates`, `sys_cscall_detail`, `sys_cube_reconcile`, `sys_cube_reconcile_hist`, `sys_custliability`, `sys_custl_entry`, `sys_defrev`, `sys_defrev_details_cross_tab`, `sys_durbin`, `sys_execcview`, `sys_execlview`, `sys_execsqlviewtext`, `sys_fdr`, `sys_fdrcosts`, `sys_fdr_calc`, `sys_fee_entry`, `sys_filemap`, `sys_first_issue`, `sys_formsecurity`, `sys_fvd_calc`, `sys_fvd_cross_tab`, `sys_fvd_details_cross_tab`, `sys_glbatch`, `sys_glbatchbin`, `sys_glbatchfeetax`, `sys_glbatch_complete`, `sys_gllinks`, `sys_glmap`, `sys_gl_entry`, `sys_gp`, `sys_gp_calc`, `sys_gp_details_cross_tab`, `sys_gp_details_variance`, `sys_import`, `sys_import_diff`, `sys_import_ic_calc`, `sys_import_txn`, `sys_interface`, `sys_issuance`, `sys_ivr`, `sys_metrics`, `sys_metrics_calc`, `sys_negbal`, `sys_periods`, `sys_plastics`, `sys_prices`, `sys_products`, `sys_program_analysis`, `sys_program_filter`, `sys_prog_costs`, `sys_que`, `sys_reports`, `sys_revenue`, `sys_revenue_gl_cross_tab`, `sys_revenue_type_cross_tab`, `sys_smots`, `sys_tb`, `sys_update_app`, `sys_update_cust_name`, `sys_update_first_issue`, `sys_update_last_rev`, `sys_usage`, `sys_usage_type`

### Functions (~120+)

Banking/date utility: `sys_day_before_bank_day`, `sys_day_before_bank_day_gl`, `sys_next_bank_day`, `sys_next_bank_day_gl`, `sys_num`

GL/batch validation: `sys_chk_glbatch`, `sys_vGLTx`, `sys_vGLTxBal`, `sys_vGLTxBal_TxDate`, `sys_vGL_FLXC`, `sys_vGL_FLXC_Bal`

eCount balance report functions (`sys_getvECBR1` through `sys_getvECBR17` with variants: `J1`, `J2`, `S`, `d`, etc.) — ~100+ table-valued functions serving as parameterized view proxies for the eCount balance reconciliation views

Sweep breakage: `sys_getSweepBreakageIssuance`, `sys_getSweepBreakageMonthly`

Utility: `sys_getls`, `sys_getvSOItems`, `sys_vCommissions1T`, `sys_vCommissionsT`, `sys_vInterfaceGL`, `sys_vInterfaceTx*`

### User-Defined Types
Located in `dbo/User Defined Types/` folder (count not enumerated but present).

### Security Objects
- `ATLYS_APP_GRP` role (bound to Windows login `NAM\PPA_PRD_ATLYS`)
- Multiple security files for various AD groups (`NAM_PROD`, `NAM_UAT`, `NAM_PPA_PRD_ATLYS`, `FortiDBRptRole`, `Prod_Support_*`, etc.)

---

## Sensitive Data Field Assessment

### PCI DSS Cardholder Data
| Field | Table | Classification | Flag |
|---|---|---|---|
| `ICA_BIN` | `tblSettle`, `tblGLBatchBin` | BIN (6-digit) — not a full PAN | REVIEW — BIN alone is not restricted under PCI DSS but combined with program data warrants CDE boundary review |
| No PANs found | — | No full 13–19 digit card numbers | CLEAR |
| No CVV/CVC found | — | No verification values | CLEAR |
| No track data found | — | No magnetic stripe data | CLEAR |

**CDE Assessment**: The presence of BIN data in `tblSettle.ICA_BIN` and `tblGLBatchBin` means this database sits adjacent to the CDE but does not contain PANs or SAD. The formal CDE boundary determination should be made by the QSA in the context of the full network/system scope assessment.

### Financial Data (Non-PCI but sensitive)
| Field | Table | Classification |
|---|---|---|
| `amount`, `comm_amt`, `rev_amt` | `revenue`, `tblCommissions` | Internal financial data |
| `NET_SPEND`, `INTER_REV`, `CHARGEBACK` | `tblSettle` | Settlement financial data |
| `CreditLimit`, `CustomerBalance` | `PrepaidCustomerBalanceHistory` | Customer financial position |
| `gl_acct_num`, `gl_acct` | `revenue`, `tblGLLinks` | GL account classification |

### PII Assessment
| Field | Table | Classification |
|---|---|---|
| `sales_rep` | `tblCommissions` | Internal employee identifier (sales rep name) |
| `acctg_name` | `revenue` | Client/program accounting name |
| `audit_uid` | `tblAuditLog` | User ID performing audit operation |

No SSN, DOB, government ID, or consumer-level PII found.

---

## Encryption at Rest
No column-level encryption or Always Encrypted DDL present. TDE must be confirmed at instance level.

## Referential Integrity
Foreign keys present: `tblAuditDetails.FK_tblAuditDetails_tblAuditLog` references `tblAuditLog.id`. This is one of the few FK relationships; most tables rely on application-level integrity.

## Data Retention
`tblAuditArchive*` tables suggest periodic archival of audit records. No explicit retention policy DDL found. Revenue and settlement data appears to be retained indefinitely (no purge procedures found in this project).

## PCI DSS CDE Scope
**REVIEW REQUIRED.** BIN data (`ICA_BIN`) in `tblSettle` places this database in close proximity to the CDE. No PANs or SAD found. Formal QSA assessment recommended to determine if this database is in-scope for PCI DSS.

## Indexing Strategy
Well-indexed: `revenue` has clustered index on `(rev_date, aff_id)` plus non-clustered on `aff_id`, `gp_product`, `item`. `tblIssuance` has clustered on `(dte, aff_id, item)` plus covering index on `aff_id`. `tblSpend` clustered on `(date1, aff_id)`. Settlement tables clustered on `(c_id, PROCESSOR, RDATE)`.
