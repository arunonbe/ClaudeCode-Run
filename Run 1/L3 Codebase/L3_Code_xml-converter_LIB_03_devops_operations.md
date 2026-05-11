# DevOps / Operations View — xml-converter_LIB

## Build System
- **Language / Framework:** C# / .NET Framework 2.0 (WinForms desktop application)
- **Build tool:** MSBuild via Visual Studio solution file `XMLConvert.sln` / project `XMLConvert.csproj`
- **Target framework:** `v2.0` (.NET Framework 2.0 — circa 2005, end-of-life)
- **Output type:** `WinExe` (Windows executable)
- **No Maven, no Docker, no CI/CD pipeline detected in repository**

## Deployment
- **Deployment model:** Manual — operator copies the compiled executable and supporting files to a local workstation
- **Runtime environment:** Windows only (`System.Windows.Forms`)
- **Supporting files required at runtime:**
  - `fields.txt` — field definitions master file (must exist in working directory)
  - `*.Northlane` — client template files (must exist in working directory)
  - `*.settings` — per-template settings (created/read from working directory)
  - `settings.ini` — user UI preferences (auto-created on first run)
- **No installer, no package management, no deployment automation detected**

## Configuration Management
- All configuration is file-based and located in the working directory alongside the executable
- `settings.ini` stores UI preferences; `*.settings` stores per-template parameters including passwords
- No environment variables, no central config server, no secrets vault integration
- Passwords (file password, batch password) are stored in plaintext in `*.settings` — no secrets management

## Observability
- No logging framework present
- No error telemetry, no health checks, no monitoring instrumentation
- Error reporting is via `MessageBox.Show()` dialogs only
- No audit trail of operations performed

## Infrastructure Dependencies
- None at runtime — fully standalone desktop tool
- No database connectivity
- No network calls
- No external API dependencies

## Operational Risks
- .NET Framework 2.0 is out of support and receives no security patches — running on a supported Windows version does not mitigate underlying framework vulnerabilities
- No audit log — impossible to reconstruct what data was processed, by whom, or when
- Template files and generated XML output files with PII reside unprotected on operator workstations
- Migration logic for `.Wirecard` → `.Northlane` runs silently on startup with no confirmation or logging
- Hardcoded US state list and sort arrays — schema changes require a code rebuild

## CI/CD
- No CI/CD pipeline exists for this repository
- No automated testing framework present
- No code signing detected (`<SignAssembly>false</SignAssembly>` in project file)
- CodeAnalysis rule set `SecurityRules.ruleset` is referenced in Debug build config but `<RunCodeAnalysis>false</RunCodeAnalysis>` is set — analysis does not run
