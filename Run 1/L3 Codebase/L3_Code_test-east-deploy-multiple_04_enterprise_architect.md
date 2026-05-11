# Enterprise Architect — test-east-deploy-multiple

## Platform Generation
**Gen-3** (test/tooling harness). Uses Java 21 and Spring Boot 3.4.2, consistent with the Gen-3 technology baseline. It is not a Gen-1 or Gen-2 production service.

## Business Domain
Platform Engineering / DevOps Tooling. Not part of any payment, card-issuing, or disbursement domain. Belongs to the CI/CD infrastructure domain.

## Role in the Architecture
- **Purpose**: Deployment validation harness. Demonstrates and certifies that the `om-ci-setup` GitHub Actions reusable workflow can handle multi-module Maven projects producing multiple deployable WARs.
- **Consumers**: DevOps and platform engineers; no downstream business services consume this app in production.
- **Producers**: None — no upstream business data feeds into this service.

## Dependencies
| Dependency | Type | Notes |
|---|---|---|
| `Onbe/om-ci-setup` (GitHub Actions) | CI/CD workflow | Pinned to `@main` — no version lock |
| GitHub Packages | Artefact registry | Destination for built WARs |
| Spring Boot 3.4.2 | Runtime framework | Via spring-boot-starter-parent |
| Java 21 | JDK | Required at build and runtime |

## Integration Patterns
- No integration patterns. The two WAR modules are independent; they do not call each other and have no shared state.
- GitHub Actions reusable-workflow pattern (call/callee) is the only integration point.

## Strategic Status
- **Active** as a CI/CD test harness.
- **Not a migration target** — already on Gen-3 stack.
- **Low strategic value** beyond validating deployment pipelines; could be replaced by a simpler smoke-test application.

## Migration Blockers
None. This repository is already on Java 21 / Spring Boot 3.x and has no legacy dependencies or patterns requiring migration.
