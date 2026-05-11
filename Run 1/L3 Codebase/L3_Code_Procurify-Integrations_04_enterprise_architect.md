# Procurify-Integrations — Enterprise Architect View

## Platform Generation

**Generation**: Gen-1 — Legacy Windows Service, End-of-Life Pattern

`Procurify-Integrations` is a .NET Framework 4.7.2 Windows Service — the oldest technology generation in this analysis set. It predates containerisation, cloud-native deployment, and modern CI/CD by design. It has no pipeline, no infrastructure-as-code, no automated testing, and runs as a manually deployed process on a specific Windows host. In Onbe's Gen-3 migration context, this is a high-priority modernisation candidate.

## Business Domain

**Domain**: Finance Operations / Procurement Integration

`Procurify-Integrations` automates the AP-to-ERP data flow between:
- **Procurify**: Onbe's SaaS procurement and purchase order management platform.
- **Microsoft Dynamics GP (ERP)**: Onbe's on-premises general ledger and accounts payable system (`TWO18` database).

The service eliminates manual re-entry of AP bills and vendor records — a direct operational cost saving for Onbe's Finance team. Without this integration, Finance staff would need to manually re-enter every purchase order and invoice approved in Procurify into Dynamics GP.

This is an **internal business process automation** — not a customer-facing capability. There are no cardholders or clients interacting with this service. It affects Onbe's internal accounts payable and vendor management functions.

## Role in the Platform

### System Context
```
Procurify SaaS (external)
    │ REST/HTTPS (OAuth 2.0 client_credentials)
    │ — AP bills, vendors
    ▼
Procurify-Integrations (Windows Service)
    │ SQL / Windows Auth
    ▼
TWO18 (SQL Server — Dynamics GP database)
    ├── dbo.procurify_stage_APHeader
    ├── dbo.procurify_stage_APDetail
    └── dbo.procurify_staging_ProcessIntegration → Dynamics GP AP module
```

### Data Movement Summary
- **Vendor sync (bidirectional)**: GP vendor master → Procurify (create/update); Procurify ID → GP cross-reference table.
- **AP bills sync (inbound)**: Procurify bills → TWO18 staging tables → Dynamics GP AP vouchers.

### No Relationship to Payment Platform
This service operates entirely within Onbe's internal finance operations. It does not touch the payments platform (`ecountcore`, `ordersvc`, `nexpay-*`), cardholder data, or disbursement processes. PCI DSS scope is limited to credential management (OAuth secrets in the database).

## Dependencies

### Upstream (who triggers this service)
- Windows Service Control Manager timer (internal, 3-hour interval).
- No external system triggers this service — it is a pure polling service.

### Inbound Data Sources
- Procurify SaaS AP bills and vendor APIs.
- Dynamics GP vendor master (`TWO18` database tables).

### Outbound Data Targets
- Procurify API (vendor create/update).
- TWO18 staging tables → Dynamics GP AP module (via stored procedures).

## Integration Patterns

| Pattern | Implementation | Generation | Notes |
|---|---|---|---|
| Timer-based polling | `System.Timers.Timer` (3-hour interval) | Gen-1 | Anti-pattern for real-time integration; suitable for low-frequency AP processing |
| REST API consumption | `System.Net.Http.HttpClient` | Gen-1/2 | No retry policies, no circuit breakers, no timeouts configured |
| OAuth 2.0 client_credentials | `Tokens.GetToken()` | Acceptable | Token cached in SQL table; refreshed when expired |
| Staging table ETL | SQL stored procedures | Gen-1 | `procurify_staging_ProcessIntegration` bridges to Dynamics GP |
| Cross-reference mapping | SQL cross-reference tables | Gen-1 | GP vendor ID ↔ Procurify vendor ID mapping |

## Strategic Status

**Status**: Operational, Modernisation Required

The service performs its function (3-hour AP bill sync) and has been in production long enough to have a working OAuth token management pattern. However, it carries significant technical risk:

1. .NET Framework 4.7.2 is Windows-only and cannot be containerised.
2. No CI/CD pipeline means deployments are invisible, unauditable, and unversioned.
3. Silent error handling means data gaps are not detected until Finance reconciliation.

**Near-term risk**: The `AJBPK\SQL2014` connection string in `App.config` appears to be a developer machine name. If this is in production `App.config`, the service may be configured against the wrong host. This must be verified immediately.

## Migration Blockers

| Blocker | Impact | Detail |
|---|---|---|
| .NET Framework 4.7.2 | High | Cannot containerise; Windows-only; mainstream support ended. Must migrate to .NET 8 LTS |
| No CI/CD pipeline | High | Manual deployments are unauditable; cannot enforce quality gates |
| Dynamics GP on-premises | High | Dynamics GP is a legacy on-premises ERP; modernisation requires coordinated ERP migration (to Dynamics 365 or similar) |
| `AJBPK\SQL2014` hardcoded | High | Production cannot safely use this config without manual intervention |
| No automated tests | High | Cannot safely refactor without regression risk |
| OAuth secret in plaintext SQL | Medium | Must be migrated to Azure Key Vault before Gen-3 |
| Single Windows host deployment | Medium | No high availability; Windows host failure = AP integration failure |
| Polling architecture (3-hour interval) | Medium | AP bills may be delayed up to 3 hours; Procurify webhooks would provide near-real-time integration |

### Gen-3 Migration Path

1. **Immediate**: Verify `App.config` `sqlServerName` is correct in production. Audit OAuth secret encryption in `procurify_GlobalSettings`.

2. **Short-term**: Migrate to .NET 8; containerise. Add CI/CD pipeline (GitHub Actions). Add basic retry logic and error alerting (email or Teams notification on processing failure).

3. **Medium-term**: Replace polling with Procurify webhook integration (if supported by Procurify API tier). Add duplicate detection in staging table logic.

4. **Long-term**: Evaluate migration path from Dynamics GP to Dynamics 365 (cloud ERP). If Dynamics 365 is adopted, this integration may be replaced by a Dynamics 365 connector for Procurify, eliminating the need for a custom Windows Service entirely.
