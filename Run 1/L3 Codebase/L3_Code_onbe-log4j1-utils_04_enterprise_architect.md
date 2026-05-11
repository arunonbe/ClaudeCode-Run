# Enterprise Architect — onbe-log4j1-utils

## Platform Generation
**Gen-1 / Gen-2 Support Library** — exists to keep Gen-1/Gen-2 applications (those still using Log4j 1.x) compliant while they await migration. It is not itself a Gen-3 component.

## Business Domain
Cross-cutting: Security / Observability Infrastructure.

## Role in the Platform
Security patching library. Consumed by legacy Java services that have not yet migrated to Log4j 2 or Spring Boot 3.x. It is a bridge artifact, not a permanent platform component.

## Known Consumers (from README examples)
- `workbench/wizard.log` reference in example config suggests workbench_WAPP or similar legacy WAR deployments.
- Any service in the Onbe portfolio still on Log4j 1.x (e.g., older ecount/xplatform services).

## Dependencies
- Upstream: `log4j:log4j:1.2.17` (compile-time, runtime provided by consumer).
- Test: JUnit Jupiter 5.11.4.
- Build: shared CI workflow `Onbe/om-ci-setup`.

## Integration Patterns
- Dependency injection via Maven: consumers declare the artifact in their POM.
- Configuration-driven: consumers update their `log4j.xml` — no code changes required.

## Strategic Status
**Deprecated / Temporary** — the README explicitly classifies this as a temporary measure. Strategic direction is upgrade to Log4j 2.x (see onbe-log4j-utils) and ultimately to Spring Boot 3.4.0 structured logging.

## Migration Blockers
1. Consumer services must still be on Java 8 + Log4j 1.x to need this artifact; the blocker is those upstream services' own migration timelines.
2. No automated mechanism prevents new services from adopting this artifact erroneously.
