# Solution Architect View — DS_DB_GP_emeam

## 1. Technical Architecture

| Attribute | Value |
|---|---|
| Project type | SSDT SQL Server Database Project (`emeam.sqlproj`) |
| Target DSP | `Microsoft.Data.Tools.Schema.Sql.Sql100DatabaseSchemaProvider` (SQL Server 2008 schema) |
| CompatibilityMode | `100` (SQL Server 2008) |
| DefaultCollation | `SQL_Latin1_General_CP1_CI_AS` |
| PageVerify | `CHECKSUM` — correct |
| TDE | `IsEncryptionOn=False` |
| Recovery | `FULL` — point-in-time recovery available |
| Service Broker | `EnableBroker` — active; GP workflow uses Service Broker |
| Query Store | `QueryStoreCaptureMode=Auto`, `QueryStoreMaxStorageSize=100MB` |
| AnsiNulls / QuotedIdentifier / ArithAbort | All `False` — non-ANSI legacy settings required by GP |
| VardecimalStorageFormat | `True` — deprecated SQL Server feature |
| Nested triggers | `IsNestedTriggersOn=True` — GP requires this |

**Database type**: Microsoft Dynamics GP company database (EMEAM region). Largest GP database in this batch — 17 stored procedure folders (Procs1–Procs17), 150+ views, full GP module coverage including Field Service Management.

---

## 2. Object Inventory Summary

| Category | Count | Notes |
|---|---|---|
| Tables (GP standard) | 500+ | GL, RM, PM, SOP, POP, IV, PP, FA, SVC, AF, BM, CAM, CM, SE modules |
| Custom stored procedures | 400+ (Procs1–Procs17) | SE_Get_*, PP_*, SVC_* (200+ field service procs), GP module procedures |
| Custom views | 150+ | Business-facing GP views: Employees, PayrollTransactions, Customers, Vendors, etc. |
| Custom functions | 100+ DYN_FUNC_* + app_func_in_same_fdr_cycle | GP decode functions + FDR cycle logic |
| Security scripts | 25+ named individual logins + 20+ rpt_* roles | Employee ID logins + granular report roles |
| Default objects | GPS_DATE, GPS_CHAR, GPS_INT, GPS_MONEY | Bound via deprecated sp_bindefault |

---

## 3. Key Technical Findings

### 3.1 Employee PII and Payroll Data — Critical GDPR Risk
The following views expose sensitive employee data:
- `Employees` / `EmployeeSummary`: Employee master records across EMEAM entities
- `PayrollTransactions` / `PayrollHistoricalTrx` / `PayrollCheckAndDistributionHistory`: Salary, deductions, withholding, net pay
- `DYN_FUNC_Gender`, `DYN_FUNC_Ethnic_Origin`, `DYN_FUNC_MaritalStatus`: These decode functions confirm the underlying tables contain GDPR Special Categories of Personal Data (Article 9)

TDE is disabled (`IsEncryptionOn=False`). Employee compensation, protected characteristics, and tax data are stored unencrypted at rest across EMEAM EU and non-EU jurisdictions.

### 3.2 Deprecated SQL Server Features — Migration Blockers
- `sp_bindefault` / `sp_unbindefault`: Used in `BindDynamicsDefaults` — removed in SQL Server 2022 (compatibility level 160)
- `SET ROWCOUNT n`: Used in `BindDynamicsDefaults` — deprecated; removed in SQL Server 2022
- Legacy catalog views (`dbo.syscolumns`, `dbo.sysobjects`): Used in `BindDynamicsDefaults`
- `VardecimalStorageFormatOn=True`: Deprecated since SQL Server 2012; no-op in modern versions

### 3.3 SE_Get_* Session Race Condition
`SE_Get_Acc_Detail_Hist` populates the permanent staging table `SE000401` scoped by `USERID`. Two concurrent sessions under the same SQL login will produce incorrect financial report data — a **data integrity risk in financial reporting**.

### 3.4 Service Broker Dependency
`ServiceBrokerOption=EnableBroker` — GP workflow uses Service Broker. Blocks migration to Azure SQL Database; requires Azure SQL Managed Instance for cloud migration.

### 3.5 Non-ANSI Settings
Required by Dynamics GP but:
- `ArithAbort=False`: Payroll and GL calculations silently return NULL on arithmetic errors
- `AnsiNulls=False`, `QuotedIdentifier=False`: Block migration to Azure SQL Database

---

## 4. Security Posture

| Control | Status | Finding |
|---|---|---|
| TDE | `IsEncryptionOn=False` | Employee PII and GDPR Special Categories unencrypted at rest |
| GDPR Special Categories | `DYN_FUNC_Gender`, `DYN_FUNC_Ethnic_Origin`, `DYN_FUNC_MaritalStatus` | Protected characteristics stored without pseudonymisation |
| Named individual SQL logins | 25+ employee-ID logins | Manual offboarding; GDPR Art. 17 (erasure) complicated by SQL login pattern |
| `rpt_payroll` role | SELECT on payroll tables | Access review required — GDPR and local labour law |
| Developer logins | `G.Couto`, `kbadre`, `kgurung` | Elevated access without visible time-limit |
| `Trustworthy=False` | Correct | Cross-database ownership chaining disabled |
| `ISAUser` | Read-only | InfoSec audit account — correct pattern |

**GDPR scope**: EMEAM covers EU entities. The Employees, PayrollTransactions, and HR attribute views confirm this database holds Special Categories of Personal Data under GDPR Article 9. No pseudonymisation, encryption, or data subject request handling is implemented at the database layer.

---

## 5. Technical Debt

| Item | Location | Severity | Notes |
|---|---|---|---|
| TDE disabled — employee PII and GDPR Special Categories | `emeam.sqlproj:50` | CRITICAL | GDPR Art. 32; Special Categories without encryption |
| `sp_bindefault` deprecated | `BindDynamicsDefaults.sql` | HIGH | Removed in SQL Server 2022; blocks future SQL upgrade |
| `SET ROWCOUNT` deprecated | `BindDynamicsDefaults.sql` | HIGH | Removed in SQL Server 2022 |
| SE_Get_* session race condition | `SE_Get_Acc_Detail_Hist` and other SE_Get_* procs | HIGH | Concurrent users produce incorrect financial report data |
| `ArithAbort=False` | `emeam.sqlproj` | HIGH | Payroll/GL calculations silently return NULL on arithmetic errors |
| Non-ANSI settings block Azure SQL migration | `emeam.sqlproj` | HIGH | Azure SQL Database requires ANSI_NULLS, QUOTED_IDENTIFIER ON |
| `VardecimalStorageFormatOn=True` | `emeam.sqlproj` | MEDIUM | Deprecated since SQL Server 2012 |
| SQL 2008 compat mode | `emeam.sqlproj` | MEDIUM | Blocks row-level security, dynamic data masking, Always Encrypted |
| Named individual SQL logins | `Security/` | MEDIUM | GDPR Art. 17 complicated; manual deprovisioning |
| No CI/CD pipeline | Repo level | MEDIUM | Active development branch with no build automation |
| Developer/consultant logins | `G.Couto.sql`, `kbadre.sql` | MEDIUM | Elevated access without visible time-limit |

---

## 6. API Surface

GP EMEAM has no REST or HTTP API surface. Access patterns:

| Pattern | Callers | Description |
|---|---|---|
| GP client direct DB access | 25+ named users (DYNGRP) | Finance/HR/operations users via GP Windows client |
| Management Reporter | SE_Get_* stored procedures | Financial statement data extraction |
| SmartList / Report Writer | rpt_* role holders | Read-only GP module data |
| ETL (DS_ETL_great-plains, DS_ETL_great-plains-to-oas-coda) | External ETL processes | Full GP table extraction to data warehouse / CODA |
| GP Application Server | All GP tables | GP application server CRUD via DYNGRP |
| ISAUser / InfoSec tools | Read-only views | Security and compliance scans |

---

## 7. Gen-3 Migration Requirements

1. **Enable TDE immediately** — employee PII and GDPR Special Categories require encryption at rest; TDE can be applied without application changes
2. **Implement GDPR data subject request handling** — identify, export, and anonymise personal data for individual employees across EMEAM jurisdictions
3. **ERP modernisation assessment** — evaluate migration from Dynamics GP to Dynamics 365 Business Central; assess EMEAM entity scope, data retention by country, intercompany reconciliation
4. **Resolve `sp_bindefault` / `SET ROWCOUNT`** — replace before any SQL Server 2022 upgrade
5. **Fix SE_Get_* session race condition** — use session-scoped temp tables (`#SE000401`) instead of permanent staging table
6. **Migrate named individual SQL logins** to Windows/Azure AD authentication with automated HR-system deprovisioning
7. **Raise compatibility level** to SQL Server 2019/2022 after resolving deprecated feature usage
8. **Separate EMEAM payroll** to a dedicated GDPR-compliant HR/payroll system with documented data subject rights handling
9. **Implement jurisdiction-aware data retention** — EU employee data typically 5-10 years; support automated archival and deletion
