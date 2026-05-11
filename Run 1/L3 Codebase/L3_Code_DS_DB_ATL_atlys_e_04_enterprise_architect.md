# Enterprise Architect Analysis — DS_DB_ATL_atlys_e (atlys_e)

## Platform Generation

`atlys_e` belongs to the **Atlys** financial-reporting and revenue-management platform, which is an internal Onbe business intelligence and fee-forecasting system. Based on:
- SSDT project compatibility mode 90 (SQL Server 2005 target)
- SSDT provider `Sql100DatabaseSchemaProvider` (SQL Server 2008 R2 tooling)
- Legacy `PWDENCRYPT()` password hashing (deprecated since SQL Server 2012)
- No modern DevSecOps tooling
- Change-log comments referencing ticket IDs from 2021 (e.g., `SQ-2389`, `SQ-2970` in `sys_calc_dormancy.sql`)

…this platform is likely **12–18 years old** in its core design, with incremental feature additions continuing through at least 2021. It predates current Onbe cloud-native infrastructure and represents a **legacy on-premises or IaaS SQL Server deployment**.

---

## Role in Atlys Architecture

`atlys_e` occupies the **hub position** in a hub-and-spoke database architecture:

```
                    ┌─────────────────────────────────┐
                    │           atlys_e               │
                    │  (entity hub, auth, reference)  │
                    └─────────────┬───────────────────┘
          ┌──────────────────┬────┴─────────────┬──────────────────┐
          │                  │                   │                  │
   atlys_fc_nca        atlys_fc_nus        atlys_fccr        atlys_rv_nca
   (FC NCA region)     (FC US region)      (FC credit)       (RV NCA region)
```

All satellite databases call `ATLYS_E.dbo.*` functions and stored procedures directly using three-part names. This is confirmed by:
- `sys_copy_table_data.sql` (atlys_fc_nca): `ATLYS_E.dbo.sys_chkstr(@table)` — line 19
- `sys_calc_dormancy.sql` (atlys_fc_nca): `ATLYS_E.dbo.sys_aggr_date(...)` — line 191, `ATLYS_E.dbo.sys_cinfo(...)` — line 50, `ATLYS_E.dbo.sys_aggrt(...)` — line 214, `ATLYS_E.dbo.sys_vPaths(...)` — line 48
- `sys_getvECBR1.sql` (atlys_rv_nca) also contains cross-database references.

This tightly couples all databases to the name `ATLYS_E`. Any rename or migration of the entity hub database requires updating every cross-database reference in every satellite, making this a **high migration-complexity dependency**.

---

## Dependencies (Outbound from atlys_e)

### Great Plains (Microsoft Dynamics GP)
`tblCompanies.gp_db_name` stores GP database names, and `client_refund_get_gp_database` returns these for external callers. The Atlys platform is therefore integrated with GP as an ERP general ledger system.

### SSAS (SQL Server Analysis Services)
`tblPaths`, `sys_cubecinfo`, `sys_cubedateformat`, `sys_cubelsinfo`, and `tblCompanies.cube1_name` / `cube2_name` reveal that the platform connects to SSAS cubes for actual maintenance-fee data retrieval (see `sys_calc_dormancy.sql` in atlys_fc_nca: `dbo.sys_execcview`). This creates a dependency on a configured SSAS instance accessible via linked server.

### Linked Servers
`sys_chkls` (check linked server) and `sys_lsinfo` / `sys_lsinfodb` functions exist specifically to test linked-server availability. This suggests multiple linked-server dependencies for cross-instance queries, particularly for the GP and SSAS integrations.

### External Monitoring (FortiDB, GTS)
`FortiDBRptRole.sql` and `NAM_GTS_gpatmon.sql` indicate FortiDB Database Activity Monitoring and GTS (Global Technology Services) monitoring are connected to this database.

---

## Dependencies (Inbound — databases that consume atlys_e)

| Consuming database | Evidence |
|---|---|
| atlys_fc_nca | `ATLYS_E.dbo.sys_chkstr`, `ATLYS_E.dbo.sys_aggr_date`, `ATLYS_E.dbo.sys_cinfo`, `ATLYS_E.dbo.sys_vPaths`, `ATLYS_E.dbo.sys_aggrt` |
| atlys_fc_nus | Same pattern (identical stored procedure set) |
| atlys_fccr | Same pattern |
| atlys_rv_nca | `ATLYS_E.dbo.*` cross-database calls in function definitions |
| ACCTGWF_APP_GRP consumers | `ACCTGWF_APP_GRP` is granted `SELECT` on `tblCompanies`, `tblUsers`, `tblUserGroups` — suggests an accounting workflow application reads atlys_e directly |

---

## Architecture Observations

### Single Point of Failure
All Atlys satellite databases fail gracefully or completely when `atlys_e` is unavailable. There is no fallback or cache for authentication, company routing, or exchange rates. High-availability configuration (Always On Availability Groups, mirroring, or log shipping) for `atlys_e` is critical and should be verified.

### Cross-Database Three-Part Name Coupling
The use of hard-coded three-part database names (`ATLYS_E.dbo.*`) in stored procedures across all satellite databases means:
1. The database must be named exactly `ATLYS_E` on any target server.
2. There is no abstraction layer (e.g., synonyms, linked server aliases) documented in these repos.
3. A failover to a secondary server with a different naming convention would require code changes.

### No API Layer
Atlys appears to be a **thick-client** application accessing the database directly via ADO.NET or similar. There is no REST API or service layer — the stored procedures and functions are the API surface. This architecture pattern is common in older financial reporting platforms but creates challenges for modern integration patterns.

### Multi-Region Design
The existence of separate `_nca`, `_nus` suffix databases for fee calculation and reward value indicates a **region-partitioned data model** where each legal entity's data is isolated in a separate database rather than tenant-discriminated by a column. This simplifies data residency but multiplies schema management overhead.

---

## Migration Complexity Assessment

| Migration scenario | Complexity |
|---|---|
| SQL Server in-place upgrade (e.g., 2019 → 2022) | Low — code changes minimal, test stored procedures with new compat level |
| Rename `ATLYS_E` database | Very High — all cross-database calls in all satellite databases must be updated; no synonym abstraction exists |
| Migrate to Azure SQL Database | Very High — Azure SQL does not support cross-database three-part names or linked servers in the traditional sense; all satellite databases would need connection pooling redesign |
| Migrate to Azure SQL Managed Instance | Medium — three-part names and linked servers are supported; but SSAS integration would need Azure Analysis Services equivalent |
| Extract authentication to Azure Entra ID / Azure AD | High — custom `PWDENCRYPT` auth must be replaced; application login flow must change |
| Containerise (SQL Server on Docker/Kubernetes) | Medium — feasible for a single-instance dev/test; production HA requires SQL Server Always On in containers |

---

## Technology Currency

| Component | Current state | Recommended state |
|---|---|---|
| SQL Server compat level | 90 (SQL 2005) | 150+ (SQL 2019) |
| Password hashing | PWDENCRYPT (SHA-1 deprecated) | Application-managed bcrypt/Argon2 or Azure AD auth |
| Recovery model | BULK_LOGGED | FULL |
| TDE | Disabled | Enabled |
| CI/CD | None | Azure DevOps with SqlPackage publish |
| SSAS integration | On-premises SSAS | Azure Analysis Services or Power BI Premium |
| Monitoring | FortiDB DAM (partial) | Full SIEM integration |
