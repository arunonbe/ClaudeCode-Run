# DS_DB_GP_emxn — Data Architect Report

## 1. Database Object Inventory

| Object Type | Count | Location |
|-------------|-------|----------|
| Tables (Tables1 subfolder) | 1,000 | `dbo/Tables/Tables1/` |
| Tables (Tables2 subfolder) | 78 | `dbo/Tables/Tables2/` |
| Total Tables | **1,078** | `dbo/Tables/` |
| Views | **143** | `dbo/Views/` |
| Stored Procedures | **16,594** | `dbo/Stored Procedures/Procs1–Procs17/` |
| Scalar/Table Functions | **193** | `dbo/Functions/` |
| Defaults | 6 | `dbo/Defaults/` |
| Security principals | ~200+ | `Security/` |

The stored procedure count of 16,594 is consistent with a full Microsoft Dynamics GP schema, which is notoriously large — GP ships with thousands of built-in procedures (prefixed `zDP_`, `taCreate`, etc.).

## 2. Module-Based Table Groupings (GP Naming Convention)

Each two/three-letter prefix maps to a GP module:

| Prefix | Module | Representative Tables |
|--------|--------|-----------------------|
| `AF` | Fixed Assets | AF00100, AF40100–AF50300 |
| `ASI` | Service | ASI00102, ASI12301–ASI28901 |
| `B0/B1` | Integration | B0310100, B1500102 |
| `BM` | Bill of Materials | BM00101, BM10200–BM40100 |
| `CAM` | Contract Administration Management | CAM10000–CAM40001 |
| `CFM` | Cash Flow Management | CFM10000–CFM40100 (Views) |
| `CM` | Cash Management | CM00500, CM20301 |
| `CPO` | Contract Purchase Orders | CPO10113–CPO10600 (Views) |
| `DS` | Distribution | DS10000, DS10100 |
| `GL` | General Ledger | GL00100–GL70501 |
| `IV / IVC` | Inventory | IV00101–IV70500 |
| `PM` | Payables Management | PM00100–PM81000 |
| `POP / POR` | Purchase Order Processing | POP10100–POP70100 |
| `RM` | Receivables Management | RM00101–RM50104 |
| `SOP` | Sales Order Processing | SOP10100–SOP70100 |
| `SVC` | Service Management | SVC0200V–SVC_ABCD |
| `SY` | System | SY00300–SY90000 |
| `UPR` | Payroll / HR | UPR00100–UPR10200 |

## 3. Key Table Definitions

### 3.1 `UPR00100` — Employee Master (CRITICAL PII)
```
File: dbo/Tables/Tables1/UPR00100.sql
```
| Column | Type | Sensitivity |
|--------|------|-------------|
| `EMPLOYID` | CHAR(15) | Internal ID |
| `LASTNAME`, `FRSTNAME`, `MIDLNAME` | CHAR | **PII — Name** |
| `SOCSCNUM` | CHAR(15) | **CRITICAL — SSN / CURP (Government ID)** |
| `BRTHDATE` | DATETIME | **HIGH — Date of Birth** |
| `BIRTHDAY`, `BIRTHMONTH` | SMALLINT | **HIGH — Partial DOB** |
| `GENDER` | SMALLINT | **MEDIUM — Protected characteristic** |
| `ETHNORGN` | SMALLINT | **HIGH — Ethnicity** |
| `MARITALSTATUS` | SMALLINT | **MEDIUM — PII** |
| `SPOUSESSN` | CHAR(15) | **CRITICAL — Spouse SSN** |
| `SPOUSE` | CHAR(15) | **PII — Spouse name** |

**PCI DSS assessment**: Out of CDE scope. Under Mexico's LFPDPPP and GDPR-equivalent obligations, this table requires data subject access controls, purpose limitation documentation, and formal retention schedule.

### 3.2 `PM00200` — Vendor Master
```
File: dbo/Tables/Tables1/PM00200.sql
```
| Column | Type | Sensitivity |
|--------|------|-------------|
| `VENDORID`, `VENDNAME` | CHAR | Business data |
| `PHNUMBR1/2` | CHAR(21) | **MEDIUM — Phone PII** |
| `TXIDNMBR` | CHAR(11) | **HIGH — Tax ID (RFC/EIN)** |
| `TXRGNNUM` | CHAR(25) | **HIGH — Tax Registration Number** |
| `ADDRESS1/2/3`, `CITY`, `STATE`, `ZIPCODE`, `COUNTRY` | CHAR | **MEDIUM — Address PII** |

### 3.3 `RM00101` — Customer Master
```
File: dbo/Tables/Tables1/RM00101.sql
```
| Column | Type | Sensitivity |
|--------|------|-------------|
| `CUSTNMBR`, `CUSTNAME` | CHAR | Business data |
| `PHONE1/2/3` | CHAR(21) | **MEDIUM — Phone PII** |
| `FAX` | CHAR(21) | Business data |
| `ADDRESS1/2/3`, `CITY`, `STATE`, `ZIP`, `COUNTRY` | CHAR | **MEDIUM — Address PII** |
| `TAXEXMT1` | CHAR(25) | Tax exemption number |

### 3.4 `SY01200` — Internet Information (Email)
```
File: dbo/Tables/Tables1/SY01200.sql
```
| Column | Type | Sensitivity |
|--------|------|-------------|
| `INET1`–`INET8` | CHAR(201) each | **HIGH — Email addresses / URL PII** |
| `INETINFO` | TEXT | **HIGH — Unstructured internet data** |

This table stores email addresses for customers, vendors, and employees linked via `Master_Type` and `Master_ID`.

### 3.5 `GL20000` — Posted GL Transactions
Core financial posting table. Contains `JRNENTRY` (journal number), `ACTNUMST` (account), `DEBITAMT` / `CRDTAMNT`, `TRXDATE`. Business confidential; no cardholder data expected.

### 3.6 `SOP10100` — Sales Order Header
Contains `CUSTNMBR`, `DOCDATE`, `ORDRDATE`, `ORDSTATS`, `SUBTOTAL`, `TAXAMNT`. Links to customer PII through `RM00101`.

## 4. Views Catalogue (143 views)

Selected views of business significance:

| View | Purpose |
|------|---------|
| `Accounts.sql` | Flattened GL account list |
| `AccountSummary.sql` | Summarised account balances |
| `AccountTransactions.sql` | Transaction-level GL detail |
| `BankTransactions.sql` | Cash management transactions |
| `Customers.sql` | Denormalised customer master |
| `CustomerAddress.sql` | Customer address records |
| `Employees.sql` | **PII — Employee details** |
| `EmployeeSummary.sql` | **PII — Employee summary** |
| `FixedAssets.sql` / `FixedAssetsBooks.sql` | Asset register |
| `PayablesTransactions.sql` | AP transaction ledger |
| `PayrollTransactions.sql` | **PII — Payroll transactions** |
| `PayrollCheckAndDistributionHistory.sql` | **PII — Payroll cheque history** |
| `PayrollHistoricalTrx.sql` | **PII — Historical payroll** |
| `PurchaseOrders.sql` | PO summary |
| `ReceivablesTransactions.sql` | AR ledger |
| `SalesTransactions.sql` | Sales ledger |
| `Vendors.sql` | Vendor master |
| `VendorAddress.sql` | Vendor address |
| `WorkOrders.sql` | Field service work orders |
| `CFM*` (26 views) | Cash flow management views |
| `SVC*` (30+ views) | Service management views |
| `ATP_*` (9 views) | Available to Promise views |

## 5. Stored Procedure Patterns

The 16,594 stored procedures are primarily **Dynamics GP auto-generated procedures** following these naming conventions:
- `zDP_*` — Data Provider procedures (CRUD wrappers auto-generated by GP Dex engine)
- `taCreate*` — eConnect transaction API procedures
- `cmGet*`, `cmPopulate*` — Cash Management utilities
- `cnpCollect*` — Collections Management stored procs
- `aagSub*`, `aagRenumber*` — Analytical Accounting procedures
- `ASID*`, `ASIS*` — ASI Service module procedures
- `cldta*` — Custom/Legacy GP data procedures

Custom Onbe procedures (non-GP-standard) are visible in `Procs1/`:
- `BindDynamicsDefaults.sql` — Applies system defaults
- `cmGetAsOfBalance.sql` — Cash balance inquiry

## 6. Functions Catalogue (193 functions)

All functions follow the `DYN_FUNC_*` naming pattern — standard Microsoft Dynamics GP decode/lookup functions. Examples:
- `DYN_FUNC_1099_Box_Type` — Returns 1099 box type description
- `DYN_FUNC_Account_Type` — Returns GL account type label
- `DYN_FUNC_Currency_Decimals` — Returns decimal precision for a currency
- `DYN_FUNC_Decimal_Places_QTYS` — Quantity decimal places

These are read-only scalar functions that decode numeric GP codes into human-readable labels. No PII data exposure risk from the functions themselves.

## 7. Default Constraints

| Default | File | Purpose |
|---------|------|---------|
| `GPS_CHAR` | `dbo/Defaults/GPS_CHAR.sql` | Default blank string for CHAR fields (~880 KB — thousands of bindings) |
| `GPS_DATE` | `dbo/Defaults/GPS_DATE.sql` | Default date `1900-01-01` (~206 KB) |
| `GPS_INT` | `dbo/Defaults/GPS_INT.sql` | Default integer `0` (~729 KB) |
| `GPS_MONEY` | `dbo/Defaults/GPS_MONEY.sql` | Default currency `0.00000` (~546 KB) |
| `TA_DATE` | `dbo/Defaults/TA_DATE.sql` | eConnect API date default |
| `TA_DBNAME` | `dbo/Defaults/TA_DBNAME.sql` | eConnect database name default |

## 8. Indexes and Performance Notes

- GP uses a mix of clustered primary keys (`DEX_ROW_ID` identity-based) and unique nonclustered indexes on business keys (e.g., `PKAF00100` on `AF00100`).
- The `AK2AF00100` unique nonclustered index on `AF00100` is an alternate key pattern standard across GP.
- No filtered indexes or columnstore indexes observed — typical for SQL 2008-era GP schemas.
- `VARDECIMAL` storage format is enabled (`VardecimalStorageFormatOn=True` in `emxn.sqlproj` line 61) — a legacy SQL 2005/2008 feature, now superseded by row compression.

## 9. PCI DSS CDE Scope Assessment

**Assessment: OUT OF CDE SCOPE**

- No PAN (Primary Account Number) columns identified in GP table structures.
- No CVV, track data, or PIN-equivalent fields present.
- GP is a financial ERP, not a payment processing system.
- However, `PM00200.ACNMVNDR` (Account Number with Vendor) may store bank account numbers — requires manual data review to confirm no full account numbers are persisted.

**Recommendation**: Confirm `PM00200.ACNMVNDR` content does not store full bank account or routing numbers. If present, this table segment must be treated as CDE-adjacent and masked/tokenised.

## 10. Data Retention Observations

No explicit retention policy is codified in the schema (no archival tables, no `deleted_at` soft-delete columns, no partition-by-date structures). Retention is managed at the GP application layer. Recommend implementing a formal data retention schedule aligned with:
- Mexican tax records: 5 years minimum (SAT requirements)
- Employee PII: Retention per LFPDPPP / labor law
- Financial transactions: 7 years (consistent with US SOX)
