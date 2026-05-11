# stip-generated — Enterprise Architect View

## Platform Generation
**Undetermined.** The repository is empty. The intended generation output would likely be Gen-2 or Gen-3 depending on the model schema and generator chosen in `stip-models`.

Based on the naming pattern and the companion `stip-models` repo, the likely intended pattern is:
- **Gen-3** if models are defined as OpenAPI/AsyncAPI/Protobuf specs generating REST clients and event contracts
- **Gen-2** if models are JAXB/XSD-based generating SOAP stubs

## Business Domain
**Critical Payments — Stand-In Processing.** STIP is the fallback authorisation engine for Onbe's prepaid card platform. It enables transaction decisions when the primary authorisation system (e.g., ecount-core, an external processor) is unreachable. This is a tier-1 availability capability.

## Role in Ecosystem
| Role | Description |
|---|---|
| Generated code library | Provides auto-generated DTOs, API clients, or service stubs derived from `stip-models` definitions |
| Dependency for STIP runtime services | Expected to be consumed by stand-in processing runtime services (e.g., `stand-in-processing-api`, `stand-in-recovery-service`) |
| Model-to-code bridge | Enforces consistency between STIP model definitions and their Java representations |

## Dependencies
| Dependency | Direction | Notes |
|---|---|---|
| `stip-models` | Upstream (generates this repo's content) | The model repository drives code generation |
| STIP runtime services | Downstream (consume this repo's artifacts) | `stand-in-processing-api`, `stand-in-recovery-service` likely depend on these generated artifacts |

## Integration Patterns
Not implemented. Expected patterns:
- Generated REST client stubs (if OpenAPI-based)
- Generated event/message contracts (if AsyncAPI/Protobuf-based)
- Generated JPA entities or JAXB classes (if XSD-based)

## Strategic Status
| Dimension | Assessment |
|---|---|
| Maturity | Non-existent — placeholder only |
| Strategic criticality | Very high — STIP is a mandatory payments resilience capability |
| Current utility | None |
| Risk if permanently absent | Critical — Onbe's prepaid card network has no automated stand-in capability, exposing cardholders to declined transactions during system degradation |
| Recommended action | Treat as P1 gap; escalate to payments platform engineering team |

## Migration Blockers
Cannot assess — no content. If STIP is being rebuilt as Gen-3, the generated code repository is a prerequisite for all STIP Gen-3 services. Its absence blocks any STIP Gen-3 implementation.
