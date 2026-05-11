# xContent-recipient — Solution Architect View

## Technical Architecture
This is a **static content repository** — no compiled code, no application server, no runtime services. The technical architecture is:

- **Repository**: Git (GitHub, `main` branch)
- **Content format**: SVG, PNG, HTML, `.properties` metadata files
- **Delivery mechanism**: Azure Blob Storage, synced via `azcopy v10`
- **CI/CD**: GitHub Actions (2 workflows)
- **Directory structure**: Flat hierarchy under `EastRecipient/xContent/recipient/`

## API Surface
No API surface — static content repository. The "interface" is:
- **Git PR workflow**: Content changes submitted via pull request
- **Azure Blob URL structure**: `https://{storage_account}.blob.core.windows.net/data/xContent/recipient/{program}/{file}`

## Security Posture

### Authentication and Authorisation
- **GitHub repository access**: Controls who can contribute content (assume private repo with branch protection)
- **Azure authentication**: Service principal credentials stored as GitHub Actions secrets (`AZURE_CREDENTIALS_QA`, `AZURE_CREDENTIALS_PROD`)
- **SAS token**: Generated with 1-hour expiry, `drlw` permissions per workflow run
- **No application-layer authentication** — static content; Azure Blob access control applies

### Crypto
- **In-transit**: azcopy uses HTTPS for all transfers to Azure Blob
- **At-rest**: Azure Blob Storage AES-256 encryption (default, Microsoft-managed keys)

### Secrets Management
- Azure service principal credentials stored as GitHub Actions environment secrets
- No secrets visible in repository files
- SAS tokens are ephemeral (1-hour); generated per run

### Supply Chain / Action Security
| Action | Version Used | Risk |
|--------|-------------|------|
| `actions/checkout` | `@v3` (main.yml), `@v4` (copy-pr-files.yml) | Not SHA-pinned — supply chain risk |
| `kheiakiyama/install-azcopy-action` | `@v1` | Not SHA-pinned; third-party action |
| `azure/login` | `@v2` | Not SHA-pinned; Microsoft action |

Not SHA-pinning actions is a supply chain security risk — a compromised action could exfiltrate `AZURE_CREDENTIALS_PROD` to an attacker.

## Technical Debt
1. **No automated fee schedule validation**: `fees_en_US.html` files are not checked for required legal content, minimum disclosure fields, or format compliance
2. **SAS token with delete permission**: `drlw` granted — `delete` is not required for content sync; reduces the blast radius if credentials are compromised
3. **No CDN**: Content served directly from Azure Blob; no edge caching, no custom domain, no cache headers management
4. **No environment promotion gate**: QA and prod sync in same matrix run; no human approval step before prod
5. **Inconsistent `actions/checkout` version**: `@v3` vs `@v4` across workflows
6. **Third-party azcopy installer action not SHA-pinned**: Supply chain risk
7. **No rollback procedure**: No documented or automated rollback for bad content deployments
8. **`EmailHeader1.png` missing `.properties` sidecar** in some programs — inconsistent with expected pattern

## Gen-3 Migration Requirements
1. **Add Azure CDN / Front Door** in front of Blob Storage for edge delivery, custom domain support, and cache control
2. **SHA-pin all GitHub Actions** to prevent supply chain attacks
3. **Reduce SAS permissions** from `drlw` to `rlw` (remove delete) for sync operations
4. **Add environment promotion gate**: Require manual approval in GitHub Environment before prod sync
5. **Add fee schedule content validation**: GitHub Actions step to check for required CFPB/Reg E disclosure elements in `fees_en_US.html`
6. **Implement rollback mechanism**: Tag or snapshot Azure Blob versions; add a rollback workflow
7. **Replace `.properties` sidecar pattern** with structured metadata in a content API database (future state)
8. **Enforce repo as private**: Verify repository visibility; BIN-related directory names should not be publicly accessible

## Code-Level Risks (file:line references)
| Risk | File | Line |
|------|------|------|
| azcopy action not SHA-pinned | `.github/workflows/copy-pr-files.yml` | 40 |
| azure/login not SHA-pinned | `.github/workflows/copy-pr-files.yml` | 46 |
| SAS permission includes delete (`drlw`) | `.github/workflows/copy-pr-files.yml` | 65 |
| No QA-to-prod gate (matrix sequential without approval) | `.github/workflows/copy-pr-files.yml` | 33–36 |
| Double-sync with `##` comment typo (non-functional) | `.github/workflows/main.yml` | 81 |
| checkout@v3 in main.yml vs @v4 in copy-pr-files.yml | `.github/workflows/main.yml` | 44 |
