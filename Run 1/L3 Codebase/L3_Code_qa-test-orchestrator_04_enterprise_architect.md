# 04 Enterprise Architect — qa-test-orchestrator

## Platform Generation
Gen-3 (cloud-native GitHub Actions SaaS). No legacy code, no on-premises infrastructure.

## Business Domain
Quality Assurance / Engineering Enablement. Not a business-facing service; an internal developer tooling layer.

## Role
Central smoke-test dispatcher for the Onbe East API estate. Acts as a fan-out coordinator that delegates execution to per-API test suites housed in `qa-api-test-automation`.

## Dependencies
| Dependency | Type | Coupling |
|---|---|---|
| `OnbeEast/qa-api-test-automation` | Cross-repo reusable workflow | Hard — specific `@main` references |
| GitHub Actions SaaS | Execution platform | Hard |
| Onbe East API endpoints (10 services) | Test targets | Soft (runtime only) |

## Integration Patterns
- **Fan-out dispatcher**: one workflow file conditionally invokes N child workflows based on user input
- **Reusable workflow** (GitHub Actions `uses:` syntax): all child invocations follow the same contract (environment_type input, PAT_TOKEN secret)
- No event-driven triggers; strictly manual / human-in-the-loop

## Strategic Status
**Active – Low strategic value as currently implemented.** The repo is a thin wrapper. Long-term, it should be merged with the scheduling and reporting tooling to provide a single test portal with dashboards, scheduling, and audit trails. Consider migrating to a dedicated QA orchestration platform (e.g., Testkube, Azure Test Plans) to support Gen-3 observability requirements.

## Migration Blockers
- None that prevent migration; repo has no persistent state, no database, no deployed service
- Dependency on `qa-api-test-automation@main` must be version-pinned before any platform migration to avoid breaking changes
