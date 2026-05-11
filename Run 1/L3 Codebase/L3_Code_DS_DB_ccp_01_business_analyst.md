# DS_DB_ccp — Business Analyst View

## 1. Business Purpose

`CCP` (Card/Client Processing Platform) is a SQL Server reporting and data-integration database that acts as the BIN-level operational data store for Onbe's NAM (North America) prepaid card programs. It receives daily batch files from the financial institution (Fiserv/FIS) containing account-level, transaction-level, balance-level, and card-status-level data for all prepaid cards under each BIN, and makes that data available for reporting, reconciliation, and client-facing outputs.

The CCP database is a **data-integration hub**: it stages incoming file data, processes and validates it, loads it into production tables, and archives replaced data via triggers. It also processes Fiserv card-stock inventory data and client billing/revenue data.

The project is a Visual Studio SSDT project (`CCP.sqlproj`) targeting SQL Server 2012 (`Sql110DatabaseSchemaProvider`).

---

## 2. Business Processes Supported

### 2.1 NAM BIN Account File Processing
- Daily account files from the financial institution are loaded into staging (`NAM_BIN_ACCOUNTS_STG`), validated and transformed, then promoted to `NAM_BIN_ACCOUNTS` by `sp_process_NAM_BIN_ACCOUNTS`.
- `NAM_BIN_ACCOUNTS` is the primary cardholder account table in CCP: it holds account identifier, BIN number, card number (last 4 digits), card expiry, card status, account holder name (first, middle, last), full address (street, city, state, zip, country), phone, email, program ID/name, **date of birth (DOB)**, and **SSN**.
- Deleted rows are archived to `NAM_BIN_ACCOUNTS_ARCHIVE` by trigger `TR_NAM_BIN_ACCOUNTS_D`, capturing the DBA's user name via `SUSER_NAME()`.

### 2.2 NAM BIN Transaction File Processing
- Daily transaction files are staged in `NAM_BIN_TRANSACTION_STG` and promoted to `NAM_BIN_TRANSACTION` by `sp_process_NAM_BIN_TRANSACTION`.
- `NAM_BIN_TRANSACTION` records settlement date, transaction date, amount, fee, description, transaction code, account identifier, merchant category code, merchant country code, foreign activity flag, card number (last 4), network code, and direct deposit ID.
- Deleted rows archived to `NAM_BIN_TRANSACTION_ARCHIVE` by trigger `TR_NAM_BIN_TRANSACTION_D`.

### 2.3 NAM BIN Balance File Processing
- Daily balance files staged in `NAM_BIN_BALANCES_STG` and promoted to `NAM_BIN_BALANCES` by `sp_process_NAM_BIN_BALANCES`.
- `NAM_BIN_BALANCES` holds per-account posted and available balances by date.
- Deleted rows archived to `NAM_BIN_BALANCES_ARCHIVE`.

### 2.4 Card Status File Processing
- Daily card-status files staged in `NAM_BIN_CARD_STATUS_STG` and promoted to `NAM_BIN_CARD_STATUS` by `sp_process_NAM_BIN_CARD_STATUS`.
- `NAM_BIN_CARD_STATUS` holds account identifier, card number (last 4), card expiry date, and card status per date.
- Deleted rows archived to `NAM_BIN_CARD_STATUS_ARCHIVE`.

### 2.5 Package Execution Management
- `package_execution` and `package_execution_log` track the execution history of SSIS or SQL Agent job steps that drive the file-loading processes.
- `get_package_last_execution_date`, `set_package_execution`, and `remove_package_imported_data` manage this execution metadata.

### 2.6 Billing Data Processing
- `Billing_Audit` and `Billing_Audit_STG` store billing audit records; `sp_process_Billing_Audit` promotes staged data.
- `Billing_Detail` and `Billing_Detail_STG` store client billing detail records; `sp_process_Billing_Detail` promotes staged data.
- `Billing_Events` is a lightweight event trigger table.

### 2.7 Fee and Revenue Processing
- `FVD_Deferred`, `FVD_Deferred_STG` — Deferred fee/value data; `sp_process_FVD_Deferred` promotes.
- `FVD_Revenue`, `FVD_Revenue_STG` — Fee/value revenue data; `sp_process_FVD_Revenue` promotes.
- `FVD_SingleLoad_STG` — Single-load fee staging; `sp_process_FVD_SingleLoad` promotes.

### 2.8 Fiserv Card Inventory
- `FISERV_INVENTORY` tracks physical card stock inventory from Fiserv: stock ID, description, beginning/ending on-hand quantities, usage quantities, adjustments, monthly consumption history (6 months), and below-minimum indicator. This supports card-embossing supply chain management.

---

## 3. Business Rules Encoded in Stored Procedures

| Procedure | Business Rule |
|---|---|
| `sp_process_NAM_BIN_ACCOUNTS` | Deletes existing batch before re-inserting (upsert-by-replace); converts date strings; automatic archive via trigger |
| `sp_process_NAM_BIN_TRANSACTION` | Same upsert-by-replace pattern; data type conversion for dates and amounts |
| `sp_process_NAM_BIN_BALANCES` | Balance data replaced per batch; archive on delete |
| `sp_process_NAM_BIN_CARD_STATUS` | Status data replaced per batch; archive on delete |
| `sp_process_Billing_Audit` | Promotes billing audit data from staging |
| `sp_process_Billing_Detail` | Promotes billing detail data from staging |
| `sp_process_FVD_Deferred` | Promotes deferred fee data |
| `sp_process_FVD_Revenue` | Promotes revenue fee data |
| `sp_process_FVD_SingleLoad` | Promotes single-load fee data |
| `remove_package_imported_data` | Purges previously imported data for a specific package execution |
| `set_package_execution` | Records start of package execution |
| `get_package_last_execution_date` | Returns the most recent successful execution date for idempotency |

---

## 4. Regulatory Relevance

### PCI DSS — CDE Assessment
- `NAM_BIN_ACCOUNTS.SSN` (NVARCHAR 50) — **Social Security Number in plaintext**. This is not a PAN, but is sensitive personal financial data that may be in scope for Onbe's data classification policy and is subject to GLBA, CCPA, and various state identity-theft statutes.
- `NAM_BIN_ACCOUNTS.DOB` (DATE) — **Date of Birth in plaintext**. PII subject to GDPR/CCPA.
- `NAM_BIN_ACCOUNTS.CardNumber` (NVARCHAR 4) — stores only **last 4 digits** of the card number. Last-4 digits are explicitly permitted to be stored under PCI DSS Req 3.4 without additional protection.
- `NAM_BIN_ACCOUNTS.BINNumber` (NVARCHAR 6) — BIN (first 6 digits) is permitted to be stored.
- `NAM_BIN_ACCOUNTS.AccountIdentifier` (NVARCHAR 32) — this is the internal account identifier (likely a DDA number or token), not the PAN.
- `NAM_BIN_TRANSACTION.CardNumber` (NVARCHAR 4) — last-4 only; compliant.

### GLBA
- SSN data in `NAM_BIN_ACCOUNTS.SSN` is GLBA-protected non-public personal information (NPPI). Its storage requires appropriate safeguarding measures under GLBA Safeguards Rule (16 CFR Part 314).

### Reg E
- Transaction data in `NAM_BIN_TRANSACTION` supports Reg E periodic statement requirements and error-resolution audit trails.

---

## 5. Data Flows

```
Financial Institution (Fiserv/FIS)
      │  (daily batch file: account, transaction, balance, card status)
      ▼
SSIS / SQL Agent job
      │
      ├──► NAM_BIN_ACCOUNTS_STG ──► sp_process_NAM_BIN_ACCOUNTS ──► NAM_BIN_ACCOUNTS
      │                                                                        │
      │                                                         (trigger) ─► NAM_BIN_ACCOUNTS_ARCHIVE
      │
      ├──► NAM_BIN_TRANSACTION_STG ──► sp_process_NAM_BIN_TRANSACTION ──► NAM_BIN_TRANSACTION
      │
      ├──► NAM_BIN_BALANCES_STG ──► sp_process_NAM_BIN_BALANCES ──► NAM_BIN_BALANCES
      │
      └──► NAM_BIN_CARD_STATUS_STG ──► sp_process_NAM_BIN_CARD_STATUS ──► NAM_BIN_CARD_STATUS
                                                                                │
cf_report database ◄──────────────────────────────────────────────────────────┘
  (reporting queries pull from CCP tables)
```

---

## 6. Object Summary

| Object Type | Count |
|---|---|
| Tables | 19 (plus 4 archive tables = 23 total DDL files) |
| Stored Procedures | 12 |
| Triggers | 4 (one per main NAM BIN table — on DELETE) |
| Views | 0 |
| Functions | 0 |
| Storage | 1 filegroup (CCP_DATA) |
