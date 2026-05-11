# Data Architect Report — DS_CCP_ods

## Database Objects Inventory

### Tables (26 total)

#### File Tracking Tables
| Table | PK | Sensitive Fields | Notes |
|---|---|---|---|
| `FileIOLog` | `fileLogId` INT IDENTITY | None | Tracks all ETL file I/O; FK to `xref_fileStatus`; has INSERT/UPDATE trigger |
| `FileIOLogActivity` | None | None | Audit shadow table populated by `TR_FileIOLog_IU` trigger |
| `FilesToArchive` | (not read) | None | Controls file retention/archival policy |
| `xref_fileStatus` | `fileStatusId` INT | None | Reference: file status codes |
| `SFTPHosts` | `SFTP` VARCHAR(50) | `SFTPKeyFile` VARCHAR(255) | SFTP configuration; no password column — key-file based auth |

#### FIS Report Tables (Production + Archive + Staging pattern)
| Table | PK | Sensitive Fields | Flag |
|---|---|---|---|
| `FISRptCardholderActivity` | `CardHolderActivityId` INT IDENTITY | **`PAN` VARCHAR(19) MASKED** — full PAN stored, DDM masking applied; `AccountNumber` VARCHAR(25) | **CDE — PCI DSS Req 3** |
| `FISRptCardholderActivityArchive` | (no PK visible) | **`PAN`** (masked copy) | **CDE — archive copy retains PAN** |
| `FISRptCardHolderActivityStaging` | (staging, no PK) | **`PAN`** (unstaged) | **CDE — staging PAN** |
| `FISRptDailyFee` | `DailyFeeId` INT IDENTITY | None — fee amounts only | Financial |
| `FISRptDailyFeeArchive` | None | None | Archive |
| `FISRptDailyFeeStaging` | None | None | Staging |
| `FISRptPlusISAFee` | `PlusISAFeeId` INT IDENTITY | None | ISA fee data |
| `FISRptPlusISAFeeArchive` | None | None | Archive |
| `FISRptPlusISAFeeStaging` | None | None | Staging |
| `FISRptProcessorSettlement` | `ProcessorSettlementId` INT IDENTITY | None | Settlement amounts |
| `FISRptProcessorSettlementArchive` | None | None | Archive |
| `FISRptProcessorSettlementStaging` | None | None | Staging |
| `FISRptHeaderStaging` | `ReportHeaderId` INT IDENTITY | None | FIS report header (date, institution) |

#### Network Settlement Tables
| Table | Sensitive Fields | Notes |
|---|---|---|
| `RptNetworkUnposted` | **`Card Number` VARCHAR(20) MASKED** — full PAN equivalent stored | **CDE — PCI DSS Req 3**; PK on `Transaction ID` |
| `RptNetworkUnposted_Staging` | **`Card Number`** | CDE staging |
| `RptNetworkImport` | None visible | Raw MC settlement rows |
| `RptNetworkImportStaging` | None | Staging |
| `RptNetworkAgg` | None | Aggregated totals |
| `RptNetworkAggStaging` | None | Staging |
| `RptNetworkSettlementData` | None | Transformed settlement |
| `RptNetworkSettlementDescr` | None | Reference descriptions |
| `RptNetworkSettlementAssociations` | None — stores bank name, MC member ID | Contains `AuthForwardingFlag` |

#### Package Execution Tables
| Table | Notes |
|---|---|
| `package_execution` | Scheduled execution parameters per package |
| `package_execution_log` | Execution history |

### Stored Procedures (20 total)

| Procedure | Purpose |
|---|---|
| `get_FilesToArchive` | Returns file archival config for SSIS packages |
| `get_package_last_execution_date` | Returns last run date for a named package |
| `RptBankList` | Returns list of banks for report parameter dropdown |
| `RptNetworkImportProcess` | Transforms raw MC import staging to production |
| `RptNetworkSettlementReport` | Generates Network Settlement / Interchange reports (multi-mode: ETL extract, RM report, raw) |
| `rpt_FIS_Client_Fee_Summary` | FIS client fee summary report |
| `rpt_FIS_ProcessorSettlement` | FIS processor settlement report |
| `rpt_Unposted_Transactions` | Unposted transaction report |
| `set_package_execution` | Inserts/updates scheduled execution config in `package_execution` |
| `sp_FileIOLog_GetOlderId` | Returns oldest FileIOLog IDs for archival |
| `sp_FileIOLog_GetStatus` | Returns current file status from FileIOLog |
| `sp_FileIOLog_Insert` | Inserts new file record into FileIOLog |
| `sp_FileIOLog_SetStatus` | Updates status of file record in FileIOLog |
| `sp_FISRpt_ImportDailyCardholderActivity` | Transforms FIS cardholder activity from staging to production |
| `sp_FISRpt_ImportDailyFee` | Transforms FIS daily fee data from staging to production |
| `sp_FISRpt_ImportDailyProcessorSettlement` | Transforms FIS processor settlement from staging |
| `sp_FISRpt_ImportDailyWrapper` | Orchestrates all three daily FIS import procedures |
| `sp_FISRpt_ImportPlusISAFee` | Transforms FIS Plus ISA fee data from staging |
| `sp_RptNetworkUnposted_Data_Transform` | Transforms raw unposted transaction staging to production |
| `spVerifyImport` | Validates all prerequisite files are present for a reporting period; sends alert email if incomplete |
| `usp_SQLAgentFail_Notification` | Polls msdb for failed jobs and sends alert emails |
| `util_get_date_range` | Utility: calculates start/end dates for a named frequency (daily, weekly, MTD, YTD, LOP, etc.) |

### Triggers

| Trigger | Table | Event | Action |
|---|---|---|---|
| `TR_FileIOLog_IU` | `FileIOLog` | INSERT, UPDATE | Copies all changes to `FileIOLogActivity` (full audit trail) |
| `TR_FISRptCardholderActivity_D` | `FISRptCardholderActivity` | DELETE | Copies deleted rows to `FISRptCardholderActivityArchive` |

### Indexes

- `IX_fileLogId` — NONCLUSTERED on `FISRptCardholderActivity(fileLogId)` — supports FK navigation from cardholder activity to file log

## Sensitive Data Fields — CDE Assessment

### PCI DSS Critical — CDE In-Scope Tables

| Table | Column | Data Type | DDM Masking | Assessment |
|---|---|---|---|---|
| `FISRptCardholderActivity` | `PAN` | VARCHAR(19) | `partial(0, "xxxxxxxxxxxx", 4)` — shows last 4 only | **STORED PAN — CDE CRITICAL** |
| `FISRptCardholderActivity` | `AccountNumber` | VARCHAR(25) | None | **Account identifier — CDE candidate** |
| `FISRptCardholderActivityArchive` | `PAN` | VARCHAR(19) | `partial(0, "xxxxxxxxxxxx", 4)` | **Archive copy retains PAN — CDE** |
| `FISRptCardHolderActivityStaging` | `PAN` | (staging) | Unknown (staging DDL not read in full) | **Staging PAN — CDE** |
| `RptNetworkUnposted` | `Card Number` | VARCHAR(20) | `partial(0, "xxxxxxxxxxxx", 4)` | **Card PAN equivalent — CDE** |
| `RptNetworkUnposted_Staging` | `Card Number` | (staging) | Unknown | **CDE staging** |

**Note on Dynamic Data Masking**: DDM (`MASKED WITH (FUNCTION = 'partial(...)')`) masks output to users without `UNMASK` privilege. However, the actual PAN data is stored unencrypted in the column. DDM is not equivalent to encryption. Under PCI DSS Requirement 3.5, stored PANs must be rendered unreadable using strong cryptography (AES-256, SHA-256 with salt, etc.). DDM alone does **not** satisfy PCI DSS Req 3.5.

### Masking Roles
- `ODS_Unmask` role: grants `UNMASK` permission — members can see raw PANs. Members include `report` login and `NAM\PROD` Windows group.
- `ODS_Execute` role: grants `EXECUTE` on all `dbo` schema procedures.
- **Risk**: The `report` login and `NAM\PROD` group having UNMASK access means report generation and production service accounts see full PANs in query results.

## Schema Design Quality

### Strengths
1. **Staging/Production/Archive pattern** is well-implemented for all FIS tables — provides clean ETL flow and historical record.
2. **FileIOLog trigger** provides full change history for all file tracking records — good auditability.
3. **FK constraints** are used appropriately (e.g., `FISRptCardholderActivity → FileIOLog`, `FileIOLog → xref_fileStatus`).
4. **Dynamic Data Masking** applied to PAN columns — partial mitigation.
5. **DEFAULT constraints** use `getdate()` and `suser_name()` for audit columns — good pattern.

### Weaknesses
1. **No column-level encryption** on PAN columns — DDM is not encryption, fails PCI DSS Req 3.5.
2. **No TDE evidence** — transparent database encryption is not configured at the repo level (would be server-level config).
3. **Inconsistent naming**: column named `[Card Number]` (with space) in `RptNetworkUnposted` vs. `PAN` in cardholder activity — represents two different source system conventions merged without harmonisation.
4. **Staging tables have no PK** on most tables — bulk loads could create duplicates if not controlled by SSIS logic.
5. **Archive tables lack PK** — no primary key on `FISRptCardholderActivityArchive`, `FISRptDailyFeeArchive`, etc.
6. **`util_get_date_range` has a duplicate `mtd` case** (lines 82 and 101 of the same procedure) — the second `mtd` branch uses a different calculation (`datediff(month, 0, @refdate)`) and will never execute because the first `mtd` match (line 82) returns first.

## Data Retention

- `FilesToArchive` table governs file-level archival on the ETL landing zone.
- **No explicit row-level retention policy** for ODS tables is visible in the schema. `FISRptCardholderActivity*` tables accumulate without a documented purge cycle. This is a **PCI DSS Req 3.2.1 gap** — cardholder data retention must be minimised and governed by a defined retention schedule.
- Archive tables (`*Archive`) grow indefinitely as deleted records are captured. No archival/purge process exists for the archive tables themselves.

## Referential Integrity

- `FileIOLog` → `xref_fileStatus` (FK `FK_FileIOLog_fileStatusId`)
- `FISRptCardholderActivity` → `FileIOLog` (FK `FK_FISRptCardholderActivity_fileLogId`)
- All other tables lack FK constraints to each other (staging tables have none by design).

## PCI DSS CDE Scope Assessment

**The ODS database is definitively in-scope for PCI DSS CDE.** It stores Primary Account Numbers in `FISRptCardholderActivity.PAN` and card numbers in `RptNetworkUnposted.[Card Number]`. The following PCI DSS requirements are directly applicable:
- Req 3.3: Render stored PANs unreadable (DDM alone is insufficient — column encryption required)
- Req 3.4: Log all access to cardholder data
- Req 3.7: Protect encryption keys
- Req 10.2: Audit log all access to cardholder data
- Req 7: Restrict access to cardholder data by business need-to-know (UNMASK grant to `report` login needs justification and review)
