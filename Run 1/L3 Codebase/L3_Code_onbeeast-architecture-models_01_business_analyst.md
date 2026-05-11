# Business Analysis — onbeeast-architecture-models

## Business Purpose
A shared architecture documentation repository containing C4 model diagrams for the OnbeEast Recipient Web platform. It provides PlantUML source files (`.puml`) and pre-rendered SVG outputs that define and communicate the system context, container, and component architecture of the OnePlatform Recipient Web system. This repository is a documentation and design artefact, not a deployable service.

## Capabilities
- **System Context diagram** (`C4-OnePlatform-SystemContext.puml`): Shows the Recipient Web system and its relationships to Users, Affiliate Data (client program DB), and eCount Core.
- **Container diagram** (`C4-OnePlatform-ContainerModel.puml`): Decomposes the Recipient Web System into:
  - OnePlatform UI (React frontend)
  - OnePlatform API (BFF, Spring)
  - Redis Cache (affiliate data and XContent)
  - Azure Function: Updates Blob Index Tags to Redis
  - Azure Function: Updates Affiliate data on DB changes
  - Cache Admin API (Redis management)
  - CDN (static content, lower latency)
  - Azure Blob Storage (static content for all clients)
- **Component diagram** (`C4-OnePlatform-ComponentModel.puml`): Decomposes the OnePlatform API (BFF) into Spring Controllers:
  - Card Activation Controller
  - Dashboard Controller
  - Generic Controller
  - Login Controller
  - Registration Controller
  - Transaction Controller

## Key Entities (Architecture Concepts)
| Entity | Description |
|--------|-------------|
| Recipient Web System | The bounded system boundary for the OnePlatform recipient experience |
| OnePlatform UI | React frontend; served via CDN |
| OnePlatform API | Spring BFF — the service that `nexpay-recipientweb-bff` is the Gen-3 replacement for |
| Redis Cache | Holds affiliate data and XContent metadata; populated by Azure Functions |
| Azure Blob Storage | Holds static UI assets; managed by `om-content-management-api` |
| Affiliate Data (external) | Relational DB of client program data |
| eCount Core (external) | Legacy core system |

## Business Rules (Architecture Constraints Documented)
- All user interactions route through the OnePlatform UI → OnePlatform API → eCount Core path.
- Redis Cache is the source of truth for affiliate lookups at runtime (populated asynchronously by Azure Functions from blob/DB changes).
- CDN caches static content from Azure Blob Storage — content updates require cache invalidation.
- Affiliate data changes trigger the Azure Function that updates Redis.
- Blob Storage tag changes trigger the Azure Function that updates Redis blob index tags.

## Compliance Relevance
- Architecture diagrams document data flows that include eCount Core (which processes card transactions) — these flows are relevant to PCI DSS scope boundary analysis.
- The Redis Cache holding affiliate data may contain program-level configuration that affects payment routing — availability and integrity are important.
- The C4 models do not document authentication/security layers explicitly — a security overlay diagram would be needed for PCI DSS scoping purposes.

## Risks
- Architecture diagrams may lag behind actual implementation — they document `OnePlatform API` (Gen-2 BFF) but the Gen-3 replacement (`nexpay-recipientweb-bff`) is now under development; diagrams need updating.
- No documentation for NexPay Gen-3 architecture is present in this repository — the Gen-3 system context, containers, and components are not yet modelled here.
- SVG outputs (`out/`) are pre-generated; they may be stale if `.puml` sources have been updated without regenerating.
