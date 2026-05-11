# DevOps & Operations Report — optic_WAPP

## Build System

There is no automated build system. The repository contains only two Excel macro-enabled workbook files (`.xlsm`) and a `.gitignore`. The "build" process for OPTIC consists of manually editing the VBA code within the Excel application using the Visual Basic for Applications IDE embedded in Microsoft Excel, then saving the updated `.xlsm` file and copying it to the RiskDB server share where users download it.

This is fundamentally not a software engineering build process — it is a manual file distribution workflow.

## CI/CD Pipeline

There is no CI/CD pipeline. There are no GitHub Actions workflows, no automated tests, no linting, and no build automation. Changes to OPTIC go through:
1. Developer opens the `.xlsm` file in Excel
2. Developer edits VBA code using the Excel VBA IDE
3. Developer saves the file
4. Developer copies/uploads the file to the RiskDB server distribution location
5. All users automatically receive the new version on next launch

This "deploy" mechanism is fully manual and has no gates, approvals, or automated validation. A developer can push broken or malicious VBA code to all users without any review process.

## Deployment Model

**Distribution via RiskDB server file share.** The `OPTIC Production Copy Link.xlsm` file downloaded by users contains logic (VBA) to pull the latest production copy from a server path (presumably an SMB network share or SharePoint/OneDrive location on the RiskDB server infrastructure). This is a pull-based distribution model where the central server is the authoritative source.

Deployment steps:
1. Updated `.xlsm` saved to git (version history)
2. File manually copied to the RiskDB server distribution path
3. No further action required — users pull on next launch

## Runtime Environment

- **Runtime:** Microsoft Excel (version unspecified — likely Office 365 or Excel 2016+ based on corporate standards)
- **Language:** Visual Basic for Applications (VBA)
- **Platform:** Windows desktop (corporate workstations)
- **Database connectivity:** ADO (ActiveX Data Objects) or DAO via ODBC, connecting to SQL Server (RiskDB)
- **No server-side compute:** All business logic runs on the user's workstation within the Excel process
- **No Java, no Spring, no containers** — this is entirely outside the Gen-3 platform stack

## Secrets Management

**Completely unknown and likely inadequate.** Database connection credentials are embedded in VBA code inside the `.xlsm` binary file. Common patterns in legacy VBA applications:
- Hardcoded connection string with embedded username and password in VBA `Sub` or `Function`
- Shared database account used by all OPTIC users (violates PCI DSS Req 8.2 — unique user IDs)
- Windows Integrated Security (SSPI) — the more secure option; uses the user's Windows identity for SQL authentication, which aligns with PCI DSS individual authentication requirements

Without extracting the VBA code, the secrets management model cannot be confirmed.

## Observability

**None.** Excel VBA applications have no built-in observability:
- No structured logging
- No metrics
- No distributed tracing
- No health checks
- No error tracking system

If the VBA code encounters a SQL error, the behavior depends entirely on the VBA error handling implemented (likely a `MsgBox` to the user or silent failure). There is no centralized error log and no alerting.

## Version Control Effectiveness

While the repository uses git, the `.xlsm` format is a binary Office Open XML package (ZIP archive). Git stores the binary diff but cannot render meaningful text diffs for VBA code changes. This means:
- Code reviews via pull request are not possible for VBA changes (no readable diff)
- `git blame` cannot pinpoint which VBA line was changed in which commit
- The git history shows "file changed" but not what changed

This makes the git repository useful only as a backup mechanism, not as a true source control system for the application logic.

## EOL / Risk Assessment

- **VBA / Excel platform:** Not EOL — Office 365 is actively maintained. However, VBA is a deprecated application development paradigm in modern enterprise contexts. Microsoft's strategic direction is Power Apps / Power Automate for business applications.
- **ADO/ODBC:** Not EOL but legacy. Modern SQL access uses JDBC/Entity Framework.
- **Distribution via server share:** The file-copy distribution model has no integrity verification — a compromised server or MITM attack could distribute a trojaned `.xlsm` file.
- **Macro security:** Office macro security policies (Group Policy Object settings) must be configured to prevent unsigned or untrusted macros from running. If OPTIC's VBA is not digitally signed with a trusted certificate, it may be blocked by enterprise macro security policies or require users to click "Enable Content" — a social engineering vector.
- **Risk level: HIGH** — this is a legacy tool with no SDLC controls, no automated testing, no security scanning, and potential credential embedding. It should be assessed for migration to a modern platform (Power Apps, internal web application, or retirement).
