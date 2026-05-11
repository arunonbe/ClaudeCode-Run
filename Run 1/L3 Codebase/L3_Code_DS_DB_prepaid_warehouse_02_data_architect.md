# DS_DB_prepaid_warehouse — Data Architect Assessment

## 1. Schema Architecture

The warehouse uses a **classic star schema** with four user-defined schemas:

| Schema | Purpose | Object Count (approx.) |
|---|---|---|
| `dbo` | ETL control, staging helpers, reporting stored procedures, utility functions | ~100 tables, ~120 stored procedures, 3 functions |
| `dim` | Dimension tables and views | ~40 tables, ~55 views |
| `fact` | Fact tables and views | ~30 tables, ~15 views |
| `stagingdata` | CDC staging tables and ETL staging | ~20 tables, 1 stored procedure |
| `Storage` | Partition functions and partition schemes | 6 objects |
| `Security` | Database roles and membership | ~25 files |

---

## 2. Complete Object Inventory

### 2.1 Dimension Tables

| Table | Key Columns | Sensitive Fields |
|---|---|---|
| `dim.DimAccountHolder` | AccountHolderKey (IDENTITY PK), DDANumber CHAR(16) UNIQUE | **FirstName, LastName, MiddleName, SuffixName** VARCHAR(50); **Address1, Address2** VARCHAR(50); **ZipCode, City, State, Country**; **HomePhone, BusinessPhone** VARCHAR(16); **HomeEmail, BusinessEmail** VARCHAR(50) |
| `dim.DimAccountHolder_inc` | Incremental variant | Same sensitive fields |
| `dim.DimAccountHolder_Rollback` | Rollback snapshot | Same sensitive fields |
| `dim.DimAccountHolderWork` | ETL work table | Same sensitive fields |
| `dim.DimAccountHolderHold` | Hold/staging variant | Same sensitive fields |
| `dim.dimAccountPayments` | AccountHolderKey, PK | None (aggregate) |
| `dim.dimAccountSpend` | AccountHolderKey | None (aggregate) |
| `dim.dimAccountStatus` | AccountStatusKey | None |
| `dim.dimAccountUtilization` | AccountHolderKey | None |
| `dim.DimActionStatus` | DimActionStatus PK | None |
| `dim.DimActionType` | ActionTypeKey | None |
| `dim.DimActionTypeWork` | Work table | None |
| `dim.DimBIN` | BinKey | BIN CHAR(6) — partial PAN prefix |
| `dim.DimBINWork` | Work table | BIN |
| `dim.DimDates` | DateKey INT | None |
| `dim.DimDayTimes` | DayTimeKey | None |
| `dim.DimEnrollment` | EnrollmentKey | None |
| `dim.DimEnrollmentWork` | Work table | None |
| `dim.DimGeography` | GeographyKey | State/Country codes |
| `dim.DimGeographyWork` | Work table | State/Country |
| `dim.DimGLCompany` | GLCompanyKey | None |
| `dim.DimInferredPromosWork` | Work table | None |
| `dim.DimInternalPaymentType` | PK | None |
| `dim.DimIssuanceType` | PK | None |
| `dim.DimJobStatus` | JobStatusKey | None |
| `dim.DimJobStatusWork` | Work table | None |
| `dim.DimMerchant` | MerchantKey | None |
| `dim.DimMerchantWork` | Work table | None |
| `dim.DimPaymentStatus` | PaymentStatusKey | None |
| `dim.DimProduct` | ProductKey | None |
| `dim.DimProduct_Rollback` | Rollback | None |
| `dim.DimProductWork` | Work table | None |
| `dim.DimProgram` | ProgramKey | None |
| `dim.DimProgram_Rollback` | Rollback | None |
| `dim.DimProgramPromoWork` | Work table | None |
| `dim.DimProgramWork` | Work table | None |
| `dim.DimRequestStatus` | RequestStatusKey | None |
| `dim.DimRequestStatusWork` | Work table | None |
| `dim.DimTransactionType` | TransactionKey | None |
| `dim.DimTransactionTypeOLD` | Legacy | None |

### 2.2 Fact Tables

| Table | Key Columns | Notes |
|---|---|---|
| `fact.FactAccountSnapshot` | AccountHolderKey, DateKey (partitioned) | Balance snapshot per cardholder per day |
| `fact.FactAccountSnapshot_PartStg` | Partition staging | None |
| `fact.FactAllotmentToCard` | AllotmentKey | None |
| `fact.FactAllotmentToCardWork` | Work | None |
| `fact.FactAllotmentToWorldLink` | AllotmentKey | None |
| `fact.FactAllotmentToWorldLinkWork` | Work | None |
| `fact.FactCardAccountDetail` | CardID INT PK, DDANumber CHAR(16) | Links card to DDA — sensitive linkage |
| `fact.FactCardAccountDetailStg` | Staging variant | Same |
| `fact.FactCardAccountDetailWork` | Work | Same |
| `fact.FactCardEmbossDetail` | CardID, EmbossKey | None |
| `fact.FactCardEmbossDetailStg` | Staging | None |
| `fact.FactCardEmbossDetailWork` | Work | None |
| `fact.FactClaimablePaymentIssuance` | ClaimKey, AccountHolderKey | Payment amounts |
| `fact.FactClaimablePaymentIssuance_OLAPInc` | OLAP incremental | None |
| `fact.FactClaimablePaymentIssuanceWork` | Work | None |
| `fact.FactJobSvcActions` | ActionKey, AccountHolderKey (partitioned) | None |
| `fact.FactJobSvcActions_Dups` | Dedup hold | None |
| `fact.FactJobSvcActions_OLAPInc` | OLAP incremental | None |
| `fact.FactJobsvcActionsWork` | Work | None |
| `fact.FactOtherTransactions` | TransKey, DDANumber (partitioned) | None |
| `fact.FactOtherTransactions_Dups` | Dedup hold | None |
| `fact.FactOtherTransactions_OLAPInc` | OLAP incremental | None |
| `fact.FactOtherTransactionsStg` | Staging | None |
| `fact.FactOtherTransactionsWork` | Work | None |
| `fact.FactPaymentReIssueWork` | Work | None |
| `fact.FactPayments` | PaymentKey | None |
| `fact.FactPaymentTransactions` | PKID BIGINT (partitioned by PrepaidSettlementDateKey), JournalID UNIQUEIDENTIFIER, DDANumber VARCHAR(16) | **DDANumber** in fact; payment amount MONEY |
| `fact.FactPaymentTransactions_Dups` | Dedup hold | Same |
| `fact.FactPaymentTransactions_OLAPInc` | OLAP incremental | Same |
| `fact.FactPaymentTransactionsHold` | Hold | Same |
| `fact.FactPaymentTransactionsStg` | Staging | Same |
| `fact.FactPaymentTransactionsWork` | Work | Same |
| `fact.FactTransactionAccounts` | TransAccountKey (partitioned) | None |
| `fact.FactTransactionAccounts_OLAPInc` | OLAP incremental | None |
| `fact.FactTransactionAccounts_Rollback` | Rollback | None |
| `fact.FactTransactionAccountsWork` | Work | None |
| `fact.FactUnknownTransactions` | None | None |
| `fact.FactUnknownTransactions_Dups` | Dedup hold | None |
| `fact.FactUnknownTransactionsWork` | Work | None |
| `fact.FactUtilizationTransactions` | TransKey, DDANumber (partitioned) | **DDANumber** in fact |
| `fact.FactUtilizationTransactions_Dups` | Dedup hold | Same |
| `fact.FactUtilizationTransactions_OLAPInc` | OLAP incremental | Same |
| `fact.FactUtilizationTransactionsHold` | Hold | Same |
| `fact.FactUtilizationTransactionsStg` | Staging | Same |
| `fact.FactUtilizationTransactionsWork` | Work | Same |

### 2.3 DBO Staging and Control Tables (Selected)

| Table | Purpose | Sensitive Fields |
|---|---|---|
| `dbo.Payment` | Payment master records | Amounts |
| `dbo.PaymentWork` | ETL work variant | Amounts |
| `dbo.PaymentWork_HashByte` | Hash-matched payment work | None |
| `dbo.Account_Summ` | Account-level summary | DDA numbers |
| `dbo.DailyAccountBalance` | Daily balance snapshot | DDA, balance amounts |
| `dbo.Journal_Transactions` | Transaction journal | DDA, amounts |
| `dbo.Journal_Payment_Summ` | Payment summary | Amounts |
| `dbo.Journal_Spend_Summ` | Spend summary | Amounts |
| `dbo.Journal_Utilization_Summ` | Utilization summary | Amounts |
| `dbo.core_member_addenda` | Member addenda data | Potentially PII |
| `dbo.CompanionCardAccounts` | Companion card linkage | DDA, Card IDs |
| `dbo.Risk_Collections` | Collections records | Amounts, DDA |
| `dbo.Risk_NegativeBalance_Snapshot` | Negative balance history | DDA, amounts |
| `dbo.Risk_NegBal_Accounts` | Negative balance accounts | DDA |
| `dbo.Risk_PaymentRecoveries` | Recovery records | Amounts |
| `dbo.Risk_PaymentReversals` | Reversal records | Amounts |
| `dbo.Risk_WriteOffs` | Write-off records | DDA, amounts |
| `dbo.ETL_Master` | ETL control | None |
| `dbo.ETL_Master_History` | ETL history | None |
| `dbo.ETL_Flags` | ETL feature flags | None |
| `dbo.ImportLog` | Import audit log | None |

### 2.4 Stagingdata Tables

| Table | Purpose |
|---|---|
| `stagingdata.cdc_control_table` | CDC watermark control |
| `stagingdata.cdc_fdr_card_account_detail` | CDC extract of FDR card account |
| `stagingdata.cdc_fdr_dda_account_detail` | CDC extract of DDA accounts |
| `stagingdata.cdc_fdr_card_account_detail_block_code_modified` | Block code change CDC |
| `stagingdata.cdc_fdr_dda_account_detail_block_code_modified` | Block code change CDC |
| `stagingdata.cdc_core_card_account_emboss_history` | Emboss history CDC |
| `stagingdata.Hold_*` | Multiple hold tables for staging incomplete ETL runs |
| `stagingdata.temp_dda_number` | Temporary DDA staging |

---

## 3. Sensitive Data Field Catalogue

The following fields are flagged as containing personally identifiable or account-sensitive data. All are stored in plaintext with no evidence of encryption or masking at the schema level.

| Table | Field | Data Type | Classification |
|---|---|---|---|
| `dim.DimAccountHolder` | `DDANumber` | CHAR(16) | **Account number — sensitive** |
| `dim.DimAccountHolder` | `FirstName` | VARCHAR(50) | PII |
| `dim.DimAccountHolder` | `MiddleName` | VARCHAR(50) | PII |
| `dim.DimAccountHolder` | `LastName` | VARCHAR(50) | PII |
| `dim.DimAccountHolder` | `SuffixName` | VARCHAR(50) | PII |
| `dim.DimAccountHolder` | `Address1` | VARCHAR(50) | PII |
| `dim.DimAccountHolder` | `Address2` | VARCHAR(50) | PII |
| `dim.DimAccountHolder` | `ZipCode` | VARCHAR(50) | PII |
| `dim.DimAccountHolder` | `City` | VARCHAR(50) | PII |
| `dim.DimAccountHolder` | `State` | VARCHAR(50) | PII |
| `dim.DimAccountHolder` | `Country` | VARCHAR(50) | PII |
| `dim.DimAccountHolder` | `HomePhone` | VARCHAR(16) | PII |
| `dim.DimAccountHolder` | `BusinessPhone` | VARCHAR(16) | PII |
| `dim.DimAccountHolder` | `HomeEmail` | VARCHAR(50) | PII |
| `dim.DimAccountHolder` | `BusinessEmail` | VARCHAR(50) | PII |
| `fact.FactPaymentTransactions` | `DDANumber` | VARCHAR(16) | Account number |
| `fact.FactUtilizationTransactions` | `DDANumber` | Multiple tables | Account number |
| `fact.FactCardAccountDetail` | `DDANumber` | CHAR(16) | Account number |
| `dbo.DailyAccountBalance` | DDA-related columns | — | Account number |

---

## 4. Indexing and Partitioning Strategy

### 4.1 Partition Functions and Schemes
Three partition functions are defined in `Storage/`:
- `TransactionPartitionFunction` — used by `FactPaymentTransactions`, `FactUtilizationTransactions`, `FactOtherTransactions` (partitioned by `PrepaidSettlementDateKey` INT)
- `AcctSnapshotPartitionFunction` — used by `FactAccountSnapshot` (partitioned by date key)
- `JobSvcPartitionFunction` — used by `FactJobSvcActions`

Corresponding partition schemes: `TransactionPartitionScheme`, `AcctSnapshotPartitionScheme`, `JobSvcPartitionScheme`.

### 4.2 Columnstore Indexes
Multiple columnstore indexes are created on the major fact and dimension tables to support OLAP query performance:
- `ColumnStore_DimAccountHolder` on `dim.DimAccountHolder` (line 98 of DimAccountHolder.sql)
- `PColumnStore_FactPaymentTrans` on `fact.FactPaymentTransactions` (line 44 of FactPaymentTransactions.sql)
- `ColumnStore_FactCardAccountDetail` on `fact.FactCardAccountDetail`

### 4.3 Standard Indexes
Clustered indexes on partition key columns for partitioned facts; unique non-clustered index `UNDX_DDANumber` on `dim.DimAccountHolder.DDANumber`.

---

## 5. Functions

| Function | Location | Purpose |
|---|---|---|
| `dbo.fn_puid_decode` | `dbo/Functions/fn_puid_decode.sql` | Decodes Partner User ID (PUID) to internal identifier |
| `dbo.fnFormatDate` | `dbo/Functions/fnFormatDate.sql` | Date formatting utility |
| `dbo.udfMultiValueParm` | `dbo/Functions/udfMultiValueParm.sql` | Splits multi-value report parameters |

---

## 6. ETL / Data Flow Architecture

The warehouse is populated through a multi-step ETL process:
1. **CDC Capture** — `stagingdata.cdc_stage_data_capure` (stored procedure in `stagingdata/`) captures change data from operational source systems (EcountCore, FDR processor) using CDC watermark control tables.
2. **Work Table Population** — `sproc_Insert_Into_*Work` procedures load raw data into work/staging variants of each dimension and fact.
3. **Dimension Merge** — `sproc_Insert_New_Into_*` and `sproc_Update_Existing_*` procedures implement Type 1 SCD (overwrite) updates to dimension tables. No evidence of Type 2 SCD (history preservation) in dimension tables.
4. **Fact Table Load** — `sproc_Insert_Into_Fact*` procedures load from work tables to final fact tables.
5. **Rollback Support** — `_Rollback` tables and `sprocInc_Rollback_*` procedures allow ETL reversal for `DimAccountHolder`, `FactTransactionAccounts`, `DimProduct`, `DimProgram`.
6. **Incremental OLAP** — `_OLAPInc` tables and procedures capture incremental changes for downstream OLAP cube refresh.

---

## 7. Key Design Observations

1. **No PAN storage observed in dimensional model** — The warehouse does not appear to store full card PANs. DDA numbers (16-char account numbers) are the primary account identifiers.
2. **PII stored unprotected in DimAccountHolder** — Full name, address, phone, and email are stored in plaintext in what is effectively a BI query-accessible table.
3. **No masking functions** — No `SUBSTRING()`-based masking, no `HASHBYTES()` hashing, and no column-level encryption (CLE) are applied to PII fields in the dimensional tables, in contrast to the `dbo.fdr_import_cd_012` trigger in the Vendor database which hashes card numbers on insert.
4. **Work and Hold table proliferation** — There are approximately 60 work/staging/hold table variants. These tables may contain the same sensitive fields as their production counterparts and are potentially not subject to the same access controls.
5. **`PartnerUserID` field** — `dim.DimAccountHolder.PartnerUserID` (VARCHAR 50) is indexed with an `NDX_PUID_DDA` index, suggesting it is used for cross-system joins. If this field contains external partner customer identifiers, it introduces a data linkage risk.
