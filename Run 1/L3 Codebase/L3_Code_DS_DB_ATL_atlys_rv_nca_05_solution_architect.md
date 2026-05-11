# DS_DB_ATL_atlys_rv_nca — Solution Architect View

## Technical Architecture
- **Engine**: SQL Server (targeted SQL Server 2008 schema provider, SQL Server 2005 compatibility mode 90).
- **Project format**: SSDT `.sqlproj` / MSBuild, producing a DACPAC.
- **Schema**: Single `dbo` schema; approximately 70+ tables, 70+ stored procedures, 8+ functions, multiple views, and User Defined Types.
- **Cross-database coupling**: Runtime dependency on `ATLYS_E` for authentication, exchange rates, system metadata, and GL views. References via three-part names (`ATLYS_E.dbo.*`) embedded in stored procedures and views — no abstraction layer.
- **Data model pattern**: Star-schema-like: `revenue` is the central fact table with dimensional references to `tblGL`, `tblProducts`, `tblProgramsBank`, and `tblProgramsBin`. Settlement and FDR tables are independent fact tables.
- **Recovery model**: BULK_LOGGED — incompatible with point-in-time recovery for bulk-loaded data.
- **Service Broker**: Disabled (`ServiceBrokerOption=DisableBroker`).

## API Surface
The database exposes its capabilities exclusively through stored procedures. Key procedures acting as the external API surface:

| Procedure | Purpose |
|---|---|
| `sys_revenue` | Revenue reporting (summary, detail, by-affiliate, by-type, multi-currency) |
| `sys_glbatch` | GL batch configuration management (read and write) |
| `sys_glbatch_complete` | GL batch posting/completion |
| `sys_comm` | Commission query |
| `sys_comm_calc` | Commission calculation |
| `sys_gl_entry` | GL entry generation |
| `sys_fdr` | FDR cost data query |
| `sys_fdrcosts` | FDR cost reconciliation |
| `sys_audit` | Reconciliation audit execution |
| `sys_bal_reconcile` / `sys_bank_reconcile` | Balance and bank reconciliation |
| `sys_issuance` | Issuance reporting |
| `sys_plastics` | Plastic/card reporting |
| `sys_spend` (implied by `tblSpend`) | Spend reporting |
| `sys_periods` | Period management |
| `sys_import` | Revenue import execution |
| `sys_program_filter` | Program filter helper (used internally) |

All procedures enforce an application-layer authorisation check via `ATLYS_E.dbo.sys_chkuser`; there is no row-level security, no column masking, and no schema-level permissions visible in the SSDT project's checked-in Security folder (empty).

## Security Posture
- **TDE**: Disabled. Financial aggregates, GL codes, and sales rep names stored in plaintext on disk.
- **Encryption at column level**: None.
- **Authorisation**: Procedural — `sys_chkuser` check in every procedure; bypassed entirely if calling user is `dbo`.
- **`dbo` bypass**: The pattern `IF USER_NAME() <> 'dbo' AND ... = 0` means any connection running as `dbo` bypasses all authorisation checks. In a shared-service account environment (common in legacy SQL Server deployments), this is a significant privilege-escalation risk.
- **ANSI settings off**: `AnsiNulls=False`, `QuotedIdentifier=False` — these session-level defaults can cause subtle query behaviour differences depending on client connection settings, creating inconsistent security enforcement.
- **No audit of data changes**: No CDC, no temporal tables, no DML triggers on sensitive tables other than `trg_revenue` (which is functional, not audit-purposed).
- **Legacy email config**: `utl_dba_drive_space_alert` (in `dbadmin`) uses `dba-notify@ecount.com` — a legacy domain. While this is in a different repo, it confirms the broader platform still references old Wirecard/ecount email infrastructure.
- **Cross-database trust**: The database trusts `ATLYS_E` completely for security decisions; there is no fallback if `ATLYS_E` is unavailable or compromised.

## Technical Debt
- **Compatibility level 90**: SQL Server 2005 semantics; no row-level security, no dynamic data masking, no temporal tables, no JSON support, no string_agg. Must be raised before any meaningful modernisation.
- **FLOAT monetary columns**: `tblEC_Txns.amount`, `tblEC_Txns.fee` — floating-point arithmetic is unsuitable for financial data. The correct type is `NUMERIC(19,4)` or equivalent.
- **`AnsiNulls=False` / `QuotedIdentifier=False`**: Legacy settings that cause subtle behavioural differences; correcting them requires regression-testing all stored procedures.
- **Trigger-embedded GL logic**: The `trg_revenue` trigger contains ~30 lines of JOIN logic that should be in application code; database triggers are difficult to test, debug, and trace in distributed systems.
- **Three-part cross-database names**: 30+ references to `ATLYS_E.dbo.*` embedded in procedure bodies; not refactorable without modifying every affected object.
- **No parameterised dynamic SQL safety**: `sys_glbatch` constructs XML from a `@ids varchar(8000)` input (`REPLACE(RTRIM(@ids), ',', '"/><a i="')`) — a potential XML injection vector if input is not validated by the calling application.
- **`DEFAULT GLOBAL CURSOR`**: A server-level legacy setting that increases memory consumption for cursor-heavy stored procedures.
- **Old `tblGLMap_old` table**: Schema artefact left from a prior migration, indicates no formal schema cleanup process.
- **`BULK_LOGGED` + high-volume inserts**: Revenue and FDR load pipelines run in minimally-logged mode; the combination of large bulk loads and a complex trigger (`trg_revenue` firing on every bulk row) will cause performance degradation.

## Gen-3 Migration Requirements
1. **Decouple from `ATLYS_E`**: Implement a dedicated AuthZ microservice or embed programme-level authorisation in the application tier. Extract exchange-rate service as a dedicated API.
2. **Replace FLOAT with DECIMAL**: Convert `tblEC_Txns.amount` and `tblEC_Txns.fee` to `NUMERIC(19,4)` and run a data audit to quantify existing precision errors.
3. **Extract trigger logic**: Move the GL-coding derivation from `trg_revenue` into an application-layer event handler or domain service; the trigger must be removed before the data model can be safely migrated to a new platform.
4. **Raise compatibility level**: Increment to 130 or higher; test all stored procedures for behaviour changes (especially NULL handling, cardinality estimation).
5. **Switch recovery model to FULL**: Required for point-in-time recovery of revenue data; must be paired with a log-backup schedule.
6. **Enable TDE**: Encrypt the database at rest; coordinate with the broader Onbe key management strategy.
7. **Introduce parameterised migration tooling**: Replace DACPAC snapshot deployments with a migration-script framework (Flyway or DbUp) to produce an auditable change history.
8. **Add automated tests**: Implement tSQLt or equivalent database unit tests for all revenue calculation procedures before any migration attempt.
9. **Refactor XML parsing in `sys_glbatch`**: Replace the `REPLACE(RTRIM(@ids), ',', '"/><a i="')` XML construction with a proper table-valued parameter or JSON parsing.
10. **Consolidate regional instances**: Design a multi-tenant data model that can serve NCA, NUS, and CR regions from a single schema with a region discriminator, eliminating the four parallel `rv_*` databases.

## Code-Level Risks
- **Silent GL miscoding**: If `vAffiliates` or `vProducts` has no matching row, the trigger sets `gl_channel`, `gl_product`, `item`, `gp_product`, `gl_acct_num` to empty strings and `gl_acct` to a malformed account number (e.g., `'-00-000-00'`). No error is raised; the revenue row is silently mis-coded.
- **XML injection in `sys_glbatch`**: The `@ids` parameter is concatenated directly into an XML string literal. If the calling application does not sanitise this input, an attacker could inject arbitrary XML structure.
- **Unbounded `@prg_id varchar(10)` vs table columns `CHAR(8)`**: The procedure accepts a wider type than the table stores; silent truncation or mismatches can occur.
- **`NOLOCK` table hints**: Multiple procedures use `WITH (NOLOCK)` which can return dirty or phantom reads; in a financial reporting context this means revenue summaries can be inconsistent during write operations.
- **`SESSION_USER` bypass**: The `USER_NAME() <> 'dbo'` check means any application that connects as `dbo` (a common anti-pattern in legacy SQL Server deployments) bypasses all application-level security.
- **`sys_import` inserts into `dbo.revenue`**: Report mode `'I'` or `'L'` of `sys_revenue` performs an INSERT into `dbo.revenue` — a side-effect of a reporting procedure that is non-obvious and creates a risk of data contamination if called with incorrect parameters.
