# Data Architecture — onbeeast-architecture-models

## Data Stores
This repository contains **no application data stores**. It is a documentation-only repository.

## Data Modelled (Architecture-Level)
The C4 diagrams document the following data stores and flows at the architecture level:

| Data Store (per C4 model) | Technology | Purpose |
|--------------------------|-----------|---------|
| Redis Cache | Redis | Affiliate data and XContent blob index tag cache |
| Azure Blob Storage | Azure Blob | Static content (HTML, images, CSS, JS) for all client programs |
| Affiliate Data (external) | Relational DB (external) | Client program configuration data |
| eCount Core (external) | Legacy system | Core card/account processing |

## Data Flows Documented
1. User → OnePlatform UI → OnePlatform API (BFF) → eCount Core.
2. Azure Blob Storage → Azure Function (blob tag updates) → Redis Cache.
3. Affiliate Data DB → Azure Function (affiliate updates) → Redis Cache.
4. OnePlatform API → Redis Cache (affiliate lookup).
5. OnePlatform UI → CDN → Azure Blob Storage (static content delivery).
6. IT Admin → Cache Admin API → Affiliate Data + Blob Storage + Redis Cache.

## Sensitive Data (Architecture Awareness)
- The C4 container model does not annotate which flows carry PII or cardholder data.
- eCount Core integration handles card transactions — this flow is within PCI DSS scope.
- Affiliate Data DB contains client program configuration, not cardholder data.
- Redis Cache holds affiliate data and content metadata — sensitivity depends on affiliate record contents.

## Compliance Gaps (Documentation)
- No security overlay or threat model diagram — PCI DSS scope boundaries are not explicitly marked in the diagrams.
- No authentication/authorisation flows documented in the C4 models.
- The `EndClientContextDiagram.svg` output file exists but the corresponding `.puml` source is not in the `RecipientWebApplication/C4Models` tree — source is missing or in a sub-directory not captured at depth 3.
