# DevOps & Operations — onbeeast-architecture-models

## Build
This repository contains **no build artifacts** — it is a pure documentation repository.

- No `pom.xml`, `package.json`, `Dockerfile`, or build tooling observed.
- PlantUML `.puml` source files must be rendered to SVG externally using a PlantUML tool or IDE plugin (PlantUML server, VS Code extension, IntelliJ plugin).
- Pre-rendered SVG outputs are committed to the `out/` directory.

## Deployment
- Not deployable. Documentation artefacts only.
- SVG files in `out/` may be served statically or embedded in wikis/Confluence.
- The `.puml` files reference external PlantUML icon libraries via HTTPS URLs (`https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master/`), `tupadr3/plantuml-icon-font-sprites`, and `plantuml-stdlib/Azure-PlantUML` — internet connectivity required to render locally.

## Configuration Management
- No configuration management.
- Architecture changes are made by editing `.puml` source files and regenerating SVG outputs.
- No versioning or release tagging observed.

## Observability
- Not applicable.

## Infrastructure Dependencies
| Dependency | Purpose |
|-----------|---------|
| PlantUML rendering tool | Convert `.puml` to SVG |
| GitHub raw content CDN | PlantUML `!include` URLs for C4 macros and icons |
| Azure PlantUML library | Azure-specific icon set for container diagram |

## CI/CD
- No CI/CD pipeline present in this repository (no `.github/workflows/` directory observed).
- Manual workflow: developer edits `.puml`, renders to SVG, commits both to repo.

## Operational Risks
- **Stale diagrams**: Pre-rendered SVGs in `out/` may not match the current `.puml` sources if someone edits `.puml` without re-rendering.
- **External URL dependencies**: PlantUML `!include` URLs point to external GitHub raw content — if those repos change or are unavailable, local rendering will fail.
- `!includeurl` directive (deprecated in newer PlantUML versions) used in the container model — rendering may fail with newer PlantUML versions.
- No diagram-as-code CI to validate `.puml` syntax or auto-regenerate SVGs on commit.
- `EndClientContextDiagram.svg` in `out/` has no corresponding `.puml` source in the observed directory tree — source of truth is missing for that diagram.
