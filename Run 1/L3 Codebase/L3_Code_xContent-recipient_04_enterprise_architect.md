# xContent-recipient — Enterprise Architect View

## Platform Generation
**Gen-2 (Content as Code pattern)**

This is not a software application in the traditional sense; it is a content-as-code repository. Assessment:
- Uses modern GitHub Actions for CI/CD
- Azure Blob Storage as delivery infrastructure
- `azcopy v10` for cloud-native transfer
- PR-based review workflow
- Organized per-affiliate content hierarchy

It is more mature than Gen-1 (no compiled code, no legacy frameworks) but is not a Gen-3 content delivery platform (no CDN, no content API, no versioning service).

## Business Domain
**Content Delivery — Recipient-facing Brand Assets**

This repository is the authoritative source of brand customization for the `mypaymentvault` recipient web application. Each payment program/affiliate has dedicated branding that differentiates the recipient experience.

## Role in Platform
- **Content source of truth**: Single authoritative location for recipient-portal brand assets
- **Upstream of xcontent_SVC**: The xcontent_SVC reads content from a filesystem path; this repository populates that path (via Azure Blob, consumed by xcontent_SVC or directly by the recipient app)
- **Downstream of program onboarding**: When a new prepaid program is launched, content assets are added to this repository
- **Direct to blob**: Content bypasses xcontent_SVC in the newer architecture — Azure Blob Storage may be consumed directly by the recipient web app or served via CDN

## Dependencies
**Inbound contributors:**
- Content/Brand team (program managers, designers)
- Operations team (onboarding new programs)

**Outbound targets:**
| Target | How |
|--------|-----|
| Azure Blob Storage (QA) | azcopy sync via GitHub Actions |
| Azure Blob Storage (Prod) | azcopy sync via GitHub Actions |
| mypaymentvault web app | Reads from Azure Blob Storage at runtime |

## Integration Patterns
- **GitOps pattern**: Content changes follow a Git PR workflow; merges trigger automated deployment
- **Object storage delivery**: Static files hosted in Azure Blob Storage; no application server required for delivery
- **Sidecar metadata pattern**: Each content file accompanied by a `.properties` sidecar file providing metadata to the consuming application

## Strategic Status
**Appropriate for Current Stage / Enhance for Gen-3**

This repository represents a reasonable Gen-2 pattern:
- GitOps gives audit trail and review control
- Azure Blob storage is a suitable platform for static content

For Gen-3, consider:
- Adding Azure CDN in front of Azure Blob for edge delivery and cache control
- Replacing `.properties` sidecar pattern with a structured content metadata API (database-backed)
- Adding automated fee schedule content validation (checking for required legal disclosures)
- Implementing environment promotion gate (QA approval before prod sync)
- Considering whether xcontent_SVC (Lucene-based) is still needed or if direct Blob/CDN delivery is sufficient

## Migration Blockers (to Gen-3)
1. **`.properties` sidecar files**: Consuming applications (mypaymentvault, xcontent_SVC) depend on the `.properties` file format and structure; format change requires coordinated update of consumers
2. **Directory naming convention**: `{BIN}_{ClientName}_{ProductCode}` is implicit schema understood by consuming apps; any renaming or restructuring requires consumer updates
3. **No CDN currently**: Direct blob access means content is served from a single Azure region; CDN addition is an infrastructure addition, not a blocker to repository migration
4. **Volume of programs**: Many programs are present; any new delivery mechanism must handle all existing programs on cutover
