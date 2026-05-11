# DS_DB_GP_dynamics — Business Analyst View

## 1. Repository Identity
| Attribute | Value |
|-----------|-------|
| Repo name | DS_DB_GP_dynamics |
| Project file | `dynamics.sqlproj` (322 KB — large, multi-object SSDT project) |
| README | One line: "dynamics" |
| Schema provider | Microsoft.Data.Tools.Schema.Sql.Sql100DatabaseSchemaProvider (SQL Server 2008 R2) |
| Schema scope | `dbo` + `$(DefaultSchema)` (audit-trigger tables) |

---

## 2. Business Purpose

`DS_DB_GP_dynamics` is the **Microsoft Dynamics GP (Great Plains) system-level database**. In Onbe's architecture this is the **DYNAMICS** company database — the GP system-wide registry that governs:

- **Company registration** — the `SY01500` table holds all GP company databases (ECAN, ECNT, EMEAM, EAST, etc.) with their company IDs, names, addresses, and tax registration numbers.
- **User management** — `SY01400` holds all GP user accounts including hashed passwords, and `SY10500` maps users to security roles per company.
- **Security role and task definitions** — the SY07xxx and SY40xxx table series define GP security roles, tasks, operations, and resource access.
- **System-wide configuration** — database version tracking, SQL options, messages, paths, and currency setup.
- **Audit infrastructure** — custom audit triggers (`AuditGPUserCreateUpdateDelete`, `AuditGPUserCreateDeleteSY10550`) capture all GP user creation, modification, and deletion events for SOX/audit purposes.
- **eConnect integration** — `eConnectOut` stored procedures and tables provide the GP-to-external-system integration layer (outbound document transactions).

This database is shared across all regional GP company databases (ECAN, ECNT, EMEAM, EAST) which log in through the DYNAMICS registry to authenticate users and resolve company IDs.

---

## 3. Business Processes Supported

### 3.1 Financial Ledger (via Regional Companies)
The DYNAMICS database provides the user authentication and configuration backbone for all regional GP company databases. Financial transactions (AP, AR, GL, payroll, fixed assets) are recorded in the individual company databases (ECAN, ECNT, EMEAM) but user access and role-based security is governed here.

### 3.2 Budget Management
Budget functionality uses the `SLB` table series (SLB10000 through SLB90000) — 20+ tables covering budget categories, ranges, amounts, breakdowns, and calculation rules. These support budget vs. actual variance reporting across Onbe's finance function.

### 3.3 Banker SVC Integration
The `amAutoGrant` stored procedure (in DYNAMICS and replicated to regional company databases) automatically grants `SELECT, INSERT, DELETE, UPDATE` on any named table and EXECUTE on associated dynamic programming (DP) stored procedures to the `DYNGRP` role. This pattern is the GP standard for extending access to new GP tables at deployment time, ensuring the Banker service account (`NAM\PPA_PRD_CLU`, member of DYNGRP) has access.

### 3.4 Multi-Currency Operations
The `MC` table series (MC00100, MC40200, MC40300, MC40400, MC40401, MC60100, MC60200) and associated `omcGetTasks`, `omcImportRates`, `omcSaveRates` procedures manage multi-currency exchange rate import and application — relevant for EMEA, ECAN, and Mexico operations.

### 3.5 HR / Payroll
The `UPR` table series (UPR10300, UPR10304, UPR41105, UPR41300–UPR41303, UPR41600) supports US payroll and HR data within GP — relevant for SOX HR controls and GLBA employee data handling.

### 3.6 User and Security Audit
The `zAuditGPUserSec` table (defined in the `$(DefaultSchema)` folder as `AuditGPUserCreateUpdateDelete.sql` and related trigger tables) captures every change to GP user accounts and security assignments. This is a direct SOX control supporting the "User Access Review" requirement.

---

## 4. Data Stored

### Key GP Standard Tables (representative sample)

| Table | GP Module | Data |
|-------|-----------|------|
| `SY01400` | System | GP user accounts: USERID, USERNAME, **PASSWORD (BINARY 16)**, USRCLASS, security access bits |
| `SY01500` | System | Company master: company ID, name, address, tax registration numbers (`TAXEXMT1`, `TAXEXMT2`, `TAXREGTN`), DUNS number, SIC code |
| `SY10500` | Security | User-to-company-to-security-role mapping |
| `SY10550` | Security | User alternate/modified forms and reports IDs |
| `SLB10000–SLB90000` | Budget | Budget master, categories, ranges, amounts |
| `WDC40000–WDC51102` | Workflow | Workflow definition and transaction tables |
| `UPR10300, UPR10304` | Payroll | Employee payroll details, deductions |
| `MC00100–MC60200` | Multi-Currency | Exchange rate tables |
| `FA03500, FAINST01, FAINST02` | Fixed Assets | Asset master and installation tables |
| `GPS_SQL_Error_Codes`, `MESSAGES` | System | GP error codes and system messages |
| `zAuditGPUserSec` | Audit | Audit trail of all user security changes |

---

## 5. Regulatory Relevance

| Regulation | Relevance |
|------------|-----------|
| **SOX (Sarbanes-Oxley)** | High. DYNAMICS is the user-access control system for Onbe's ERP. SOX requires documented, audited user provisioning and de-provisioning. The `AuditGPUserCreateUpdateDelete` and `AuditGPUserCreateDeleteSY10550` triggers directly support SOX IT controls (ITGC — User Access). |
| **PCI DSS v4.0.1 Req 7/8** | The `SY01400.PASSWORD` column stores GP user passwords as a 16-byte binary hash. PCI DSS Requirement 8 mandates strong authentication for systems in or connected to the CDE. GP user password strength and the hashing algorithm must be validated. |
| **GLBA** | Employee data in the `UPR` (payroll) tables is NPI subject to GLBA safeguards. |
| **GDPR / CCPA** | `SY01500` includes full legal names (`COUNTRY` field mapped to `FullLegalName` in ECAN views), addresses, and tax IDs for Onbe's legal entities — internal corporate data rather than consumer data, but subject to data protection principles. |

---

## 6. Data Flows

```
GP Client Application
        │
        ▼ Authentication
DYNAMICS.dbo.SY01400 (user credentials)
DYNAMICS.dbo.SY10500 (role assignment per company)
        │
        ▼ Resolved company database
ECAN / ECNT / EMEAM / EAST
        │
        ▼ Financial transactions posted
GL20000 (GL work), PM* (AP), RM* (AR), SOP* (Sales), POP* (Purchasing)
        │
        ▼ eConnect outbound
eConnectOut stored procedures → external systems (Banker API, finance WebService)
        │
        ▼ Audit
DYNAMICS.dbo.zAuditGPUserSec (all user security changes)
```

---

## 7. Integration with Onbe Services

- **Banker API** (`banker_API` repo) — queries GP company databases via `BankerProgram`, `BankerAllSOView`, `BankerSOView` views. The `NAM\PPA_PRD_CLU` (Banker service account) is a member of `DYNGRP` in DYNAMICS.
- **Finance WebService** (`finance-webservice_API` repo) — consumes GP data for reporting.
- **DS_ETL_finance-gp** and **DS_ETL_great-plains** — ETL pipelines that extract GP data for the data warehouse and reporting.
- **Atlys** (`DS_DB_ATL_*`) — the `ATLYS_APP_GRP` security role in DYNAMICS grants Atlys application access to GP data.
- **PPA_FinSVC_GRP** — the Finance Service group (`NAM_PPA_PRD_FinSVC`) is granted selective access for financial reconciliation processes.
