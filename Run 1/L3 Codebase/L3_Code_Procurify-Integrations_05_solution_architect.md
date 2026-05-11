# Procurify-Integrations — Solution Architect View

## Technical Architecture

`Procurify-Integrations` is a .NET Framework 4.7.2 Windows Service with a flat class structure and no layered architecture pattern. It consists of approximately 10 classes across 3 functional areas:

```
Procurify Integrations.exe (Windows Service)
├── ProcurifyIntegration.cs     ← ServiceBase entry point + timer orchestration
├── Program.cs                  ← ServiceBase.Run() entry
├── ProjectInstaller.cs         ← Windows Service installer
├── Classes/
│   ├── Tokens.cs               ← OAuth token acquisition and refresh
│   ├── dataSettings.cs         ← SQL operations (CRUD, connection string, staging insert)
│   ├── APBills.cs              ← AP bill processing orchestration
│   └── Vendors.cs              ← Vendor synchronization
├── Models/
│   ├── cEventLog.cs            ← Windows Event Log wrapper + static state
│   ├── jsonAPGetBills.cs       ← GET all AP bills API client
│   ├── jsonAPGetBillByID.cs    ← GET bill by ID API client
│   ├── jsonAPGetBillsByIDResponse.cs ← Deserialized response model
│   ├── jsonAuthorizeConnection.cs    ← OAuth token request/response model
│   ├── jsonCreateVendor.cs          ← Create vendor API client + model
│   ├── jsonCreateVendorResponse.cs  ← Create vendor response
│   ├── jsonUpdateVendor.cs          ← Update vendor API client + model
│   ├── jsonVendorAll.cs             ← Get all vendors API client
│   └── jsonVendorById.cs            ← Get vendor by ID API client
└── frmTesting.cs               ← Windows Forms test harness (developer utility)
```

### Execution Flow
```
OnStart()
  └── TimerEventsHere() [immediate + every 3 hours]
        ├── Tokens.GetToken()
        │     ├── Read token from dbo.procurify_GlobalSettings
        │     └── If expired: POST OAuth token_url → update dbo.procurify_GlobalSettings
        │
        ├── Vendors.BeginProcess()
        │     ├── EXEC dbo.procurify_Get_DynamicsVendors → DataTable
        │     └── For each GP vendor:
        │           ├── GET Procurify vendor by external_id
        │           ├── If exists: PUT update vendor in Procurify
        │           └── If not exists: POST create vendor in Procurify
        │                 └── EXEC dbo.procurify_Push_ProcurifyVendorIDToDynamicsGP
        │
        └── APBills.BeginProcess()
              ├── GET all AP bills from Procurify
              └── For each bill:
                    ├── GET bill detail by ID from Procurify
                    ├── [SILENT CATCH: on error, log and continue]
                    └── [NOTE: APHeaderStagingInsert / APDetailStagingInsert
                              appear to be called from jsonAPGetBillByID, not APBills directly]

dataSettings.APBeginSQL()  [called after APBills.BeginProcess() completes]
  └── EXEC dbo.procurify_staging_ProcessIntegration
```

**Note**: Reviewing `APBills.cs` closely, the `APHeaderStagingInsert` and `APDetailStagingInsert` calls appear to originate from within `jsonAPGetBillByID.NEWAPGetBillByID()` rather than directly in `APBills.BeginProcess()`. This means staging inserts are triggered as a side effect of the detail fetch — a hidden coupling that makes the data flow harder to trace.

## API Surface

This service has **no inbound API surface** — it is a Windows Service that cannot be called by other systems. All integration is outbound (polling-based).

### Outbound API Calls to Procurify

| API Call | HTTP Method | Endpoint Key | Purpose |
|---|---|---|---|
| Get all active vendors | GET | `get_vendor_actives` | Vendor sync list |
| Get vendor by external ID / ID | GET | `get_vendor_by_id_url` | Vendor existence check |
| Create vendor | POST | `create_vendor_url` | New vendor in Procurify |
| Update vendor | PUT | `update_vendor_url` | Sync GP changes to Procurify |
| Get all AP bills | GET | `get_bills_url` | AP bill list |
| Get AP bill by ID | GET | `get_bills_by_id_url` | AP bill detail (line items) |
| OAuth token | POST | `token_url` | Get/refresh access token |

All API URLs are loaded from `dbo.procurify_GlobalSettings` at runtime, making endpoint configuration data-driven.

## Security Posture

### Strengths
- OAuth credentials stored in SQL database (not in source code or `App.config`).
- HTTPS used for all Procurify API calls.
- Windows Integrated Authentication for SQL connection (no SQL password in config).
- Token refresh logic avoids expired token reuse.

### Critical Weaknesses

#### 1. OAuth `Client_Secret` Stored in Plaintext SQL
`dataSettings.GetSQLTable()` loads `Client_Secret` directly from a varchar column in `dbo.procurify_GlobalSettings`. Any user with `SELECT` access to this table can read the Procurify OAuth secret.

**Recommendation**: Migrate to Azure Key Vault. Read the secret at service startup using `DefaultAzureCredential` (Managed Identity if running on Azure-hosted Windows, or service principal otherwise).

#### 2. OAuth `access_token` Stored in Plaintext SQL
The token is stored in `dbo.procurify_GlobalSettings` and persists until the next token refresh. A compromised database exposes a valid OAuth token that can be used to query the Procurify API directly.

**Recommendation**: Do not persist the access token to the database. Use an in-memory cache with the token's expiry time. Persist only the credentials needed to re-acquire a token.

#### 3. No TLS Certificate Validation Override Detected
`HttpClient` is created with no custom `HttpClientHandler` — the default TLS validation behaviour applies. This is correct, but it should be verified that no developer has added `ServerCertificateCustomValidationCallback = (m, c, ch, e) => true` (which would disable TLS certificate validation).

#### 4. No Input Sanitization for SQL Parameters
`dataSettings.APHeaderStagingInsert()` uses `command.Parameters.AddWithValue()` throughout — parameterised queries, which correctly prevent SQL injection. This is the right pattern and is applied consistently.

#### 5. `frmTesting.cs` — Windows Forms Test UI in Production Assembly
A Windows Forms form (`frmTesting.Designer.cs`, `frmTesting.resx`) is included in the production assembly. This is a developer test harness that should not be in a production binary. It adds unnecessary attack surface and binary size.

## Technical Debt

| Item | Severity | Detail |
|---|---|---|
| OAuth secret in plaintext SQL | Critical | Must move to Azure Key Vault |
| No CI/CD pipeline | Critical | Manual builds are unauditable; no versioning |
| .NET Framework 4.7.2 | High | Windows-only; cannot containerise; migrate to .NET 8 |
| No retry logic for API failures | High | Transient Procurify API failures cause permanently missed bills |
| No duplicate detection | High | AP bills re-staged on every cycle |
| No error alerting | High | Silent failures; Finance team discovers gaps in reconciliation |
| `frmTesting.cs` in production binary | Medium | Developer test UI included in production assembly |
| `AJBPK\SQL2014` hardcoded | Medium | Developer machine name in production config |
| `APBeginSQL()` called synchronously after `APBills.BeginProcess()` | Medium | Sequential; no error check between staging and processing steps |
| Static mutable state in `cEventLog` (`eventId++`) | Low | Not thread-safe; if async operations overlap (possible with `async void`), `eventId` can corrupt |
| `async void` methods (`OnTimer`, `TimerEventsHere`) | Low | `async void` prevents proper exception propagation; unhandled exceptions in these methods terminate the service |

## Gen-3 Migration Path

### Phase 1 — Immediate Security (No Architecture Change)
1. Encrypt `Client_Secret` in `dbo.procurify_GlobalSettings` using SQL Server column encryption or replace with Azure Key Vault reference.
2. Remove `access_token` persistence from database; use in-memory cache.
3. Verify `App.config` `sqlServerName` is correct in production.

### Phase 2 — .NET 8 Migration
1. Migrate from .NET Framework 4.7.2 to .NET 8 (LTS).
2. Replace `System.Windows.Forms` references (remove `frmTesting`).
3. Replace `System.Data.SqlClient` with `Microsoft.Data.SqlClient`.
4. Use `IHttpClientFactory` with `Polly` retry policies (replacing manual `HttpClient` instantiation).
5. Add GitHub Actions CI/CD pipeline with automated build, test, and deployment.

### Phase 3 — Architecture Modernisation
1. Add duplicate detection: check `ExportDate` or UUID in staging table before re-inserting.
2. Add alerting: integrate with Teams / email / PagerDuty on processing failures.
3. Consider Procurify webhook integration to replace 3-hour polling with event-driven processing.
4. Containerise (Linux container, .NET 8 runtime) for Kubernetes deployment.
5. Add structured logging (Serilog / OpenTelemetry) replacing Windows Event Log.

### Phase 4 — ERP Strategy
Evaluate Dynamics GP → Dynamics 365 migration. If Dynamics 365 is adopted, a native Procurify-to-Dynamics 365 connector (available from Procurify's integration marketplace) may replace this custom service entirely.
