# atlys_WAPP — DevOps & Operations View

## Build & Packaging

The solution is a Visual Studio 2010-era .NET solution (`AtlysSL.sln`) containing two projects:

| Project | File | Output | Framework |
|---|---|---|---|
| `AtlysSL` | `AtlysSL\AtlysSL.csproj` | `AtlysSL.xap` (Silverlight XAP package) | Silverlight 4.0 (TargetFrameworkIdentifier=Silverlight, TargetFrameworkVersion=v4.0) |
| `AtlysSL.Web` | `AtlysSL.Web\AtlysSL.Web.csproj` | `AtlysSL.Web.dll` (ASP.NET Web Application) | .NET Framework 4.0 |

**Build toolchain:**
- MSBuild 4.0 (`ToolsVersion="4.0"`)
- Silverlight build targets: `$(MSBuildExtensionsPath32)\Microsoft\Silverlight\$(SilverlightVersion)\Microsoft.Silverlight.CSharp.targets`
- Web project targets: `$(MSBuildExtensionsPath32)\Microsoft\VisualStudio\v10.0\WebApplications\Microsoft.WebApplication.targets`
- WCF proxy generation: `WCF Proxy Generator` for `wsdAtlys` and `wsdReporting` service references
- `ExpressionBlendVersion` = `3.0.1927.0` — indicates the UI was designed in Expression Blend 3

**Build outputs:**
- `AtlysSL.xap` is copied to `AtlysSL.Web\ClientBin\AtlysSL.xap` (the `SilverlightApplicationList` entry in the web project links the two)
- No NuGet package references; all Silverlight SDK assemblies are version-pinned GAC references (e.g., `System.Windows.Controls, Version=2.0.5.0, PublicKeyToken=31bf3856ad364e35`)

**No automated build system** (no `Makefile`, `Jenkinsfile`, `.github/workflows`, `azure-pipelines.yml`, `build.bat`, or equivalent) is present anywhere in the repository.

## Deployment

**Server-side (AtlysSL.Web):**
- Deployed as an IIS application on Windows Server
- Development port configured as `1333` (`IISUrl=http://localhost:1333/`) in the `.csproj` but with `UseIISExpress=true`, suggesting local development used IIS Express
- Custom server URL `http://192.168.1.201` is present in the project file (`CustomServerUrl`), indicating a known target deployment server on a private subnet
- Log files written to `c:\AtlysSL\logs\` (WCF diagnostic logs: `custom_messages.svclog`, `web_messages.svclog`, `web_tracelog.svclog`) — hardcoded local Windows path in `Web.config` lines 38–52
- Application log (`errlog.txt`) written to `{ApplicationPhysicalPath}//Logs//errlog.txt`
- SQL server target: `ppamwdcdifsql1\ppamwdcdifsql1` — hardcoded in `Web.config` `appSettings`

**Client-side (AtlysSL):**
- Delivered as a `.xap` file served from `ClientBin/AtlysSL.xap` via the `AtlysSL.aspx` host page
- Requires Silverlight 4.0 plugin installed in the browser (Internet Explorer only for practical purposes)
- `EnableOutOfBrowser=false` — must run inside browser

**No containerization**: No Dockerfile, no `docker-compose.yml`, no Kubernetes manifests.

**No infrastructure-as-code**: No Terraform, Bicep, ARM templates, Ansible, or similar.

## Configuration Management

| Configuration Item | Location | Value / Status |
|---|---|---|
| SQL Server name | `AtlysSL.Web\Web.config`, `appSettings` key `sv` | `ppamwdcdifsql1\ppamwdcdifsql1` — **production server name committed to source control** |
| WCF binding timeouts | `Web.config` `customBinding` | `sendTimeout`, `closeTimeout`, `openTimeout`, `receiveTimeout` all set to `00:10:00` (10 minutes) |
| Command timeout | `wsAtlys.svc.cs` line 24; `wsReporting.svc.cs` line 24 | `iCommTimeout = 7200` seconds (2 hours) — extremely long DB command timeout |
| WCF transport | `Web.config` | `binaryMessageEncoding` + `httpTransport` — binary HTTP, no TLS at service level |
| ASP.NET authentication | `Web.config` line 75 | `mode="Windows"` — Windows Integrated Authentication |
| Compilation | `Web.config` line 68 | `debug="true"` — **debug mode enabled in committed config** |
| Custom errors | `Web.config` line 67 | `mode="Off"` — **full error details exposed to all clients** |
| App version | `wsAtlys.svc.cs` line 23; `Login.xaml.cs` line 18 | `"1.0.9.1"` hardcoded in both client and server |
| Encryption key | `Enc.cs` line 24; `wsAtlys.svc.cs` line 6053 | `"WJKGRSCQ3#4yujfg"` / `"theSLAPPass"` — **hardcoded secrets in source** |
| WCF diagnostic log path | `Web.config` lines 38–52 | `c:\AtlysSL\logs\` — **absolute Windows path, no environment variable** |
| MEX endpoint | `Web.config` | `mexHttpBinding` on both services — WSDL/metadata publicly accessible |

There is **no environment-based configuration switching** (no `Web.Release.config` transforms, no environment variable injection, no secrets management solution such as Azure Key Vault or HashiCorp Vault).

## Observability

**Error Logging:**
- Flat file `errlog.txt` at `{ApplicationPhysicalPath}//Logs//errlog.txt`
- Written by `ErrorLog(msg, stkTrace)` method in `wsAtlys.svc.cs` (lines 6017–6044)
- Contents: exception message, stack trace, timestamp
- Max size 100,000 bytes before truncation — no rotation, no indexing
- Client-side errors are sent to `wsAtlys.ErrLog` from `App.xaml.cs` `Application_UnhandledException` handler (line 58)
- An `errlog.txt` file exists in the committed repository at `AtlysSL.Web\errlog.txt` — **actual error log committed to source control**

**WCF Diagnostics (when enabled):**
- `AtlysCustomTracing` → `c:\AtlysSL\logs\custom_messages.svclog`
- `System.ServiceModel.MessageLogging` → `c:\AtlysSL\logs\web_messages.svclog`
- `System.ServiceModel` trace → `c:\AtlysSL\logs\web_tracelog.svclog`
- Switch level `Warning, ActivityTracing` — currently set to warnings only
- Message logging: `logMalformedMessages="true"`, `logMessagesAtTransportLevel="true"`, `logEntireMessage="false"`

**No APM integration**: No Application Insights, Datadog, New Relic, Splunk, or structured logging framework (no log4net, NLog, Serilog) is referenced in any project file or source file.

**No health check endpoints**: No `/health`, `/ping`, or status endpoints.

**Heartbeat**: `MainPage.xaml.cs` runs a `DispatcherTimer` with 1-minute interval calling `CntUnreadMsgAsync` — this is a UI heartbeat for unread message count, not a server health check.

## Infrastructure Dependencies

| Dependency | Details |
|---|---|
| SQL Server (named instance) | `ppamwdcdifsql1\ppamwdcdifsql1` hosting `ATLYS_E`, `ATLYS_FcCR`, `ATLYS_RvCR` |
| Windows Server + IIS | Host for `AtlysSL.Web` ASP.NET 4.0 application |
| .NET Framework 4.0 | Server runtime |
| Silverlight 4.0 SDK | Client build requirement; Silverlight 4.0 plugin required on client machine |
| Internet Explorer | Only browser that ran Silverlight; EOL for Silverlight support |
| Windows Authentication (Active Directory / Kerberos) | `authentication mode="Windows"` in Web.config; service account for SQL Integrated Security |
| OLAP/Cube infrastructure | `cube1_name`, `cube2_name`, `views_db`, `views_schema` fields in `CompListItem` and `txinstances` detail suggest SQL Server Analysis Services (SSAS) cubes are used for certain cross-tab reports |
| Expression Blend 3 | Design-time tooling (historical, not a runtime dependency) |

## Operational Risks

| Risk | Evidence | Severity |
|---|---|---|
| **Silverlight EOL** | `TargetFrameworkIdentifier=Silverlight`, `SilverlightVersion=v4.0`; plugin unsupported in all modern browsers | Critical |
| **2-hour SQL command timeout** | `iCommTimeout = 7200` — long-running queries can hold DB connections for 2 hours | High |
| **Debug mode in production config** | `compilation debug="true"` in committed `Web.config` | High |
| **Custom errors Off** | `customErrors mode="Off"` — full .NET stack traces returned to clients | High |
| **No HTTPS** | `httpTransport` in WCF binding — credentials and session tokens transmitted unencrypted | High |
| **MEX endpoints exposed** | Both `wsAtlys` and `wsReporting` expose `mex` endpoints with `httpGetEnabled="true"` — WSDL publicly discoverable | Medium |
| **No connection pooling configuration** | New `SqlConnection` created per service call with no explicit pooling min/max | Medium |
| **SQL server name in source** | `ppamwdcdifsql1\ppamwdcdifsql1` in `Web.config` — infrastructure exposed in version control | Medium |
| **Temp report files in web root** | GUID `.xml` files in `//Logs//` are web-accessible; contain financial data | Medium |
| **errlog.txt committed** | Actual error log in repo at `AtlysSL.Web\errlog.txt` | Low-Medium |
| **No graceful shutdown** | `Application_Exit` handler commented out (`App.xaml.cs` lines 31–36); logout not called on browser close | Low |

## CI/CD

**No CI/CD pipeline exists.** There is no:
- Jenkinsfile
- GitHub Actions workflow
- Azure DevOps pipeline
- Build script (`.bat`, `.ps1`, `.sh`)
- NuGet restore automation
- Test project or unit tests

Deployment is entirely manual — developers build in Visual Studio, copy outputs to IIS server, update `Web.config` manually. The presence of a developer IP (`192.168.1.201`) and a hardcoded SQL server name in committed config confirms an ad-hoc, manual deployment model with no environment separation.
