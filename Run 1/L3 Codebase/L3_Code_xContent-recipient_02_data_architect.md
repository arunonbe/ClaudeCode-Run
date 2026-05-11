# xContent-recipient — Data Architect View

## Data Stores
| Store | Type | Purpose |
|-------|------|---------|
| Git repository | Version-controlled filesystem | Source of truth for all brand content assets |
| Azure Blob Storage (`data` container) | Cloud object storage | Production and QA delivery store; path: `xContent/recipient/` |
| GitHub Actions runner (ephemeral) | Transient file cache | Files checked out during workflow execution |

## Schema / Tables
This is a static content repository with no relational database. The "schema" is the directory naming convention:

```
EastRecipient/
  xContent/
    recipient/
      {BIN}_{ClientName}_{ProductCode}/
        fees_en_US.html                  -- Fee schedule disclosure (HTML)
        fees_en_US.html.properties       -- Metadata for fee schedule
        images/
          activation_banner.svg          -- Activation page banner
          activation_banner.svg.properties
          login_page.png                 -- Login page image
          login_page.png.properties
          paymentvault_logo.svg          -- PaymentVault brand logo
          paymentvault_logo.svg.properties
          recipient_virtual_master.svg   -- Virtual card artwork
          recipient_virtual_master.svg.properties
          registration_banner.svg        -- Registration page banner
          registration_banner.svg.properties
          EmailHeader1.png               -- Email header image
```

**Directory naming convention**: `{6-digit-BIN}_{ClientName}_{ProductType}`
- `04011026` prefix suggests BIN range (Bank Identification Number) in the `401100`–`401199` range
- Product type codes: `_SI_US` (Single Issue), `_VE` (Virtual Express), `_CI` (Card Issue), `_ER` (Electronic Refund), `_RES` (Residential), `_SMB` (Small/Medium Business)

## Sensitive Data
- **No PAN, CVV, account numbers, or personal data** in this repository
- **Fee schedule HTML files**: Legally required disclosures; not personal data but must be accurate
- **Azure credentials**: `AZURE_CREDENTIALS_QA` and `AZURE_CREDENTIALS_PROD` are stored as GitHub Actions secrets — not present in repository files
- **BIN ranges exposed**: Directory names contain what appear to be partial BIN codes (e.g., `04011026`) — these identify Onbe's program BINs; not a PCI DSS violation per se but represents business-sensitive information in a potentially public repository

## Encryption
- **At-rest in Azure Blob**: Azure Blob Storage encrypts all data at rest by default (AES-256, Microsoft-managed keys)
- **In-transit**: `azcopy` transfers to Azure Blob Storage use HTTPS
- **SAS tokens**: Short-lived (1-hour expiry) SAS tokens are generated for each sync operation; `drlw` permissions (delete, read, list, write) on `data` container
- **Git repository**: Content in transit over HTTPS (GitHub)

## Data Flow
```
Content team
  → Commits to feature branch
  → PR raised against main
  → PR review/approval
  → PR merged to main

GitHub Actions (copy-pr-files.yml on PR merge):
  → checkout with full history (fetch-depth: 0)
  → Azure CLI login (AZURE_CREDENTIALS_QA or _PROD)
  → az storage container generate-sas (1-hour, drlw, container: data)
  → git diff {base_sha} {head_sha} → changed files list
  → For each changed directory:
    → azcopy sync (non-properties) → Azure Blob data/xContent/recipient/
    → azcopy sync (properties only) → Azure Blob data/xContent/recipient/

Azure Blob Storage
  → Consumed by mypaymentvault web app (xContent-recipient portal)
  → CDN or direct Blob URL delivery to browser
```

## Data Quality / Retention
- **Git history** provides full change audit trail for all content modifications
- **No automated content validation**: Fee schedule HTML is not validated for completeness, accuracy, or required field presence
- **No automated accessibility testing** for brand images (alt-text, contrast)
- **Retention**: Content files persist in Azure Blob until explicitly deleted (no lifecycle policy visible)
- **Orphaned files**: No automated cleanup of content for deprecated programs

## Compliance Gaps
1. **BIN information in directory names**: Partial BIN exposure in a potentially-public repository; recommend verification that the repository is private
2. **No fee schedule content validation**: Automated checks for required legal disclosures (Reg E, CFPB) are absent
3. **SAS token permissions include delete**: `drlw` grants delete permission to the sync runner; if the runner is compromised, content could be deleted from production
4. **Simultaneous QA and prod deployment**: No promotion gate between QA and production; content goes to both in the same workflow run
5. **`EmailHeader1.png` without `.properties` file in some programs** (e.g., `04011101_EquityTrust_Plastic_1101`) — inconsistent metadata coverage
