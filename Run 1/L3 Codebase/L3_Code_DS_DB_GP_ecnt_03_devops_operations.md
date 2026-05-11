# DevOps / Operations Report — DS_DB_GP_ecnt

## 1. Build System

| Property | Value |
|---|---|
| Project type | SSDT SQL Server Database Project (`ecnt.sqlproj`) |
| Build tool | MSBuild with SSDT targets (`Microsoft.Data.Tools.Schema.SqlTasks.targets`) |
| Output | DACPAC (`ecnt.dacpac`) |
| Target DSP | `Microsoft.Data.Tools.Schema.Sql.Sql100DatabaseSchemaProvider` (SQL Server 2008) |
| CompatibilityMode | `90` (SQL Server 2005 mode) |
| Build configurations | `Debug` and `Release` (standard SSDT) |
| Project GUID | `{2bdc609a-320c-4ac6-83d9-67b9d5dcaa68}` |
| `SqlServerVerification` | `False` — SQL Server verification suppressed during build |

**Dynamics GP schema complexity**: ECNT is a Dynamics GP company database. The SSDT project contains both the GP-standard tables (defined by Microsoft GP DDL scripts, hundreds of tables) and Onbe custom objects. The `DYN_FUNC_*` functions (100+) are standard GP decode functions. This creates a **very large DACPAC** — any publish must use `--BlockOnPossibleDataLoss=false` or `--DropObjectsNotInSource=false` to avoid attempting to drop GP-standard objects.

**SSDT project completeness**: The SSDT project for a GP database is typically a partial representation — GP installs many objects via its own installer that are not in source control. This means the SSDT DACPAC cannot be used for full database provisioning; it captures only the Onbe custom objects and GP-standard objects that were explicitly added to the project.

---

## 2. Deployment

There is **no CI/CD pipeline configuration** visible in this repository. No `Jenkinsfile`, Azure DevOps YAML, CI-scripts references, or deployment scripts are present.

**Deployment complexity for GP databases**: Microsoft Dynamics GP databases cannot be deployed purely from a DACPAC. The standard deployment path for GP:
1. GP is installed on the SQL Server using Microsoft GP Installer (creates base GP tables, stored procedures, and functions)
2. Company database is created via GP Utilities
3. Onbe custom objects are deployed on top of GP via SSDT DACPAC or manual script execution

**Security scripts deployment risk**: 100+ Security script files define named individual user logins. If deployed via DACPAC to a new environment, the DACPAC may attempt to create GP default logins (`DYNGRP`, `DYNSA`, `DYNWORKFLOWGRP`) which are normally created by GP Installer — attempting to create these via DACPAC may conflict with the GP installation.

**`RSM_CitiDirect_ACH_WithBank` dependency on email addresses**: This procedure contains hardcoded email recipient references (commit history mentions changing from `prod.support.wirecard.com` to `namsupport@wirecard.com` in January 2019). Any deployment must verify email routing is current — email addresses are embedded in procedure body, not in a configuration table.

---

## 3. Configuration Management

**Dynamics GP configuration is not in this repository**. GP system configuration (company setup, fiscal periods, posting settings, bank integration setup) is stored in GP system and company tables, managed through the GP client application or GP PowerShell/web service. This includes:
- `SY40100` — fiscal period setup
- `SY00300` — company setup
- GP bank reconciliation setup

**Onbe custom configuration** (where visible):
- `rsm_customer_rollup` view — program-to-GFCID mapping (reference data)
- `CONTRACTPRICING` view — contract pricing configuration
- Banking integration settings in `rsm_citidirect_*` procedures — email addresses and bank configurations are hardcoded

**`Banker_available_balance` hardcoded database name** (`Banker_available_balance.sql:37`): The procedure uses `from ecnt.dbo.rm00103` — the ECNT database name is hardcoded. If the database is hosted on a linked server or renamed, this breaks without a code deployment.

---

## 4. Observability

| Capability | Status |
|---|---|
| Query Store | `QueryStoreCaptureMode=Auto` — active |
| FortiDB DAM | `FortiDBRptRole` role defined — database activity monitoring configured |
| `RSM_CitiDirect_ACH_WithBank` logging | Procedure includes email notifications for ACH processing results (multi-bank emails); additional logging added May 2018 by Nick Doan |
| GP Audit Trail | Standard GP module-level posting journals provide financial audit trail |
| SQL Agent jobs | GP uses SQL Agent for scheduled batch processing (reconciliation, payroll, etc.) |
| Error handling in custom procedures | `RSM_CitiDirect_ACH_WithBank` has duplicate-execution prevention checks (May 2018 modification) |

---

## 5. Service Account and User Access

The Security scripts reveal an **unusually large number of named individual user logins** compared to other databases in this batch. Key access categories:

| Category | Examples | Count |
|---|---|---|
| GP system roles | `DYNGRP`, `DYNSA`, `DYNWORKFLOWGRP` | 3 |
| Onbe service accounts | `ACCTGWF_APP_GRP`, `ATLYS_APP_GRP`, `Banker_execute` | 3 |
| Named individual full-name logins | `G.Couto`, `Amber.Lukacko`, `Kate.Rebar`, `J.Hillard` | 4 (visible) |
| Employee ID logins | `AA10644`, `AD12345`, `AG29025`, `GK42747`... | 80+ |
| Monitoring | `FortiDBRptRole` | 1 |

The employee ID logins (e.g., `AA10644`, `AD12345`) appear to be Windows AD user accounts using employee badge/ID identifiers. This confirms ECNT is accessed **directly by individual finance users** using their personal logins — a standard GP access pattern but one that requires periodic access reviews.

**GP-specific access risk**: GP databases are traditionally accessed by named users through the GP client. Finance users with GP access can run GL reports, modify journal entries, and view payroll data directly. This direct user access model requires strict periodic access reviews and separation of duties controls.

---

## 6. Infrastructure Dependencies

| Dependency | Type | Notes |
|---|---|---|
| Microsoft Dynamics GP ERP | Platform | ECNT is a GP company database; GP client and GP application server required |
| SQL Server instance (GP production) | Runtime | Hosts ECNT alongside other GP company databases (`ecan`, `dynamics` system db) |
| Banker API (`banker_API` repo) | Consumer | Calls `Banker_available_balance` and other Banker procedures via ECNT |
| Atlys web application | Consumer | `ATLYS_APP_GRP` role — Atlys reads ECNT for program financial data |
| Finance WebService | Consumer | `NAM_PPA_PRD_FinSVC` reads ECNT |
| Accounting Workflow (`ACCTGWF`) | Consumer | Finance approval workflows access ECNT |
| Citi Direct banking system | Integration | `rsm_citidirect_*` procedures interface with Citi Direct for ACH and drawdown |
| Meridian Bank | Integration | `VRFMERIDIAN` view for Meridian bank reconciliation |
| DS_ETL_finance-gp / DS_ETL_great-plains | ETL consumers | Export ECNT GP tables to the data warehouse |

---

## 7. Operational Risks

| Risk | Severity | Description |
|---|---|---|
| 80+ named individual user logins | HIGH | Finance users with direct DB access; no visible access review cycle in source control; leavers' access must be manually revoked |
| Employee payroll data (UPR) unencrypted | HIGH | SSN-equivalent PII and payroll amounts at rest without TDE |
| BULK_LOGGED recovery | HIGH | Point-in-time recovery unavailable during bulk loads; SOX financial data RPO gap |
| SQL 2005 compat mode | MEDIUM | Performance ceiling; modern features unavailable |
| No CI/CD pipeline | MEDIUM | Manual deployment; risk of GP schema conflicts |
| Hardcoded email addresses in stored procedures | MEDIUM | `RSM_CitiDirect_*` email addresses embedded in procedure body; requires deployment to update |
| TORN_PAGE_DETECTION | LOW | Older page integrity method; CHECKSUM preferred |
| `DYNSA` login (GP superuser) | HIGH | `DYNSA` is the Dynamics GP superuser account — must be managed as a privileged account |

---

## 8. CI/CD Assessment

**Current state**: No CI/CD. GP database deployments are typically performed manually using SqlPackage.exe or SSMS Publish, constrained by the GP product installation lifecycle.

**Recommended approach for Gen-3 migration planning**:
1. Identify all Onbe-custom objects vs. GP-standard objects in the SSDT project
2. Maintain only Onbe-custom objects in source control (GP standard objects are managed by GP product lifecycle)
3. Build a separate CI/CD pipeline for Onbe custom procedure/view/function deployments that applies on top of the GP baseline
4. Implement periodic access review for all 80+ individual user logins (quarterly review recommended for SOX ITGC compliance)
5. Move email addresses from stored procedure bodies to a configuration table to enable non-deployment configuration changes
