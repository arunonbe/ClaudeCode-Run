# Enterprise Architecture — om-content-management-api

## Platform Generation
**Gen-2 / OnePlatform** — Part of the OnePlatform (OM) platform, which is the second-generation recipient web and program management platform at Onbe. Uses Spring Boot 3.x / Java 21 (more modern than legacy Gen-1 but predates NexPay Gen-3).

## Business Domain
Content Management / UI Asset Delivery. Owns the static content lifecycle for the recipient-facing OnePlatform web application (`xContent-recipient`).

## Role in the Platform
| Attribute | Value |
|-----------|-------|
| Type | Internal API service (content management) |
| Deployed in production | Yes |
| API exposure | Internal APIM (INTERNAL_APIM: true, EXTERNAL_APIM: false) |
| Content target | Azure Blob Storage + GitHub `xContent-recipient` repo |

## Dependencies
### Upstream (callers)
- Internal admin tooling, content editors, deployment pipelines that need to push updated UI assets.
- Protected by internal APIM — not directly callable from public internet.

### Downstream (services/stores called)
| Target | Purpose |
|--------|---------|
| Azure Blob Storage | Persists uploaded content files |
| GitHub API (`api.github.com`) | Version-controls content in `OnbeEast/xContent-recipient` |
| Azure App Configuration | Runtime config and feature flags |
| Redis Cache Admin Service | Referenced in config (URL); likely triggers cache invalidation |

## Integration Patterns
- **REST API (synchronous)** — POST for upload, DELETE for remove.
- **Azure Blob lease pattern** — optimistic concurrency control for concurrent uploads to the same blob.
- **Feature-flagged integration** — GitHub commit is toggled by `api.settings.github.enable` from Azure App Config.
- **Content pipeline** — uploaded files flow from this API → Azure Blob → CDN → recipient browser (CDN layer is separate per the architecture models).

## Strategic Status
- **OnePlatform Gen-2 service** — Java 21 / Spring Boot 3.5.9; more modern than Gen-1 but not aligned to NexPay Gen-3 conventions (no Flyway, no OpenAPI-first, no Envers audit).
- CI/CD uses `Onbe/om-ci-setup` (not `OnbeEast/nexpay-iac`) — different deployment infrastructure from NexPay Gen-3.
- `openapi.json` file present in repo root — indicates an OpenAPI spec exists but the implementation does not use the OpenAPI-generator delegate pattern used by NexPay Gen-3 services.
- The `xContent-recipient` GitHub repo dependency means content changes require either API calls or direct repo commits — dual-path content management.

## Migration Blockers
- No migration to Gen-3 is planned or required for this service based on observed code; it serves OnePlatform (Gen-2), not NexPay Gen-3.
- If NexPay Gen-3 requires its own content management, a separate Gen-3 service should be created rather than reusing this OnePlatform service.
- CI/CD pipeline references a `feature/` branch — must be stabilised before treating this as production-ready.
- `CONTAINER_SCAN: false` must be re-enabled.
