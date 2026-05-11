# Enterprise Architect Analysis — DS_DB_ATL_atlys_fc_nca (atlys_fc_nca)

## Platform Generation

`atlys_fc_nca` is the same generation as `atlys_e` — a 12–18-year-old SSDT database project in the Atlys platform. The presence of 2021-era change comments (`SQ-2389`, `SQ-2970` in `sys_calc_dormancy.sql`) confirms active development continued at least to 2021, meaning this is a live production system receiving maintenance updates on legacy foundations.

---

## Role in Atlys Architecture

`atlys_fc_nca` is the **NCA regional fee-calculation satellite** in the Atlys hub-and-spoke architecture. Its specific role is to:
1. Maintain programme fee and behavioural assumptions for North/Central America programs.
2. Execute the financial calculation engine (dormancy, issuance, interchange, commission, recurring).
3. Provide pivoted reporting data to the Atlys UI for the NCA portfolio.
4. Feed amortisation entries to the Great Plains GL system via data produced by `sys_amortization_rev_post` and `sys_amortization_issuance_post`.

It is one of at least two parallel fee-calculation databases for the same platform:
- `atlys_fc_nca` — North/Central America
- `atlys_fc_nus` — United States (separate regional instance)

The existence of both NCA and NUS databases suggests that programs are partitioned by geography, and the NUS database may represent a subset or different regulatory variant of the NCA portfolio.

---

## Dependencies (Outbound)

### atlys_e (Hard Dependency)
All cross-database calls are to `ATLYS_E.dbo.*`. See `sys_calc_dormancy.sql`, `sys_copy_table_data.sql`, and the extensive use of `ATLYS_E.dbo.sys_aggrt`, `sys_aggrt2`, `sys_aggr_date`, `sys_cinfo`, `sys_vPaths`. If `atlys_e` is unavailable, all calculation and reporting procedures in this database will fail.

### SSAS (Microsoft Analysis Services)
`sys_calc_dormancy.sql` calls `ATLYS_E.dbo.sys_cinfo(1, @c_id)` to obtain a connection reference, then executes `sys_execcview` against a cube-based view (`vRevenueT_MaintFees_PrgId`) to retrieve actual historical maintenance fee data. This means the dormancy calculation depends on a live SSAS connection. The SSAS connection is conditionally accessed only when `@@SERVERNAME` begins with 'Q', 'P', or 'C' (line 43 of `sys_calc_dormancy.sql`).

### Great Plains (Microsoft Dynamics GP)
The amortisation posting procedures (`sys_amortization_issuance_post`, `sys_amortization_rev_post`) are expected to feed data to the GP GL system. The exact integration mechanism (linked server, SSIS, or application-level) is not visible in this codebase.

### Salesforce CRM
`cursforecast.ext_id` maps programs to Salesforce opportunity IDs. The `vsfdc_extract` view provides a Salesforce extract. The `sys_copy_table_data` procedure may be used to transfer Salesforce-sourced data. While no direct Salesforce API calls are visible, the data model clearly supports CRM-to-Atlys data synchronisation.

---

## Dependencies (Inbound)

| Consumer | Evidence |
|---|---|
| Atlys UI application | EXECUTE grants on all reporting procedures to `ATLYS_APP_GRP` |
| Great Plains GL | `sys_amortization_issuance_post`, `sys_amortization_rev_post` produce GL entries |
| Management reporting | `sys_revenue_cross_tab`, `sys_comm_cross_tab` family |
| atlys_fccr | Likely shares similar data patterns; structural relationship not definitively confirmed from this repo alone |

---

## Intra-Platform Relationship with atlys_fc_nus

`atlys_fc_nus` has an **identical stored procedure set** to `atlys_fc_nca` (confirmed by examining the `atlys_fc_nus.sqlproj` Build includes, which mirror `atlys_fc_nca.sqlproj` exactly). This strongly implies:
- Both databases were forked from a common baseline.
- Schema and procedure changes must be made identically in both databases.
- There is no shared code library or reference — only code duplication.

This is a significant technical debt: any bug fix or enhancement to the fee calculation engine must be applied twice (and to `atlys_fccr` as a third variant). Without CI/CD tooling to enforce simultaneous deployment, drift between regional instances is virtually inevitable.

---

## Integration Architecture Observations

### Salesforce → Atlys Data Flow
The `vsfdc_extract` view and `cursforecast.ext_id` field suggest a Salesforce → Atlys integration for pipeline management. New programs are created in Salesforce and then synchronised to `cursforecast`. The reverse flow (Atlys forecast data → Salesforce) may also exist via the extract view. This integration is likely implemented at the application layer, not within this database.

### GL Amortisation Feed
The amortisation posting procedures generate entries that feed the Great Plains GL. This creates a financial reporting dependency: any calculation error in the dormancy/amortisation engine will propagate to the company's financial statements. This is the most financially material integration point in the system.

### Dashboard Data
`tblDash_data` is pre-populated by `sys_dash` and related procedures, suggesting the Atlys dashboard performs a periodic refresh (likely nightly) rather than real-time computation. The operational dependency is therefore on scheduled procedure execution, which (based on the absence of SQL Agent jobs in the codebase) must be managed externally.

---

## Migration Complexity Assessment

| Scenario | Complexity |
|---|---|
| Deploy new region (e.g., South America) | Medium — copy atlys_fc_nca schema and stored procedures, update `tblCompanies` routing in atlys_e |
| Consolidate NCA and NUS into one database | High — requires data model merge, tenant-discriminating column addition, procedure refactoring |
| Migrate to cloud SQL (Azure SQL MI) | Medium — linked server and three-part name calls to ATLYS_E work in MI; SSAS cube dependency requires Azure Analysis Services |
| Upgrade compatibility level to 150 | Low-Medium — test dormancy WHILE loop behaviour and cross-apply patterns at newer compat level |
| Replace SSAS with Power BI Premium | High — requires replacing `sys_execcview` cube query pattern throughout dormancy calculation |
| Introduce microservices / API layer | Very High — calculation logic is entirely in SQL stored procedures; extracting to .NET/Python services requires full re-implementation |
