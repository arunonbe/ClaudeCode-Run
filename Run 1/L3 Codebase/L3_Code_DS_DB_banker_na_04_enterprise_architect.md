# DS_DB_banker_na — Enterprise Architect View

## Platform Generation
**Generation 1 / Gen-1 legacy.** Created circa 2008 (the `banker_insert_action_log` procedure header reads "Created: 2008-10-22, i-Flex"), the database uses SSDT `Sql100DatabaseSchemaProvider`, hardcoded production server names in synonyms, a plain-text SSIS configuration table, and manually managed security role grants. It predates any modern CI/CD, secrets management, or microservice patterns.

## Business Domain
**Program Financing / Funds Management** — North America region.

`banker_na` sits at the intersection of the **Client Program Administration** and **Card Operations** domains. It manages the financial reservoir for each prepaid program — specifically the float of funds that have been collected from clients but not yet disbursed to cardholders — and drives the card manufacturing re-issuance lifecycle for expiring cards. It feeds the job-service platform, Dynamics GP (via eConnect), and indirectly the reporting layer.

## Role in Platform
- **Funds reservation ledger**: the authoritative record of how much of each program's float is reserved against pending promotions/orders, and what the available-funds rules are.
- **Approval gate**: controls whether large fund movements require manager approval via the notification workflow.
- **Plastic operations engine**: drives the card expiry and re-issue pipeline by selecting expiring cards from `ecountcore_ss` and staging re-issue work items.
- **GP billing intermediary**: generates and stages invoice records for card manufacturing costs before they are posted to Dynamics GP via eConnect.
- **SSIS configuration store**: serves as the runtime configuration database for SSIS-driven ETL processes related to banker operations.

## Dependencies
| Dependency | Type | Direction | Notes |
|---|---|---|---|
| `ecountcore_ss` (ppamwdcudsql1c1) | SQL Server database | Inbound (reads via synonyms) | Card account master, device ecard, expiry queue |
| `jobsvc` database | SQL Server database | Outbound (writes via procedure) | Audit log (`banker_action_log`) |
| Dynamics GP / eConnect | ERP | Outbound | Invoice posting via SSIS eConnect package |
| Job Service application | Application | Bidirectional | Reads banker data; writes action log |
| SSIS packages | ETL | Inbound (reads config) / Outbound (processes data) | Plastic expiry and ONUS ETL |
| SQL Server Agent | Scheduler | Inbound | Triggers scheduled banker and ONUS jobs |
| `syn_ItemPricePerContractPlusKit` | GP pricing table | Inbound (reads) | Pricing for invoice calculation |

## Integration Patterns
- **Synonym abstraction**: Cross-database reads to `ecountcore_ss` are wrapped in synonyms rather than hard-coded three-part names within procedure bodies, providing one level of indirection — but the synonym DDL itself hardcodes the server name, so the abstraction is shallow.
- **Stored procedure API**: All banker operations (reserve, release, get, update) are encapsulated in named stored procedures with consistent naming conventions (`banker_*`, `ab_process_plastic_*`, `onus_*`, `gp_process_*`).
- **Staging table integration with GP**: The GP eConnect integration uses a staging-table pattern; invoice rows accumulate in `gp_process_econnect_invoice*` tables and are consumed by an SSIS package that calls eConnect to post them to GP. This decouples the database write from the GP API call.
- **SSIS configuration table**: The `SSISConfigurations` table is a standard SSIS configuration pattern (deprecated in SQL Server 2012 SSIS in favour of the SSISDB catalog); its presence indicates the SSIS packages use the legacy package deployment model.
- **No message queue or event bus**: All integration is synchronous (stored proc calls) or batch (SSIS). No Service Broker, Azure Service Bus, or event streaming is in use.

## Strategic Status
- **Active and operationally critical**: The funds reservation and approval workflow is actively used; the plastic expiry pipeline is a regulatory necessity (card re-issuance before expiry).
- **Tightly coupled to `ecountcore_ss`**: The synonym dependency on a single named production server instance means this database cannot be migrated or tested in isolation.
- **SSIS legacy packaging**: The use of the SQL Server SSIS configuration table (pre-SSISDB) indicates a legacy SSIS deployment model that should be migrated to SSISDB project deployment or replaced with a modern pipeline tool (Azure Data Factory, dbt).
- **Parallel regional instance**: `DS_DB_banker` (without `_na` suffix) likely serves a different region or is a predecessor; the relationship should be clarified before any consolidation.
- **No decommission plan visible**: The database is actively extended (plastic processing, ONUS processing added over time) and is not scheduled for retirement.

## Migration Blockers
1. **Hardcoded production server in synonyms**: Cannot deploy to non-production environments without manual synonym redefinition; blocks self-contained DevOps pipeline creation.
2. **External audit log (`banker_action_log` in `jobsvc`)**: The audit trail is split across databases; a Gen-3 migration must consolidate audit data or design a distributed audit strategy.
3. **SSIS legacy configuration table**: The `SSISConfigurations` pattern is deprecated; the SSIS packages using it must be re-platformed before the configuration store can be removed from the database.
4. **`ecountcore_ss` coupling**: The plastic processing workflow is tightly bound to the `ecountcore_ss` schema; migrating to a Gen-3 card platform requires parallel access to both legacy and new card data during transition.
5. **No automated tests**: Zero test coverage for funds reservation logic; any migration carries unquantified risk of financial-state corruption.
6. **GP eConnect dependency**: The eConnect staging pattern requires the legacy GP integration to remain operational; replacing GP billing requires a parallel integration to be built and tested.
7. **Approval workflow state in database tables**: If the banker approval workflow is migrated to a modern workflow engine, in-flight approvals in `banker_approval_notification` must be handled during cutover.
