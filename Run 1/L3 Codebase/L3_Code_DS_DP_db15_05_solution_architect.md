# Solution Architect Report — DS_DP_db15

## Repository Identity

**Repository:** DS_DP_db15  
**Risk Profile:** HIGH — analytical shard with CDE-adjacent data, legacy linked server dependency, and dynamic SQL execution pattern

---

## Complete Object Inventory

| Object Name | Database | Type | Purpose |
|---|---|---|---|
| `dbo.qryReports` | RiskDB | Table | Report query registry — stores T-SQL query bodies as strings |
| `OnbeATM_CashForecastDetail` | RiskDB.qryReports | Report Entry | ATM terminal cash forecast detail query |
| Report 131: `Stock - No Change Balance` | RiskDB.qryReports | Report Entry | Emboss stock reconciliation — detects vendor balance discrepancies |
| Report 191: `Build DB Roll Backs` | RiskDB.qryReports | Report Entry | Card inventory build rollback tracking |
| Report 216: `Emboss Report - POD Transition` | RiskDB.qryReports | Report Entry | Point-of-disbursement transition emboss report |
| `dbo.rpt_qryReports_QRY_Insert` | RiskDB | Stored Procedure | Report registration/update mechanism |
| `dbo.EUC_DMT_updaterelated` | RiskDB | Stored Procedure | DMT cascade update procedure |
| `dbo.EUC_DMT_ATM_DATACACHE` | RiskDB | Table | ATM terminal current-state cache |
| `dbo.EUC_DMT_ATM_DATAChangesetCACHE` | RiskDB | Table | ATM terminal change history |
| `dbo.EUC_DMT_ATM_DATA` | RiskDB | Table | ATM terminal base data |
| `dbo.EUC_DMT_GLOBAL_DATA` | RiskDB | Table | Global DMT configuration change log |
| `dbo.EUC_DMT_GLOBAL_DATACACHE` | RiskDB | Table | Global DMT configuration current state |
| `dbo.EUC_DMT_ContractSummary_FIELDS` | RiskDB | Table | Contract field/category definitions |
| `dbo.EUC_DMT_SPAMAP_DATA` | RiskDB | Table | Program-to-account mapping change log |
| `dbo.EUC_DMT_SPAMAP_DATACACHE` | RiskDB | Table | SPAMAP current state |
| `dbo.EUC_DMT_Separation_DATACACHE` | RiskDB | Table | Separation configuration cache |
| `fdr_card_account` | ECountcore_ss | Table (ref) | FDR card accounts — contains DDA numbers |
| `fdr_card_account_detail` | ECountcore_ss | Table (ref) | Card account access level |
| `core_card_account_emboss_history` | ECountcore_ss | Table (ref) | Card emboss events |
| `psx_inventory_file` | ECountcore_ss | Table (ref) | PSX plastic inventory |
| `fdr_process_report_inventory_management` | ECountcore_ss | Table (ref) | FDR inventory management report |
| `JAX_Plastic_Volumes` | cf_report | Table (ref) | JAX plastic volume data |
| `HJ_Forms_Volumes` | cf_report | Table (ref) | HJ forms volume data |
| `reportingdbserver2008` | Linked Server | Server | Legacy SQL Server 2008 era reporting server |

---

## Security Vulnerabilities

### CRITICAL

**1. Potential EOL SQL Server Linked Server in CDE**  
File: `20210503_SQ-3028_CREATE - OnbeATM_CashForecastDetail.sql`, lines 27, 41, 52 (OPENQUERY calls to `reportingdbserver2008`)  
If `reportingdbserver2008` is running SQL Server 2008 R2 or earlier, it has received no Microsoft security patches since July 2019. A SQL Server instance with 5+ years of unpatched vulnerabilities in or adjacent to the CDE is a **critical PCI DSS Req 6.3.3 violation**. Even if it has been upgraded and merely retains the legacy name, this should be formally documented.

**2. Dynamic SQL in `qryReports` — SQL Injection Risk**  
The report execution framework retrieves T-SQL from `dbo.qryReports.QRYTXT` and executes it dynamically. If the reporting application executes this with `EXEC()` or `sp_executesql` and any parameters are injected without proper sanitisation, this is a SQL injection vector. The risk depends entirely on the reporting application code, which is not in this repository. The pattern of embedding long T-SQL in a table column is inherently harder to audit and maintain than parameterised stored procedures.

### HIGH

**3. `fdr_card_account.dda_number` — Potential Unmasked Account Number**  
File: `20210315_SQ-1820_ALTER - 131 - Stock - No Change Balance.SQL`, line 52  
```sql
select LEFT(fca.dda_number,8) [Program]
```
The full `dda_number` column exists in `fdr_card_account`. The report query takes only the first 8 digits, but the underlying column may store a full card/account number. If `dda_number` is a PAN or DDA account number, storing and querying it without truncation/masking in `ECountcore_ss` violates PCI DSS Req 3.4. **This requires immediate classification review.**

**4. `MAX(change#) + 1` Sequence Generation — Race Condition**  
Files: `20210201_SQ-1841_DB15`, line 7; `spamap_update_query.sql`, line 3  
```sql
Declare @change# As integer = (select max(change#) + 1 from [RiskDB].[dbo].[EUC_DMT_GLOBAL_DATA])
```
This non-atomic sequence generation will produce duplicate `change#` values under concurrent execution. While DMT appears to be batch-driven (reducing concurrency risk), this pattern is architecturally fragile. It should be replaced with `SEQUENCE` objects or `IDENTITY` columns.

### MEDIUM

**5. Hard-Coded Employee Username in Scripts**  
Files: `20210201_SQ-1841_DB15`, line 19; `spamap_update_query.sql`, line 18  
```sql
'pat.brown' [UpdatedBy]
,'byron.young' [UpdatedBy]
```
Employee names hard-coded in deployment scripts create data quality issues when scripts are reused or when employees leave. `UpdatedBy` should capture the executing SQL login (`SYSTEM_USER`) rather than a hard-coded string.

**6. Linked Server OPENQUERY with No Error Handling**  
File: `20210503_SQ-3028_CREATE - OnbeATM_CashForecastDetail.sql`, lines 74–84  
OPENQUERY calls to `reportingdbserver2008` have no TRY/CATCH wrapper. A linked server failure leaves the entire ATM cash forecast report silently broken.

---

## Technical Debt Inventory

| Item | Debt Type | Priority |
|---|---|---|
| `reportingdbserver2008` linked server dependency — potential EOL server | Security/Architecture | P1 |
| `fdr_card_account.dda_number` not formally classified | Compliance | P1 |
| Dynamic SQL in `qryReports` without injection protection | Security | P1 |
| `MAX(change#) + 1` non-atomic sequence generation | Architecture | P2 |
| Hard-coded employee names as `UpdatedBy` | Data Quality | P2 |
| No OPENQUERY error handling | Operations | P2 |
| No rollback scripts for any changes | Process | P2 |
| Report logic stored in table rather than source-controlled procedures | Architecture | P2 |
| No migration tracking | Process | P2 |
| `qryReports` not included in DR plan documentation | Operations | P3 |

---

## Remediation Priorities

### Immediate (P1)
1. Confirm whether `reportingdbserver2008` is running EOL SQL Server software. If so, upgrade immediately and document the new version. If the name is legacy, update linked server documentation.
2. Formally classify `fdr_card_account.dda_number` — engage PCI DSS QSA to determine if it constitutes a PAN. If so, implement tokenisation or masking at the storage layer.
3. Review the reporting application's query execution method to confirm `qryReports` values are not susceptible to SQL injection via unsanitised parameter injection.

### Short-Term (P2)
4. Replace `MAX(change#) + 1` with `SEQUENCE` objects in all DMT tables.
5. Replace hard-coded `UpdatedBy` values with `SYSTEM_USER` in all DMT insert/update scripts.
6. Add TRY/CATCH with meaningful error handling around all OPENQUERY calls.
7. Add `BEGIN TRANSACTION` / `COMMIT` / `ROLLBACK` patterns to all data-patch scripts.

### Longer-Term (P3)
8. Migrate ATM cash forecast from `qryReports` dynamic SQL to a dedicated stored procedure with proper parameters, reducing SQL injection surface.
9. Evaluate migrating `reportingdbserver2008` data to a current SQL Server instance, removing the legacy linked-server dependency.
10. Introduce a migration tracking mechanism for all DB15 change scripts.
