# Data Architect View — DS_DB_GP_emeam

## Data Stores
Single SQL Server database: **emeam** (Great Plains EMEAM regional instance). The database is the Microsoft Dynamics GP application database for the EMEAM region. It follows the standard GP schema: all objects in the `dbo` schema, tables identified by cryptic 6-8 character GP codes, defaults bound via `BindDynamicsDefaults`.

## Schema / Table Structure
The database follows the Dynamics GP table naming convention where table names are GP module codes (e.g., `GL10111` = General Ledger open-year transaction history, `SOP10100` = Sales Order Work header, `PM00200` = Payables Vendor Master). The SSDT project organises tables under `dbo\Tables\Tables1\` (and presumably `Tables2`, `Tables3`, etc. for the full GP schema).

### Module Prefixes Observed
| Prefix | Module |
|---|---|
| `AF` | Analytical Accounting / Fixed Assets |
| `ASI` | Advanced Serial/Lot Inventory |
| `B` | Business Portal / Banking |
| `BM` | Bill of Materials |
| `CAM` | Cash Flow Management |
| `GL` | General Ledger |
| `IV` | Inventory Valuation |
| `PM` | Payables Management |
| `PP` | Payroll Processing |
| `RM` | Receivables Management |
| `SE` | Management Reporter (SmartList/Extender) |
| `SOP` | Sales Order Processing |
| `SVC` | Field Service Management |
| `POP` | Purchase Order Processing |

### Key Tables
| Table | Description |
|---|---|
| `AF00100` | Analytical Accounting — subsidiary ID / account mapping |
| `GL00105` | GL Account master (ACTINDX, ACTNUMST = account number string) |
| `GL10111` | GL open-year transaction detail (DEBITAMT, CRDTAMNT by period) |
| `SE00400` | Management Reporter session account list |
| `SE000100` | Management Reporter period definitions |
| `SE000401` | Session-level account detail staging (populated by `SE_Get_*` procs) |
| `PP400000` | Payroll batch headers (BACHNUMB, BCHSOURC, SERIES, NUMOFTRX, BCHTOTAL) |
| `PP400001` | Payroll batch transactions (BACHNUMB, BCHSOURC, SERIES, TRXAMNT) |

### Defaults (GP-standard)
| Default Object | Bound to |
|---|---|
| `GPS_DATE` | All datetime columns |
| `GPS_CHAR` | All char/varchar columns |
| `GPS_INT` | All int/tinyint/smallint/binary columns |
| `GPS_MONEY` | All money/smallmoney columns |
| `TA_DATE` / `TA_DBNAME` | TA (Transaction Analysis) columns |

These legacy SQL Server default objects (created via `CREATE DEFAULT`) are bound to individual columns via `sp_bindefault` — a pattern deprecated since SQL Server 2005 in favour of column-level `DEFAULT` constraints.

## Sensitive Data Handling
- **Payroll data (PP* tables)**: TRXAMNT fields represent gross pay amounts. Depending on configuration, payroll tables may contain employee identification data (SSN, bank account numbers for direct deposit). These are **not visible in the table DDL files reviewed** but are standard GP payroll fields in the full schema.
- **Vendor data (PM tables)**: Vendor TIN/EIN for 1099 reporting. `DYN_FUNC_1099_Type` and `DYN_FUNC_1099_Box_Type` functions indicate 1099 data is stored.
- **Employee data**: HR module functions (`DYN_FUNC_HR_Status`, `DYN_FUNC_Gender`, `DYN_FUNC_Ethnic_Origin`, `DYN_FUNC_MaritalStatus`, `DYN_FUNC_EIC_Filing_Status`, `DYN_FUNC_Federal_Filing_Status`) indicate HR/payroll employee data including protected characteristics — GDPR/CCPA sensitive.
- **Customer data (RM tables)**: Customer name, address, credit limit data.
- **Multi-currency financials**: EMEAM scope implies EUR, GBP, AED, and MXN transactions.

## Encryption and Protection
- **`IsEncryptionOn=False`** — TDE is explicitly disabled in `emeam.sqlproj` line 51.
- **No Always Encrypted** or column-level encryption visible in table DDL.
- **`Trustworthy=False`** (correct) — cross-database ownership chaining disabled.
- **`PageVerify=CHECKSUM`** — page-level integrity checksums enabled (good).
- **`AllowSnapshotIsolation=False`**, **`ReadCommittedSnapshot=False`** — standard GP configuration; snapshot isolation not enabled.

**Critical finding**: TDE is explicitly `False` for a database that contains payroll data (employee compensation, potentially SSN/EIN), HR sensitive attributes (gender, ethnicity, marital status), and 1099 tax data. Under GDPR (EMEAM EU entities) and GLBA (if US employees are included), encryption at rest is expected for sensitive financial and HR data.

## Data Flow
```
Dynamics GP Application (front-end)
  -> Dynamics GP Application Server
       -> SQL Server EMEAM database (this database)
            -> GL/PM/RM/SOP/POP/PP/IV/SVC tables

Management Reporter / FRx
  <- SE_Get_* procedures
       <- GL10111, GL00105, SE000401

Payroll processing
  <- PP_Batch_Total / PP_Remove_History
       <- PP400000, PP400001

SmartList / Reports
  <- Permissions.sql (DYNGRP SELECT/INSERT/UPDATE/DELETE on all tables)
  <- rpt_* roles (SELECT only on relevant tables)
```

## Data Quality / Retention
- `AnsiNulls=False` and `AnsiPadding=False` in project settings — non-ANSI behaviour; GP requires this for legacy GP stored procedures that depend on non-ANSI comparison semantics.
- `QuotedIdentifier=False` — legacy GP stored procedures do not use quoted identifiers.
- `PP_Remove_History` procedure exists to remove payroll history — retention management exists at application layer but policy duration not specified in source.
- No automated archival or partitioning is visible in the schema DDL reviewed.

## Compliance Gaps
1. **TDE disabled** on a database containing payroll, HR, and 1099 tax data — gap against GDPR Art. 32, GLBA, and Onbe data protection obligations.
2. **ANSI settings disabled** (`AnsiNulls=False`, `AnsiWarnings=False`, `QuotedIdentifier=False`) — creates SQL injection and data integrity risks; modern security reviews flag non-ANSI NULL handling as a vulnerability in some threat models.
3. **Compatibility level 100 (SQL 2008)** — prevents use of modern security features (row-level security, dynamic data masking, Always Encrypted), all of which require higher compatibility levels.
4. **No column-level data masking** on sensitive HR fields (`GDPR-sensitive DYN_FUNC_*` attributes suggest underlying columns hold gender, ethnicity, filing status).
5. **`rpt_payroll` role read access**: Payroll reporting role has SELECT access to payroll tables — ensure this access is governed by a formal access review (PCI DSS Req 7, GDPR principle of least privilege).
6. **Named individual SQL logins**: GP uses individual SQL logins for each user (employee IDs) — manual deprovisioning required; no evidence of automated offboarding integration.
