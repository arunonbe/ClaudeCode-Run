# DS_DB_ATL_atlys_rv_nca — Data Architect View

## Data Stores
- **Primary database**: `atlys_rv_nca` — SQL Server SSDT project targeting `Sql100DatabaseSchemaProvider` (SQL Server 2008 engine compatibility), compatibility mode 90, recovery model BULK_LOGGED, collation `SQL_Latin1_General_CP1_CI_AS`.
- **Linked cross-database dependency**: `ATLYS_E` — referenced in stored procedures and views for authorisation (`sys_chkuser`), exchange rates (`sys_exchrates_actual`), linked-server paths (`sys_vPaths`), and system configuration (`sys_lsinfo`, `vSystems`). This is a hard runtime dependency: the `atlys_rv_nca` database cannot function without `ATLYS_E` being available on the same or a linked server.
- **File groups**: Default PRIMARY only; no custom filegroup partitioning observed in the project.

## Schema & Tables
All objects reside in schema `dbo`. Key table groups:

| Group | Tables | Row Pattern |
|---|---|---|
| Revenue | `revenue`, `tblFVD_Revenue`, `tblFVD_Rev`, `tblFVD`, `tblFVD_DefFVD` | High-volume insert/update, clustered on date+affiliate |
| GL Mapping | `tblGL`, `tblGLBatch`, `tblGLBatchFeeTax`, `tblGLBatchRecon*` | Low-volume configuration |
| GL Posting | `tblGLEntry`, `tblGLEntryIDs`, `tblGLMap`, `tblGLMapLog`, `tblGLCashBal`, `tblGLTxBal_fwdUSD` | Medium-volume append |
| Settlement | `tblSettle`, `tblSettleDtl`, `tblBalReconcile` | Batch-load per network cycle |
| FDR Processor | `tblfdr`, `tblfdrcosts`, `tblFDR_CD083`, `tblFDR_DD442`, `tblFDR_SD090`, `tblFDR_SD091`, `tblFDR_SD902` | Batch-load per FDR cycle |
| Commissions | `tblCommissions`, `tblCommissions1`, `tblCommissionsRates`, `tblAffiliateComm` | Periodic calculation |
| Programs / Products | `tblProducts`, `tblProgramsBank`, `tblProgramsBin`, `tblProgramsCardType`, `tblProgramsEmboss`, `tblProgramCompPlan`, `tblProgramCompPlan1`, `tblProgramCompPlanFees` | Reference data |
| Costs | `tblCostsAlloc`, `tblCostsAllocLog`, `tblCostsAllocMethodExtVendorRates`, `tblCostsRates`, `tblProg_Costs`, `tblStockCosts` | Configuration + audit |
| Issuance / Plastic | `tblIssuance`, `tblPlastics`, `tblCoreEmboss`, `tblCoreEmbossAdjust`, `tblCoreVirtual` | High-volume append |
| Spend / Transactions | `tblSpend`, `tblEC_Txns`, `tblEC_Accts`, `tblEC_Iss`, `tblEC_Ordersvc1-4` | High-volume append |
| Audit | `tblAuditLog`, `tblAuditDetails`, `tblAuditComments`, `tblAuditItems`, `tblAuditArchive*` | Append-only audit |
| Metrics / Reporting | `tblMetrics`, `tblNegBal`, `tblCallData`, `tblgprecords`, `tblFileMap`, `tblAff_App` | Variable |
| Periods | `tblPeriods` | Reference |

**Indexing patterns**: Most large tables use a clustered index on `(date, aff_id)` or `(date, prg_id)` to optimise time-series reporting; non-clustered covering indexes on frequent query predicates (e.g., `aff_id`, `gp_product`) are present on `revenue`.

## Sensitive Data Handling
- **No PAN, CVV, PIN, or track data** is stored in this database; tables contain only financial aggregates and GL codes.
- **`aff_id` / `prg_id`**: Program identifiers are used extensively but do not directly identify cardholders.
- **`tblCommissions.sales_rep`**: Stores a VARCHAR(30) sales representative name — a PII field.
- **`tblAuditLog.audit_uid`**: Stores a VARCHAR(50) user identifier — could be a personal identifier depending on the authentication model.
- **`tblCallData`**: Contains call data attributed to programs; the schema does not expose individual cardholder data.
- **Revenue source codes** (`MANUAL`, `IMPORT`) are stored in the `revenue.source` column but carry no financial institution account numbers.

## Encryption & Protection
- **`IsEncryptionOn`: False** — database-level Transparent Data Encryption (TDE) is not enabled per the SSDT project settings.
- **No column-level encryption** observed in any table DDL.
- **No Always Encrypted** configuration found.
- No evidence of key management or Certificate objects in the project.
- Protection relies entirely on SQL Server login/role permissions; the `Security` folder contains role and permission definitions but the directory was empty in the checked-out version.

## Data Flow
```
External feeds (FDR processor files, IVR, SSIS)
    → INSERT into revenue / tblSettle / tblFDR_* / tblEC_Txns
        → trg_revenue fires → GL coding resolved from tblProducts / vAffiliates
            → Stored procs (sys_comm_calc, sys_gl_entry, sys_glbatch_complete)
                → tblGLEntry / tblCommissions / tblGLBatch
                    → ATLYS web app reads via sys_revenue / sys_glbatch / sys_reports
                        → GP (Dynamics GP via ATLYS_E or ETL)
```
Cross-database reads from `ATLYS_E` are made via direct three-part names (no linked-server wrappers, no synonyms), making them brittle to server-name changes.

## Data Quality & Retention
- **No retention policy** is defined within the database (no archiving procs, no delete/purge logic visible in the stored procedures).
- `tblAuditArchiveComments`, `tblAuditArchiveDetails`, `tblAuditArchiveLog` exist as archive tables, suggesting manual archive operations outside the SSDT project.
- **NULL revenue coding**: The trigger can silently produce empty GL accounts when product master data is absent; there is no compensating constraint or alert.
- **FLOAT precision risk**: `tblEC_Txns.amount` and `tblEC_Txns.fee` use FLOAT(53); cumulative summation errors can accumulate in revenue reports.
- **Orphaned `tblGL_old`** table suggests historical schema drift without migration cleanup.
- **No CHECK constraints** on monetary amount columns (no negative-value guards on `tblSettle`, `revenue.amount`, etc.).

## Compliance Gaps
- **TDE absent**: Financial aggregates and GL coding data at rest are unencrypted; this falls short of a defence-in-depth posture expected under PCI DSS Requirement 3.5 for databases in or adjacent to the CDE.
- **Audit log is not tamper-evident**: `tblAuditLog` is a plain heap-style table with no write-once enforcement; rows can be deleted or modified by any user with appropriate rights.
- **BULK_LOGGED recovery model**: Cannot guarantee point-in-time restore for revenue data loaded via bulk operations; SOX requires the ability to reconstruct financial records.
- **Compatibility level 90**: Prevents use of modern SQL Server security features (e.g., row-level security, dynamic data masking) and will become unsupported.
- **Cross-database authorisation gate**: `ATLYS_E.dbo.sys_chkuser` is the sole access-control check; any misconfiguration of that database's security will silently grant or deny access without a local fallback.
- **No data masking**: Sales rep names and user IDs stored in plain text with no masking for non-production environments.
