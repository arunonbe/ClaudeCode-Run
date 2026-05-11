# Enterprise Architect Report — finance-webservice_API

## 1. Platform Generation Assessment

`finance-webservice_API` is a **second-generation, on-premises .NET WCF service** from the Microsoft stack. Key indicators:

| Indicator | Evidence |
|---|---|
| .NET Framework 4.0 | `Web.config` line 14: `targetFramework="4.0"` |
| WCF (Windows Communication Foundation) | `ServiceContract`, `OperationContract` attributes; `FinanceWS.svc` file |
| Microsoft Dynamics GP eConnect | `Microsoft.Dynamics.GP.eConnect` DLL dependency |
| ASMX/WCF hosting on IIS | `basicHttpBinding` SOAP endpoint |
| No dependency injection framework | Manual object construction throughout |
| ADO.NET direct SQL | `SqlConnection`, `SqlCommand`, `SqlDataReader` — no ORM |
| Manual config file management | Multiple Web.config variants |
| Citi email addresses in config | `kanchan.sardana@citi.com` in `Web.config` lines 55–65 |
| `com.citiprepaid` / `ecount` nomenclature in ClassDiagram | Legacy ecount/Citi era |

This places the codebase at approximately **10–15 years old** in design generation, written during the Citi Prepaid / ecount era, targeting the Microsoft Dynamics GP 2010 era.

---

## 2. Role in Enterprise Architecture

### 2.1 Integration Position

`finance-webservice_API` sits at the **ERP integration layer**, bridging Onbe's card platform billing engine (upstream caller) and Microsoft Dynamics GP (downstream ERP system). It also bridges to the email delivery channel for client invoicing.

```
[Card Platform Billing Engine]
          |
          | SOAP / basicHttpBinding (HTTP, no auth)
          v
[FinanceWS WCF Service] ← This service
          |
          |--→ [Banker_NA SQL Server]
          |       (pricing, audit, GP routing)
          |--→ [Dynamics GP eConnect API]
          |       (GP ECNT, ECAN, EMXN, etc.)
          |--→ [SMTP: mail.citicorp.com]
                  (client invoice emails)
```

### 2.2 Multi-Entity GP Architecture

A significant architectural feature is the **multi-entity GP routing** (`GPDBHelper.cs` line 18). The service supports multiple GP company databases, each mapped to a 4-character card program prefix. This architecture supports Onbe's multi-jurisdiction business (US, Canada, Mexico based on `DS_DB_GP_ecnt`, `DS_DB_GP_ecan`, `DS_DB_GP_emxn` repo names in the repo listing):

| GP Company | Jurisdiction | Prefix |
|---|---|---|
| ECNT | US | EC (ecount) |
| ECAN | Canada | CA |
| EMXN | Mexico | MX |
| EMEAM | EMEA | ME |

This multi-entity design demonstrates that `finance-webservice_API` is a shared service handling financial operations across multiple legal entities and jurisdictions.

---

## 3. Dependencies

### 3.1 Hard Dependencies (Service Cannot Function Without)

| Dependency | Type | Risk |
|---|---|---|
| Microsoft Dynamics GP eConnect | On-premise ERP DLL | CRITICAL — server-bound |
| `Banker_NA` SQL Server | Database | CRITICAL — all operations fail without it |
| `so.*` stored procedures | Database logic | HIGH — business logic embedded in DB |
| IIS hosting | Windows Server | HIGH — Windows-only |

### 3.2 Soft Dependencies (Degraded Function Without)

| Dependency | Impact if Missing |
|---|---|
| `mail.citicorp.com` SMTP | Email delivery fails; GP document still created |
| `D:\c-base\FinanceWS\temp\` | GP document creation fails entirely |
| `D:\c-base\FinanceWS\bin\log4net.config` | Silent log failure; service continues |

---

## 4. Fit / Gap Analysis Against Onbe Target Architecture

| Dimension | Current State | Target State Gap |
|---|---|---|
| Protocol | SOAP over basicHttpBinding (no auth) | REST over HTTPS with OAuth 2.0 / mTLS |
| Deployment | Manual IIS / Windows only | Azure App Service or container |
| ERP | On-premise Dynamics GP via eConnect | Dynamics 365 Finance (cloud) or equivalent |
| Configuration | Multiple Web.config files, manual copy | Azure App Configuration |
| Secrets | Connection strings in Web.config | Azure Key Vault |
| Observability | Log4net file logs | Azure Application Insights |
| Build/Deploy | Manual msbuild | Azure DevOps Pipelines |
| Framework | .NET Framework 4.0 | .NET 8+ |
| Testing | None visible | xUnit/NUnit with integration tests |

---

## 5. Migration Complexity Assessment

Migration complexity is rated **VERY HIGH** for the following reasons:

1. **Dynamics GP eConnect Dependency**: The Microsoft Dynamics GP eConnect API is on-premise software with a specific DLL that must be installed on the server hosting the service. Migration to cloud requires either migrating GP to Dynamics 365 Finance or implementing an on-premise gateway.

2. **Stored Procedure Business Logic**: Critical business logic is in SQL stored procedures (`so.items_price_per_contract`, `so.get_gp_database`, `so.get_so_from_job_id`) in the `Banker_NA` database. These must be migrated or re-hosted.

3. **Multi-Company GP Routing**: The dynamic GP database selection logic is specific to the Onbe multi-entity architecture and would need careful mapping to any replacement ERP solution.

4. **No Automated Tests**: Zero test coverage means any migration is a complete rewrite without regression safety nets.

5. **SOX Impact**: Changes to billing and revenue recognition systems require SOX change management processes, including impact analysis, testing, and sign-off from Finance and Internal Audit.

6. **Manual Deployment**: The manual build-on-server-with-GP approach means there is no documented infrastructure-as-code. Migration must include capturing the full deployment topology.

7. **.NET Framework 4.0 to .NET 8+**: eConnect is not available for .NET Core/.NET 5+. The entire GP integration layer would need to be rewritten using Dynamics 365 Business Central APIs or a custom middleware.

---

## 6. Lifecycle Recommendation

This service is a candidate for **strategic replacement** as part of an ERP modernization initiative:

1. **Near-term**: Migrate to HTTPS (add TLS termination in front of IIS), disable `debug=true` and `includeExceptionDetailInFaults=true`, and add Windows authentication to the WCF endpoint
2. **Medium-term**: Wrap in an Azure API Management gateway for authentication, rate limiting, and observability
3. **Long-term**: Replace Dynamics GP with Dynamics 365 Finance; rebuild FinanceWS as a .NET 8 REST microservice with Azure Service Bus integration for async invoice processing

The GP dependency is the primary blocker for cloud migration. It is recommended to align the timeline of this service's modernization with the ERP upgrade roadmap.
