# Enterprise Architecture — onbeeast-architecture-models

## Platform Generation
**Cross-generational documentation** — This repository documents the OnePlatform (Gen-2) Recipient Web architecture, which is the system that NexPay Gen-3 is progressively replacing.

## Business Domain
Architecture Governance / Documentation. Provides the shared architecture reference model for the OnbeEast Recipient Web platform, spanning the boundary between Gen-2 OnePlatform and Gen-3 NexPay.

## Role in the Platform
| Attribute | Value |
|-----------|-------|
| Type | Architecture documentation repository |
| Deployable | No |
| Audience | Solution architects, enterprise architects, developers |
| Scope | RecipientWebApplication — OnePlatform UI + BFF + Redis + Azure Functions + CDN + Blob Storage |

## Architecture Models Present
| Model | Level | File |
|-------|-------|------|
| System Context | C4 L1 | `Context/C4-OnePlatform-SystemContext.puml` |
| Container | C4 L2 | `Container/C4-OnePlatform-ContainerModel.puml` |
| Component | C4 L3 | `Component/C4-OnePlatform-ComponentModel.puml` |

## Key Architecture Decisions Documented
1. **BFF pattern**: OnePlatform API is the Backend for Frontend between React UI and eCount Core — Gen-3 `nexpay-recipientweb-bff` is the successor.
2. **Redis as affiliate cache**: Affiliate data is not queried from DB on every request; Redis is the runtime cache, populated asynchronously by Azure Functions.
3. **CDN + Blob Storage**: Static UI assets delivered via CDN backed by Azure Blob Storage; content managed by `om-content-management-api`.
4. **Event-driven cache invalidation**: Blob tag changes and DB affiliate changes each trigger separate Azure Functions to update Redis — eventual consistency model.
5. **IT Admin interface**: Cache Admin API allows manual Redis management by IT admins.

## Strategic Status
- The documented architecture is **Gen-2 OnePlatform** — the diagrams need to be updated to reflect Gen-3 NexPay services as they come online.
- The `nexpay-recipientweb-bff` is the Gen-3 replacement for `OnePlatform API`; `nexpay-recipient-profile-svc` is the Gen-3 replacement for recipient data stored in eCount Core.
- No Gen-3 C4 diagrams are present in this repository — a gap in architecture documentation for the NexPay platform.

## Migration Blockers
- Not a deployable system; no migration blockers in the traditional sense.
- Architectural blocker: Gen-3 NexPay C4 diagrams should be added to this repository (or a new `NexPayPlatform` directory) to maintain architectural coherence and governance documentation as the migration progresses.
- The `EndClientContextDiagram.svg` output lacks a source `.puml` — its architectural intent is undocumented.
