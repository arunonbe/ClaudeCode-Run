# DS_DB_GP_emxn — Business Analyst Report

## 1. Repository Identity

| Attribute | Value |
|-----------|-------|
| Repo name | DS_DB_GP_emxn |
| Internal alias | EMXN / ECount Mexico |
| Project file | `emxn.sqlproj` (GUID `88f773a1-e560-4230-8839-b6d8ed0a4d6e`) |
| SQL Server version target | SQL Server 2008 (DSP `Sql100DatabaseSchemaProvider`) |
| Collation | `SQL_Latin1_General_CP1_CI_AS` |
| Compatibility level | 100 (SQL Server 2008) |

## 2. Business Purpose

`DS_DB_GP_emxn` is the Microsoft Dynamics GP (Great Plains) company database for the **ECount Mexico (EMXN)** legal entity. Dynamics GP is Onbe's back-office ERP, used to manage multi-currency financial accounting, vendor payables, customer receivables, payroll, inventory, purchasing, and sales order processing for Mexican-domiciled operations. The "EMXN" designator aligns with the Onbe entity naming convention visible across the `DS_DB_GP_*` family (EAST, ECAN, ECNT, EMEAM, EMXN, two).

Because Onbe operates as a B2C disbursements and incentives platform, the GP Mexico instance most likely:
- Records intercompany settlements and expense allocations routed to the Mexican entity.
- Captures vendor payables for local Mexican suppliers, contractors, and card processors.
- Processes multi-currency transactions where MXN (Mexican Peso) is the functional currency alongside USD.
- Holds Human Resources / payroll data for any Mexico-based employees (stored in `UPR*` tables).
- Supports tax compliance obligations under Mexican SAT (Servicio de Administración Tributaria) — tax ID numbers stored in `TXIDNMBR` and `TXRGNNUM` columns of `PM00200` and `RM00101`.

## 3. Core Business Processes Supported

### 3.1 General Ledger (GL Module)
Tables `GL00100`–`GL70501` record chart-of-accounts master, journal entries, fiscal year periods, budget data, and account transaction history. The `GL10000` (Unposted Journal Entry Header) and `GL20000` (Posted Transaction) tables are the primary accounting backbone.

### 3.2 Accounts Payable / Payables Management (PM Module)
Tables `PM00100`–`PM81000` handle vendor master (`PM00200`), open payables transactions (`PM10000`), payment batches, 1099 reporting, and aged payables. The `PM00200.TXIDNMBR` field holds vendor Tax ID numbers — directly relevant to Mexican RFC (Registro Federal de Contribuyentes) obligations.

### 3.3 Accounts Receivable / Receivables Management (RM Module)
Tables `RM00101`–`RM50104` manage customer master, open and historical receivable transactions, cash receipts, and customer aging. `RM00101.PHONE1/PHONE2/PHONE3` contain customer telephone numbers (PII).

### 3.4 Sales Order Processing (SOP Module)
Tables `SOP10100`–`SOP70100` track sales orders, fulfillment, invoices, and revenue recognition. This module links to inventory and receivables.

### 3.5 Purchase Order Processing (POP Module)
Tables `POP10100`–`POP70100` manage purchase orders, purchase receipts, and three-way matching (PO → receipt → invoice) for procurement activity.

### 3.6 Inventory Control (IV Module)
Tables `IV00101`–`IV70500` manage item master, stock quantities, item costing, and inventory valuation. Inventory Variance Correction (IVC) sub-tables also present.

### 3.7 Human Resources / Payroll (UPR Module)
Tables `UPR00100`–`UPR10200` store **employee PII** including:
- `SOCSCNUM` (Social Security / CURP-equivalent number — **CRITICAL PII flag**)
- `SPOUSESSN` (Spouse SSN — **CRITICAL PII flag**)
- `BRTHDATE` / `BIRTHDAY` / `BIRTHMONTH`
- Employee names, marital status, gender, ethnicity

### 3.8 Fixed Assets (AF Module)
Tables `AF00100`–`AF50300` record fixed asset master, depreciation books, additions, retirements, and asset-to-GL reconciliation.

### 3.9 Field Service / Contract Management (ASI, SVC Modules)
Tables `ASI*` and `SVC*` handle service calls, contracts, equipment, RMAs (Return Material Authorizations), and RTVs (Return-to-Vendor). Views `SVC0200V`–`SVCSOCOV` expose consolidated service data.

### 3.10 Cash Management (CM Module)
Tables `CM00500`, `CM20301` and related views manage bank reconciliation against GL.

### 3.11 Analytical Accounting (AAG Module)
Stored procedures `aagCreateSubWorkDist`, `aagSubLedgerDistDelete`, etc., provide dimensional cost allocation across GP transactions — important for multi-entity reporting at Onbe.

### 3.12 Multi-Currency (Currency Management)
The system table `SY01200` stores internet/email addresses for master records. Currency exchange rate tables (not enumerated here) would be in `MC*` tables, consistent with GP Mexico requiring MXN/USD exchange.

## 4. Data Stored and Data Classification

| Data Category | Tables | PII/Sensitive Flag |
|---------------|--------|--------------------|
| Employee SSN / CURP | `UPR00100.SOCSCNUM`, `UPR00100.SPOUSESSN` | **HIGH — SSN/Gov ID** |
| Employee DOB | `UPR00100.BRTHDATE` | **HIGH — PII** |
| Employee names, gender, ethnicity | `UPR00100` | **MEDIUM — PII** |
| Customer phone numbers | `RM00101.PHONE1/2/3` | **MEDIUM — PII** |
| Vendor phone numbers | `PM00200.PHNUMBR1/2/3` | **MEDIUM — PII** |
| Vendor Tax ID (RFC) | `PM00200.TXIDNMBR` | **HIGH — Tax ID** |
| Internet/email addresses | `SY01200.INET1–INET8` | **MEDIUM — PII (email)** |
| Financial GL transactions | `GL20000`, `GL10000` | Business confidential |
| Vendor payment amounts | `PM10000`, `PM20000` | Business confidential |
| Customer balances | `RM00101`, `RM10101` | Business confidential |
| Inventory costs | `IV00101`, `IV10000` | Business confidential |

## 5. Regulatory Relevance

### PCI DSS
GP EMXN is an ERP/back-office system, not a cardholder data environment (CDE). No PANs, CVVs, or track data are expected in GP. However, if vendor payment batches reference card network settlement amounts, there is an indirect relationship. The database **should be confirmed as out-of-scope for PCI CDE** but may fall within the PCI connected-systems scope requiring network segmentation controls.

### GDPR / Privacy (Mexico LFPDPPP — Ley Federal de Protección de Datos Personales)
Employee PII in `UPR00100` (SSN/CURP, DOB, gender, ethnicity, marital status) is subject to Mexico's personal data protection law (LFPDPPP), which is equivalent in scope to GDPR for Mexican residents. Retention, access controls, and data-subject rights processes must be documented.

### SOC 1 / SOC 2
GP is a financial reporting system. Changes to the GL, payables, and receivables modules are in-scope for SOC 1 Type II (internal controls over financial reporting). Change management and access controls for this database are directly auditable.

### NACHA / Reg E
If GP Mexico initiates or records ACH disbursements to US-side recipients via Onbe's payment rails, those transactions may be Reg E-adjacent. However, the primary regulatory framework for Mexico-side payments is SPEI (Sistema de Pagos Electrónicos Interbancarios) rather than NACHA.

## 6. Data Flows

```
External Inputs                  GP EMXN Database               Downstream
──────────────────────           ──────────────────────         ──────────────────
Vendor invoices (AP)         →   PM10000, PM20000           →   ETL to DS_ETL_finance-gp
Client sales orders          →   SOP10100–SOP30100          →   GL20000 (posted)
Payroll runs                 →   UPR10100–UPR10200          →   GL distribution
Purchase receipts            →   POP10300–POP30300          →   IV10000 (inventory)
Bank statements              →   CM20301                    →   GL reconciliation
GP ETL (DS_ETL_great-plains) ←──────────────────────────────── Data warehouse feeds
```

## 7. Integration Points

- **DS_ETL_great-plains**: Likely reads from GP EMXN to extract financial data for warehousing.
- **DS_ETL_finance-gp**: Finance ETL pipeline consuming GP tables.
- **DS_DB_GP_EAST / GP_two**: Sibling GP entities; intercompany transactions link across instances.
- **Reporting**: Crystal Reports templates (`DS_RPT_crystal-invoice-templates-us`) render invoices from SOP and PM data.

## 8. Key Operational Observations

1. The README contains only the word "emxn" — indicating minimal documentation governance for this database.
2. Security users stored in `Security/` folder include named individuals (e.g., `Amber.Lukacko.sql`, `Sharon.Sywulak.sql`) — individual SQL logins rather than service accounts, which is a governance concern.
3. `TA_DATE` and `TA_DBNAME` defaults in `dbo/Defaults/` are standard GP timestamp defaults.
4. The `GPS_CHAR`, `GPS_DATE`, `GPS_INT`, `GPS_MONEY` defaults (each several hundred KB) are generated GP system defaults — auto-generated from the GP application schema.
