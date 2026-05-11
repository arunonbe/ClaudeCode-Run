# atlys_WAPP — Enterprise Architect View

## Platform Generation (Gen-1/Gen-2/Gen-3)

**Classification: Gen-1**

Atlys_WAPP is a Generation-1 application by every measurable dimension:

| Criterion | Evidence |
|---|---|
| UI technology | Microsoft Silverlight 4.0 — browser plugin, discontinued October 2021 |
| Service technology | WCF (Windows Communication Foundation) with custom binary HTTP binding — .NET 3.0-era RPC |
| Data access | Raw ADO.NET with `SqlCommand` / `SqlDataAdapter` / `DataTable` — no ORM |
| Architecture | 2-tier: thick client (Silverlight XAP) + WCF service + SQL Server; no API layer, no message bus |
| Configuration | Hardcoded strings, no secrets management, no environment separation |
| Build/deploy | Manual Visual Studio build, no CI/CD, no containerization |
| Target framework | .NET Framework 4.0 + Silverlight 4.0 (both EOL) |
| Version | `"1.0.9.1"` — version string hardcoded in both client and server |

The application pre-dates REST APIs, microservices, cloud infrastructure, and modern DevSecOps practices. It was almost certainly built circa 2010–2014 based on the toolchain (Expression Blend 3, VS 2010 toolchain, .NET 4.0).

## Business Domain

**Financial Management & Reporting — Prepaid Card Programs**

The application is scoped to internal financial operations for a prepaid card business unit. It is not a card-issuing or transaction-processing system — it sits above the transactional layer and consumes aggregated data (actuals imported from card processor files) to support:

- Program profitability management (revenue, costs, GP)
- Financial forecasting (multi-version, multi-period)
- Sales commission management
- GL accounting interface and reconciliation
- Regulatory compliance tracking (Durbin/Reg II BIN exemptions)
- Internal audit and period controls

The domain maps directly to Onbe's prepaid card business, specifically the finance and FP&A functions supporting client programs.

## Role in Platform

Atlys is an **internal back-office tool** — not customer-facing and not part of the card issuance or transaction authorization path. Its role in the broader Onbe platform:

1. **Consumer of processed transaction data**: Imports actuals from card processor/transaction instance files (`Import.xaml`, `dbo.sys_imports` implied; `FileTxIdItem` tracks file-to-transaction-ID mappings)
2. **Publisher of GL data**: Generates GL files and journal entry files consumed by ERP/accounting systems (`RptGLFile`, `RptJEFile`)
3. **Reconciliation layer**: Compares cube/OLAP data against transactional source data (`dbo.sys_cube_reconcile`, `dbo.sys_bal_reconcile`)
4. **Reporting layer**: Provides cross-tab, pivot, and Excel export capabilities for finance and executive stakeholders
5. **Commission calculation engine**: Computes and stores sales commissions; generates commission statements

It does **not** handle: card issuance, cardholder data, authorization, settlement, ACH origination, or customer-facing operations. It is purely a finance internal tool.

## Dependencies

**Upstream dependencies (systems Atlys consumes data from):**

| Dependency | Evidence |
|---|---|
| Card transaction processor / data warehouse | `ATLYS_RvCR` and `ATLYS_FcCR` are populated by batch imports; `FileTxIdItem` (`StartTxId`, `EndTxId`) tracks transaction file boundaries |
| SSAS (SQL Server Analysis Services) cubes | `cube1_name`, `cube2_name`, `views_db`, `views_schema`, `prgid_mdx_str`, MDX-related fields in `CompListItem.s[]` array; `dbo.sys_cube_reconcile` stored proc; `sys_smots` (SMoTS = Settlement Management on Transaction System?) |
| Card processor reference data (BIN data) | `dbo.sys_durbin` stores BINs with Durbin exemption; BINs come from card network/processor |
| First Data Resources (FDR) | `dbo.sys_fdr` stored procedure — `act.StartsWith("fdr")` in `GetCT` (wsAtlys.svc.cs line 2460); FDR is a major card processor |
| Active Directory | `authentication mode="Windows"` — user identities managed in AD |

**Downstream dependencies (systems that consume Atlys outputs):**

| Dependency | Evidence |
|---|---|
| ERP / General Ledger system | GL file export (`RptGLFile`), JE file export (`RptJEFile`) — format and target system unknown from source |
| Excel / reporting consumers | Report exports are XML-format Excel files (.xml SpreadsheetML) served via URL |
| Salesforce (potential) | `dbo.sys_sf_upload` stored proc referenced in `GetCT` (`act.Equals("sfupload")`) — may push data to Salesforce CRM |

**Internal database dependencies (cross-database queries):**

The three databases (`ATLYS_E`, `ATLYS_FcCR`, `ATLYS_RvCR`) are queried from a single SQL Server instance. Cross-database joins likely exist within stored procedures (not visible from application code).

## Integration Patterns

| Pattern | Implementation | Notes |
|---|---|---|
| RPC via WCF | `wsAtlys` and `wsReporting` WCF services with binary HTTP binding | Tight coupling; not RESTful; binary protocol not interoperable with non-.NET clients |
| Stored procedure facade | All DB operations via named stored procedures with `@action` parameter dispatch | Single-SP multi-action pattern (e.g., `dbo.sys_user` handles login, logout, changepwd, msg_list) — reduces surface area but creates monolithic SPs |
| Polling heartbeat | `DispatcherTimer` in `MainPage.xaml.cs` calls `CntUnreadMsgAsync` every 60 seconds | Primitive push simulation |
| File-based report delivery | Reports generated as GUID `.xml` files in web directory; URL returned to client for download | No streaming, no blob storage |
| Batch import | `Import` operation triggers `dbo.sys_imports` (implied) for date-range data ingestion | Exact mechanism not visible; likely file-based batch from processor |
| Direct OLAP query | MDX strings (`prgid_mdx_str`) stored in configuration for SSAS cube queries | Tightly coupled to specific SSAS cube names and schemas |

**No event-driven patterns**: No message queues (RabbitMQ, Azure Service Bus, Kafka), no webhooks, no pub/sub.
**No API gateway**: Direct WCF service calls from client.
**No service mesh**: Single monolithic WCF service.

## Strategic Status

**Status: End-of-Life / Legacy Decommission Candidate**

| Factor | Assessment |
|---|---|
| Runtime viability | Critically impaired — Silverlight plugin not available in any current browser |
| Security posture | Poor — no HTTPS, hardcoded keys, SQL injection vector, debug mode on |
| Maintainability | Very low — WCF/Silverlight expertise extremely scarce; no CI/CD; no tests |
| Scalability | None — stateful SQL-session model; no horizontal scaling |
| Cloud readiness | Zero — Windows Auth, hardcoded server IPs, absolute Windows paths |
| Regulatory alignment | Gaps in PCI DSS, no HTTPS, secrets in source |
| Business value | Active (functional for internal finance team if legacy browser/OS available) |

The application is almost certainly running on a dedicated Windows workstation with Internet Explorer and Silverlight installed, or has already been partially or fully replaced. It represents a significant operational and security liability.

## Migration Blockers

The following are concrete blockers to a Gen-3 (cloud-native, REST API + modern SPA) migration:

| Blocker | Details | Remediation Effort |
|---|---|---|
| **Silverlight UI** | 70+ XAML views with code-behind; Silverlight-specific controls (DataGrid, DataForm, DataVisualization toolkit, navigation framework) | Very High — complete UI rewrite required in React/Angular/Vue or Blazor |
| **WCF binary binding** | Custom WCF binary HTTP protocol; Silverlight WCF proxy generated stubs (`wsdAtlys`, `wsdReporting`); not compatible with REST or gRPC without full rewrite | High — replace with REST API (ASP.NET Core controllers or minimal API) |
| **Monolithic stored procedures** | ~60+ stored procedures with action-dispatch pattern; cross-database queries; no visible DDL | High — requires DB schema documentation, SP decomposition, possible ORM introduction |
| **Windows Authentication** | AD-backed Windows auth for both IIS and SQL Server; not compatible with cloud identity (Entra ID / OAuth) without ADFS/hybrid bridge | Medium-High — requires identity migration to OAuth2/OIDC |
| **Three-database architecture** | `ATLYS_E`, `ATLYS_FcCR`, `ATLYS_RvCR` on a single named SQL Server instance; cross-DB dependencies unknown | Medium — requires DB consolidation or microservice decomposition |
| **SSAS cube dependencies** | MDX queries and cube reconciliation tied to specific SSAS cube topology | Medium — requires cube schema documentation and possible migration to Azure Analysis Services or Power BI Premium |
| **Hardcoded configuration** | Server names, encryption keys, file paths all hardcoded | Low-Medium — requires secrets management (Key Vault), parameterized configuration |
| **No tests** | Zero test coverage — no unit, integration, or E2E tests | Medium — risk of regression during migration without test harness |
| **No API documentation** | WCF WSDL available but ~60 service operations undocumented | Medium — requires API inventory and documentation before migration |
| **FDR / SMoTS integration** | `dbo.sys_fdr` and `dbo.sys_smots` suggest live integrations with card processor; migration must preserve these data flows | Unknown — requires integration mapping exercise |
