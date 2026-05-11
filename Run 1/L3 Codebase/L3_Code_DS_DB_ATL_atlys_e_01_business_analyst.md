# Business Analyst Analysis — DS_DB_ATL_atlys_e (atlys_e)

## Repository Identity
- **Database name:** atlys_e
- **Project GUID:** fa57385d-f84d-4d10-a5d6-61e4cb09d32a
- **SQL Server compatibility:** level 90 (SQL Server 2005 target), deployed via SSDT project type `Sql100DatabaseSchemaProvider` (SQL 2008 R2 provider)
- **Collation:** SQL_Latin1_General_CP1_CI_AS

---

## Business Purpose

`atlys_e` is the **shared entity and authentication hub** for the entire Atlys financial-reporting platform. Every other Atlys database (`atlys_fc_nca`, `atlys_fc_nus`, `atlys_fccr`, `atlys_rv_nca`, and sibling regional databases not in this batch) depends on it for cross-cutting reference data. It performs three distinct business functions:

1. **Identity and access control** — it is the only database that stores Atlys application users (`tblUsers`), user groups (`tblUserGroups`), and per-group right assignments (`tblUserGroupRights`, `tblUserRightTypes`). No other Atlys database maintains its own user store; they call back into `atlys_e` via three-part names (e.g., `ATLYS_E.dbo.sys_chkuser`).

2. **Global reference data** — it maintains the canonical lookup tables for companies (`tblCompanies`), countries (`tblCountries`), currencies (`tblCurrencies`), exchange rates (`tblExchRates`, `tblFCExchRates`), regions (`tblRegions`), card-program BIN prefixes (`tblPrgPrefixes`), and the transaction-system registry (`tblTxInstances`, `tblSystems`, `tblInterfaces`, `tblPaths`).

3. **Sales and relationship management scaffolding** — it records sales representatives (`tblSalesReps`), relationship managers (`tblRelMgrs`), and account managers (`tblAcctMgrs`), which are FK-referenced by every fee-calculation and reward-value database when associating a program with its commercial owner.

---

## Processes Supported

### User Authentication and Authorisation
The `tblUsers` table stores hashed passwords (`pwd VARBINARY(256)`) using the legacy SQL Server `PWDENCRYPT()` function, which is invoked by the `trgUsers` trigger (`tblUsers.sql` lines 35–43). A user-facing password-policy function `sys_chkpwd` (`dbo/Functions/sys_chkpwd.sql`) enforces a minimum of 8 characters with at least one alpha and one numeric character. The function `sys_chkuserrights` and stored procedure `sys_userrights` enforce object-level access checks before other databases expose data to the application layer.

### Company Registry and Cross-Database Routing
`tblCompanies` (`dbo/Tables/tblCompanies.sql`) maps each legal-entity company to its associated fee-calculation database (`fc_db_name NVARCHAR(256)`) and reward-value database (`rev_db_name NVARCHAR(256)`). This is the central routing table: when a user selects a company in the Atlys UI, the application reads these columns to determine which regional satellite database to query. A CHECK constraint (`CK_tblCompanies_db`, line 20) validates that referenced database names actually exist on the server at the time of insert/update, using `DB_ID()`. The `gp_db_name` column points to the Great Plains (Microsoft Dynamics GP) general ledger database for that entity.

### Exchange Rate Management
`tblExchRates` and `tblFCExchRates` hold actual and forecast exchange rates respectively. Functions `sys_exchrates`, `sys_exchrates_actual`, `sys_exchrates_fc`, and `sys_exchrates_p` provide parameterised lookups used by fee-calculation procedures across all satellite databases when converting monetary amounts to a reporting currency.

### Internal Messaging
`tblMsgs`, `tblMsgsTo`, and `tblMsgsRefTypes` implement a lightweight in-application notification system used for workflow alerts (e.g., program review reminders). Views `vMsgsInbox` and `vMsgsSent` expose inbox and sent-mail perspectives. The `sys_msgs` stored procedure handles message CRUD operations.

### Reporting Cross-Tab Engine
`sys_cross_tab` and `sys_cross_tab1` (`dbo/Stored Procedures/`) are a general-purpose dynamic pivot engine consumed by every reporting procedure across all Atlys satellite databases. They accept table names, column expressions, grouping strings, and date ranges as parameters, dynamically construct `SELECT … EXEC sp_executesql` chains, and return pivoted month-column result sets.

### Client Refund Integration
`client_refund_get_gp_database` (`dbo/Stored Procedures/`) maps a client identifier to its GP database name, supporting client refund workflows that originate in external systems and need to resolve the correct GP instance.

---

## Regulatory Relevance

### PCI DSS
`atlys_e` does not directly store Primary Account Numbers (PANs), CVVs, or track data. The `bin` column present in downstream `cursforecast` tables appears here only in the `tblPrgPrefixes` table, which stores BIN range metadata (prefix strings, not live card numbers). However, `atlys_e` **indirectly scopes into the CDE** because:
- It stores application user credentials (`tblUsers.pwd`) used to access Atlys systems that process fee data derived from cardholder transaction volumes.
- The `PWDENCRYPT()` hashing function is deprecated and is not a PCI-approved cryptographic algorithm. Under PCI DSS v4.0.1 Requirement 8.3, passwords protecting access to systems in or connected to the CDE must be protected with strong cryptography.
- The `sys_chkstr` function (`dbo/Functions/sys_chkstr.sql`) is used as a SQL-injection guard in dynamic SQL procedures; its presence indicates awareness of injection risk but does not guarantee full parameterisation coverage.

### NACHA / Reg E
`atlys_e` does not contain ACH origination data or electronic funds transfer records. However, the company and transaction-instance registries it maintains (`tblCompanies`, `tblTxInstances`) are referenced when ACH-related disbursement programs are configured in satellite databases, making atlys_e a supporting system for NACHA-governed workflows.

### GLBA / SOC
As the authentication database for the Atlys application, `atlys_e` holds personal data (user names, email addresses in `tblUsers`) and is subject to GLBA safeguards requirements for data held in the production environment. Audit trails for user changes are not visible in this codebase; the `combine_dtl` and `combine_log` tables (`atlys_e.sqlproj` lines 129–134) appear to be data-combination/consolidation tables that may carry change history, but their DDL was not available in the analysed files.

---

## Key Business Entities and Their Relationships

| Entity | Table | Business Role |
|---|---|---|
| Application user | `tblUsers` | Atlys UI login identity |
| User group | `tblUserGroups` | Role-based access tier |
| User rights | `tblUserGroupRights` | Object-level permission grants |
| Company | `tblCompanies` | Legal entity, links to FC/RV databases |
| Country | `tblCountries` | ISO country reference |
| Currency | `tblCurrencies` | ISO currency reference |
| Exchange rate | `tblExchRates` / `tblFCExchRates` | Actual / forecast FX |
| Region | `tblRegions` | Sales territory grouping |
| Sales rep | `tblSalesReps` | Commercial owner of a program |
| Relationship manager | `tblRelMgrs` | Client relationship owner |
| Account manager | `tblAcctMgrs` | Account management owner |
| BIN prefix | `tblPrgPrefixes` | Card programme BIN range metadata |
| Transaction instance | `tblTxInstances` | Processing system reference |
| Interface | `tblInterfaces` | GL interface reference |
| Path | `tblPaths` | File system / SSAS cube paths |
| Message | `tblMsgs` / `tblMsgsTo` | Internal notification |

---

## Summary Assessment

`atlys_e` is a foundational dependency for the entire Atlys platform. Any disruption to it (schema changes, access outages, or credential compromise) cascades to all fee-calculation and reward-value databases. Business continuity and PCI access-control obligations both point to this database as the highest-priority hardening target in the Atlys tier.
