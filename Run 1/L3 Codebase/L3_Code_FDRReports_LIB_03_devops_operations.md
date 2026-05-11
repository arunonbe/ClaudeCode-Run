# DevOps / Operations View — FDRReports_LIB

## Build System

**Language**: C# (.NET Framework 4.0)  
**Build Tool**: MSBuild (`.csproj` project file)  
**IDE**: Visual Studio (project was created with VS 2010 based on ToolsVersion="4.0", `FDRReportProject.csproj` line 1)  
**README note**: "Visual Studio Code to be used to compile, until conversion to ETL/ELT process"  
**Output**: `FDRReports.exe` (x86 Console Application)  
**Solution File**: `FDRReports.sln`

### MSBuild Command
```powershell
msbuild FDRReports.sln /p:Configuration=Release
```

Or open in Visual Studio and build.

### Dependencies

| Reference | Source |
|-----------|--------|
| `System` | .NET BCL |
| `System.Core` | .NET BCL |
| `System.Xml.Linq` | .NET BCL |
| `System.Data.DataSetExtensions` | .NET BCL |
| `Microsoft.CSharp` | .NET BCL |
| `System.Data` | .NET BCL (ADO.NET) |
| `System.Xml` | .NET BCL |

**No third-party NuGet packages**. All dependencies are .NET Framework BCL assemblies. No NuGet package management (no `packages.config` or `PackageReference`).

## CI/CD Pipeline

There is **no CI/CD pipeline** in this repository. There are no:
- GitHub Actions workflows
- Azure DevOps pipelines
- Jenkins pipelines
- `.github/` directory

This is a fully manual build-and-deploy process. The README mentions "until conversion to ETL/ELT process", indicating this was intended to be a transitional tool.

The `.gitignore` file excludes standard Visual Studio build artifacts (`bin/`, `obj/`, `.vs/`).

## Deployment Model

This is a **scheduled Windows batch job**. Deployment pattern:
1. Compile `FDRReports.exe` on developer workstation.
2. Copy `FDRReports.exe` to the Windows server (historically: GP/DynamicsGP server environment based on file paths).
3. Schedule via Windows Task Scheduler or SQL Server Agent job.
4. The job runs against the network share containing daily FDR RMS28 files.

**Runtime environment**: Windows Server (on-premises). The file paths in `FDRReports.cs` (UNC paths like `\\ppamwdcpdsql5\DynamicsGP\FDRReport\`) confirm a Windows Server on-premises deployment connected to the Great Plains/Dynamics GP infrastructure.

**Scheduling**: The application processes all files in the report directory in a single run. The UAT and production environments are processed sequentially in the same execution.

## Operations Details

### Startup Sequence
1. Application connects to `Banker.dbo.SSISJobConfigurations` to retrieve job parameters (report path, DB server, email addresses).
2. Iterates over `ConfigurationArray` = `{41, 39}` (UAT first, then production).
3. For each environment, reads all files in the configured report path.
4. For each file, reads line by line, detecting report type by header prefix.
5. Parses each line into the appropriate DataTable.
6. Bulk-inserts DataTable contents into the `ECNT` SQL database.

### Error Handling
Minimal. The application uses `try/catch` blocks but error handling is limited to preventing crashes. There is no retry logic, no dead-letter mechanism, no alerting.

### Email Notification
The application reads `FromEmail` and `ToEmail` from the job configuration XML. These are presumably used to send completion/error emails (the actual email-sending code is further into the file, not fully read here).

### Report Detection Logic
Report type is detected by checking the first 8 characters of each line:
- `"1VS-110"` → switch to VS-110 parsing mode
- `"1VS-115"` → switch to VS-115 parsing mode
- `"1CD-523"` → switch to CD-523 parsing mode
- `"1CD-025"` → switch to CD-025 parsing mode
- `"1CD-525"` → switch to CD-525 parsing mode
- `"1DD-441"` → switch to DD-441 parsing mode
- `"1SD-018"` → switch to SD-018 parsing mode
- (VS-120, VS-130 detected similarly)

This state-machine approach using boolean flags (`bReport_VS110`, `bReport_DD441`, etc.) is brittle — if a report appears multiple times in the file or appears in an unexpected order, flags may not reset correctly.

## Operational Risks

1. **No CI/CD**: Any code change requires manual compile-and-deploy. No automated testing, no automated vulnerability scanning.
2. **Manual deployment**: No deployment automation, version tracking, or rollback capability.
3. **File system dependency**: Relies on UNC network share availability. Share unavailability causes silent failure (empty file list).
4. **No idempotency**: If the same file is processed twice (e.g., re-run after failure), duplicate records are inserted into the `ECNT` database unless the database has deduplication constraints.
5. **Single-file architecture**: All 530+ KB of parsing logic is in one file (`FDRReports.cs`). Unmaintainable.

## Recommended DevOps Improvements

1. Migrate to a proper ETL tool (SSIS, Azure Data Factory) as the README itself suggests.
2. Implement idempotency via a file processing log table.
3. Add CI/CD with automated build and security scanning.
4. Remove hardcoded credentials from source code before next commit.
5. Migrate from .NET Framework 4.0 to .NET 8 for active support and security.
