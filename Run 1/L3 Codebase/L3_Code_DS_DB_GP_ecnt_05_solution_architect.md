# Solution Architect Report — DS_DB_GP_ecnt

## 1. Technical Architecture

`DS_DB_GP_ecnt` is a **Microsoft Dynamics GP company database** for the US Central (ECNT) entity, managed as an SSDT SQL Server Database Project targeting SQL Server 2008 (`Sql100DatabaseSchemaProvider`) with SQL Server 2005 compatibility mode (`CompatibilityMode=90`).

**Project identity:**
- Project GUID: `{2bdc609a-320c-4ac6-83d9-67b9d5dcaa68}`
- Target DSP: `Sql100DatabaseSchemaProvider` (SQL Server 2008 schema provider)
- Compatibility mode: `90` (SQL Server 2005)
- Collation: `SQL_Latin1_General_CP1_CI_AS`
- Recovery: `BULK_LOGGED` — not FULL; point-in-time restore unavailable during bulk loads
- TDE: `IsEncryptionOn=False`
- Page verification: `TORN_PAGE_DETECTION` (not CHECKSUM)
- ANSI settings: `AnsiNulls=False`, `QuotedIdentifier=False`, `ArithAbort=False` — all non-ANSI

**Functional layers:**

| Layer | Objects | Description |
|---|---|---|
| GP Standard Schema | Hundreds of GP tables (GL, RM, PM, SOP, POP, UPR, FA, IV, SLB, SY modules) | Microsoft Dynamics GP ERP baseline installed by GP Installer |
| Onbe Custom Layer | 30+ stored procedures, 15+ views, 5 Banker functions | Onbe/RSM business logic deployed on top of GP standard schema |
| GP Decode Functions | `DYN_FUNC_*` (100+ functions) | Standard GP enumerated value decode functions |
| Security Layer | 100+ named login definitions | Individual user and service account access scripts |

---

## 2. API Surface

### 2.1 Banker SVC Integration (Real-Time, Latency-Sensitive)

```sql
-- Primary real-time authorisation balance check
dbo.Banker_available_balance(
    @program CHAR(8),
    @promo varchar(10) = null
)
```

Implementation detail: reads `ecnt.dbo.rm00103` directly with hardcoded DB name at line 37:
```sql
select top 1 @CUSTBLNC = CUSTBLNC * -1
from ecnt.dbo.rm00103
where custnmbr like @customer
```

This procedure is in the **card authorisation path** — it is called synchronously by the Banker API before approving card loads. Latency and availability are critical.

**Supporting Banker functions** (all authored ACHEN 2009):

| Function | Purpose |
|---|---|
| `banker_get_required_deposit_date(@current_date, @num_days_to_usable)` | Business day deposit date calculation: check=3 days, ACH=2 days, cash=0 days; excludes Sat/Sun |
| `banker_get_sum_saved_credit_memos` | Credit memo aggregate summation for available balance |
| `banker_get_sum_saved_invoices_per_program_promo` | Invoice aggregate for available balance |
| `banker_get_sum_saved_usable_payments` | Usable payment aggregate for available balance |
| `banker_get_x_days_payments` | X-day payment window summation |

### 2.2 Citi Direct Banking Integration

| Procedure | Purpose | Notes |
|---|---|---|
| `RSM_CitiDirect_ACH_WithBank` | ACH origination with multi-bank email notification | Hardcoded email addresses; last modified 2019 (Julia Ginzburg/Van Nguyen) |
| `RSM_CitiDirect_Drawdown_WithBank` | Wire drawdown processing | Citi Direct integration |
| `RSM_Wirecard_Fees_ACH` / `RSM_Wirecard_Fees_Drawdown` | Wirecard fee ACH and drawdown | Wirecard-era fee processing |

`RSM_CitiDirect_ACH_WithBank` was modified by four different developers across 2017-2019 (Greg Couto, Nick Doan, Van Nguyen, Julia Ginzburg) — an actively maintained production integration. Email recipient changed from `prod.support.wirecard.com` to `namsupport@wirecard.com` in January 2019.

### 2.3 Prepaid Program Financial Procedures

| Procedure | Purpose |
|---|---|
| `CitiPrepaidONUS_RevCSA_INSERT` / `_RevJobSvc_INSERT` / `_RevOrderSvc_INSERT` | OnUS revenue record insertion |
| `CitiPrepaid_ZeroTotalSOBatch` | Zero-total sales order batch for OnUS programs |
| `PrepaidProgramBankingUpdate` / `PrepaidProgramBankingUpdateAllPrograms` | Banking information maintenance |
| `Prepaid_ONUS_BankInformationExport` | OnUS bank data export |
| `Client_Digital_Invoice` | Digital invoice generation |
| `Account_Balance_Aging` | AR ageing by balance bucket |
| `PP_Batch_Total` / `PP_Remove_History` | Payroll batch totals and history management |

### 2.4 Compliance and Reporting Views

| View | Purpose | Sensitivity |
|---|---|---|
| `VW_MISSING_REFUNDS` | Identifies unfulfilled refund obligations | CRITICAL — Reg E error resolution |
| `VRFMERIDIAN` | Meridian bank transaction verification | HIGH |
| `AR_VIEW` / `ARTOTALVIEW` / `ARVIEW` | AR reporting views | MEDIUM |
| `SOPDETAILVIEW` / `SOPHEADERVIEW` | Sales order views consumed by Finance WebService | MEDIUM |
| `CustomerBalance_w_Address` | Customer balance with address | MEDIUM |
| `rsm_customer_rollup` | Program-to-GFCID mapping | LOW |

---

## 3. Security Posture

| Control | Status | Finding |
|---|---|---|
| TDE | `IsEncryptionOn=False` | UPR payroll data (employee SSN-equivalent, salary) unencrypted at rest |
| Column-level encryption | None | No column encryption on any GP table |
| Named individual user logins | 100+ login definition files in `Security/` | Finance users with direct DB access; no visible offboarding automation |
| `DYNSA` GP superuser | Present in Security scripts | Dynamics GP system superuser — must be managed as privileged account under PAM |
| `ArithAbort=False` | Database-level ANSI setting | Arithmetic errors produce NULL results instead of query failure — silent data errors |
| `AnsiNulls=False` / `QuotedIdentifier=False` | Database-level ANSI settings | Non-standard SQL behaviour; delimited identifier handling differs from ANSI standard |
| FortiDB DAM | `FortiDBRptRole` role defined | Database activity monitoring configured |
| `Banker_execute` service account | Defined in Security scripts | Used by Banker API — confirm minimum privilege scope |
| `ACCTGWF_APP_GRP` | Defined in Security scripts | Accounting Workflow service account |
| `ATLYS_APP_GRP` | Defined in Security scripts | Atlys application reads ECNT program financial data |

**PCI DSS scope**: ECNT is a connected system to the CDE via Banker SVC. The GP database does not store PANs, but `Banker_available_balance` queries `rm00103` (customer balance history) which is in the real-time authorisation path. ECNT is therefore within the CDE-connected system scope under PCI DSS.

**GLBA scope**: `UPR00100` (employee master) and `UPR10400` (payroll transactions) contain US employee PII including SSN-equivalent data, salary, and tax withholding. These are GLBA Non-Public Personal Information (NPI) records. ECNT has no at-rest encryption for this data.

---

## 4. Technical Debt

| Item | File:Line | Impact |
|---|---|---|
| Hardcoded database name in stored procedure | `Banker_available_balance.sql:37` — `from ecnt.dbo.rm00103` | If database is renamed or moved to a linked server, procedure breaks without code deployment; cannot be migrated or cloned without code change |
| Employee PII unencrypted at rest | `ecnt.sqlproj` — `IsEncryptionOn=False`; UPR tables | SSN-equivalent payroll data, salary, tax records stored without TDE; GLBA NPI gap |
| `ArithAbort=False` database setting | `ecnt.sqlproj` | Numeric calculation errors yield NULL silently; financial calculations (GL, payroll) may produce incorrect totals without raising errors |
| `TORN_PAGE_DETECTION` page verify | `ecnt.sqlproj` | Older page integrity method vs. CHECKSUM; reduces reliability of page-level corruption detection |
| `BULK_LOGGED` recovery model | `ecnt.sqlproj` | No point-in-time restore during bulk operations; SOX financial data RPO gap |
| Hardcoded email addresses in procedure body | `RSM_CitiDirect_ACH_WithBank.sql` | Email recipient addresses require code deployment to change; not configuration-table driven |
| 100+ named individual user logins | `Security/` directory | Individual finance users with direct DB access; access does not auto-revoke on employee termination; periodic access review must be manual |
| SQL 2005 compat mode | `ecnt.sqlproj` — `CompatibilityMode=90` | Prevents use of SQL Server features from 2008 onward (windowing functions, filtered indexes, etc.); performance ceiling |
| GP standard tables not abstracted | Direct reads from `rm00103`, `GL10000`, etc. | No API layer between Banker SVC and GP table internals; GP version upgrades may change table structure without warning |
| `DYNSA` superuser in source control | `Security/DYNSA.sql` | GP superuser account definition committed to source control; privileged account management requires PAM integration |
| `DYN_FUNC_*` 100+ decode functions | GP standard install objects in SSDT project | GP decode functions are managed by the GP installer lifecycle; having them in SSDT creates conflict risk during GP version upgrades |

---

## 5. Gen-3 Migration Requirements

| Requirement | Description |
|---|---|
| ERP replacement programme | ECNT cannot be migrated to Gen-3 without a full ERP replacement (e.g., Microsoft Dynamics 365 Business Central or equivalent cloud ERP); this is a multi-year programme |
| Fund Management Service for Banker SVC | `Banker_available_balance` is in the real-time card authorisation path; a Gen-3 Fund Management Service must replace it with equivalent sub-second latency before ECNT can be decommissioned |
| Payroll system migration | US employee payroll (UPR module) must be migrated to a replacement payroll system (ADP, Workday, etc.) with GLBA privacy impact assessment for employee PII migration |
| Banking integration replacement | `RSM_CitiDirect_ACH_WithBank` and `RSM_CitiDirect_Drawdown_WithBank` must be replicated via API-based banking integration (not stored procedure + email) |
| AR/AP migration | All open invoices, credit memos, and payment applications must be migrated or fully reconciled before cutover |
| VW_MISSING_REFUNDS replacement | Reg E missing refund tracking view must be replicated in the Gen-3 platform before cutover; this is a regulatory obligation |
| MERIDIAN bank reconciliation | `VRFMERIDIAN` view functionality must be replicated or replaced |
| SOX ITGC continuity | Gen-3 ERP must have SOX ITGC audit controls in place from the first financial period; mid-year migration creates an audit gap risk |
| Access review and cleanup | All 100+ individual user logins must be reviewed, inactive accounts revoked, and remaining accounts migrated to role-based access in the replacement platform |
| Enable TDE before migration | Employee PII in UPR tables requires encryption at rest under GLBA; TDE should be enabled on ECNT regardless of migration timeline |
| Remove email addresses from stored procedures | Before any environment cloning for Gen-3 testing, hardcoded email addresses in `RSM_CitiDirect_*` procedures must be moved to a configuration table to prevent test environments from sending live bank notifications |
| DS_ETL pipeline updates | `DS_ETL_finance-gp` and `DS_ETL_great-plains` ETL pipelines must be updated for the new ERP data model before ECNT is decommissioned |

---

## 6. Code-Level Risks

| Risk | File:Line | Notes |
|---|---|---|
| Hardcoded DB name in real-time authorisation path | `Banker_available_balance.sql:37` — `from ecnt.dbo.rm00103` | Self-referential four-part name; breaks on database rename, migration to linked server, or Gen-3 platform |
| `ArithAbort=False` affecting financial calculations | `ecnt.sqlproj` | GP financial calculations in GL, payroll, and AR may silently return NULL on arithmetic errors instead of failing visibly; SOX financial reporting integrity risk |
| Email addresses embedded in banking procedures | `RSM_CitiDirect_ACH_WithBank.sql` | Any environment clone (dev, QA) that executes this procedure will send emails to live bank partners unless procedure body is manually modified before deployment |
| `BULK_LOGGED` during period-end close | `ecnt.sqlproj` | If bulk operations are used during GP period-end posting, point-in-time restore is unavailable for that window; SOX RPO gap |
| Direct GP table access without abstraction | `Banker_available_balance.sql` reads `rm00103` directly | GP table structure is version-specific to the installed GP release; no API contract; GP upgrade could silently break `Banker_available_balance` |
| `DYNSA` GP superuser not under PAM | `Security/DYNSA.sql` | GP superuser account with unrestricted access to all GP data including payroll; not visible in any PAM-gated access pattern in source |
