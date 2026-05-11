# stip-models — Enterprise Architect View

## Platform Generation
**Undetermined / Not Yet Implemented.** The repository is empty. Based on the name and pattern:
- If using OpenAPI 3.x / AsyncAPI → Gen-3 intent
- If using XSD/WSDL/JAXB → Gen-2 pattern
No content is present to confirm which direction was intended.

## Business Domain
**Critical Payments — Stand-In Processing domain model layer.** This is the authoritative source of truth for all STIP data contracts. Its strategic importance is very high: every STIP service implementation depends on these model definitions being correct, complete, and versioned.

## Role in Ecosystem
| Role | Description |
|---|---|
| Canonical model source | Defines the authoritative data structures for STIP domain |
| Code generation upstream | Drives `stip-generated` repository via automated code generation |
| Contract boundary | Defines the interface between STIP and the rest of the platform |
| Versioning anchor | Schema versions control compatibility between STIP services and consumers |

## Dependencies
| Dependency | Direction | Notes |
|---|---|---|
| `stip-generated` | Downstream | Generated code output; depends on this repo |
| `stand-in-processing-api` | Downstream | Runtime service that depends on generated models |
| `stand-in-recovery-service` | Downstream | Recovery/reconciliation service that depends on models |
| Card account data services | Lateral | STIP decisions reference card account data |
| Payment network (Visa/Mastercard) | External | STIP implements network-mandated stand-in rules |

## Integration Patterns
Not implemented. Expected patterns:
- **Schema-first design**: models defined as machine-readable specs; implementations generated
- **API contract versioning**: semantic versioning of model releases
- **Event schema registry**: if STIP uses event streaming (Kafka/Azure Service Bus), event schemas registered in a schema registry

## Strategic Status
| Dimension | Assessment |
|---|---|
| Maturity | Non-existent — placeholder only |
| Strategic criticality | Highest possible — STIP model definitions are the foundation for stand-in processing capability |
| Current utility | None |
| Risk if permanently absent | Critical — no stand-in processing, no business continuity for card authorisation during outages |
| Recommended action | P1 escalation; assign domain owner; define and implement STIP schema within current sprint |

## Migration Blockers
This repository is itself a blocker for any STIP Gen-3 implementation. No STIP service can be built on a stable contract without these model definitions existing. It must be populated before any downstream STIP work can proceed.

## Relationship to stip-generated
```
stip-models (this repo — upstream)
    ↓  code generation
stip-generated (downstream — currently also empty)
    ↓  Maven dependency
stand-in-processing-api
stand-in-recovery-service
```
Both the model source and its generated output are currently empty. The entire STIP contract layer is absent.
