# Data Architect — poc_elasticsearch

## Data Stores

| Store | Type | Purpose |
|---|---|---|
| Azure Cognitive Search | Managed search service (cloud) | Primary data store for customer lookup; index `azureblob-index` on service `csapoc1.search.windows.net` |
| Azure Blob Storage (inferred) | Object storage | Source for the search index (`azureblob-index` naming convention indicates blob-based indexer) |

No relational database, Redis, or other data stores are present in this repository. All data persistence is in Azure infrastructure.

## Schema / Index Structure

The search index structure is inferred from the JavaScript result processors in `CustomerService.html`:

| Field | Inferred Type | Sensitivity |
|---|---|---|
| `name` | String | PII — full cardholder name |
| `email` | String | PII — email address |
| `card` | String | CHD — appears to be card number or proxy (last 4 displayed; full value present in index) |
| `client` | String | Business reference — client/program identifier |
| `token` | String | Payment token — sensitivity depends on token type |
| `platform` | String | Operational metadata |
| `program` | String (facet) | Program identifier |
| `amount` | Numeric (facet) | Transaction amount or balance |

## Sensitive Data

| Data Class | Location | Classification |
|---|---|---|
| Cardholder name | Azure Cognitive Search index | PII — GLBA, CCPA, GDPR |
| Email address | Azure Cognitive Search index | PII |
| Card number / proxy | Azure Cognitive Search index (`card` field) | CHD — PCI DSS in-scope if full PAN |
| Payment token | Azure Cognitive Search index (`token` field) | Sensitive — depends on token format |
| Card last-4 | Displayed in UI results | Non-sensitive per PCI DSS if all that is shown |

## Encryption

| Layer | Status |
|---|---|
| Azure Cognitive Search at-rest encryption | Microsoft-managed encryption enabled by default on Azure |
| Azure Cognitive Search in-transit | HTTPS (TLS) — `azsearch.js` uses `search.windows.net` endpoint |
| Application-level field encryption | None — fields indexed and returned in plaintext |
| API key protection | None — query key is embedded in client-side HTML source |

## Data Flow

```
Azure Blob Storage (source data)
  --> Azure Cognitive Search Indexer
      --> Index: azureblob-index (service: csapoc1)
          --> Browser (CustomerService.html)
              azsearch.js AzSearch.Automagic
              --> HTTPS GET queries to csapoc1.search.windows.net
              --> Results rendered in browser DOM
              --> Cardholder data visible to agent browser session
```

## Data Quality / Retention

| Concern | Detail |
|---|---|
| Index currency | Depends on Azure indexer run schedule — not configured in this repo |
| Data retention | Not defined; Azure Cognitive Search retains index until manually purged |
| Duplicate/stale records | Index built from blob storage snapshots — no deduplication logic visible |
| Field masking | Only last-4 of card displayed in results processor; full `card` value present in index response |

## Compliance Gaps

| Gap | Standard | Impact |
|---|---|---|
| Hard-coded query API key in HTML source | PCI DSS Req 8.3, Req 6.2 | Critical — exposes read access to potentially CHD-containing index |
| Full card field present in search index responses | PCI DSS Req 3.3 | If `card` contains a full PAN, this is a CDE scope violation |
| No authentication on the HTML interface | PCI DSS Req 8 | Unauthenticated access to cardholder search violates access control requirements |
| No field-level masking for CHD in search results | PCI DSS Req 3.3 | Raw card data returned to browser; only display layer masks it |
| Azure Cognitive Search access audit | PCI DSS Req 10.2 | Query-level audit logging requires Azure Diagnostic Settings to be configured — not visible in this repo |
| No data retention or purge policy | PCI DSS Req 3.2, GLBA | CHD in search index has no defined retention boundary |
