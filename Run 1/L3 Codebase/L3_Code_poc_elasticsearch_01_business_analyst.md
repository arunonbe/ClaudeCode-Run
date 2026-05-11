# Business Analyst — poc_elasticsearch

## Business Purpose
A proof-of-concept (POC) exploring Azure Cognitive Search (Elasticsearch-compatible) as a unified customer-lookup interface for Onbe's customer service tooling. The POC demonstrates a web-based "Global Search" UI that enables customer service agents to search cardholders by card number, account number, name, email, phone, program, or platform — with faceted filtering and drill-down to account, transaction, and funding details.

There is no backend service code in this repository. It is a static HTML/CSS/JavaScript prototype backed directly by Azure Cognitive Search.

## Capabilities

| Capability | Artefact | Summary |
|---|---|---|
| Full-text cardholder search | `CustomerService.html` + `azsearch.js` | Searches an Azure Cognitive Search index (`azureblob-index`) across name, email, card number, client, token, program, platform |
| Faceted search / filtering | HTML facet panels (`sortBy`, `platformFilter`, `amountFacet`, `clientFacet`, `programFacet`) | Left-panel facet widgets powered by AzSearch.Automagic |
| Advance search modal | `CustomerService.html` (modal `modalAdvanceSearch`) | Allows agent to search by name, email, phone, card number, card proxy |
| FIS CSA account detail view | `CustomerService.html` (modal `modalFISCsa`) | Tabbed detail: Account Holder, Account Details, Funding Details |
| Recipient activation UI content | `xContent/recipient/op/` | Static CSS and images for a recipient-facing activation flow (appears to be content assets, not search) |
| Program-specific activation content | `xContent/recipient/TMO_4848/` | T-Mobile-branded activation banners (program ID TMO_4848) |

## Key Entities

| Entity | Fields visible in UI |
|---|---|
| Cardholder | name, email, card number (last 4), account number, client, token |
| Program | pid, platform |
| Account | activation status, suspend status, transaction history (screenshots) |
| Funding | Permission-based; add/remove/adjust funds |

## Business Rules
1. Search supports wildcard lookup across card number, account number, first name, last name, email, phone, program, and platform.
2. Account funding operations are permission-gated ("This tab will be permission based").
3. Cardholder search results display last 4 of card number only (result.card.substr(result.card.length - 4)).
4. The prototype uses a static query API key embedded in the HTML — this is explicitly a POC pattern, not production-safe.

## Key Flows

### Customer Service Agent Search Flow
```
Agent opens CustomerService.html
  --> AzSearch.Automagic initialises against Azure Cognitive Search
      index: azureblob-index, service: csapoc1
  --> Agent types in search box
      --> Suggestions display: name + email + card (last 4) + client + token
      --> Agent selects result / presses search
          --> Full results rendered with facets
          --> Agent clicks result row --> FIS CSA modal opens
              --> Tabs: Account Holder Details / Account Details / Funding Details
```

## Compliance Relevance

| Standard | Relevance |
|---|---|
| PCI DSS v4.0.1 | Search index may contain card numbers and account numbers — highly sensitive CHD; POC does not implement masking beyond last-4 display |
| PCI DSS Req 3.3 | Card numbers in search index must be masked or tokenised; the advance-search form accepts "Card Number" as a direct input field |
| GLBA / CCPA | Name, email, phone, address are PII searchable — data classification and access controls required |

## Business Risks

| Risk | Severity | Notes |
|---|---|---|
| Hard-coded Azure Cognitive Search query API key in production-accessible HTML | Critical | Key `[REDACTED — rotate immediately]` is in plain HTML source — anyone who loads the page can use the key directly against the search index |
| Search index (`azureblob-index`) may contain PAN/CHD | Critical | If the backing index was built from raw card data, this is a PCI DSS CDE exposure |
| No authentication on the HTML page | High | Static HTML served without any authentication layer — any network-accessible client can search the index |
| Advance search form accepts full card number | High | Input field labelled "Card Number" — should accept only masked values |
| POC artefact mixed with production-looking recipient content (`xContent/`) | Medium | Program-specific activation content (TMO_4848) in the same repo suggests inadvertent mixing of POC and production assets |
| No clear status (POC vs retired vs proposed for production) | Medium | Repo name says "poc" but content is detailed enough to suggest prior use |
