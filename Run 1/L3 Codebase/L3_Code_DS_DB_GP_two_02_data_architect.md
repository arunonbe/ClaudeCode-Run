# DS_DB_GP_two — Data Architect Report

## 1. Database Object Inventory

| Object Type | Count | Location |
|-------------|-------|----------|
| Tables (Tables1 subfolder) | 1,000 | `dbo/Tables/Tables1/` |
| Tables (Tables2 subfolder) | 15 | `dbo/Tables/Tables2/` |
| Total Tables | **1,015** | `dbo/Tables/` |
| Views | **250** | `dbo/Views/` |
| Stored Procedures | **15,923** | `dbo/Stored Procedures/Procs1–Procs*` |
| Scalar/Table Functions | **193** | `dbo/Functions/` |
| Defaults | 6 | `dbo/Defaults/` |
| Security principals | ~15 | `Security/` |

The reduced Tables2 count (15 vs 78 in EMXN) and higher view count (250 vs 143) are the primary structural differences from GP_EMXN.

## 2. Module-Based Table Groupings

The table naming convention is identical to GP_EMXN (full standard Dynamics GP schema):

| Prefix | Module |
|--------|--------|
| `AF` | Fixed Assets |
| `ASI` | Service / Field Service |
| `BM` | Bill of Materials |
| `CAM` | Contract Administration Management |
| `CM` | Cash Management |
| `GL` | General Ledger |
| `IV / IVC` | Inventory |
| `PM` | Payables Management |
| `POP / POR` | Purchase Order Processing |
| `RM` | Receivables Management |
| `SOP` | Sales Order Processing |
| `SVC` | Service Management |
| `SY` | System |
| `UPR` | Payroll / HR |

## 3. Sensitive Data Assessment

### 3.1 Employee PII (CRITICAL)
`UPR00100` — same structure as GP_EMXN:
- `SOCSCNUM` CHAR(15) — **SSN (US employees) — CRITICAL PII**
- `SPOUSESSN` CHAR(15) — **Spouse SSN — CRITICAL PII**
- `BRTHDATE` DATETIME — **Date of Birth — HIGH PII**
- `GENDER` SMALLINT — **Protected characteristic**
- `ETHNORGN` SMALLINT — **Ethnicity — HIGH sensitivity**
- `LASTNAME`, `FRSTNAME`, `MIDLNAME` — **PII — Names**

### 3.2 Vendor Data (HIGH)
`PM00200` — Vendor master:
- `TXIDNMBR` CHAR(11) — **Tax ID / EIN — HIGH**
- `PHNUMBR1/2`, `PHONE3` — **Phone numbers — MEDIUM PII**
- `FAXNUMBR` — Fax number
- `ADDRESS1/2/3`, `CITY`, `STATE`, `ZIPCODE` — **Address — MEDIUM PII**

### 3.3 Customer Data (MEDIUM)
`RM00101` — Customer master:
- `PHONE1/2/3` — **Phone numbers — MEDIUM PII**
- `FAX` — Fax
- `ADDRESS1/2/3`, `CITY`, `STATE`, `ZIP` — **Address — MEDIUM PII**
- `TAXEXMT1` — Tax exemption number

### 3.4 Email / Internet Addresses (HIGH)
`SY01200` — Internet information:
- `INET1`–`INET8` each CHAR(201) — **Email addresses, URLs — HIGH PII**
- `INETINFO` TEXT — **Unstructured internet data — HIGH PII**

## 4. Extended View Catalogue (250 views — higher than EMXN)

The additional ~107 views compared to GP_EMXN likely represent custom reporting views created for GP_two-specific reporting. Standard GP views present in both databases:

**Financial Reporting Views** (common with EMXN):
- `Accounts`, `AccountSummary`, `AccountTransactions`
- `BankTransactions`
- `PayablesTransactions`, `ReceivablesTransactions`
- `SalesTransactions`, `SalesLineItems`, `SalesDistributions`
- `PurchaseOrders`, `PurchaseLineItems`

**PII-Exposing Views** (common with EMXN):
- `Employees`, `EmployeeSummary` — **HIGH PII**
- `PayrollTransactions`, `PayrollCheckAndDistributionHistory`, `PayrollHistoricalTrx` — **HIGH PII**
- `Customers`, `CustomerAddress`, `CustomerItems`
- `Vendors`, `VendorAddress`, `VendorItems`

**Inventory and Service Views**:
- `Items`, `ItemQuantities`, `InventoryTransactions`
- `FieldServiceCalls`, `Equipment`, `WorkOrders`
- `Contracts`, `ContractLines`, `HistoryContracts`

**CFM Views** (Cash Flow Management — 26 views):
`CFM10000`, `CFM10301/2`, `CFM20000`, `CFM20101/2`, `CFM30200/300/500`, `CFM40100`, `CFM_SOPAll`

**SVC Views** (~30 service views):
`SVC0200V`–`SVC600TV`, `SVCSOCOV`, `SVC_ABCD`, `SVC_BTSV`, `SVC_Cont_Line_Last_Time`, `SVC_Inv_Pivot`

**ATP Views** (Available to Promise):
`ATP_BOM`, `ATP_BOMWIP`, `ATP_IVXFR_IN/VIA`, `ATP_POP/REC/RET`, `ATP_SOP`, `ATP_STK_IN/OUT`

## 5. Tables2 Differences

GP_two has only 15 tables in Tables2 (vs 78 in EMXN). This lower count in Tables2 indicates fewer extended/custom tables have been added to this GP entity. Tables2 likely contains:
- Custom extension tables added by Onbe's GP customisation team
- Integration staging tables
- Custom reporting or analytical tables

## 6. Default Constraints

Same 6 defaults as GP_EMXN:
- `GPS_CHAR.sql` (~867 KB) — Blank string defaults
- `GPS_DATE.sql` (~206 KB) — Date `1900-01-01` defaults
- `GPS_INT.sql` (~727 KB) — Integer 0 defaults
- `GPS_MONEY.sql` (~546 KB) — Money 0.00000 defaults
- `TA_DATE.sql` — eConnect date default
- `TA_DBNAME.sql` — eConnect database name default

## 7. Security Model

The GP_two Security folder contains only group-based principals:
| Login/Group | Purpose |
|-------------|---------|
| `DYNGRP` | Standard GP application users |
| `DYNWORKFLOWGRP` | GP Workflow users |
| `NAM_PROD` | Production domain group |
| `NAM_sitescope_AD` | HP SiteScope monitoring |
| `NAM_svc_gp_prd` | GP production service account (integration) |
| `RAPIDGRP` | Rapid integration group |
| `rpt_*` roles | Reporting role grants |

This is a significantly cleaner security model than GP_EMXN and is much closer to PCI DSS Requirement 7/8 compliance (role-based access, no named individual logins).

## 8. Index Architecture

Identical to GP_EMXN — Dynamics GP uses:
- Clustered primary keys on `DEX_ROW_ID` (identity integer) or composite business keys
- Unique nonclustered alternate key indexes (`AK2*` pattern)
- No columnstore indexes (incompatible with SQL 2008 compat)
- No filtered indexes (incompatible with `ANSI_NULLS=OFF`)

## 9. PCI DSS CDE Scope Assessment

**Assessment: OUT OF CDE SCOPE**

Identical assessment to GP_EMXN. No PAN, CVV, or track data expected in GP_two. `PM00200.ACNMVNDR` (vendor account number) requires manual data review to confirm no routing/account numbers are stored.

## 10. Data Retention Observations

No retention policy encoded in schema. US federal guidelines suggest:
- Employee records (including SSN): 7 years post-termination
- Payroll records: 4 years (FLSA) to 7 years (IRS)
- AP/AR records: 7 years (IRS / Sarbanes-Oxley)
- Financial statements: Permanently (or 7 years minimum)

A formal retention schedule aligned to these requirements has not been implemented at the database layer.
