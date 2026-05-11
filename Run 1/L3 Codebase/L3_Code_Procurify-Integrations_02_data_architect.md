# Procurify-Integrations — Data Architect View

## Data Stores

| Store | Technology | Role | Sensitivity |
|---|---|---|---|
| `TWO18` SQL Server database | SQL Server 2014 on `AJBPK\SQL2014` | Primary Onbe-side data store (Dynamics GP ERP + integration tables) | High — financial + vendor PII |
| Procurify SaaS API | REST API (OAuth 2.0) | Source of AP bills and vendor records | Medium — financial + employee PII |

The service has no other data stores. There is no Redis cache, no message queue, and no local file storage.

## Schema / Tables (Onbe-side, `TWO18` database)

### Integration Tables (custom Procurify integration tables)

| Table / Object | Type | Columns of Note | Purpose |
|---|---|---|---|
| `dbo.procurify_stage_APHeader` | Staging table | `ParentID`, `ID`, `UUID`, `Status`, `CurrencyID`, `CurrencyName`, `CurrencyRate`, `VendorID`, `VendorName`, `DueDate`, `InvoiceDate`, `GLPostDate`, `InvoiceNumber`, `UserID`, `UserName` | Staged AP bill headers from Procurify |
| `dbo.procurify_stage_APDetail` | Staging table | `ParentID`, `ID`, `UUID`, `ACTNUMST`, `TRXDESC`, `Item_ID`, `Item_SKU`, `Item_Description`, `Item_PO`, `Item_Unit`, `Item_UnitCost`, `Item_Quantity`, `Item_TotalCost`, `Item_ShippingAmount` | Staged AP bill line items |
| `dbo.procurify_VendorCrossReference` | Cross-reference | Dynamics GP `VENDORID`, Procurify vendor ID | Maps GP vendor IDs to Procurify vendor IDs |
| `dbo.procurify_GlobalSettings` | Configuration table | `UserDomain`, `Token_URL`, `Token`, `Token_Date`, `Client_ID`, `Client_Secret`, `Audience`, `Grant_Type`, vendor API URLs, bills API URLs | OAuth credentials and API endpoint configuration |

### Dynamics GP Tables (read-only by this service)

| Table | Columns Read | Purpose |
|---|---|---|
| `dbo.PM00200` (Vendor Master — inferred from SP `procurify_Get_DynamicsVendors`) | `VENDORID`, `VENDNAME`, `VENDSTTS`, `ADDRESS1`, `ADDRESS2`, `ZIPCODE`, `CITY`, `STATE`, `COUNTRY`, `PHNUMBR1`, `INET1`, `CURNCYID`, `PYMTRMID` | Source vendor records for sync to Procurify |

### Stored Procedures

| Procedure | Direction | Purpose |
|---|---|---|
| `dbo.procurify_Get_GlobalSettings` | Read | Load OAuth credentials and API URLs |
| `dbo.procurify_Put_GlobalSettings` | Write | Update OAuth token and token timestamp |
| `dbo.procurify_staging_InsertAPHeader` | Write | Insert AP bill header into staging |
| `dbo.procurify_staging_InsertAPDetail` | Write | Insert AP bill line item into staging |
| `dbo.procurify_staging_ProcessIntegration` | Execute | Move staged data into ERP system |
| `dbo.procurify_Get_VendorCrossReference` | Read | Look up Procurify ID for a GP vendor |
| `dbo.procurify_Push_ProcurifyVendorIDToDynamicsGP` | Write | Write Procurify vendor ID back to GP |
| `dbo.procurify_Get_DynamicsVendors` | Read | Get all GP vendors needing sync |
| `dbo.procurify_Get_DynamicsVendorById` | Read | Get single GP vendor by VENDORID |
| `dbo.procurify_Get_CurrencyCrossReference` | Read | Map GP currency to Procurify currency ID |
| `dbo.procurify_Get_PaymentCrossReference` | Read | Map GP payment term to Procurify term ID |

## Sensitive Data Assessment

| Field | Classification | Location | Risk |
|---|---|---|---|
| `Client_Secret` (OAuth) | Secret / Credential | `dbo.procurify_GlobalSettings` | High — stored in DB, loaded into memory at runtime |
| `Client_ID` (OAuth) | Secret / Credential | `dbo.procurify_GlobalSettings` | High — same as above |
| `Token` (access token) | Secret | `dbo.procurify_GlobalSettings` | High — OAuth bearer token stored in DB |
| `UserName` (employee first + last name) | PII | `dbo.procurify_stage_APHeader` | Medium — CCPA/GDPR; employee who submitted the bill |
| `VendorName` | Business data | Staging tables | Low-Medium — vendor names are generally not PII |
| `ACTNUMST` (GL account number) | Financial | `dbo.procurify_stage_APDetail` | Medium — internal financial account codes |
| `Item_UnitCost`, `Item_TotalCost` | Financial amounts | `dbo.procurify_stage_APDetail` | Medium — procurement spend data |
| Invoice numbers, PO numbers | Financial references | Staging tables | Low-Medium |

**No payment card data (PAN, CVV, PIN) flows through this system.** This service operates in the procurement/AP domain, not the payments/issuing domain. PCI DSS scope is limited to ensuring the OAuth credentials stored in the database are protected per PCI DSS Requirement 8.6 (system/application accounts).

## Encryption Assessment

| Layer | Current State | Gap |
|---|---|---|
| OAuth `Client_Secret` at rest | Stored as plaintext in SQL table `procurify_GlobalSettings` | High — credentials should be encrypted at column level or stored in Azure Key Vault |
| OAuth `Token` at rest | Stored as plaintext in SQL table | Medium — token is short-lived but should not be stored in cleartext |
| Data in transit (Procurify API) | HTTPS via `HttpClient` (System.Net.Http) | Acceptable — TLS enforced by HTTPS URLs |
| SQL connection | Windows Integrated Authentication (`Trusted_Connection=True`) | Acceptable for domain-joined Windows service |
| Connection string in `App.config` | SQL Server name and database in config file | Low — server name is not a secret; database name is not a secret |

## Data Flow

```
[3-hour timer cycle]

Procurify API (HTTPS)
    │
    │ 1. GET all active vendors
    │ 2. GET vendor by ID
    │ 3. POST create/update vendor
    │
    ▼
Vendors.BeginProcess()
    ├── Read: TWO18.dbo.procurify_Get_DynamicsVendors (GP vendor master)
    ├── Read: TWO18.dbo.procurify_Get_VendorCrossReference
    ├── POST/PUT: Procurify vendor API
    └── Write: TWO18.dbo.procurify_Push_ProcurifyVendorIDToDynamicsGP

Procurify API (HTTPS)
    │
    │ 4. GET all open AP bills
    │ 5. GET bill by ID (per-bill detail)
    │
    ▼
APBills.BeginProcess()
    ├── Write: TWO18.dbo.procurify_staging_InsertAPHeader (per bill)
    └── Write: TWO18.dbo.procurify_staging_InsertAPDetail (per line item)

dataSettings.APBeginSQL()
    └── EXEC: TWO18.dbo.procurify_staging_ProcessIntegration
              (moves staged data into Dynamics GP)
```

## Data Quality and Retention

### Duplicate Detection Gap
The `APBills.BeginProcess()` method fetches all open AP bills from Procurify on every 3-hour cycle and re-stages them. There is no visible deduplication logic — if a bill is already in `procurify_stage_APHeader`, it will be re-inserted on every cycle until removed by `procurify_staging_ProcessIntegration`. Duplicate entries may cause duplicate AP vouchers in Dynamics GP unless the stored procedure is idempotent.

### Error Handling Gap
Per-bill errors are caught and logged but do not halt processing. A failed bill is silently skipped. There is no dead-letter queue, no retry logic, and no alerting mechanism beyond Windows Event Log entries. Failed bills may create reconciliation gaps between Procurify and GP.

### Retention
No explicit retention policy is implemented in this service. Staged data in `dbo.procurify_stage_APHeader` and `dbo.procurify_stage_APDetail` persists until `dbo.procurify_staging_ProcessIntegration` processes and presumably removes it.

## Compliance Gaps

| Gap | Regulatory Ref | Detail |
|---|---|---|
| OAuth `Client_Secret` stored in plaintext DB | PCI DSS Req 8.6, NIST | Must be encrypted at rest or managed via Azure Key Vault |
| Employee PII (`UserName`) in staging tables | GDPR, CCPA | Employee first/last name; must have documented retention and deletion policy |
| No audit log of integration runs | SOC 2 Type II | Windows Event Log is transient; no durable audit trail of data movements |
| `AJBPK\SQL2014` connection string hardcoded | Ops hygiene | Developer machine name in production config; must be environment-specific |
