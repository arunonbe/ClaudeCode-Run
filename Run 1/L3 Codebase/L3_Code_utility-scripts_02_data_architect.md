# Data Architect — utility-scripts

## Data Stores
This repository itself holds no persistent data stores. However, several scripts interact with external data stores:

| Script | External Data Store | Nature of Access |
|---|---|---|
| `schema_doc_generator.py` | Microsoft SQL Server (production/non-prod DB via ODBC) | Read-only schema metadata queries |
| `clean_remote_repo.py` | GitHub REST API | Read (branch list, PR list); Write (branch delete) |
| `update_deps.ps1` | Onbe Nexus (`d-issrepo-app01.wirecard.sys:8081` via Maven wrapper settings) | Read-only (dependency resolution) |
| `replace_page/replace_page.py` | Atlassian Confluence (V2 REST API) | Read (page fetch); Write (page update, image upload) |

## Schema / Tables
`schema_doc_generator.py` generates documentation for tables and views in MS SQL Server databases. The specific schemas/tables are not defined in the repository — they are configured at runtime in the script's `main()` function. No schema is defined within this repository.

## Sensitive Data
- `schema_doc_generator.py`: Per the README, `USERNAME` and `PASSWORD` for the SQL Server connection are set inside the script's `main()` function. This constitutes a secrets-in-source risk. The schemas targeted may contain PII or financial data depending on which database is documented.
- `replace_page/`: Uses `~/.config/replace_page.json` for Confluence email + API token. The file must not be committed.
- `clean_remote_repo.py`: Requires `GITHUB_TOKEN` environment variable. The token is read via `os.environ.get("GITHUB_TOKEN")` (line 507) — acceptable pattern if the environment is secured.
- `update_deps.ps1`: Maven repository credentials (`mavenPublishRepo.aws.username`, `mavenPublishRepo.aws.password`) are read from Gradle properties, not from the script itself; no direct secrets exposure identified.

## Encryption
- All external API calls (`GitHub`, `Confluence`, `Nexus`) are expected to be over HTTPS at the transport layer. No explicit TLS configuration is present in the scripts — they rely on library defaults.
- SQL Server connection via `pyodbc` ODBC: encryption depends on the ODBC driver connection string; no `Encrypt=yes` or `TrustServerCertificate` parameters are visible in the repo — connection string is set at runtime.

## Data Flow
```
schema_doc_generator.py:
  ODBC Connection --> SQL Server sys.* metadata views
  --> Markdown output file (local filesystem)

clean_remote_repo.py:
  git CLI (local) --> Remote origin (GitHub)
  GitHub REST API (https://api.github.com) --> PR check, branch list
  git push --delete --> Remote branch deletion

update_deps.ps1:
  Maven Wrapper --> Nexus / Maven Central (dependency resolution)
  --> docs/dependencies.md (local filesystem write)

replace_page/:
  Markdown file (local) --> Mermaid (npx) --> SVG
  --> Confluence V2 API (HTTPS) --> Page content update + image upload
```

## Data Quality / Retention
- No data is retained in this repository.
- Generated files (`docs/dependencies.md`) are ephemeral outputs written to the developer's local workspace.
- Confluence page updates are versioned by Confluence itself.

## Compliance Gaps
1. **PCI DSS Req 8.6 / Req 3.4**: Hardcoded credentials in `schema_doc_generator.py` violate the requirement to protect authentication credentials. If this script is used against a CDE database, it is a finding.
2. **PCI DSS Req 6.3.3**: `replace_page/requirements.txt` dependencies (BeautifulSoup4, Pillow, requests, etc.) should be verified against known CVEs.
3. **Secrets Management**: No secrets vault integration (e.g., Azure Key Vault, AWS Secrets Manager, HashiCorp Vault) is used by any script. All secrets are either environment variables or local config files.
4. **Audit Trail**: `clean_remote_repo.py` deletes remote branches with no server-side audit log beyond Git reflog. For change-management purposes, branch deletions on protected repositories should require PR approval, not an ad-hoc script run.
