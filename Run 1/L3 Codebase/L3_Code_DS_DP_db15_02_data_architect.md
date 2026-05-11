# Data Architect Report — DS_DP_db15

## Repository Identity

**Repository:** DS_DP_db15  
**Primary Database:** `RiskDB`  
**Cross-database references:** `cf_report`, `ECountcore_ss`, `reportingdbserver2008` (linked server)

---

## Database Object Inventory

### RiskDB Database

#### Tables Referenced

| Table | Schema | Purpose |
|---|---|---|
| `dbo.qryReports` | dbo | Report registry — stores named T-SQL query texts executed by the reporting engine |
| `dbo.EUC_DMT_ATM_DATACACHE` | dbo | ATM terminal data cache — field/value pairs for active terminal state |
| `dbo.EUC_DMT_ATM_DATAChangesetCACHE` | dbo | ATM terminal change-set cache — tracks field value changes over time |
| `dbo.EUC_DMT_ATM_DATA` | dbo | ATM terminal base data — point-in-time terminal field values |
| `dbo.EUC_DMT_GLOBAL_DATA` | dbo | Global DMT configuration data — change records |
| `dbo.EUC_DMT_GLOBAL_DATACACHE` | dbo | Global DMT configuration cache |
| `dbo.EUC_DMT_ContractSummary_FIELDS` | dbo | Contract summary field definitions — including FVD tier categories |
| `dbo.EUC_DMT_SPAMAP_DATA` | dbo | Special Program Account Mapping — program to account mappings |
| `dbo.EUC_DMT_SPAMAP_DATACACHE` | dbo | SPAMAP cache |
| `dbo.EUC_DMT_Separation_DATACACHE` | dbo | Separation data cache — cross-reference for SPAMAP updates |

#### Stored Procedures Referenced

| Procedure | Schema | Purpose |
|---|---|---|
| `rpt_qryReports_QRY_Insert` | dbo | Inserts or updates report queries in `qryReports` — primary DDL mechanism for reporting |
| `EUC_DMT_updaterelated` | dbo | Cascades DMT data changes to related tables after an insert/update operation |

**Source:** `20210503_SQ-3028_CREATE - OnbeATM_CashForecastDetail.sql`, lines 7–12; `20210201_SQ-1841`, line 24; `spamap_update_query.sql`, line 28

---

### Cross-Database References

#### ECountcore_ss Database (Linked via same SQL Server instance or linked server)

| Table | Purpose |
|---|---|
| `dbo.fdr_card_account` | FDR card account master — contains `dda_number` (DDA = Demand Deposit Account number), `card_id` |
| `dbo.fdr_card_account_detail` | Card account detail — contains `access_level` |
| `dbo.core_card_account_emboss_history` | Emboss history — contains `created` timestamp for emboss events |
| `dbo.psx_inventory_file` | Plastic inventory file from PSX system — contains `file_date` |
| `dbo.fdr_process_report_inventory_management` | FDR inventory management process report — contains `file_date` |

**Source:** `20210315_SQ-1820_ALTER - 131 - Stock - No Change Balance.SQL`, lines 52–70

#### cf_report Database

| Table | Purpose |
|---|---|
| `dbo.JAX_Plastic_Volumes` | Plastic card volume data from JAX processor — contains `Rpt_Date` |
| `dbo.HJ_Forms_Volumes` | Forms (carrier) volume data — contains `ReceivedDate` |

**Source:** `20210315_SQ-1820_ALTER - 131 - Stock - No Change Balance.SQL`, lines 45–47

#### reportingdbserver2008 (Linked Server)

The `OnbeATM_CashForecastDetail` query accesses:

| Table | Remote DB | Purpose |
|---|---|---|
| `riskdb.dbo.EUC_DMT_ATM_DATACACHE` | riskdb | Remote ATM data cache |
| `riskdb.dbo.EUC_DMT_ATM_DATAChangesetCACHE` | riskdb | Remote ATM changeset cache |
| `riskdb.dbo.EUC_DMT_ATM_DATA` | riskdb | Remote ATM base data |

**Source:** `20210503_SQ-3028_CREATE - OnbeATM_CashForecastDetail.sql`, lines 27, 41, 52, 90  
**Note:** `reportingdbserver2008` is a linked server pointing to a server named `reportingdbserver2008` — this is likely a legacy SQL Server 2008 reporting instance. The name suggests **the platform has not fully decommissioned a server running SQL Server 2008**, which reached end of extended support in July 2019.

---

## Data Lineage

### ATM Cash Forecast Flow
```
[reportingdbserver2008].[riskdb].EUC_DMT_ATM_DATA          ← historical base
[reportingdbserver2008].[riskdb].EUC_DMT_ATM_DATACACHE      ← current state cache
[reportingdbserver2008].[riskdb].EUC_DMT_ATM_DATAChangesetCACHE ← change tracking
         ↓ OPENQUERY / linked server join
[RiskDB].dbo.qryReports (OnbeATM_CashForecastDetail)
         ↓ Reporting application reads
[ATM Management Dashboard / Cash Forecast Report]
```

### Emboss Stock Reconciliation Flow
```
[ECountcore_ss].dbo.fdr_card_account + fdr_card_account_detail + core_card_account_emboss_history
[cf_report].dbo.JAX_Plastic_Volumes + HJ_Forms_Volumes
[ECountcore_ss].dbo.psx_inventory_file + fdr_process_report_inventory_management
         ↓ Multi-join query in qryReports (Report 131)
[RiskDB stock reconciliation report]
```

---

## Sensitive Data Identification

### HIGH SENSITIVITY — CDE Scope Candidate

| Table | Column | Sensitivity | Flag |
|---|---|---|---|
| `ECountcore_ss.dbo.fdr_card_account` | `dda_number` | **HIGH** | PCI DSS Req 3: `dda_number` is likely a card DDA/PAN or account number. The query extracts `LEFT(fca.dda_number,8)` as a program identifier — this 8-digit prefix is a BIN-range identifier. The full `dda_number` must be formally classified. If it stores a full 16-digit card number, it is a PAN and subject to PCI DSS Req 3.4 (render unreadable). |
| `ECountcore_ss.dbo.fdr_card_account` | `card_id` | MEDIUM | Internal card identifier — scope depends on whether it is the PAN or a surrogate |
| `ECountcore_ss.dbo.core_card_account_emboss_history` | `created` | LOW | Emboss timestamp — not sensitive alone but combined with card_id links to card lifecycle |

**Recommendation:** Formal data classification of `fdr_card_account.dda_number` is required to determine CDE boundary. This should be escalated to the PCI DSS compliance team.

### MEDIUM SENSITIVITY

| Table | Column | Sensitivity | Flag |
|---|---|---|---|
| `EUC_DMT_ContractSummary_FIELDS` | FVD tier data | MEDIUM | Contract financial terms — commercially sensitive |
| `EUC_DMT_SPAMAP_DATA` | Program-to-account mappings | MEDIUM | Bank account routing information |

---

## Linked Server Risk — reportingdbserver2008

The use of `OPENQUERY` against `reportingdbserver2008` introduces several data architecture risks:

1. **SQL Server 2008 End of Life:** If `reportingdbserver2008` is indeed running SQL Server 2008 R2 or earlier, it has not received security patches since July 2019. This is a **critical PCI DSS Req 6.3.3 (patching) violation** if the server is in the CDE.

2. **Linked Server Credentials:** Linked server connections use either SQL authentication (password stored in SQL Server credential store) or Windows authentication pass-through. The specific authentication method is not visible in this repo. If SQL authentication, the password is at risk if the SQL Server instance is compromised.

3. **Data Traversal:** Queries pulling from the linked server into temp tables (`#ATMCACHEDATASUBSET`, `#ATMChangeDATASUBSET`) create temporary copies of ATM data on the local RiskDB instance, potentially extending the data residency scope.

---

## Encryption Assessment

No encryption-specific DDL or configuration scripts are present in this repository. TDE and column-level encryption status cannot be determined. The linked server connection to `reportingdbserver2008` should use encrypted connections if the data traversed includes any CDE data.
