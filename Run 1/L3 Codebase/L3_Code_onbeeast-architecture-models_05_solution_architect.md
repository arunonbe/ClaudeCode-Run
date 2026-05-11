# Solution Architecture — onbeeast-architecture-models

## Technical Architecture
This repository contains **PlantUML C4 model source files** and pre-rendered SVG outputs. There is no application code.

- **Modelling language**: PlantUML with C4-PlantUML macro library.
- **Directory structure**:
  - `RecipientWebApplication/C4Models/Context/` — L1 System Context.
  - `RecipientWebApplication/C4Models/Container/` — L2 Container model.
  - `RecipientWebApplication/C4Models/Component/` — L3 Component model.
  - `out/` — Pre-rendered SVG outputs.
- **External dependencies** (PlantUML render-time includes):
  - `https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master/C4_Context.puml`
  - `https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master/C4_Container.puml`
  - `https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master/C4_Component.puml`
  - `https://raw.githubusercontent.com/tupadr3/plantuml-icon-font-sprites/v3.0.0/icons/`
  - `https://raw.githubusercontent.com/plantuml-stdlib/Azure-PlantUML/release/2-2/dist/`

## API Surface
Not applicable — no running service.

## Security Posture
- No secrets, credentials, or sensitive data in this repository.
- PlantUML `!include` from external GitHub URLs — if those URLs are compromised, rendered diagrams could be affected; this is a documentation integrity risk, not a runtime security risk.
- No `.puml` comments indicate security zones, network segmentation, or authentication flows — security architecture is not documented.

## Technical Debt
- `!includeurl` directive (deprecated) used in `C4-OnePlatform-ContainerModel.puml` lines 13-20 for Azure PlantUML icons — newer PlantUML versions may reject this syntax; should be migrated to `!include` with a local cache or a supported CDN URL pattern.
- Azure PlantUML library pinned to `release/2-2` — may be outdated; Azure icons may not reflect current Azure service names/icons.
- C4-PlantUML included from `master` branch (unpinned) — diagram behaviour may change if the upstream library is updated.
- No component diagrams for Gen-3 NexPay services — significant documentation gap.
- SVG outputs pre-committed — no automated regeneration; staleness risk.

## Code-Level Risks (PlantUML)
| File | Line | Risk |
|------|------|------|
| `C4-OnePlatform-ContainerModel.puml` | 13-20 | `!includeurl` (deprecated); will break in PlantUML v1.2022+ without `!define` workaround |
| `C4-OnePlatform-ContainerModel.puml` | 13 | `C4-PlantUML` included from `master` (floating reference) — diagram may change without notice |
| `C4-OnePlatform-ComponentModel.puml` | 12 | Link `[[../C4-GenericController-ObjectModel-Tentative/...]]` to a "Tentative" diagram — provisional design not finalised |
| `out/EndClientContextDiagram.svg` | — | SVG present but no `.puml` source in the scanned tree — source of truth missing |

## Gen-3 Migration Requirements
- Add Gen-3 NexPay C4 diagrams:
  - System context showing NexPay services alongside eCount Core and OnePlatform.
  - Container diagram for the NexPay Gen-3 microservices platform (auth, config, claim-code, recipient-profile, recipient-orchestrator, recipientweb-bff, card-processor, order-orchestrator, mock-processor).
  - Component diagrams for key services as they stabilise.
- Migrate `!includeurl` to supported `!include` syntax.
- Pin C4-PlantUML to a specific tag rather than `master`.
- Add CI pipeline to validate `.puml` syntax and auto-generate SVGs on commit.
