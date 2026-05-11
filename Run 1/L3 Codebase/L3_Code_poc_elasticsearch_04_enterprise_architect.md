# Enterprise Architect — poc_elasticsearch

## Platform Generation
**Gen-1 / POC** — Static HTML prototype, no service architecture, no authentication, no build pipeline. Technology stack (React 15.x, azsearch.js 0.0.21, Bootstrap 5 alpha) is a mixed vintage indicating rapid experimentation rather than planned investment.

## Business Domain
**Customer Service Tooling** — Agent-facing cardholder lookup and account management surface. Adjacent to the customer service / operations domain.

## Role in the Architecture
This repository represents a **discarded or shelved proof-of-concept** for a unified customer search experience powered by Azure Cognitive Search. It has no production role and should not be deployed as-is. Its artefacts include:
- A customer service agent search UI prototype (`CustomerService.html`)
- Recipient-facing activation content assets (`xContent/`) that appear to have been added separately and may belong to a different repository

## Dependencies on Other Onbe Systems

| System | Relationship |
|---|---|
| Azure Cognitive Search (`csapoc1`) | Direct query dependency — hard-coded in HTML |
| Azure Blob Storage | Upstream data source for the search index |
| FIS CSA (Customer Service Accounts) | UI references FIS CSA account/transaction data via screenshots embedded in mockup |
| Onbe Client Service / Client Tools / KYB portals | Navigation links in the dropdown menu |

## Integration Patterns
- **Direct browser-to-search-service** integration — no API gateway, no backend proxy
- **CDN-served dependencies** — all JS frameworks from public CDNs

## Strategic Status
**Retired / Abandoned POC.** Evidence:
- `test.txt` contains only "test file to test git repo sync" — indicates repo was used for connectivity testing
- No CI/CD, no build system, no versioning
- React 15 and azsearch.js 0.0.21 are both years out of support
- Hard-coded API key is a POC shortcut not acceptable in any production context

## Recommendation
1. **Immediate:** Rotate the Azure Cognitive Search query key found in `CustomerService.html`. Verify whether the `csapoc1` search service is still active and whether it contains real cardholder data. If so, this is a live PCI DSS CDE exposure.
2. **Short-term:** Archive or delete this repository. If the search capability is needed in production, it must be re-architected with:
   - Server-side query proxy (API key never exposed to browser)
   - Authenticated access (OAuth2/OIDC)
   - Proper data masking for CHD fields in the index
3. **Medium-term:** If a production customer search tool is required, evaluate whether this POC's design aligns with Gen-3 platform direction (Spring Boot microservices, Azure infrastructure, React front-end from `react-component_LIB`).

## Migration Blockers (to Gen-3)
- No codebase to migrate — this is HTML/JS prototype only
- Recipient `xContent/` assets may need to be relocated to the correct content delivery repository
- Azure Cognitive Search service `csapoc1` must be assessed for data residency and compliance before any production use
