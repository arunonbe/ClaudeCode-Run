# Data Architect Report — DS_DP_db08

## Repository Identity

**Repository:** DS_DP_db08  
**Database Engine:** Microsoft SQL Server (version inferred: SQL Server 2014–2019 based on script features)  
**Schema topology:** Multi-database shard — single SQL Server instance hosting logically separate databases

---

## Database Object Inventory

### DBAdmin Database

| Object | Type | Purpose |
|---|---|---|
| `dbo.Audit_blocked_ip_user` | Table (DDL in repo) | Audit log for login attempts blocked by the IP-allowlist trigger. Columns: `created` (datetime), `IP_Address` (varchar 48), `Host_Name` (nvarchar 256), `Original_Login` (nvarchar 256), `Program_Name` (nvarchar 256). Index: `IX_Audit_blocked_ip_user_created` on `created` ASC. |
| `dbo.enabled_production_jobs` | Table (referenced, not created here) | Stores names of SQL Agent jobs enabled in production; consumed by DR enablement scripts |

**Source:** `20200917_WDNAMCBTS-517_001_DBAdmin.Audit_blocked_ip_user.sql`, lines 6–19

### master Database

| Object | Type | Purpose |
|---|---|---|
| `TR_check_ip_address_functional_user` | LOGON Trigger (ALL SERVER) | Blocks service account logins from IPs not in `ValidIPAddress` table; logs blocked attempts to `DBAdmin.dbo.Audit_blocked_ip_user`. Executes as `sa`. |
| `usernames_functional_accounts` | Table (referenced) | List of functional account usernames subject to IP restriction |
| `ValidIPAddress` | Table (referenced) | Allowlist of approved source IP addresses |

**Source:** `20200917_WDNAMCBTS-517_002_master.TR_check_ip_address_functional_user.sql`, lines 14–55

### Banker Database

| Object | Type | Purpose |
|---|---|---|
| `dbo.SSISJobConfigurations` | Table | Stores XML job parameters for SSIS-driven batch jobs. The `JobParameters` column is typed as `xml`. Used by SO Automation, Fee Invoicing, Void, and other pipelines. |

**Columns referenced:**
- `Name` — job identifier (e.g., `'SO Ordersvc'`)
- `JobParameters` (xml) — serialised XML including `<CertThumbprint>`, `<FinanceWSURL>`, SMTP settings, email addresses

**Source:** `20191019_NATS-5490_UpdateCert_in_Banker_SSISJobConfigurations.sql`, lines 1–6; `20201106_SQ-124-update-Banker.SSISJobConfigurations.sql`

### ECNT Database (eCount North America — US GP ledger)

| Object | Type | Purpose |
|---|---|---|
| `dbo.PrepaidBankInformation` | Table | Bank and email configuration for prepaid card invoicing. Contains `FromEmailAddress`, `EmailSubject`, `CompanyName`, `ProdSupportEmailAddress`. Extended with additional columns (SQ-137). |
| `dbo.RM00101` | Table (GP) | GP Receivables Master — Customer records with `BANKNAME`, `CUSTNMBR` fields. Contains bank affiliation data. |
| `dbo.ASITables` | Table (referenced) | Atlys ASI configuration tables updated during SQ-543 |
| GP Sales / Journal tables | Tables (referenced) | GP work tables for sales transaction entries and journal entries subject to periodic deletion/correction |

**Source:** `20200630_NAMDATASVC-2310_UpdateBankInfo.sql`; `20201027_SQ-543-003-Update-ECNT.ASITables.sql`

### ECAN Database (eCount Canada)

Same logical schema as ECNT but for Canadian entities. Tables `ASITables`, `PrepaidBankInformation`, `RM00101` mirror the ECNT equivalents.

### ATLYS_* Databases (Revenue and Forecast Reporting)

The Atlys family comprises 7 databases accessed in this shard:

| Database | Meaning |
|---|---|
| `ATLYS_E` | Atlys Enterprise (primary reporting hub) |
| `ATLYS_Fc_NCA` | Forecast — North America Canada |
| `ATLYS_Fc_NUS` | Forecast — North America US |
| `ATLYS_FcCR` | Forecast — (variant) |
| `ATLYS_Rv_NCA` | Revenue — North America Canada |
| `ATLYS_Rv_NUS` | Revenue — North America US |
| `ATLYS_RvCR` | Revenue — (variant) |

Commonly referenced objects:
- Settings tables (updated with cost allocation, emboss rates)
- Period/controls tables (invoicing period status, actuals date)
- GP comparison report description tables
- Replication articles (`20210513_SQ-3032_DB08 add tables to replication.sql` adds tables to transactional replication)

### AcctgWf Database
Referenced only in audit access grants. Hosts accounting workflow data.

### DYNAMICS Database
Microsoft Dynamics GP system database; BakerTilly auditors given `db_datareader` access.

---

## Sensitive Data Identification

### Financial / Bank Data — MODERATE SENSITIVITY
| Table | Column(s) | Sensitivity | PCI / Regulatory Flag |
|---|---|---|---|
| `ECNT.dbo.PrepaidBankInformation` | `FromEmailAddress`, `CompanyName`, bank config | Low–Medium | GLBA — financial institution data |
| `ECNT.dbo.RM00101` | `BANKNAME`, `CUSTNMBR` | Medium | GLBA — customer bank assignment |
| `ECAN.dbo.RM00101` | Same | Medium | GLBA |
| `Banker.dbo.SSISJobConfigurations` | `JobParameters` XML | Medium–High | Contains certificate thumbprints, SMTP hosts, URLs — treat as configuration secrets |

### Card-Adjacent Data — REVIEW REQUIRED
The `CUSTNMBR` values like `'04012311%'` and `'04016333%'` in `ECNT.dbo.RM00101` (source: `20200630_NAMDATASVC-2310_UpdateBankInfo.sql`, line 7) resemble **BIN-like prefixes** (6-to-8 digit patterns). If `CUSTNMBR` stores card BINs or masked account numbers, this table enters **PCI DSS CDE scope** under Requirement 3. This requires a formal data classification review by the Data Governance / Security team.

**No full PANs (Primary Account Numbers), CVVs, or PINs were observed in any script in this repository.** Sensitive Authentication Data (SAD) does not appear to be stored in these operational tables.

### Audit Data
`DBAdmin.dbo.Audit_blocked_ip_user` stores IP addresses and login names, which are personal data under GDPR/CCPA if they identify individuals. Retention is 90 days (weekly cleanup job).

---

## ETL / Data Flow Patterns

This repo does not contain SSIS packages. Instead, it manages **configuration data consumed by SSIS packages** running in the separate `DS_DB_dtsx` or `DS_DP_*` pipeline projects. The `Banker.dbo.SSISJobConfigurations` table is the runtime configuration store.

Data flows through this shard in the following directions:
- **Inbound:** GP journal entries posted from upstream GP processes, CCP card transactions replicated via transactional replication
- **Outbound:** Atlys reporting databases read from ECNT/ECAN via linked server or direct query; accounting workflow reads from AcctgWf
- **Replication:** `20210513_SQ-3032` adds tables to transactional replication, indicating the shard participates in SQL Server replication topology (publisher role)

---

## Encryption and Data Protection

### In Transit
- `Banker.dbo.SSISJobConfigurations` contains a `CertThumbprint` XML element (updated in `20191019_NATS-5490` and `20210923_NATS-12287`). This governs TLS certificate binding for a Finance web service endpoint, indicating encrypted transport to that service.
- SMTP connections referenced in SSISJobConfigurations use the internal relay `nl-smtp-01.nam.wirecard.sys` / SMTP server updated over time. No TLS enforcement is visible at the configuration level stored in this repo.

### At Rest
No Transparent Data Encryption (TDE) configuration is present in this repository. TDE status of the underlying SQL Server instances cannot be confirmed from this repo alone.

### Access Control
- Windows Authentication is used for all database access (no SQL logins created in scripts other than the `NAM\BakerTilly_Auditors` Windows group login)
- Role-based access: auditors receive `db_datareader` only; `GRANT VIEW DEFINITION ON SCHEMA` granted selectively to allow schema inspection without data access

---

## Schema Evolution Notes

The repository covers approximately 28 months of changes (October 2019 – March 2022). Key schema evolution events:

1. **Oct 2019:** BakerTilly audit access provisioning across 11 databases
2. **Sep 2020:** IP-allowlist LOGON trigger and audit table introduced (WDNAMCBTS-517)
3. **Oct 2020:** ASI table updates for new prepaid programs (SQ-543)
4. **Dec 2020:** `PrepaidBankInformation` schema extended with new columns (SQ-137)
5. **Jan 2021:** Same Day ACH transaction codes added (SQ-456)
6. **May 2021:** Tables added to replication (SQ-3032)
7. **Jul 2021:** Same Day ACH cost allocation method added (SQ-4056)
