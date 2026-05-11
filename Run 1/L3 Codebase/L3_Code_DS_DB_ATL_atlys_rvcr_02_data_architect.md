# Data Architect Report: DS_DB_ATL_atlys_rvcr

## Overview

This SSDT database project contains ~20 tables, ~35 views, ~45 stored procedures, ~20 functions, and a comprehensive Security folder. It serves as the router/dispatcher tier of the Atlys application, with stored procedures that aggregate across multiple company-specific databases.

---

## Complete Database Object Inventory

### Tables (~20)

| Table | Purpose | Key Fields |
|---|---|---|
| `tblBankHolidays` | Bank holiday calendar | Date, description |
| `tblBankWorkdays` | Bank business day calendar | Date, region |
| `tblCompareBuckets` | Comparison bucket definitions | Configuration |
| `tblCompareMetrics` | Comparison metric definitions | Metric config |
| `tblCompareMetrics2` | Extended comparison metrics | Metric config |
| `tblCompareMetricsComponents` | Metric component breakdown | Config |
| `tblCompareMetricsMap` | Metrics to display mapping | Config |
| `tblEC_Accts` | eCount account staging (session-scoped) | `prg_id`, `qty`, `spid` |
| `tblEC_Accts_Errors` | eCount account import errors | `prg_id`, error data |
| `tblEC_Iss` | eCount issuance staging (session-scoped) | `prg_id`, `amount`, `qty`, `item`, `spid` |
| `tblEC_Iss_Errors` | eCount issuance import errors | Error data |
| `tblEC_Ordersvc1-4` | eCount order service staging (4 variants) | `prg_id`, amounts, `spid` |
| `tblEC_Ordersvc1-4_Errors` | eCount order service errors | Error data |
| `tblEC_Txns` | eCount transaction staging (session-scoped) | `prg_id`, `source`, `facility`, `qty`, `amount`, `fee`, `card_type`, `spid` |
| `tblEC_Txns_Errors` | eCount transaction import errors | Error data |
| `tblFDR_CD083` | FDR CD083 clearing report | `RDATE`, `SYS`, `TYPE`, `CODE`, `DESCR`, `AMOUNT` |
| `tblFDR_DD442` | FDR DD442 detail | `RDATE`, `SYS`, `TYPE`, `CNT`, `RATE`, `AMOUNT`, `MTD_AMOUNT` |
| `tblFDR_SD090` | FDR SD090 summary settlement | `RDATE`, `SYS`, `TYPE`, `CODE`, `AMOUNT` |
| `tblFDR_SD091` | FDR SD091 summary variant | Same structure as SD090 |
| `tblFDR_SD902` | FDR SD902 summary | Same structure |
| `tblFLXC` | Flex context configuration | File format config |
| `tblFLXCtx` | Flex context entries | Import/format context |
| `tblFLXCtx_add` | Additional flex context | Import config |
| `tblInterface` | FDR file interface field definitions | `rec_type`, `position`, `length`, `type`, `formula` |
| `tblInterfaceXLS` | Excel interface definitions | Similar to tblInterface |
| `tblJobRerun` | Job rerun tracking | Job rerun state |
| `tblJobs` | Scheduled job definitions | `job_name`, `exec_proc`, `bus_days`, `region_id` — NOTE: `exec_proc` is used in dynamic EXEC |
| `tblSettle` | FDR settlement data | `ICA_BIN`, `PROCESSOR`, `NET_SPEND`, `INTER_REV`, `CHARGEBACK`, `CLR_AMT`, `c_id` |
| `tblSettleDtl` | Settlement detail | Financial details |

### Views (~35)

| View | Purpose |
|---|---|
| `vCompareMetricsJoin` | Joined comparison metrics |
| `vEC_ACCT_i1`, `vEC_ACCT_i2` | eCount account import stages |
| `vEC_ALLOT_i1` | eCount allocation import |
| `vEC_BankHolidays_i1`, `vEC_BankHolidays_i2` | Bank holiday import views |
| `vEC_BULK_i1`, `vEC_BULK_i2` | eCount bulk import views |
| `vEC_CLAIM0_i1`, `vEC_CLAIM_i1`, `vEC_CLAIM_i2`, `vEC_CLAIMBC_i1` | eCount claim import views |
| `vEC_ORDERSVC1_i1`, `vEC_ORDERSVC1_i2` through `vEC_ORDERSVC4_i1`, `vEC_ORDERSVC4_i2` | eCount order service import views |
| `vEC_SPIN_i1`, `vEC_SPIN_i2` | eCount SPIN import views |
| `vEC_TXN_i1`, `vEC_TXN_i2` | eCount transaction import views |
| `vFDR_CD083`, `vFDR_DD442`, `vFDR_SD090`, `vFDR_SD091`, `vFDR_SD902` | FDR report views |
| `vFLXC` | Flex context view |
| `vGLBatch` | GL batch summary view |
| `vInterface` | Interface field definitions view |
| `vInterfaceXLS` | Excel interface view |
| `vSettle` | Settlement summary view |
| `vSettleDtl` | Settlement detail view |

### Stored Procedures (~45)

| Procedure | Purpose |
|---|---|
| `sys_audit` | Audit reconciliation router |
| `sys_bal_reconcile` | Balance reconciliation router |
| `sys_bank_dates` | Bank business day calculator |
| `sys_bank_reconcile` | Bank recon router |
| `sys_bank_reconcile_ddaj` | DD-AJ adjustment bank recon router |
| `sys_comm` | Commission reporting router |
| `sys_comm_calc` | Commission calculation router |
| `sys_comm_type_cross_tab` | Commission type cross-tab router |
| `sys_compare` | Period comparison router |
| `sys_compare_by_month` | Monthly comparison router |
| `sys_compare_metrics` | Metrics comparison |
| `sys_cscall_detail` | CS call detail router |
| `sys_cube_reconcile` | Cube reconciliation router |
| `sys_cube_reconcile_hist` | Historical cube recon router |
| `sys_custl_entry` | Customer liability entry router |
| `sys_durbin` | Durbin analysis router |
| `sys_execlview` | Execute list view |
| `sys_execsqlviewtext` | Dynamic SQL view execution |
| `sys_fdr` | FDR processing router |
| `sys_fdrcosts` | FDR cost allocation router |
| `sys_fdr_calc` | FDR cost calculation router |
| `sys_filemap` | File import mapping router |
| `sys_flxctx` | Flex context management |
| `sys_fvd_calc` | FVD calculation router |
| `sys_fvd_cross_tab` | FVD cross-tab router |
| `sys_fvd_details_cross_tab` | FVD detail cross-tab router |
| `sys_glbatch` | GL batch router |
| `sys_glbatchbin` | GL batch by BIN router |
| `sys_glbatchfeetax` | GL batch fee/tax router |
| `sys_glbatch_complete` | GL batch completion router |
| `sys_gllinks` | GL links management router |
| `sys_glmap` | GL account mapping router |
| `sys_gp` | GP report router |
| `sys_gp_calc` | GP calculation router |
| `sys_gp_details_cross_tab` | GP details cross-tab router |
| `sys_gp_details_variance` | GP variance router |
| `sys_holidays` | Holiday management |
| `sys_import` | Data import router |
| `sys_import_holidays` | Holiday import |
| `sys_import_txn` | Transaction import router |
| `sys_interface` | Interface management |
| `sys_issuance` | Issuance reporting router |
| `sys_ivr` | IVR cost router |
| `sys_jobrerun` | Job rerun management |
| `sys_jobrun` | Job execution scheduler |
| `sys_metrics` | Performance metrics router |
| `sys_metrics_calc` | Metrics calculation router |
| `sys_negbal` | Negative balance router |
| `sys_periods` | Period management |
| `sys_plastics` | Plastics reporting router |
| `sys_products` | Products management router |
| `sys_program_analysis` | Program analysis router |
| `sys_prog_costs` | Program cost router |
| `sys_que` | IVR queue router |
| `sys_reports` | Report dispatcher router |
| `sys_revenue` | Revenue reporting router |
| `sys_revenue_gl_cross_tab` | Revenue GL cross-tab router |
| `sys_revenue_type_cross_tab` | Revenue type cross-tab router |
| `sys_smots` | SMOTS report router |
| `sys_sys_paths` | System path management |
| `sys_tb` | Trial balance router |
| `sys_usage` | Usage reporting router |
| `sys_usage_type` | Usage type management |

### Functions (~20)

| Function | Purpose |
|---|---|
| `sys_day_before_bank_day` | Returns the bank business day before a given date |
| `sys_day_before_bank_day_p` | Variant of above |
| `sys_flxcfname` | Flex context file name |
| `sys_fname` | File name utility |
| `sys_getECAccts` | Get eCount accounts staging data |
| `sys_getECIss` | Get eCount issuance staging data |
| `sys_getECOrdersvc1-4` | Get eCount order service staging (4 variants) |
| `sys_getECTxns` | Get eCount transaction staging data |
| `sys_getvECACCTi1`, `sys_getvECACCTi2` | Parameterized eCount account import |
| `sys_getvECALLOTi1` | Parameterized eCount allocation import |
| `sys_getvECBULKi1`, `sys_getvECBULKi2` | Parameterized eCount bulk import |
| `sys_getvECCLAIM*` | Parameterized eCount claim import |
| `sys_getvECORDERSVC*` | Parameterized eCount order service import |
| `sys_getvECSPINi1`, `sys_getvECSPINi2` | Parameterized eCount SPIN import |
| `sys_getvECTXNi1`, `sys_getvECTXNi2` | Parameterized eCount transaction import |
| `sys_getvFDR_CD083`, `sys_getvFDR_DD442`, etc. | FDR report table-valued functions |
| `sys_getvSettle`, `sys_getvSettleDtl` | Settlement data TVFs |
| `sys_getls` | Get last statement |
| `sys_glfname` | GL file name |
| `sys_next_bank_day` | Next bank business day |
| `sys_next_bank_day_p` | Variant |

### Security Objects

Role memberships, AD logins, and permission grants for: `ATLYS_APP_GRP`, `NAM\PPA_PRD_ATLYS`, `NAM\PPA_PRD_ABAT`, `Prod_Support_*`, `FortiDBRptRole`, `gers_read`, `gers_role`, `ifs_gidadb`, `ifs_infosec`, `NAM_GTS_gpatmon`, `NAM_GTS_MSSQL_DBA_RO`, `NAM_ICG_DBA_Default`, `NAM_ISA_SQL_SECADMIN`, `NAM_PROD`, `NAM_UAT`, `NAM_PROD_CPP`, `NAM_PROD_CPP_APAC`, `NAM_PROD_ITOPS`, `report`, `report_full`, `scpardb`, `raf`

---

## Sensitive Data Field Assessment

### PCI DSS Cardholder Data
| Field | Table | Flag |
|---|---|---|
| `ICA_BIN` | `tblSettle` | BIN data — CDE boundary review required |
| `SYS` (FDR system ID) | `tblFDR_*` | Internal FDR system identifier |
| No PANs | — | CLEAR |

### Session-Scoped eCount Tables
The `tblEC_*` staging tables include `spid` (SQL Server session process ID) as part of their clustered indexes. Data in these tables is keyed by session, meaning concurrent sessions should not see each other's data. However, the tables are permanent (not temp tables), so data from crashed or orphaned sessions may persist. These tables contain program-level transaction summaries (amounts, quantities) but not individual cardholder data.

### Financial Data
`tblSettle` contains settlement amounts, interchange revenue, chargebacks, and representments — all financially sensitive internal data.

---

## Referential Integrity

No foreign key constraints found between tables (consistent with the session-keyed staging table pattern). The `tblJobs` CHECK constraint (`exec_proc` must be NULL or a valid procedure name) is an integrity control on the job scheduler configuration.

## Encryption
No column-level encryption. TDE at instance level should be confirmed.

## PCI DSS CDE Scope
**REVIEW REQUIRED.** `tblSettle.ICA_BIN` places this database adjacent to the CDE. Same assessment as `atlys_rv_nus`. The `sys_chkstr` function used for SQL injection prevention in `sys_execsqlviewtext` is a positive security control.

## Data Retention
No purge procedures found. Settlement and FDR staging data accumulated without defined retention schedule.
