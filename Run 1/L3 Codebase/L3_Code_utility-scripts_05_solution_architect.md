# Solution Architect — utility-scripts

## Technical Architecture
A polyglot script collection with no shared runtime framework:
- **Python scripts** (`clean_remote_repo.py`, `convert_wsdl.py`, `schema_doc_generator.py`): Standard library only (no third-party imports at module level in root scripts); Python 3.x required.
- **PowerShell scripts** (`purge_branches.ps1`, `update_deps.ps1`): Windows PowerShell 5.x / PowerShell 7+ compatible; use .NET XML DOM (`System.Xml.XmlDocument`) for POM parsing.
- **`replace_page/` Python package**: Managed via `uv` + `pyproject.toml`; dependencies include `beautifulsoup4`, `requests`, `Pillow`, `lxml`, `mistletoe` (or equivalent Markdown parser); compiled to standalone binary via PyInstaller.

## API Surface
No REST API is exposed. All scripts are consumed as CLI tools.

| Script | Interface | Authentication |
|---|---|---|
| `purge_branches.ps1` | PowerShell CLI (`-RemoteName` param) | Git credentials (existing git config) |
| `clean_remote_repo.py` | Python CLI (`--dry-run`, `--debug`, filter flags) | `GITHUB_TOKEN` env var |
| `update_deps.ps1` | PowerShell CLI (`-PomPath`, `-OutputPath` params) | Maven settings (`settings.xml`) |
| `convert_wsdl.py` | Python CLI (positional args: input/output paths) | None |
| `schema_doc_generator.py` | Python CLI (no args; config in `main()`) | Hardcoded DB credentials |
| `replace_page/replace_page.py` | Python CLI (URL, `-f`, `-p`, `-d`, `-q`, `-v` flags) | `~/.config/replace_page.json` (email + API token) |

## Security Posture

### Authentication / Authorisation
- `clean_remote_repo.py`: Token passed via `GITHUB_TOKEN` env var; used in `Authorization: token <value>` HTTP header. Acceptable pattern. Risk: if `GITHUB_TOKEN` has overly broad scopes (e.g., `repo` with write access), a compromised token could delete branches on production repos.
- `replace_page/`: Confluence Basic auth (email + API token) stored in `~/.config/replace_page.json`. Token is read at runtime, not committed. Risk: plaintext token in a JSON config file on a developer workstation.
- `schema_doc_generator.py`: Credentials hardcoded in Python source (README confirms this). **This is a critical finding.** If credentials for a CDE-adjacent SQL Server are committed, it constitutes a PCI DSS Requirement 8 violation.

### Cryptography
- No encryption at rest. No custom cryptographic operations. TLS is delegated to HTTP client libraries and the ODBC driver.

### Secrets
- `GITHUB_TOKEN`: environment variable — acceptable.
- Confluence API token: `~/.config/replace_page.json` on developer workstation — acceptable if workstation is encrypted and access-controlled.
- SQL Server credentials: **hardcoded in `schema_doc_generator.py:main()`** — not acceptable. **Must be externalised to environment variables or a secrets vault before any commit containing real credentials.**

### Known CVEs
- `replace_page/requirements.txt` and `uv.lock` should be scanned with `pip-audit` or equivalent. Libraries such as `Pillow` and `lxml` have historical CVE history. No specific CVEs identified from inspection — recommend automated SBOM/CVE scan.
- Root Python scripts use stdlib only — minimal CVE surface.

## Technical Debt
1. **`schema_doc_generator.py`**: Credentials in source (`schema_doc_generator.py` — `main()` function). Must be refactored to accept env vars or CLI args.
2. **`update_deps.ps1`**: `spring-boot-starter-parent:3.5.5` is hardcoded as the parent version display string in `Generate-Markdown` (line ~1213). This is stale if the project being analysed uses a different version.
3. **`update_deps.ps1`**: Debug `Write-Host "DEBUG: ..."` statements present in production code (lines ~806, ~809, ~867) — should be removed or gated behind a `-Debug` flag.
4. **No automated tests for root scripts**: `clean_remote_repo.py`, `convert_wsdl.py`, `schema_doc_generator.py`, `purge_branches.ps1`, and `update_deps.ps1` have no test coverage.
5. **Python 2 / 3 compatibility**: `convert_wsdl.py` uses `print` function syntax (Python 3) but has no `__future__` import or version check. If run with Python 2.x it will fail with obscure errors.

## Gen-3 Migration Requirements
Not applicable — utility scripts are not subject to the Gen-3 migration programme.

## Code-Level Risks

| File | Location | Risk |
|---|---|---|
| `schema_doc_generator.py` | `main()` function | Hardcoded DB credentials — PCI DSS Req 8 finding |
| `update_deps.ps1` | ~line 1213 | Hardcoded `spring-boot-starter-parent:3.5.5` version string — stale constant |
| `update_deps.ps1` | ~line 420 | `taskkill` via `cmd.exe` — Windows-only, will silently fail on non-Windows hosts |
| `update_deps.ps1` | ~lines 806–867 | `Write-Host "DEBUG: ..."` statements should not be in production output |
| `clean_remote_repo.py` | line 507 | `GITHUB_TOKEN` missing warning printed to stderr but script continues — branches with open PRs may be deleted if token is absent |
| `replace_page/replace_page.py` | auth config | Plaintext Confluence API token in `~/.config/replace_page.json`; no keychain or vault integration |
