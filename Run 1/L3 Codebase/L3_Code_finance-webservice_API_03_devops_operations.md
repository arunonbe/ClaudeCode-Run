# DevOps & Operations Report — finance-webservice_API

## 1. Build System

### 1.1 Build Technology

`finance-webservice_API` is a **C# .NET Framework 4.0** solution built with MSBuild. There is no Maven, Gradle, or other JVM build tool. The solution file is `FinanceWS.sln`.

### 1.2 Build Command

Per `README.md` lines 13–17, the build command is:

```cmd
cd C:\Windows\Microsoft.NET\Framework64\v4.0.30319
msbuild "C:\the path to our project directory\FinanceWS\FinanceWS.csproj" /t:Rebuild
```

This must be run on the **target deployment server** because of the hard dependency on `Microsoft.Dynamics.GP.eConnect` DLL, which is only available on servers with Dynamics GP installed.

### 1.3 Projects

| Project | Type | Output |
|---|---|---|
| `FinanceWS` | ASP.NET WCF Web Application | DLL deployed to IIS |
| `FinanceWSClient` | Console Application | Test client executable |

### 1.4 Target Framework

- **Framework**: .NET Framework 4.0 (`Web.config` line 14: `targetFramework="4.0"`)
- **Debug mode enabled**: `compilation debug="true"` in `Web.config` line 14 — this should be `false` in production

### 1.5 Dependencies

| Assembly | Source | Notes |
|---|---|---|
| `Microsoft.Dynamics.GP.eConnect` | GP server installation | Must be present on build/deploy server |
| `Microsoft.Dynamics.GP.eConnect.MiscRoutines` | GP server installation | For `GetNextDocNumbers` |
| `Microsoft.Dynamics.GP.eConnect.Serialization` | GP server installation | For `SOPTransactionType` XML serialization |
| `log4net` | NuGet/bin reference | Logging (`log4net.config`) |
| `System.Data.SqlClient` | .NET Framework | SQL Server ADO.NET |

---

## 2. CI/CD Pipeline

### 2.1 No Automated CI/CD

There is **no CI/CD pipeline** defined in this repository. There is:
- No `.gitlab-ci.yml`
- No `.github/workflows/` directory
- No Dockerfile
- No deployment scripts

The README explicitly states the manual build process: run `msbuild` on the target server and copy the resulting DLLs. This is a fully manual deployment model.

### 2.2 Environment Management

| Environment | Server | Notes |
|---|---|---|
| QA | `q-na-app01` (`README.md` line 9) | Must have GP installed |
| Production | `p-na-app31` (`README.md` line 10) | Must have GP installed |

Environment-specific configurations are stored as separate Web.config variants:
- `Web.config` — base configuration
- `Web.config-uatintl` — UAT international configuration
- `web.config.prodintl` — Production international
- `web.config.sit` — SIT environment
- `Web.Debug.config` — Debug transform
- `Web.Release.config` — Release transform
- `app.config.sampleuatIntl` — Sample UAT international config

These are manually copied/renamed during deployment, which is error-prone and a deployment risk.

---

## 3. Deployment

### 3.1 Deployment Model

The service is deployed as an **IIS-hosted WCF service** (`FinanceWS.svc`). The `.svc` file (`src/FinanceWS/FinanceWS.svc`) activates the WCF service factory. Deployment consists of:

1. Build on the target server using `msbuild`
2. Copy output DLLs to IIS application directory
3. Ensure appropriate Web.config is in place

### 3.2 IIS Configuration

The `<system.webServer>` section in `Web.config` (lines 17–18) enables all managed modules:
```xml
<modules runAllManagedModulesForAllRequests="true"/>
```

Service metadata is enabled via HTTP GET (`httpGetEnabled="true"`) and exception details are exposed to callers (`includeExceptionDetailInFaults="true"`, lines 22–23). **Both of these should be disabled in production** as they expose internal implementation details.

### 3.3 Log Configuration

Log4net is configured via a separate file: `log4net.config` (path set at `D:\c-base\FinanceWS\bin\log4net.config` in `Web.config` line 40). Log4net configuration is loaded from the filesystem at the hardcoded path, not from the application directory.

### 3.4 Temp Directory

Temp files for GP XML documents are written to `D:\c-base\FinanceWS\temp` (configured in `Web.config` lines 43–47). The IIS application pool identity must have read/write access to this directory.

---

## 4. Source Control

The repository uses Git (`.git/` directory present). The remote is tracked in `refs/remotes/origin/HEAD` pointing to the `master` branch. There is no branch protection, PR requirement, or code review workflow evidenced in the repository.

---

## 5. Monitoring and Observability

### 5.1 Logging

Log4net is used throughout all service classes. Log levels used include `Debug`, `Info`, `Warn`. There is no structured logging (JSON format) — all logs are plaintext. The centralized log path (`D:\c-base\FinanceWS\bin\log4net.config`) must be manually configured on each server.

### 5.2 Audit Table

The `so.FWSAuditTable` in `Banker_NA` provides a persistent record of every transaction. Operations teams can query this table to investigate failed transactions. The `Success` bit column and `Mesg` text column record outcome and error messages.

### 5.3 No APM / No Health Endpoint

There is no Application Performance Monitoring (APM), no WCF diagnostic tracing configuration (unless enabled in the undisclosed web.config transforms), and no health check endpoint.

---

## 6. Operational Risks

| Risk | Severity | Notes |
|---|---|---|
| Manual deployment | HIGH | No automation means human error risk on every release |
| `debug="true"` in Web.config | HIGH | May be in production — exposes internals |
| `includeExceptionDetailInFaults="true"` | HIGH | Stack traces visible to SOAP callers |
| GP server dependency | HIGH | Build and deploy must happen on GP host |
| Multiple Web.config variants | MEDIUM | Manual copy/rename — environment mismatch risk |
| No CI/CD | HIGH | No automated regression detection |
| Temp file cleanup reliance | MEDIUM | GP XML files with financial data persist if process crashes |
| Hardcoded email server `mail.citicorp.com` | MEDIUM | May no longer exist in Onbe environment |
| log4net.config at hardcoded path | MEDIUM | Silent log failure if path missing |
