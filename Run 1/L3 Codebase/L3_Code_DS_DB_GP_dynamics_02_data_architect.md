# DS_DB_GP_dynamics — Data Architect View

## 1. Database Object Inventory

### 1.1 Tables (dbo schema — representative categories)

The `dynamics.sqlproj` contains several hundred table definitions following standard Microsoft Dynamics GP naming conventions. Key table series:

| Series Prefix | Module | Representative Tables | Notes |
|---------------|--------|----------------------|-------|
| `SY01xxx` | System Setup | `SY01400` (Users), `SY01500` (Companies), `SY01600`, `SY01700`, `SY01900` | Core system configuration |
| `SY03xxx–SY05xxx` | System Options | `SY03500`, `SY04000`, `SY05000`, `SY05100`, `SY05300`, `SY05400`, `SY05501` | Database options, paths, printers |
| `SY07xxx` | Security | `SY07101`, `SY07105`, `SY07110`, `SY07121`, `SY07125`, `SY07130`, `SY07200–SY07240` | Security roles, tasks, operations, resources |
| `SY08xxx–SY09xxx` | Workflow | `SY08000`, `SY08100`, `SY08120–SY08140`, `SY09000–SY09400` | Approval workflow engine |
| `SY10xxx` | Security assignments | `SY10500` (user-role-company), `SY10550`, `SY10600`, `SY10700`, `SY10750–SY10997` | Role membership, access bits |
| `SY40xxx–SY70xxx` | Additional system | `SY40200–SY40800`, `SY40600`, `SY60100`, `SY70700` | Alert templates, report options |
| `SLB10000–SLB90000` | Budget | 20 tables | Budget master, amounts, ranges, categories |
| `WDC40000–WDC51102` | Workflow Documents | 8 tables | Document workflow state |
| `MC00100, MC40200–MC60200` | Multi-Currency | 6 tables | Exchange rates, MC setup |
| `UPR10300–UPR41600` | Payroll | 9 tables | Employee pay, deductions |
| `FA03500, FAINST01/02` | Fixed Assets | 3 tables | Asset installation tracking |
| `ERB10000–ERB90500` | eReceipt Builder | 17 tables | Electronic receipt document tables |
| `STN41100–STN41350` | Station | 4 tables | POS terminal/station setup |
| `ASI00800–ASI80200` | Additional setup | 9 tables | Lookup/integration setup |
| `ETI`, `EXT`, `ECM`, `ICxx` | Module tables | Various | Intercompany, inventory, EC modules |
| `InDex101–InDex401` | Index | 4 tables | Index/search auxiliary tables |
| `ACRSTBL, ACTIVITY, LKACTVTY` | Activity | 3 tables | User activity tracking |
| `GPS_SQL_Error_Codes` | Error handling | 1 table | GP SQL error code registry |
| `DBVERSION, DB_Upgrade, SYUPDATE` | Versioning | 3 tables | Database version and upgrade tracking |
| `$(DefaultSchema)` tables | Audit | `AuditGPUserCreateDeleteSY10550` (trigger), `AuditGPUserCreateUpdateDeleteSY01400` (trigger), `AuditGPUserCreateUpdateDeleteSY10500` (trigger), `AuditGPUserCreateUpdateDeleteSY60100` (trigger) | User security audit triggers |

### 1.2 Views (dbo schema)
| View | Purpose |
|------|---------|
| `ORG00101` | Organisation hierarchy |
| `ORG10000`, `ORG10100` | Organisation unit views |
| `SY10000` | Security role/user assignment view |

### 1.3 Stored Procedures (representative — 80+ in project)

**System / Auto-grant:**
- `amAutoGrant` — Grants SELECT/INSERT/DELETE/UPDATE on a named table + EXECUTE on DP procs to DYNGRP; uses dynamic SQL via `EXEC (@command)`. **Dynamic SQL — HIGH RISK** (see Section 3).
- `amAutoGrantsys` — System variant of amAutoGrant.

**Lookup / SmartList:**
- `ASI_SP_ACCOUNT_LOOKUP`, `ASI_SP_CUSTOMER_LOOKUP`, `ASI_SP_CUSTOMER_LOOKUP_PROSPECT`, `ASI_SP_EMPLOYEE_LOOKUP`, `ASI_SP_IV_ITEM_NUMBER_LOOKUP`, `ASI_SP_PM_OPEN_DOCUMENT_LOOKUP`, `ASI_SP_POP_DOCUMENT_LOOKUP`, `ASI_SP_PROSPECT_LOOKUP`, `ASI_SP_RM_OPEN_LOOKUP`, `ASI_SP_SALES_DOC_LOOKUP`, `ASI_SP_SOP_DOCUMENT_LOOKUP`, `ASI_SP_VENDOR_ADDRESS_LOOKUP`, `ASI_SP_VENDOR_LOOKUP`, `ASI_SP_VOUCHER_LOOKUP` — SmartList lookup procedures.

**eConnect:**
- `eConnectOut`, `eConnectOutCreate`, `eConnectOutCreateProc`, `eConnectOutTriggers`, `eConnectOutVerify` — Manage outbound GP document integration.

**Audit / Reporting:**
- `sar_rpt_all_user`, `sar_rpt_human_resource_administrator`, `sar_rpt_power_user`, `sar_rpt_rapid` — Security audit report procedures.
- `SearchAllTables` — Searches across all GP tables (used for data investigation; potentially high I/O).
- `AddGPSSQLErrorCode` — Adds error codes to the GPS_SQL_Error_Codes registry.
- `rsaUpdateMessageCenter` — Updates the GP message center.
- `erAvailableCompanies`, `erAvailableCompaniesWithUserAccessFlag`, `erCurrencyCodes`, `erRegistrationInformation` — Company/user lookups.

**SmartModule:**
- `smAddRecordAddedRecord`, `smAddRecordDeletedRecord`, `smAddRelationMSTR`, `smAddRoutineRecord`, `smBindTableDefaults`, `smCheckRelationID` and many more — GP SmartModule framework procedures.

**Other named procedures (partial)**: `mcEuroCheckForUnpostedICTrx`, `omcGetTasks`, `omcImportRates`, `omcSaveRates`, `zAuditGPUserSec` — plus over 50 additional Dexterity/GP-standard procedures in Procs1–Procs3 subfolders.

### 1.4 Defaults
| Default | Value | Applied To |
|---------|-------|-----------|
| `GPS_CHAR` | `' '` (space) | CHAR columns |
| `GPS_DATE` | `'01/01/1900'` | DATETIME columns |
| `GPS_INT` | `0` | INT columns |
| `GPS_MONEY` | `0` | MONEY/NUMERIC columns |
| `TA_DATE` | GP-specific date | TA series columns |
| `TA_DBNAME` | GP-specific string | TA series columns |

### 1.5 Audit Triggers (in `$(DefaultSchema)`)
| Trigger | Table | Events | Audit Table |
|---------|-------|--------|-------------|
| `AuditGPUserCreateUpdateDelete` | `SY01400` | INSERT, UPDATE, DELETE | `zAuditGPUserSec` |
| `AuditGPUserCreateDeleteSY10550` | `SY10550` | INSERT, UPDATE, DELETE | `zAuditGPUserSec` |
| `AuditGPUserCreateUpdateDeleteSY10500` | `SY10500` | INSERT, UPDATE, DELETE | `zAuditGPUserSec` |
| `AuditGPUserCreateUpdateDeleteSY60100` | `SY60100` | INSERT, UPDATE, DELETE | `zAuditGPUserSec` |

---

## 2. Sensitive Data Fields

| Field | Table | Classification | PCI / Regulatory Flag |
|-------|-------|---------------|----------------------|
| `PASSWORD` | `SY01400` col 19 — BINARY(16) | **CRITICAL** — GP user credentials | PCI DSS Req 8.3 mandates strong hashing with salt. A 16-byte binary is consistent with GP's proprietary MD5/DES-based scheme, which is considered **weak by current standards**. Must be assessed against Req 8.3.6. |
| `TAXEXMT1`, `TAXEXMT2`, `TAXREGTN` | `SY01500` | Tax registration numbers for Onbe legal entities | Sensitive corporate data; relevant to GLBA / SOX. |
| `GOVCRPID` | `SY01500` | Government corporate ID | Corporate compliance data |
| `DUNS_Number` | `SY01500` | DUNS (Data Universal Numbering System) identifier | Public business identifier |
| `USERNAME`, `USERID` | `SY01400` | GP user identities | Could constitute PII if usernames are email-based |
| Employee data | `UPR10300`, `UPR10304` | Employee payroll records | **PII / NPI** — SSN, compensation data may be present in live database (not visible in DDL alone) |
| `PPSFRNUM`, `PPSTAXRT`, `PPSVNDID` | `SY01500` | Payroll tax fields per company | Tax data |

**PCI DSS CDE Assessment**: DYNAMICS is **not a payment card data store** — it holds no PANs, CVVs, or track data. However, it is a **connected business system** hosting credentials for accounts that have access to Onbe's financial systems. PCI DSS Requirement 8 (user authentication) applies to GP user accounts, and Requirement 6 (secure systems) applies because GP is maintained with vendor updates.

---

## 3. Encryption at Rest

- No Always Encrypted or column-level encryption present in DDL.
- GP's `PASSWORD` field is a 16-byte binary — this is GP's proprietary credential hash, not a standardised PBKDF2/bcrypt hash. This predates modern password-hashing standards.
- TDE status: not declared in repo DDL; would be set at instance level.

---

## 4. Cross-Database Dependencies

The DYNAMICS database is referenced by all regional GP company databases (ECAN, ECNT, EMEAM, EAST) for user authentication and company lookup. It does not contain cross-database calls itself in the standard GP model.

---

## 5. Data Retention

No data-retention DDL is present. GP historical data (closed fiscal years) is typically archived via GP's built-in archive/purge utilities at the application layer, not at the database DDL level. The `DBVERSION`, `DB_Upgrade`, and `SYUPDATE` tables track schema version history.
