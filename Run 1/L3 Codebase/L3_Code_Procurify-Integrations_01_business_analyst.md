# Procurify-Integrations — Business Analyst View

## 1. Repository Purpose and Business Context

`Procurify-Integrations` is a **.NET Framework 4.7.2 Windows Service** (C#) that bridges Onbe's internal financial processes with the **Procurify** procurement SaaS platform. It automates the synchronization of vendor master data and accounts payable (AP) bills between Procurify and Onbe's internal ERP system (Microsoft Dynamics GP, based on the `TWO18` database reference and GP-related repo names visible in the organization).

This integration eliminates manual data re-entry for procurement-related financial transactions, ensuring that purchase orders and invoices approved in Procurify flow automatically into Onbe's accounting and accounts payable systems.

## 2. Business Process Automated

The service runs on a **timer-based polling architecture** (default interval: 10,800,000 ms = **3 hours**, configurable via `App.config`). Each timer cycle:

1. **Token acquisition**: Retrieves/refreshes an OAuth 2.0 `client_credentials` access token from the Procurify authorization endpoint (`Tokens.GetToken()`)
2. **Vendor synchronization**: Calls `Vendors.BeginProcess()` — syncs vendor master records between Procurify and the internal GP/SQL database
3. **AP Bill processing**: Calls `APBills.BeginProcess()` — fetches all open AP bills from Procurify API and processes them line by line into internal staging tables
4. **Staging integration**: Calls `dataSettings.APBeginSQL()` — executes stored procedure `dbo.procurify_staging_ProcessIntegration` to move staged data into the target ERP system

## 3. Data Flows

### Vendor Sync
- **Source**: Procurify API (`get_vendor_actives`, `get_vendor_by_id_url`, `create_vendor_url`, `update_vendor_url` — configured in SQL settings table)
- **Target**: Internal SQL database (`TWO18` on `AJBPK\SQL2014`)

### AP Bills Sync
- **Source**: Procurify API (`get_bills_url`, `get_bills_by_id_url`)
- **Staging table**: `dbo.procurify_stage_APHeader` and `dbo.procurify_staging_InsertAPDetail` stored procedures
- **Final target**: GP/ERP system via `dbo.procurify_staging_ProcessIntegration`

## 4. Business Data Elements Processed

Based on `dataSettings.APHeaderStagingInsert()` (lines 110–156):

| Field | Source | Business Meaning |
|---|---|---|
| `id`, `uuid` | Procurify | AP bill unique identifiers |
| `status` | Procurify | Bill approval status |
| `currency.id/name/rate` | Procurify | Currency code, name, exchange rate |
| `vendor.id/name` | Procurify | Vendor identifier and name |
| `due_date` | Procurify | Payment due date |
| `invoice_date` | Procurify | Invoice date |
| `invoice_number` | Procurify | Invoice reference number |
| `gl_post_date` | Procurify | General ledger posting date |
| `user.firstName/lastName` | Procurify | Submitting employee name |
| `group`, `type` | Procurify | Bill grouping and type classification |

Line item data from `APDetailStagingInsert()` (lines 159–232) includes:
- `ACTNUMST`: GL account number (from `orderitem.account.account_code.code` or `cost_allocations[0].budget.account_code.code`)
- `TRXDESC`: Transaction description
- `Item_SKU`, `Item_Description`: Line item product details
- `Item_PO`: Purchase order number
- `Item_UnitCost`, `Item_Quantity`, `Item_TotalCost`, `Item_ShippingAmount`: Financial amounts

## 5. Configuration and Secrets Management

OAuth credentials (client ID, client secret) and API endpoint URLs are **stored in the SQL database** (table queried by `dbo.procurify_Get_GlobalSettings`) rather than in `App.config`. This is a security-positive design choice — credentials are not stored in the application binary or configuration file.

The `App.config` only stores:
- SQL Server connection details: `sqlServerName=AJBPK\SQL2014`, `sqlDatabaseName=TWO18`
- `sTestProduction=T` (test/production toggle)
- `sInterval=10800000` (3-hour polling interval)

**However**: The `App.config` has a hardcoded SQL Server instance name `AJBPK\SQL2014` and database `TWO18` — this is a development/UAT configuration committed to source control.

## 6. Business Risks and Concerns

1. **SQL Server named instance in App.config**: `AJBPK\SQL2014` appears to be a developer machine name committed to the repository — a deployment and security concern.
2. **No error notification mechanism**: Errors are written to the Windows Event Log (`cEventLog`) but there is no email or alert integration. AP bill processing failures could go unnoticed for up to 3 hours until the next poll.
3. **All errors are swallowed per bill**: The per-bill error handling in `APBills.BeginProcess()` catches exceptions and logs them but continues processing. A failed bill is silently skipped, which could cause reconciliation gaps between Procurify and GP.
4. **No duplicate detection**: There is no visible mechanism to detect if an AP bill has already been processed — repeated runs may re-insert the same bills into staging tables.
5. **Finance data compliance**: AP bills and vendor data may contain personal information (employee names, addresses) subject to GDPR/CCPA. The `user.firstName/lastName` fields from Procurify are PII.
