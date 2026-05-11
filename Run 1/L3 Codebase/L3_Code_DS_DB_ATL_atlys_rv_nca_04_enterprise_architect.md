# DS_DB_ATL_atlys_rv_nca — Enterprise Architect View

## Platform Generation
**Generation 1 / Gen-1 legacy.** The SSDT project targets `Sql100DatabaseSchemaProvider` (SQL Server 2008 schema), compatibility level 90 (SQL Server 2005 behaviour), uses FLOAT for monetary data, relies on a monolithic cross-database authorisation gate, and has no CI/CD automation. The naming conventions (`tbl*`, `sys_*` prefixes), the BULK_LOGGED recovery model, and the absence of ANSI settings are characteristic of the eCount/Wirecard-era platform inherited before the Onbe rebranding.

## Business Domain
**Finance / Revenue Accounting** — North and Central America (NCA) region.  
This database sits at the intersection of the **Card Issuing** and **Financial Operations** domains. It receives processed transaction data from the card processor layer (FDR) and produces GL-coded financial records for consumption by the General Ledger system (Dynamics GP) and the ATLYS finance analytics application. It is a critical system for period-close, revenue reporting, and sales commission processing.

## Role in Platform
- **Revenue ledger** for NCA prepaid card programs.
- **GL coding engine**: the `trg_revenue` trigger and `sys_glbatch` proc are the authoritative source of GL account assignment for NCA revenue transactions.
- **Commission source**: provides the commission amounts used by sales operations to pay affiliate/partner commissions.
- **Settlement reconciliation store**: holds raw network settlement data (FDR, CitiBank, ACH, MELLON) used for daily/monthly balancing.
- This database is a **reporting source** for the ATLYS web application and a **posting source** for Dynamics GP; it is not a transactional card-processing database.

## Dependencies
| Dependency | Type | Direction | Notes |
|---|---|---|---|
| `ATLYS_E` | SQL Server database | Inbound (reads) | Authorisation, exchange rates, system paths, GL views. Hard runtime dependency. |
| FDR processor feed | External batch | Inbound | Raw cost and settlement files loaded into `tblFDR_*` tables |
| SSIS/ETL packages | Data pipeline | Inbound | Revenue and transaction data loaded externally |
| Dynamics GP (`emeam` / `ecnt` etc.) | ERP | Outbound | GL entries posted via ATLYS_E intermediary |
| ATLYS web application | Application | Outbound (reads) | Revenue and GL reporting via stored procedure API |
| SQL Server Agent | Scheduler | Inbound | Periodic execution of revenue calculation procedures |

## Integration Patterns
- **Stored procedure API**: All application reads and writes go through named stored procedures (`sys_revenue`, `sys_glbatch`, `sys_comm`, etc.). No ORM or direct table access from application code is evident; this is a tightly coupled database-first integration pattern.
- **Trigger-driven derivation**: GL coding is derived automatically via the `trg_revenue` trigger on every revenue insert/update. This is an event-driven pattern implemented at the database layer rather than in application code.
- **Cross-database three-part-name queries**: `ATLYS_E.dbo.*` references are embedded throughout procedures and views, creating a tight coupling to database topology.
- **No message queue or event bus**: Data flows are synchronous (procedure calls) or batch (SSIS loads). There is no evidence of Service Broker, event-driven integration, or REST API endpoints served from this layer.
- **SSIS configuration table**: `SSISConfigurations` is absent from this database (it is in `banker_na`); SSIS packages for this database likely read config from a central location.

## Strategic Status
- **Active but legacy**: The database is in active use for NCA revenue accounting. No migration or decommission plan is evidenced in the repository.
- **Parallel regional instances exist**: Sister databases `DS_DB_ATL_atlys_rv_nca_r` (reporting replica?), `DS_DB_ATL_atlys_rv_nus` (US), `DS_DB_ATL_atlys_fc_nca` (fee calc?), and `DS_DB_ATL_atlys_rvcr` indicate a horizontal per-region, per-function sharding pattern. Consolidation into a single Gen-3 service is a significant architectural undertaking.
- **No versioning or changelog**: There is no evidence of a change history within the database; migrations are managed as full schema snapshots.
- **Tech debt**: Compatibility level 90, FLOAT monetary columns, BULK_LOGGED recovery, disabled ANSI settings, and no CI/CD represent high tech-debt that must be cleared before a safe Gen-3 migration.

## Migration Blockers
1. **`ATLYS_E` hard dependency**: The authorisation and exchange-rate logic must be re-implemented as a microservice or shared library before this database can be decoupled.
2. **`trg_revenue` GL coding logic**: The trigger embeds GL derivation rules that are tightly coupled to `vAffiliates`, `vProducts`, and `tblProgramsBank`; this logic must be extracted into an application service and tested thoroughly before migration.
3. **FLOAT monetary columns**: All `FLOAT`/`FLOAT(53)` monetary columns in `tblEC_Txns` must be migrated to `NUMERIC`/`DECIMAL` before the data can be trusted in a new system.
4. **Compatibility level 90**: Must be raised to at least 130 (SQL Server 2016) before any platform upgrade; behaviour changes (e.g., ANSI NULLs, cardinality estimation) must be tested.
5. **No automated tests**: Zero automated test coverage means every migration step carries an unquantified regression risk.
6. **Regional duplication**: The per-region database pattern means any migration must handle `rv_nca`, `rv_nus`, `rv_nca_r`, `rv_nus_r`, `rvcr` simultaneously or introduce a consolidation layer.
7. **SSIS dependency**: The external SSIS packages loading data into this database are in separate repositories and would need to be re-pointed or replaced with modern ingestion pipelines.
