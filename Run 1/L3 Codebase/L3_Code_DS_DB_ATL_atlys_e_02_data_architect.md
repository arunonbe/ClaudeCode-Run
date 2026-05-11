# Data Architect Analysis — DS_DB_ATL_atlys_e (atlys_e)

## Database Configuration (from atlys_e.sqlproj)

| Property | Value |
|---|---|
| Compatibility mode | 90 (SQL Server 2005) |
| Default collation | SQL_Latin1_General_CP1_CI_AS |
| Recovery model | BULK_LOGGED |
| Page verify | CHECKSUM |
| Snapshot isolation | OFF |
| Read committed snapshot | OFF |
| Encryption at rest (TDE) | `<IsEncryptionOn>False</IsEncryptionOn>` — **NOT ENABLED** |
| Parameterisation | SIMPLE |
| Trustworthy | False |
| Change tracking | OFF |
| Service broker | Disabled |

---

## Tables (DDL sourced from `dbo/Tables/`)

### tblUsers (`dbo/Tables/tblUsers.sql`)
| Column | Type | Notes |
|---|---|---|
| id | INT IDENTITY | Surrogate PK |
| uid | VARCHAR(15) | Application username — **SENSITIVE: login identity** |
| pwd | VARBINARY(256) | Password hash via PWDENCRYPT() — **SENSITIVE: credential** |
| uname | VARCHAR(50) | Display name |
| nuname | NVARCHAR(50) | Unicode display name |
| email | VARCHAR(100) | User email address — **SENSITIVE: PII** |
| group_id | SMALLINT | FK → tblUserGroups |
| inv_logins | TINYINT | Invalid login counter |
| preset | DATETIME | Password reset timestamp |
| enabled | TINYINT | Account active flag |

**Indexes:** Clustered on `uid`; unique non-clustered on `id INCLUDE(uname, group_id)`.  
**Trigger:** `trgUsers` — fires on INSERT/UPDATE. Re-hashes password using `PWDENCRYPT(CAST(pwd AS varchar))` when `pwd` column is updated (lines 35–43). Also cascades username changes to `tblSalesReps`, `tblRelMgrs`, `tblAcctMgrs`.  
**Sensitive data flag:** CRITICAL — stores application credentials. The `pwd` column is hashed but with a deprecated, non-NIST-approved algorithm.

### tblUserGroups (`dbo/Tables/tblUserGroups.sql`)
Role container. Referenced by `tblUsers.group_id`. Determines which group-level rights are applied.

### tblUserGroupRights (`dbo/Tables/tblUserGroupRights.sql`)
Maps user groups to right types — implements row-level permission grants for the Atlys application.

### tblUserRightTypes (`dbo/Tables/tblUserRightTypes.sql`)
Enumeration of application right types (e.g., read, write, approve).

### tblUsersC, tblUsersR, tblUsersS (`dbo/Tables/`)
Supplemental user attribute tables (configuration `C`, regional `R`, settings `S`). The `trgUsers` trigger updates `tblUsersS.enabled` when `tblUsers.enabled` changes.

### tblCompanies (`dbo/Tables/tblCompanies.sql`)
| Column | Type | Notes |
|---|---|---|
| id | SMALLINT IDENTITY | Surrogate key |
| co_name | VARCHAR(200) | Business name — PK (clustered on id, PK on co_name) |
| fc_db_name | NVARCHAR(256) | Fee-calculation database name |
| rev_db_name | NVARCHAR(256) | Reward-value database name |
| currency | VARCHAR(5) | FK → tblCurrencies |
| le_country_code | VARCHAR(4) | FK → tblCountries |
| glinterface | SMALLINT | FK → tblInterfaces |
| txinstance | TINYINT | FK → tblTxInstances |
| gp_db_name | NVARCHAR(256) | Great Plains GL database |
| cube1_name, cube2_name | NVARCHAR(128) | SSAS cube names |

**CHECK constraint** validates that referenced databases exist on the server at row-write time — creates fragility during migrations.

### tblCountries / tblCountriesC
ISO country codes and display metadata.

### tblCurrencies
ISO 4217 currency codes.

### tblExchRates / tblFCExchRates
Actual and forecast foreign exchange rates. `tblFCExchRates` stores forward-looking rates used in fee forecasting.

### tblRegions / tblRegionsC
Sales territory groupings. `tblRegionsC` stores additional region configuration/metadata.

### tblSalesReps / tblSalesRepsC / tblSalesRepsV
Sales representative master records. `tblSalesReps.user_id` FK to `tblUsers.id`. Auto-managed by `trgUsers` trigger.

### tblRelMgrs / tblRelMgrsC / tblRelMgrsV
Relationship manager records. Same trigger-managed FK pattern as sales reps.

### tblAcctMgrs / tblAcctMgrsC / tblAcctMgrsV
Account manager records.

### tblPrgPrefixes
BIN prefix ranges for card programs. Columns include prefix string and range boundaries. Referenced by `sys_prefix_ranges` function. **Potential indirect CDE scope** — BIN data, even without full PANs, can indicate network membership.

### tblSystems
Processing system registry (e.g., the card processing or reward platform identifier).

### tblTxInstances
Transaction-processing system instances. FK target from `tblCompanies.txinstance`.

### tblInterfaces
GL interface definitions. FK target from `tblCompanies.glinterface`.

### tblPaths / tblPathTypes
File system and SSAS cube path registry. Used by the dormancy/maintenance calculation code in satellite databases to locate SSAS cube folders (e.g., `sys_vPaths` in `atlys_fc_nca/sys_calc_dormancy.sql` at line 48).

### tblMsgs / tblMsgsTo / tblMsgsRefTypes
Internal workflow notification tables.

### combine_dtl / combine_log
Data combination/consolidation tables — DDL present in project but individual SQL files not surfaced in this analysis. Likely used for cross-database data rollup.

---

## Views (from atlys_e.sqlproj `<Build>` elements)

| View | Purpose |
|---|---|
| vUsers, vUsersA, vUsersC, vUsersE, vUsersLoggedIn, vUsersR | User perspectives — `vUsersLoggedIn` flags active sessions |
| vCompanies, vCompany | Company lookups |
| vAcctMgrs, vAcctMgrsC, vAcctMgrsR, vAcctMgrsV | Account manager perspectives |
| vRelMgrs, vRelMgrsC, vRelMgrsR, vRelMgrsV | Relationship manager perspectives |
| vSalesReps, vSalesRepsC, vSalesRepsR, vSalesRepsV | Sales rep perspectives |
| vCountries, vCountriesC | Country lookups |
| vCurrencies | Currency lookup |
| vExchRates, vExchRatesP | Exchange rate actual and period views |
| vRegions | Region lookup |
| vPrgPrefixes | BIN prefix lookup |
| vEC_Programs_CardType | Card type dimension |
| vInterfaces | Interface lookup |
| vPaths | Path lookup |
| vSystems | System registry |
| vTxInstances | Transaction instance lookup |
| vMsgs, vMsgsInbox, vMsgsSent | Messaging |
| vUserGroupRights, vUserGroups, vUserRightTypes | Access control |

---

## Functions (from atlys_e.sqlproj `<Build>` elements)

| Function | Purpose |
|---|---|
| sys_chkpwd | Password-policy validator |
| sys_chkuser | User-existence check |
| sys_chkuserrights | User rights validator |
| sys_chkaccess | Access check |
| sys_chkacctmgr / sys_chkrelmgr / sys_chksalesrep | Role-membership checks |
| sys_chkls | Linked-server availability check |
| sys_chkpath | Path validity check |
| sys_chkstr | SQL-injection guard (string sanitisation) |
| sys_chkuserexchrates | Exchange rate access check |
| sys_exchrates, sys_exchrates_actual, sys_exchrates_fc, sys_exchrates_p | FX rate lookups |
| sys_cinfo / sys_cinfodb / sys_companyinfo / sys_compinfodb | Company info retrievers |
| sys_aggr / sys_aggr_date / sys_aggrt / sys_aggrt2 | Aggregate helpers |
| sys_convert_formula | Formula-string converter |
| sys_dbnm | Database name resolver |
| sys_lsinfo / sys_lsinfodb | Linked-server info |
| sys_prefix_ranges | BIN prefix range resolver |
| sys_sqlstr | SQL string formatter |
| sys_prgmark | Program marker |
| sys_regioncinfo | Region info |
| sys_cubecinfo / sys_cubedateformat / sys_cubelsinfo | SSAS cube helpers |
| sys_ctcol / sys_clist | Column-list utilities |
| sys_getusergroup / sys_getuserinfo / sys_getuser | User info getters |
| sys_vPaths / sys_vAcctMgrsC / sys_vAcctMgrsV / sys_vRelMgrsC / sys_vRelMgrsV / sys_vSalesRepsC / sys_vSalesRepsCm / sys_vSalesRepsV / sys_vUserRights | Inline TVF wrappers for views |
| sys_msgto / sys_msgtoid | Message-to resolver |
| sys_stralpha | Alpha string extractor |
| sys_num | Numeric converter |

---

## Stored Procedures

| Procedure | Purpose |
|---|---|
| sys_user | User CRUD |
| sys_userrights | Rights management |
| sys_companies | Company management |
| sys_countries | Country lookup |
| sys_currencies | Currency lookup |
| sys_regions | Region management |
| sys_sales_reps | Sales rep management |
| sys_rel_managers | Relationship manager management |
| sys_acct_managers | Account manager management |
| sys_prefixes | BIN prefix management |
| sys_txinstances | Transaction instance management |
| sys_interfaces | Interface management |
| sys_exchrates_fcv / sys_exchrates_update | Exchange rate management |
| sys_msgs | Message management |
| sys_newcompany | Company creation wizard |
| sys_cross_tab / sys_cross_tab1 | Dynamic pivot report engine |

---

## Sensitive Data Fields — Summary

| Field | Table | Classification | PCI / Regulatory Flag |
|---|---|---|---|
| `uid` | tblUsers | Login identity | PCI Req 8 — user identity |
| `pwd` | tblUsers | Password hash | PCI Req 8.3 — credential must use strong cryptography; PWDENCRYPT() is deprecated SHA-1 based |
| `email` | tblUsers | PII | GLBA / CCPA |
| `uname` | tblUsers | PII | GLBA |
| `co_name` | tblCompanies | Business entity name | Sensitive business data |
| `fc_db_name`, `rev_db_name`, `gp_db_name` | tblCompanies | Database connection topology | Infrastructure disclosure risk |
| BIN prefix columns | tblPrgPrefixes | Card network BIN | Indirect CDE scope |

---

## PCI DSS CDE Scope Assessment

`atlys_e` does not store full PANs or SAD. However, it is **in-scope as a connected system** under PCI DSS v4.0.1 because:
1. It authenticates users of all Atlys databases, some of which may process or display transaction-level financial data.
2. The `tblPrgPrefixes` table holds BIN range data that, while not a full PAN, relates to card programmes.
3. Cross-database calls from fee-calculation databases use three-part names resolved at runtime, making `atlys_e` a network-reachable component from CDE-adjacent systems.

**Assessment: Connected-system scope. Subject to PCI DSS network segmentation, access control, and vulnerability management requirements.**

---

## Encryption at Rest

`<IsEncryptionOn>False</IsEncryptionOn>` — Transparent Data Encryption (TDE) is **not enabled** in the project definition. Passwords in `tblUsers.pwd` are hashed (not plaintext) but the hashing algorithm (`PWDENCRYPT`, based on SHA-1 with a salt) is insufficient for PCI compliance per current standards. No column-level encryption is observed for any sensitive fields.

---

## Data Retention

No explicit data retention or purge procedures are visible in the codebase. The `combine_log` table suggests some archival activity occurs. Retention policy for user records, exchange rate history, and messaging data is not defined in code and should be governed by a formal data classification policy.
