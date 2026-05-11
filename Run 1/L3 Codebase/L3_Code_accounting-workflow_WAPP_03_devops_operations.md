# accounting-workflow_WAPP — DevOps & Operations View

## Build & Packaging

| Attribute | Value |
|---|---|
| Solution file | `AccountingWorkflow.sln` (Visual Studio 2010 format, Format Version 11.00) |
| Primary project | `AccountingWorkflow\AccountingWorkflow.csproj` (ToolsVersion 4.0 / MSBuild) |
| Target framework | .NET Framework 3.5 (`<TargetFrameworkVersion>v3.5</TargetFrameworkVersion>`) |
| Output type | `WinExe` (Windows Forms executable) |
| Assembly name | `AccountingWorkflow` |
| Assembly version | `1.0.0.0` (AssemblyInfo.cs); Application revision `46`, Application version `1.0.0.46` in the `.csproj` |
| Build configurations | `Debug|AnyCPU`, `Release|AnyCPU` |
| Additional projects | `Install\Install.csproj` — creates desktop/start-menu shortcuts via `IWshRuntimeLibrary` (WSH COM) |
| Legacy setup project | `AWSetup\AWSetup.vdproj` (Visual Studio Deployment Project, VS 2010 era) — also duplicated as `AWSSetup\AWSSetup.vdproj` |
| `ehash` project | Referenced in solution (`ehash\ehash.csproj`) but directory not present in repository; likely a password-hashing utility that was planned or removed |
| Key dependencies | `adodb.dll` (ADODB COM PIA, local hint path `Program Files\Microsoft.NET\Primary Interop Assemblies\`), `Microsoft.Office.Interop.Excel v11.0` (Office 2003 PIA), `SchCalendar.dll` (custom calendar control at `..\..\Controls\SchCalendar.dll`), `Microsoft.VisualBasic.PowerPacks.Vs v10.0` |
| Code signing | `AccountingWorkflow_TemporaryKey.pfx` referenced; `SignManifests=false` — **signing is disabled** |
| Bootstrapper | Configured to install `.NET Framework 3.5 SP1` and `Windows Installer 3.1` |

**Build is not automated.** No `Makefile`, `build.ps1`, `build.sh`, `.github/workflows`, `azure-pipelines.yml`, Dockerfile, or any CI script is present in the repository.

---

## Deployment

| Attribute | Value |
|---|---|
| Deployment mechanism | ClickOnce-style publish to UNC share: `<PublishUrl>\\devserv2\apps\AWf\</PublishUrl>` |
| Install type | `<Install>false</Install>` — application runs from the UNC share, not installed locally |
| Install source | `<InstallFrom>Unc</InstallFrom>` |
| Auto-update | `<UpdateEnabled>false</UpdateEnabled>` — updates disabled; manual republish required |
| Desktop shortcut | Created by `Install\Program.cs` using `IWshRuntimeLibrary.IWshShortcut`; shortcut name `AW.lnk` pointing to `AccountingWorkflow.exe` |
| Target platform | Windows (WinForms); `AnyCPU` target; requires .NET 3.5 SP1 runtime on client |
| Application manifest | `Properties\app.manifest` — specifies `TargetZone=LocalIntranet`; `TrustUrlParameters=true`; `AutorunEnabled=true` |

The `AWSetup.vdproj` / `AWSSetup.vdproj` files suggest an alternative MSI-based installer was also prepared, though the two `.vdproj` files in different folders (`AWSetup` vs `AWSSetup`) indicate a duplicated or forked setup project with no clear canonical version.

---

## Configuration Management

| Configuration Item | Location | Notes |
|---|---|---|
| Database server IP | `AccountingWorkflow\app.config` (`<setting name="Server">192.168.10.200</setting>`) and `AccountingWorkflow\Properties\Settings.settings` | Hardcoded in both config and settings file; no environment-variable or secrets-manager indirection |
| Application mode (FinSt vs TaskMon) | `userSettings` in `app.config`: `<setting name="Appr">2</setting>`; `AppSet.cs` reads/writes `Properties.Settings.Default.Appr` and calls `.Save()` | Per-user setting stored in the user profile (`allowExeDefinition="MachineToLocalUser"`); default value `2` (TaskMon mode) |
| Database credentials | `SQLData.cs` lines 34 and 56 — `User Id=raf;Pwd=[REDACTED — rotate immediately]` hardcoded in C# source; not in any config file | Cannot be changed without recompiling |
| Default document browse directory | `TaskDoc.cs:346`, `TaskDoc.cs:703`, `NewDoc.cs:48` — `"F:\\Daily_Recons1"` hardcoded in source | Not configurable without recompile |
| SchCalendar control | `HintPath` references `..\..\Controls\SchCalendar.dll` — a relative path outside the repository | External dependency not under source control |
| Excel/Office version | `Microsoft.Office.Interop.Excel Version=11.0.0.0` (Office 2003) | Hardcoded version; newer Office installations may require binding redirects or cause COM failures |
| ADODB version | `adodb Version=7.0.3300.0` with local hint path to developer machine's Program Files | Extremely brittle; path will not exist on most machines |

No environment-separation (dev / test / prod) configuration exists. There is one set of settings pointing at a single SQL Server IP.

---

## Observability

| Capability | Implementation | Gaps |
|---|---|---|
| Error logging | `ErrorHandler.cs` hooks `Application.ThreadException` and `AppDomain.CurrentDomain.UnhandledException`; delegates to `ErrorLog.WriteToErrorLog` | Plain-text file (`errlog.txt`) in app directory; no log levels, no rotation, no remote aggregation |
| Error log content | Computer name, OS username, exception message, stack trace, timestamp written to `<StartupPath>\Errors\errlog.txt` | No log IDs; no correlation with session ID; file appended indefinitely |
| Progress feedback | `PBForm` (progress bar form) shown during login `BW_DoWork` background worker; timer-driven step | No real progress reporting — marquee style implied |
| User-visible errors | `MessageBox.Show(LReader["sError"].ToString())` throughout all forms | SP error text shown directly to user; no abstraction layer |
| Application tracing | `TRACE` compile constant in Release; no actual `System.Diagnostics.Trace` statements found in code | Effectively no tracing |
| Performance monitoring | None | No timing, no counters, no APM integration |
| Audit trail | Server-side only: every SP call includes `@s_id` for server-side correlation | No client-side activity log; SP-level auditing depends entirely on database |

---

## Infrastructure Dependencies

| Dependency | Type | Version / Notes |
|---|---|---|
| SQL Server @ 192.168.10.200 | Database (required) | Version unknown; accessed via `System.Data.SqlClient` (SQL Native Client ODBC for ADODB path) |
| `ATLYS_E` database | Source GL (required for account import) | Same SQL Server instance |
| `ATLYS_RvCR` database | Secondary source (declared in `SQLData.Conn(1)`; not directly exercised from client code found) | Same SQL Server instance |
| `AcctgWf` database | Primary application DB (required) | Same SQL Server instance |
| `\\devserv2\apps\AWf\` | UNC file share for ClickOnce deployment | Must be accessible for app to run from network |
| `F:\Daily_Recons1\` | Document storage (local or mapped drive) | Hardcoded; must exist on client machine |
| .NET Framework 3.5 SP1 | Runtime | Must be installed on client; bootstrapper configures installer |
| Microsoft Office (Excel 11.0 / 2003+) | COM automation (required for Excel reports) | `Microsoft.Office.Interop.Excel v11.0` |
| ADODB (Primary Interop Assembly 7.0.3300) | COM interop | Path hardcoded to developer `Program Files` |
| `SchCalendar.dll` | Custom calendar control | Path `..\..\Controls\SchCalendar.dll` outside the repo |
| Windows Script Host (`IWshRuntimeLibrary`) | Install shortcut creation | Used only in `Install` project |
| `AccountingWorkflow_TemporaryKey.pfx` | ClickOnce signing | Not committed (listed in `.csproj`; not found in glob); signing disabled anyway |

---

## Operational Risks

1. **No DR / redundancy:** Single SQL Server IP hardcoded. If the server at `192.168.10.200` is unavailable, the application is non-functional with no fallback path.
2. **No version management / rollback:** `UpdateEnabled=false` means clients will not auto-update. There is no mechanism to roll back a deployed version.
3. **Excel COM automation instability:** `AcctDetails.adReport()` launches a visible Excel instance via `ApplicationClass`. COM interop with Excel is known to leave orphaned processes and fails silently on Office version mismatches.
4. **Log file growth:** `errlog.txt` is appended indefinitely with no rotation. On a heavily-used or crashing client, this file could grow without bound.
5. **Dependency on external DLLs not in repo:** `SchCalendar.dll` and `adodb.dll` are referenced via absolute/relative hint paths outside the repository. Build will fail on any machine without these pre-installed.
6. **Document attachment path fragility:** Documents stored as local filesystem paths (`F:\Daily_Recons1\`). Path changes, drive remapping, or file moves silently break document links.
7. **No connection pooling configured:** Multiple forms open and close `SqlConnection` objects per operation without explicit pooling settings; default .NET connection pooling applies but is unmanaged.
8. **Single-threaded UI with synchronous DB calls in most forms:** Only `Login.cs` uses a `BackgroundWorker`; all other DB calls block the UI thread, risking unresponsiveness on slow network queries.

---

## CI/CD

**No CI/CD pipeline exists.** The repository contains:
- No pipeline configuration files (`.github/workflows/`, `azure-pipelines.yml`, `Jenkinsfile`, `GitLab CI`, etc.)
- No test projects or automated test scripts
- No Dockerfile or container configuration
- No NuGet package restore configuration (all references are GAC or hint-path DLLs, not NuGet packages)

Deployment is a manual, developer-initiated ClickOnce publish to `\\devserv2\apps\AWf\`. The `ApplicationRevision` is `46` and `ApplicationVersion` is `1.0.0.46`, incremented manually in the `.csproj` file.
