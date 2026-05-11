# xContent-recipient — DevOps / Operations View

## Build
- **No build process**: This is a static content repository (SVG, PNG, HTML, `.properties` files)
- **No compilation, JAR, or WAR produced**
- **Toolchain**: `git` + `azcopy v10` + `azure/login` GitHub Action

## Deployment
- **Deployment mechanism**: Azure `azcopy sync` to Azure Blob Storage
- **Target**: Azure Blob container `data`, path `xContent/recipient/`
- **Environments**: QA and Production (matrix strategy)
- **GitHub environment protection**: Separate `qa` and `prod` GitHub environments with distinct `AZURE_CREDENTIALS` secrets

### Workflow: `copy-pr-files.yml` (primary deployment)
- **Trigger**: PR closed/merged to `main`, path filter `EastRecipient/**`
- **Strategy**: Delta sync — only files changed in the merged PR are synced
- **Concurrency**: `max-parallel: 1` — sequential QA then prod
- **Steps**:
  1. Checkout with `fetch-depth: 0` (full history for git diff)
  2. Install azcopy v10
  3. Azure CLI login with environment-specific credentials
  4. Generate 1-hour SAS token (`drlw` permissions on `data` container)
  5. `git diff {base_sha} {head_sha}` to identify changed files
  6. For each changed directory: two `azcopy sync` calls (non-properties, then properties)

### Workflow: `main.yml` (manual full sync)
- **Trigger**: Manual `workflow_dispatch`
- **Strategy**: Full azcopy sync of entire `EastRecipient/xContent/recipient/` directory
- **Same matrix**: QA then prod
- **Use case**: Recovery sync, initial setup, or complete refresh

## Configuration Management
- **GitHub Environments**: `qa` and `prod` with environment-level secrets
  - `AZURE_CREDENTIALS_QA` → QA storage account
  - `AZURE_CREDENTIALS_PROD` → production storage account
  - `AZURE_STORAGE_ACCOUNT_NAME` → environment-specific storage account name (as a variable, not secret)
- **No application-level config files** (static content only)
- **Content organization**: Managed purely through directory structure and git

## Observability
- **No runtime observability**: This is a static content repository; no application to monitor
- **Deployment audit**: GitHub Actions run history provides audit of all sync operations
- **Git history**: Full change audit trail for all content modifications (who changed what and when)
- **No alerting** on sync failures beyond GitHub Actions workflow failure notifications

## Infrastructure Dependencies
| Dependency | Type | Details |
|-----------|------|---------|
| Azure Blob Storage (QA) | Object storage | `AZURE_STORAGE_ACCOUNT_NAME` (QA); `data` container |
| Azure Blob Storage (Prod) | Object storage | `AZURE_STORAGE_ACCOUNT_NAME` (Prod); `data` container |
| Azure CLI (`azure/login@v2`) | Auth | Service principal credentials stored as GitHub secrets |
| `azcopy v10` | Transfer tool | Installed via `kheiakiyama/install-azcopy-action@v1` |
| GitHub (source control) | Repository | Private repo assumed; `main` branch protected by PR requirement |

## Operational Risks
1. **Pinned action version `@v1`** (`kheiakiyama/install-azcopy-action@v1`): Not SHA-pinned; if the action is updated with a breaking change or compromised, it could affect deployments
2. **`azure/login@v2`** without SHA pin: Same supply-chain risk
3. **`actions/checkout@v3` / `@v4` mixed**: `copy-pr-files.yml` uses `@v4`; `main.yml` uses `@v3` — inconsistency may cause subtle behavior differences
4. **SAS token with delete permission**: `drlw` permissions grant the runner ability to delete blobs — unnecessary for content sync; should use `rlw` (read, list, write) only
5. **No QA gate before prod**: QA and prod sync in the same job matrix run; no manual approval gate between environments
6. **No rollback mechanism**: `azcopy sync` with `--recursive=true` can overwrite but not revert to a previous state; a bad content merge cannot be automatically rolled back
7. **Sequential matrix (max-parallel: 1)**: If QA sync takes long or fails, prod sync is blocked, not skipped — requires manual intervention

## CI/CD Pipeline
```
PR lifecycle (copy-pr-files.yml):
  PR merged to main
  → Triggers copy-pr-files.yml (path: EastRecipient/**)
  → Matrix: QA environment
    → Azure login (AZURE_CREDENTIALS_QA)
    → Generate SAS (1hr, drlw)
    → git diff to find changed files
    → azcopy sync (non-properties) to QA blob
    → azcopy sync (properties) to QA blob
  → Matrix: Prod environment
    → Azure login (AZURE_CREDENTIALS_PROD)
    → Generate SAS (1hr, drlw)
    → azcopy sync (non-properties) to Prod blob
    → azcopy sync (properties) to Prod blob

Manual full sync (main.yml):
  workflow_dispatch (manual trigger)
  → Same matrix: QA → Prod
  → Full azcopy sync of EastRecipient/xContent/recipient/
```
