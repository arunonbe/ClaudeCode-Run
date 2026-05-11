# Business Analyst — utility-scripts

## Business Purpose
A shared developer toolbox providing scripts for common engineering tasks at Onbe. The repository aggregates operational scripts that are broadly useful across teams, reducing duplication of effort for routine repository hygiene, dependency management, WSDL conversion, database schema documentation, and Confluence content management.

## Capabilities

### Git and Repository Management
- **`purge_branches.ps1`** (PowerShell): Safely removes stale local branches whose remote counterparts have been deleted. Protects `main`, `master`, and the currently checked-out branch. Prompts before force-deleting branches with unmerged commits.
- **`clean_remote_repo.py`** (Python): Interactive remote-branch cleanup tool. Applies configurable filters (merge status, tag references, open GitHub PRs via the GitHub REST API) to identify deletion candidates. Supports dry-run mode and provides reversal commands.

### Build and Dependency Management
- **`update_deps.ps1`** (PowerShell): Parses a Maven `pom.xml`, executes Maven commands (`dependency:tree`, `versions:display-dependency-updates`, `help:effective-pom`) and generates a `docs/dependencies.md` file with version information, BOM imports, transitive dependencies, plugin versions, and available update recommendations.

### Data and Web Services
- **`convert_wsdl.py`** (Python): Converts a WSDL document from RPC/encoded binding style to Document/literal (wrapped) — required when migrating legacy SOAP services.
- **`schema_doc_generator.py`** (Python): Connects to a Microsoft SQL Server database (via `pyodbc` / ODBC) and auto-generates Markdown documentation for specified tables and views. Requires manual configuration of `JDBC_URL`, `USERNAME`, `PASSWORD`, and object list in the script.
- **`replace_page/`** (Python package): Replaces Confluence page content with Markdown source. Converts Markdown to Confluence storage XHTML, uploads images, renders Mermaid diagrams via `npx`, and updates pages via the Confluence V2 REST API using HTTP Basic auth (email + API token).

## Entities
No domain payment entities. Operates on: Git branches, Maven POMs, WSDL documents, SQL Server schemas, and Confluence pages.

## Business Rules
1. `purge_branches.ps1` must never delete `main`, `master`, or the currently active branch.
2. `clean_remote_repo.py` must require explicit per-branch confirmation before deletion; dry-run must be the safe default to audit.
3. `schema_doc_generator.py` credentials (`USERNAME`, `PASSWORD`) are hardcoded in the script body — these must be removed/externalised before any commit to shared repositories.
4. `replace_page/` requires a Confluence API token stored at `~/.config/replace_page.json` — must not be committed.

## Flows
1. Developer clones a repo locally, runs `purge_branches.ps1` to remove merged branches.
2. Before a release, `clean_remote_repo.py` is run with `GITHUB_TOKEN` set to prune old remote branches.
3. After updating a `pom.xml`, `update_deps.ps1` is run to regenerate `docs/dependencies.md` and identify outdated libraries.
4. Legacy SOAP service migration: `convert_wsdl.py` transforms the WSDL; developer validates output.
5. DBA or architect runs `schema_doc_generator.py` to produce schema docs for a target database.
6. Technical writer or developer runs `replace_page/replace_page.py` to push updated Markdown to Confluence.

## Compliance Relevance
- **PCI DSS**: `schema_doc_generator.py` can connect to production databases including those in the CDE. Hardcoded credentials (noted above) are a PCI DSS Requirement 8.6 violation if left in source.
- **GLBA / GDPR / CCPA**: The Confluence integration (`replace_page`) may inadvertently publish sensitive architecture or schema documentation to Confluence — access controls on target Confluence spaces should be reviewed.
- **GitHub API access**: `clean_remote_repo.py` uses `GITHUB_TOKEN` (environment variable) to call the GitHub API. Token scope must be limited to branch management, not admin or write-to-packages.

## Risks
1. **Hardcoded DB credentials** in `schema_doc_generator.py` (README confirms `USERNAME`, `PASSWORD` must be set in `main()`) — high risk if the file is ever committed with real values.
2. **No input validation on branch deletion** — `clean_remote_repo.py` deletes remote branches; a misconfigured run could delete active branches on production repositories.
3. **`update_deps.ps1` executes Maven commands** using the local Maven wrapper and settings, including connecting to Onbe's internal Nexus. If run from a compromised machine, the Maven resolver could fetch malicious artefacts.
4. `replace_page/` uploads images and content to Confluence; a misconfigured target URL could overwrite production documentation.
