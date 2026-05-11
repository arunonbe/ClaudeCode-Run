# DevOps / Operations — poc_elasticsearch

## Build System
No build system. The repository contains only static HTML, CSS, JavaScript (via CDN), and image assets. There is no `pom.xml`, `package.json`, `Dockerfile`, or any build configuration.

## Deployment
No CI/CD configuration (no `.github/workflows/` directory). Deployment, if it occurred, was manual — likely by copying static files to a web server or Azure Static Web App.

## Configuration Management
All configuration is hardcoded in `CustomerService.html`:

| Parameter | Value (as found) | Sensitivity |
|---|---|---|
| Azure Cognitive Search service name | `csapoc1` | Low |
| Azure Cognitive Search index name | `azureblob-index` | Low |
| Azure Cognitive Search query API key | `[REDACTED — rotate immediately]` | CRITICAL — must be rotated immediately |
| DNS suffix | `search.windows.net` | Low |

## Observability
None. No logging, metrics, monitoring, or alerting infrastructure. No APM agents. No audit trail of queries made through this interface.

## Infrastructure Dependencies

| Dependency | URL / Identifier | Notes |
|---|---|---|
| Azure Cognitive Search | `csapoc1.search.windows.net` | POC service; unclear if active |
| Azure Blob Storage (inferred) | Source of `azureblob-index` | Underlying data store |
| Bootstrap 5.3.0-alpha3 | CDN (`cdn.jsdelivr.net`) | UI framework |
| React 15.5.4 | CDN (`cdn.jsdelivr.net`) | Loaded but not visibly used in the HTML |
| Redux 3.6.0 | CDN (`cdn.jsdelivr.net`) | Loaded but not visibly used |
| azsearch.js 0.0.21 | CDN (`cdn.jsdelivr.net`) | Azure Cognitive Search client library |
| FontAwesome | `kit.fontawesome.com/3c6a1f2f0f.js` | Icon kit (kit ID in URL) |
| Popper.js 1.16.0 | CDN | Bootstrap dependency |

Note: All CDN dependencies are loaded with `crossorigin="anonymous"` and some use SRI hashes (Bootstrap CSS has `integrity` attribute). azsearch.js has no SRI hash.

## Operational Risks

| Risk | Severity | Notes |
|---|---|---|
| Query API key hard-coded in HTML — readable by any browser client | Critical | Key must be rotated; service should require server-side proxy pattern instead |
| No authentication — any network user can search | Critical | If this page is accessible on any network, it exposes cardholder data without login |
| CDN dependency — entire UI fails if CDN is unavailable | High | No local copies of Bootstrap, azsearch.js, React, Redux |
| azsearch.js 0.0.21 (published 2018) — no maintenance | High | Unmaintained library with no SRI hash; supply-chain risk |
| React 15.5.4 loaded but unused | Medium | Outdated React version adds unnecessary attack surface |
| No SRI integrity check on azsearch.js | Medium | CDN compromise could inject malicious code |
| Azure Cognitive Search POC service may still be active with live data | Critical | If `csapoc1` index contains real cardholder data, the hardcoded key grants read access |

## CI/CD Pipeline Summary
No CI/CD pipeline exists for this repository.

**Recommended immediate action:** Rotate the Azure Cognitive Search query key `[REDACTED — rotate immediately]` and assess whether the `csapoc1` search service contains real cardholder data.
