# Enterprise Architect View — DS_DB_GP_emeam

## Platform Generation
**Gen-1** — Microsoft Dynamics GP ERP, SQL Server 2008 compatibility level, legacy catalog views, deprecated SQL features (`sp_bindefault`, `SET ROWCOUNT`, `DEFAULT` objects, `VardecimalStorageFormat`). Represents inherited Wirecard/ecount ERP infrastructure. The GP application itself is a commercial off-the-shelf (COTS) system; Onbe can customise but not replace the schema structure.

## Business Domain
**Finance and ERP — EMEAM Region**: General ledger, accounts payable/receivable, payroll, inventory, sales, purchasing, field service management for Europe, Middle East, Africa, and Mexico entities. This is the back-office financial system of record for EMEAM operations — the source of truth for financial reporting, tax compliance, and intercompany reconciliation in those regions.

## Role in the Platform
- **ERP back-office**: Financial transactions, journal entries, vendor payments, customer billing, payroll processing for EMEAM entities.
- **Regulatory compliance data source**: 1099/tax data, HR/payroll compliance (local labour laws per EMEAM country), Management Reporter financial statements used for statutory reporting.
- **Isolated from payments CDE**: GP EMEAM is a financial management system, not a card processing system. It does not appear to store PANs or cardholder data directly, but may receive settlement amounts from payment processing systems.
- **Companion to other GP instances**: Sibling repos include `DS_DB_GP_dynamics`, `DS_DB_GP_ecan`, `DS_DB_GP_ecnt`, `DS_DB_GP_emxn`, `DS_DB_GP_two`, `DS_DB_GP_EAST` — each likely represents a different GP company or region.

## Dependencies

### Upstream (GP EMEAM depends on)
| Component | Reason |
|---|---|
| Dynamics GP Application Server | GP client/server ERP application |
| Management Reporter | Financial reporting (consumes SE_Get_* procedures) |
| DS_DB_dbadmin | Instance-level monitoring |
| SQL Server Agent | GP-managed scheduled processes |

### Downstream (depends on GP EMEAM)
| Component | Reason |
|---|---|
| Finance reporting pipeline (`DS_ETL_great-plains`, `DS_ETL_great-plains-to-oas-coda`) | ETL extracts from GP EMEAM for warehouse/CODA |
| CODA/OAS general ledger | Receives GP journal data via ETL |
| Statutory reporting / tax filing | Draws from GP EMEAM as financial system of record |
| Intercompany reconciliation | Cross-entity financial management |

## Integration Patterns
- **COTS ERP integration**: GP integrates with external systems via Integration Manager, eConnect, and SSRS/FRx reporting — not REST APIs.
- **ETL-sourced**: Downstream analytical/reporting systems extract from GP EMEAM via ETL (Great Plains ETL repos in the wider estate).
- **Service Broker**: Enabled in project settings — GP workflow may use Service Broker for asynchronous workflow operations.
- **No direct REST API surface**: GP EMEAM is not a microservice and does not expose REST endpoints; all access is via SQL or the GP application tier.

## Strategic Status
**Operational dependency — strategic direction: ERP modernisation assessment needed.**

Dynamics GP is an on-premises ERP system reaching end of mainstream support. Microsoft has positioned Dynamics 365 Business Central as the cloud successor. Key strategic questions:
1. Is Onbe planning a migration from GP to D365 Business Central or another ERP?
2. Are EMEAM entities being retained, divested, or reorganised post-acquisition?
3. What is the data retention obligation for EMEAM financial records under EU, UK, and Mexican law?

The `DS_DB_GP_emxn` sibling suggests Mexico was separated into its own entity — potentially indicating a migration or carve-out is in progress.

## Migration Blockers
1. **SQL Server 2008 compatibility level**: Must be raised before migrating to any cloud SQL service; many features used (`VardecimalStorageFormat`, `SET ROWCOUNT`, `sp_bindefault`, legacy catalog views) are removed in newer compatibility levels.
2. **Non-ANSI settings**: `AnsiNulls=False`, `QuotedIdentifier=False` — must be remediated for Azure SQL compatibility; Azure SQL enforces ANSI settings.
3. **GP schema ownership by Microsoft**: Full schema migration requires GP product upgrade path, not just SQL migration.
4. **Named individual SQL logins**: Must be migrated to Azure AD authentication for Azure SQL.
5. **`sp_bindefault` / `sp_unbindefault`**: Removed in SQL Server 2022; must be replaced with column-level DEFAULT constraints before any SQL Server version upgrade.
6. **Service Broker dependency**: Service Broker is limited in Azure SQL MI and not supported in Azure SQL Database.
7. **Named cursor patterns**: `SE_Get_Acc_Detail_Hist` uses explicit CURSOR — will work in Azure SQL MI but represents performance risk at scale.
8. **`DEX_ROW_ID` IDENTITY columns**: Standard GP pattern; compatible with most migration targets.
