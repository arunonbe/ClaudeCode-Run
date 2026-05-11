# Solution Architect View — xml-converter_LIB

## Technical Architecture
- **Language:** C# targeting .NET Framework 2.0
- **UI pattern:** Windows Forms (WinForms) single-form application with two forms: `frmMain` (main data entry / XML generation) and `FormTemplate` (template management)
- **Architecture style:** Monolithic desktop application; all logic (presentation, business rules, file I/O, XML construction) is embedded in form code-behind files
- **No layering:** no separate service, domain, or data access layer
- **XML generation:** Manual string concatenation using sorted field arrays — no XML serialisation library

## API Surface
None. This is a standalone desktop executable with no exposed API, no HTTP endpoints, no inter-process communication.

## Security Posture

### Authentication
- Single-factor: Windows identity check only — `System.Security.Principal.WindowsIdentity.GetCurrent().Name` is checked for the substring `"INT"` to toggle between "internal" and "client" modes (`FormMain.cs:79`)
- No password prompt, no MFA, no role-based access control beyond this binary mode switch

### Cryptography
- No encryption is applied by this tool to any data it produces or stores
- File passwords and batch passwords collected in the UI (`txtFilePass`, `txtBatPass`) are written to `*.settings` files in **plaintext** (`FormMain.cs:LoadSettings`)
- These passwords likely control downstream encryption (e.g., PGP file encryption for transmission), but are not protected locally

### Secrets Management
- Passwords stored in plaintext text files on the operator workstation — no secrets vault, no protected storage
- No secrets in source code detected, but the `*.settings` runtime files represent a secrets management gap

### Known CVE Exposure
- **.NET Framework 2.0** is entirely out of Microsoft support (EOL since 2011). It has accumulated numerous unpatched CVEs including remote code execution vulnerabilities. The risk applies to the runtime environment.
- No NuGet packages with known CVEs detected (no third-party packages referenced in the project file)

## Technical Debt
| Item | Severity | Detail |
|---|---|---|
| .NET Framework 2.0 (EOL) | Critical | Runtime has been end-of-life since 2011; no security patches available |
| No automated tests | High | Zero test coverage; no test project in solution |
| No CI/CD | High | Manual build and deploy; no regression safety net |
| All logic in form code-behind | High | `FormMain.cs` exceeds 1,500+ lines; no separation of concerns |
| Plaintext password storage | High | `txtFilePass` / `txtBatPass` values written to `*.settings` without encryption |
| No audit logging | High | No record of operations, data processed, or errors |
| Hardcoded business rules | Medium | XML sort orders, state list, BIN prefixes hardcoded in arrays (`FormMain.cs:156–225`) |
| Hardcoded Galileo BIN `514977` | Medium | BIN embedded in `MaskCCHelper`-equivalent logic; schema changes require recompile |
| Wirecard icon in repo | Low | `wirecard.ico` still present — heritage artefact |
| Windows-1252 encoding assumptions | Low | `App.config` targets .NET 2.0; no explicit encoding handling |

## Gen-3 Migration Requirements
1. Replace desktop tool with a web-based or API-driven batch submission service
2. Implement proper secrets management (e.g., Azure Key Vault) for file/batch credentials
3. Migrate `fields.txt` and `.Northlane` template schemas to a managed configuration store (database or configuration service)
4. Re-express hardcoded XML ordering rules as configurable metadata
5. Implement audit logging for all submission activities (operator, timestamp, template, record count)
6. Apply input validation and data masking for PII fields in the UI
7. Implement role-based access control beyond the Windows username substring check

## Code-Level Risks
| Risk | File:Line | Detail |
|---|---|---|
| Windows identity-only auth | `FormMain.cs:79` | `!lblUser.Text.Contains("INT")` — trivially bypassed if username contains "INT" |
| Plaintext password persistence | `FormMain.cs:LoadSettings` | `txtFilePass.Text` / `txtBatPass.Text` written to and read from `*.settings` without encryption |
| Unconstrained file write to working directory | `FormMain.cs` (multiple) | XML, settings, and HTML files written to `Directory.GetCurrentDirectory()` without path sanitisation |
| Silent file deletion on startup | `FormMain.cs:64–74` | `.Wirecard` files are copied and deleted without user confirmation or logging |
| HTML injection in generated reports | `FormTemplate.cs:lnkClient_LinkClicked` | Field friendly names and assigned values written directly into HTML without encoding |
| No exception handling in XML generation | `FormMain.cs` (generation methods) | `try/catch` blocks with `// do nothing` swallow errors silently |
