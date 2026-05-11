# DS_DB_ccp — Data Architect View

## 1. Schema Overview

CCP uses a single `dbo` schema. All NAM BIN tables reside on the `CCP_DATA` filegroup. The project targets SQL Server 2012 (`Sql110DatabaseSchemaProvider`). The schema follows a clean pattern: `*_STG` (staging), production, and `*_ARCHIVE` (deleted-row audit) table triads for each data domain.

---

## 2. Complete Table Inventory

### 2.1 NAM BIN Account Domain

| Table | Key Columns | Sensitivity |
|---|---|---|
| `NAM_BIN_ACCOUNTS` | `RecordID` BIGINT IDENTITY, `BatchDate`, `FinancialInstitution`, `ProgramCurrency`, `AccountIdentifier` NVARCHAR(32), `AccountCreateDate`, `CardNumber` NVARCHAR(4), `CardExpirationDate`, `BINNumber` NVARCHAR(6), `CardStatus`, `AccountHolderFirstName/MiddleName/LastName`, `StreetLine1/2`, `City`, `State`, `ZipCode`, `Country`, `PhoneNumber`, `EmailAddress`, `ProgramID/Name`, `AccountChannel`, **`DOB`** DATE, **`SSN`** NVARCHAR(50), `CreateDate`, `CreateUser` | **CRITICAL — SSN plaintext; DOB plaintext; full cardholder PII** |
| `NAM_BIN_ACCOUNTS_STG` | Same columns as above (staging variant, no IDENTITY PK) | **CRITICAL** |
| `NAM_BIN_ACCOUNTS_ARCHIVE` | Same columns plus `HistDate`, `HistUser` | **CRITICAL — historical SSN/DOB/PII** |

### 2.2 NAM BIN Transaction Domain

| Table | Key Columns | Sensitivity |
|---|---|---|
| `NAM_BIN_TRANSACTION` | `RecordID` BIGINT IDENTITY, `BatchDate`, `FinancialInstitution`, `UniqueTransactionId`, `SettlementDate`, `TransactionDate`, `Amount`, `Fee`, `Description`, `TransactionCode`, `AccountIdentifier`, `MerchantCategoryCode`, `MerchantCountryCode`, `ForeignActivityFlag`, **`CardNumber`** NVARCHAR(4), `Addenda`, `NetworkCode`, `DirectDepositID`, `trans_grp_level1/2`, `CreateDate`, `CreateUser` | **MEDIUM — transaction data; CardNumber last-4 only** |
| `NAM_BIN_TRANSACTION_STG` | Staging variant | MEDIUM |
| `NAM_BIN_TRANSACTION_ARCHIVE` | Archive with `HistDate`, `HistUser` | MEDIUM |

### 2.3 NAM BIN Balance Domain

| Table | Key Columns | Sensitivity |
|---|---|---|
| `NAM_BIN_BALANCES` | `RecordID` BIGINT, `BatchDate`, `FinancialInstitution`, `Date`, `AccountIdentifier`, `PostedBalance`, `AvailableBalance`, `CreateDate`, `CreateUser` | **HIGH — balance data per account** |
| `NAM_BIN_BALANCES_STG` | Staging variant | HIGH |
| `NAM_BIN_BALANCES_ARCHIVE` | Archive | HIGH |

### 2.4 NAM BIN Card Status Domain

| Table | Key Columns | Sensitivity |
|---|---|---|
| `NAM_BIN_CARD_STATUS` | `RecordID` BIGINT, `BatchDate`, `FinancialInstitution`, `Date`, `AccountIdentifier`, `CardNumber` NVARCHAR(4), `CardExpirationDate`, `CardStatus`, `CreateDate`, `CreateUser` | MEDIUM |
| `NAM_BIN_CARD_STATUS_STG` | Staging variant | MEDIUM |
| `NAM_BIN_CARD_STATUS_ARCHIVE` | Archive | MEDIUM |

### 2.5 Billing Domain

| Table | Key Columns | Sensitivity |
|---|---|---|
| `Billing_Audit` | `RecordID`, `BatchDate`, billing audit fields | LOW |
| `Billing_Audit_STG` | Staging variant | LOW |
| `Billing_Detail` | `RecordID`, `BatchDate`, client billing detail fields | LOW-MEDIUM |
| `Billing_Detail_STG` | Staging variant | LOW |
| `Billing_Events` | Event flag table | LOW |

### 2.6 FVD (Fee/Value Data) Domain

| Table | Key Columns | Sensitivity |
|---|---|---|
| `FVD_Deferred` | `RecordID`, `BatchDate`, deferred fee fields | LOW |
| `FVD_Deferred_STG` | Staging variant | LOW |
| `FVD_Revenue` | `RecordID`, `BatchDate`, revenue fields | LOW |
| `FVD_Revenue_STG` | Staging variant | LOW |
| `FVD_SingleLoad_STG` | Single-load staging | LOW |

### 2.7 Inventory and Execution

| Table | Key Columns | Sensitivity |
|---|---|---|
| `FISERV_INVENTORY` | `RecordID` INT IDENTITY, `BatchDate`, `SourceFileName`, `FileDateTime`, `StockID`, `StockDesc`, inventory counts, `Below Min` | LOW |
| `package_execution` | `PackageID`, `ExecutionStartDateTime`, `ExecutionEndDateTime`, `ExecutionStatus`, `BatchDate`, record counts | LOW |
| `package_execution_log` | Per-step log for package execution | LOW |

---

## 3. Sensitive Data Field Inventory

| Table.Column | Data Type | Classification | Regulatory/Compliance Flag |
|---|---|---|---|
| `NAM_BIN_ACCOUNTS.SSN` | NVARCHAR(50) | **SSN — Plaintext** | **CRITICAL: GLBA NPPI, CCPA Sensitive Personal Info, 50-state breach notification laws. Must be encrypted or masked** |
| `NAM_BIN_ACCOUNTS.DOB` | DATE | **Date of Birth — Plaintext** | HIGH: GDPR, CCPA; combined with name = identity theft risk |
| `NAM_BIN_ACCOUNTS.AccountHolderFirstName/LastName` | NVARCHAR(80/72) | PII — Cardholder name | PCI DSS CHD (cardholder name); GDPR/CCPA |
| `NAM_BIN_ACCOUNTS.StreetLine1/2`, `City`, `State`, `ZipCode`, `Country` | NVARCHAR | PII — Full address | GDPR/CCPA |
| `NAM_BIN_ACCOUNTS.PhoneNumber` | NVARCHAR(50) | PII — Phone number | GDPR/CCPA |
| `NAM_BIN_ACCOUNTS.EmailAddress` | NVARCHAR(100) | PII — Email | GDPR/CCPA |
| `NAM_BIN_ACCOUNTS.AccountIdentifier` | NVARCHAR(32) | Account reference (DDA token or similar) | Requires classification — if PAN, CDE scope |
| `NAM_BIN_ACCOUNTS.BINNumber` | NVARCHAR(6) | BIN (first 6 digits) | PCI-compliant to store unencrypted |
| `NAM_BIN_ACCOUNTS.CardNumber` | NVARCHAR(4) | Last-4 digits only | PCI-compliant to store unencrypted |
| `NAM_BIN_ACCOUNTS_ARCHIVE.SSN` | NVARCHAR(50) | **SSN in archive — Plaintext** | Same as above; archive tables carry same risk |
| `NAM_BIN_ACCOUNTS_STG.SSN` | NVARCHAR(50) | **SSN in staging — Plaintext** | Staging tables are often less controlled than production tables |
| `NAM_BIN_BALANCES.PostedBalance`, `AvailableBalance` | NUMERIC(19,5) | Financial — card balance | HIGH — balance exposure |

---

## 4. Triggers

| Trigger | Table | Event | Action |
|---|---|---|---|
| `TR_NAM_BIN_ACCOUNTS_D` | `NAM_BIN_ACCOUNTS` | DELETE | Inserts deleted rows into `NAM_BIN_ACCOUNTS_ARCHIVE`; captures `GETDATE()` as HistDate, `SUSER_NAME()` as HistUser |
| `TR_NAM_BIN_TRANSACTION_D` | `NAM_BIN_TRANSACTION` | DELETE | Archives to `NAM_BIN_TRANSACTION_ARCHIVE` |
| `TR_NAM_BIN_BALANCES_D` | `NAM_BIN_BALANCES` | DELETE | Archives to `NAM_BIN_BALANCES_ARCHIVE` |
| `TR_NAM_BIN_CARD_STATUS_D` | `NAM_BIN_CARD_STATUS` | DELETE | Archives to `NAM_BIN_CARD_STATUS_ARCHIVE` |

All triggers are FOR DELETE (AFTER DELETE) triggers — they only fire on deletion, not on updates. This means updates to `NAM_BIN_ACCOUNTS` (e.g., SSN or DOB changes) are not archived; only the delete event is captured. **This is a data-lineage gap for PII change history.**

---

## 5. Stored Procedures

| Procedure | Purpose |
|---|---|
| `sp_process_NAM_BIN_ACCOUNTS` | Stage-to-production load; upsert-by-batch-replace; converts date strings |
| `sp_process_NAM_BIN_BALANCES` | Stage-to-production balance load |
| `sp_process_NAM_BIN_CARD_STATUS` | Stage-to-production card status load |
| `sp_process_NAM_BIN_TRANSACTION` | Stage-to-production transaction load |
| `sp_process_Billing_Audit` | Billing audit staging promotion |
| `sp_process_Billing_Detail` | Billing detail staging promotion |
| `sp_process_FVD_Deferred` | Deferred fee staging promotion |
| `sp_process_FVD_Revenue` | Revenue fee staging promotion |
| `sp_process_FVD_SingleLoad` | Single-load fee staging promotion |
| `get_package_last_execution_date` | Returns most recent execution date for a package |
| `set_package_execution` | Inserts package execution record |
| `remove_package_imported_data` | Removes previously loaded data for a specific package execution |

---

## 6. Encryption at Rest Assessment

- **SSN field**: `NAM_BIN_ACCOUNTS.SSN` NVARCHAR(50) — **no column-level encryption**. SSN is stored in plaintext in the production table, staging table, and archive table.
- **DOB field**: `NAM_BIN_ACCOUNTS.DOB` DATE — plaintext. Combined with name, this constitutes a breachable identity dataset.
- **TDE**: Cannot be confirmed from DDL alone. Must be verified on production instance.
- **Staging table risk**: `NAM_BIN_ACCOUNTS_STG` contains the same SSN and DOB data as the production table but is a transient staging table. Staging tables are often excluded from TDE encryption key rotation schedules and access controls — creating a secondary uncontrolled PII data store.

---

## 7. PCI DSS CDE Scope Assessment

| Scope Question | Assessment |
|---|---|
| Does CCP store PAN (full card number)? | No — CardNumber is NVARCHAR(4), last-4 only; compliant per PCI DSS Req 3.4 |
| Does CCP store BIN? | Yes — BINNumber NVARCHAR(6); permitted by PCI DSS |
| Does CCP store cardholder name? | Yes — AccountHolderFirstName/LastName; PCI DSS Req 3 CHD |
| Does CCP store SSN? | Yes — GLBA NPPI, not PCI DSS but equally sensitive |
| Is CCP in PCI CDE scope? | **Conditional** — if AccountIdentifier is an unprotected PAN or DDA number, YES. If it is a token, NO for PAN scope but YES for cardholder name scope |

**Recommendation**: Classify `AccountIdentifier` definitively; engage PCI QSA for scoping assessment.

---

## 8. Data Retention

- `CreateDate` and `CreateUser` columns on all production tables.
- Archive tables (`*_ARCHIVE`) serve as a deleted-record audit log but have no purge mechanism.
- No explicit retention policy columns present.
- For Reg E periodic statement obligations, transaction data must be accessible for 2 years from the transaction date (12 CFR 1005.9). The archive trigger pattern supports this but requires a formal retention schedule.
