# DevOps / Operations — utility-scripts

## Build
- No build system. This is a collection of standalone scripts.
- Python scripts use `uv` (PEP 621 project) in the `replace_page/` subdirectory: `replace_page/pyproject.toml` defines the project; `uv.lock` pins dependencies.
- `replace_page/scripts/build.sh` and `build.fish` produce a standalone binary via PyInstaller (`replace_page.spec`).
- PowerShell scripts require no installation beyond PowerShell 5.0+ and a local Git installation.

## Deployment
- Scripts are run locally by developers; there is no server deployment.
- `replace_page/` binary (built via PyInstaller) can be distributed as a standalone executable.
- No Dockerfile, no Kubernetes manifests, no Ansible playbooks, no Terraform configs.

## Configuration Management
| Script | Configuration Source |
|---|---|
| `clean_remote_repo.py` | CLI flags + `GITHUB_TOKEN` env var |
| `purge_branches.ps1` | Optional `-RemoteName` param; defaults to first git remote |
| `update_deps.ps1` | Optional `-PomPath` and `-OutputPath` params; auto-discovers project root |
| `schema_doc_generator.py` | Hardcoded in `main()` — requires source edit before use |
| `replace_page/replace_page.py` | `~/.config/replace_page.json` (email, API token, base URL) |

## Observability
- No structured logging, no log aggregation, no metrics.
- Scripts print to stdout/stderr. `clean_remote_repo.py` has a `--debug` flag that emits verbose `[DEBUG]` lines to stdout.
- No distributed tracing or telemetry.

## Infrastructure Dependencies
| Dependency | Used By | Notes |
|---|---|---|
| Git (CLI) | `purge_branches.ps1`, `clean_remote_repo.py` | Must be on PATH |
| Python 3.x | `clean_remote_repo.py`, `convert_wsdl.py`, `schema_doc_generator.py`, `replace_page/` | Version not pinned in root scripts |
| `pyodbc` + ODBC driver | `schema_doc_generator.py` | OS-level ODBC driver for SQL Server required |
| `npx` (Node.js) | `replace_page/replace_page.py` | For Mermaid diagram rendering |
| GitHub REST API | `clean_remote_repo.py` | `api.github.com` HTTPS access |
| Confluence REST API V2 | `replace_page/replace_page.py` | Target Confluence instance HTTPS access |
| Maven Wrapper (`mvnw.cmd`) | `update_deps.ps1` | Must exist in the project root being analysed |
| Onbe Nexus / Maven Central | `update_deps.ps1` | Network access to Nexus required for effective-POM and updates |

## Operational Risks
1. **No version pinning for root Python scripts**: `clean_remote_repo.py`, `convert_wsdl.py`, `schema_doc_generator.py` have no `requirements.txt` at root level; only `replace_page/` has managed dependencies.
2. **Maven timeout handling** in `update_deps.ps1`: timeout is 60 seconds per command; Maven central resolution can exceed this on slow networks, causing incomplete output silently.
3. **`taskkill` hardcoded on Windows** (`update_deps.ps1` line ~420): `cmd.exe /c "taskkill /PID ... /T /F"` — this is Windows-only and will silently fail on Linux/macOS.
4. **Branch deletion is irreversible** if the reversal commands printed by `clean_remote_repo.py` are not saved before `git gc` runs.
5. **No CI/CD pipeline for this repo**: The utility scripts themselves are not automatically tested; `replace_page/` has test files (`test_replace_page.py`, etc.) but they are executed manually.
6. **`schema_doc_generator.py` requires source modification** before use, increasing risk of accidental credential commits.

## CI/CD
No automated CI/CD pipeline exists for the `utility-scripts` repository itself. The `replace_page/` subdirectory has a `scripts/smoke_harness.py` for manual smoke testing and PyInstaller build scripts, but no GitHub Actions workflows or GitLab CI files are present.
