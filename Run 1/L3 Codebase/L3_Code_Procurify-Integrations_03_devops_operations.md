# Procurify-Integrations — DevOps / Operations View

## Build System

| Component | Technology | Version | Notes |
|---|---|---|---|
| Language | C# | .NET Framework 4.7.2 | Not .NET Core / .NET 5+; Windows-only runtime |
| Build tool | MSBuild (via Visual Studio `.csproj`) | — | No CI/CD build pipeline visible in repository |
| Project type | Windows Service (`ServiceBase`) | — | Installed via Windows Service Control Manager |
| Solution file | `Procurify Integrations.sln` | — | Visual Studio solution |
| Package manager | NuGet (`packages.config`) | — | Old-style `packages.config` (not `PackageReference` format) |
| Target framework | `net472` | .NET Framework 4.7.2 | End of mainstream support; security fixes only through 2027 |

### NuGet Dependencies

| Package | Version | Purpose |
|---|---|---|
| `Newtonsoft.Json` | 13.0.3 | JSON serialization for Procurify API responses |
| `System.Net.Http` | 4.3.4 | HTTP client for Procurify API calls |
| `System.Net.Http.Json` | 7.0.1 | JSON extension methods for HttpClient |
| `System.Text.Json` | 7.0.2 | Alternate JSON support |
| `Microsoft.Bcl.AsyncInterfaces` | 7.0.0 | Async interface backport for .NET Framework |

No CI/CD pipeline files (GitHub Actions, Azure DevOps, Jenkins) are present in this repository. The service appears to be built and deployed manually via Visual Studio.

## Deployment

### Deployment Model: Windows Service
The application is a `System.ServiceProcess.ServiceBase` subclass (`ProcurifyIntegration`). Deployment involves:
1. Building the Visual Studio solution in Release mode.
2. Copying binaries to the target Windows host.
3. Installing the service via `ProjectInstaller` (`ProjectInstaller.cs`, `ProjectInstaller.Designer.cs`) using `InstallUtil.exe` or `sc.exe`.

There is no container, no Kubernetes manifest, no Terraform, and no Infrastructure-as-Code for this service. It runs as a Windows Service on a Windows host.

### Target Host
From `App.config`: `AJBPK\SQL2014` is a SQL Server named instance that appears to be a developer or UAT server name committed to source control. The actual production host is not documented in the repository.

### Service Identity
The Windows Service runs under an account with:
- Access to `TWO18` SQL Server database via Windows Integrated Authentication (`Trusted_Connection=True`).
- Network access to the Procurify API (external HTTPS).

The service account identity is not documented in the repository.

## Configuration Management

| Config Item | Location | Mechanism | Security Assessment |
|---|---|---|---|
| SQL Server name | `App.config` `sqlServerName` | `Properties.Settings.Default.sqlServerName` | Non-secret; but developer machine name committed |
| Database name | `App.config` `sqlDatabaseName` | `Properties.Settings.Default.sqlDatabaseName` | Non-secret |
| Timer interval | `App.config` `sInterval` | `Properties.Settings.Default.sInterval` | Non-secret |
| Test/Production toggle | `App.config` `sTestProduction` | `Properties.Settings.Default.sTestProduction` | Low-risk |
| OAuth Client ID | SQL table `procurify_GlobalSettings` | `dataSettings.GetSQLTable()` | Secret — stored in DB, not in file |
| OAuth Client Secret | SQL table `procurify_GlobalSettings` | `dataSettings.GetSQLTable()` | Secret — stored in DB as cleartext |
| Procurify API URLs | SQL table `procurify_GlobalSettings` | `dataSettings.GetSQLTable()` | Non-secret but configurable |

Storing OAuth credentials in a SQL table is a design choice that avoids hardcoding them in `App.config` (which would be in source control). However, the database itself must have adequate access controls to prevent unauthorized credential retrieval.

## Observability

| Aspect | Current State | Gap |
|---|---|---|
| Logging | Windows Event Log (`cEventLog`) | Transient — not centralized; no SIEM integration |
| Error alerting | None | Errors written to Event Log only; no email, no PagerDuty, no ServiceNow |
| Metric collection | None | No application metrics; no processing duration, no bill count, no error rate |
| Distributed tracing | None | No correlation IDs; no OpenTelemetry |
| Process monitoring | Windows Service Manager | Service stop/start state only; no health check beyond "is the process running?" |
| Audit trail | Windows Event Log entries only | Not durable beyond Event Log retention policy |

### Event Log Usage
`cEventLog.WriteDisplayErrorsWarnings()` is used consistently throughout the codebase. Log entries include:
- Service start/stop events
- Token retrieval start/end
- Vendor processing start/end per vendor
- AP bill processing errors (per-bill)
- AP staging errors

Without centralized log aggregation, these entries are only accessible on the Windows host running the service.

## Infrastructure Dependencies

| Dependency | Type | Criticality | Notes |
|---|---|---|---|
| `AJBPK\SQL2014` (TWO18 database) | SQL Server | Critical | Primary data store; hardcoded in `App.config` |
| Procurify API (`login.procurify.com/oauth/token`) | External HTTPS | Critical | OAuth token endpoint |
| Procurify AP Bills API | External HTTPS | Critical | AP bill data source |
| Procurify Vendor API | External HTTPS | Critical | Vendor management |
| Windows Service Control Manager | OS | Critical | Service lifecycle management |
| .NET Framework 4.7.2 runtime | OS | Critical | Must be installed on host |
| Windows Integrated Auth domain | Active Directory | Medium | SQL connection uses `Trusted_Connection=True` |

## Operational Risks

| Risk | Severity | Detail |
|---|---|---|
| No CI/CD pipeline | High | Manual builds and deployments; no automated testing, no deployment audit trail |
| No error alerting | High | Failed AP bills silently skipped; gaps may go undetected for 3 hours |
| No duplicate detection | High | Re-insertion of same bills on every cycle unless SP is idempotent |
| `AJBPK\SQL2014` hardcoded | High | Developer machine name in production config; likely non-functional in production without manual config change |
| Single-threaded timer | Medium | All processing (vendors + AP bills) runs serially on a single timer thread; a slow Procurify API call blocks the entire cycle |
| .NET Framework 4.7.2 (not .NET 8+) | Medium | Windows-only; no container support; security fixes only (mainstream support ended) |
| No health check endpoint | Medium | Cannot probe service liveness from an external monitoring system |
| OAuth token stored in plaintext DB | Medium | Credential compromise risk if DB is not properly access-controlled |
| No retry logic for Procurify API failures | Low | `APBills.BeginProcess()` catches errors per-bill but does not retry; transient API failures cause missed bills |
