# xContent-recipient — Business Analyst View

## Business Purpose
`xContent-recipient` is a static content repository for Onbe's recipient-facing web application (`mypaymentvault`). It stores and manages all public assets — images, brand logos, SVG artwork, fee schedule HTML files, and their associated `.properties` metadata files — for each prepaid program offered to payment recipients. Content is organized by affiliate/program and synchronized to Azure Blob Storage for delivery to the recipient web portal.

The README states: "It contains all the public assets of mypaymentvault web recipient application."

## Capabilities
- **Content Repository**: Git-managed store of brand assets (SVG, PNG, HTML) for each payment program
- **Affiliate Asset Management**: Each program has its own directory containing customized logos, banners, fee disclosures, and registration/activation imagery
- **Azure Blob Sync**: GitHub Actions workflows automatically synchronize content to Azure Blob Storage on merge to `main`
- **Environment Management**: Separate sync targets for QA and production environments via matrix deployment
- **Per-file Metadata**: Each content file has a corresponding `.properties` sidecar file providing metadata

## Key Entities
| Entity | Description |
|--------|-------------|
| Program/Affiliate Directory | Named directory under `EastRecipient/xContent/recipient/` — format: `{BIN}_{ClientName}_{ProductCode}` |
| Content File | Brand asset (SVG, PNG, HTML); e.g., `activation_banner.svg`, `login_page.png`, `fees_en_US.html` |
| Properties Sidecar | `.properties` file alongside each content file — metadata/configuration for that asset |
| Fee Schedule (HTML) | `fees_en_US.html` — legally required fee disclosure page per program |
| Azure Blob Container | `data` container in Azure Storage Account; content synced to `xContent/recipient/` path |

## Observed Programs/Affiliates (sample)
| Directory | Program Description |
|-----------|---------------------|
| `04011026_360_OWI_SI_US` | 360 OWI Single Issue US |
| `04011069_NorthLane_VE_1069` | NorthLane Virtual Express |
| `04011092_Charity_On_Top` | Charity On Top |
| `04011098_360_NAPA_ER` | 360 NAPA Electronic Refund |
| `04011101_EquityTrust_Plastic_1101` | Equity Trust (Plastic card) |
| `04011102_Equity_Trust_VE` | Equity Trust Virtual Express |
| `04011106_Nissan_Goodwill_Disb_CI` | Nissan Goodwill Disbursement |
| `04011109_Sendus_Edquity_CI` | Sendus Edquity |
| `04011110_Progressive_SI` | Progressive Single Issue |
| `04011111_TXU_Cashback2022_RES` | TXU Cashback 2022 Residential |
| `04011113_TXU_Cashback_2022_SMB` | TXU Cashback 2022 SMB |

(Many more programs present in the repository)

## Business Rules
- All changes go through PR-based review before merging to `main`
- Content is synced to both QA and production Azure Blob Storage on merge (via `copy-pr-files.yml`)
- Only files that changed in the merged PR are synced (delta sync using `git diff`) — reduces unnecessary overwrites
- Non-`.properties` files and `.properties` files are synced separately (two `azcopy sync` operations)
- Manual full-sync is available via `main.yml` workflow dispatch
- SAS tokens are generated with 1-hour expiry for each sync operation
- Fee schedule HTML files (`fees_en_US.html`) are mandatory for programs serving US recipients

## Key Flows
1. **Content Onboarding**: Content team creates new program directory → adds brand assets + fee schedule → raises PR → review → merge to main → `copy-pr-files.yml` triggers → delta sync to Azure Blob (QA then prod)
2. **Content Update**: Content team modifies existing asset → raises PR → merge → delta sync of changed files only
3. **Emergency Full Sync**: DevOps/content team manually triggers `main.yml` via GitHub Actions workflow dispatch → full azcopy sync of all files to QA and production

## Compliance Considerations
- **Fee disclosure HTML files (`fees_en_US.html`)**: Per-program fee schedules served directly to cardholders; accuracy and completeness are required under Reg E (Electronic Fund Transfer Act) and CFPB/UDAAP guidelines
- **Brand asset integrity**: Any unauthorized modification to brand assets could constitute false representation — must be protected by PR approval controls
- **PCI DSS scope**: This repo contains no cardholder data; it is out-of-scope for PCI DSS CHD requirements but within scope for vendor/partner brand integrity

## Business Risks
- **No content approval workflow**: PR reviews are the only control; if a reviewer approves incorrect fee schedule content, it immediately goes to production
- **Simultaneous QA + prod deployment**: QA and production are both updated in the same matrix job run — a content error affects production immediately after QA confirmation
- **Fee schedule accuracy**: HTML fee files are not validated for content accuracy or regulatory compliance by any automated check in the CI pipeline
- **Orphaned content**: No automated check for programs that have been deprecated but whose content files remain in the repository
