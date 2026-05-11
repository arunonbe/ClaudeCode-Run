# runner-test — Enterprise Architect View

## Platform Generation
**Gen-1** — Java 8, Maven Wrapper, no Spring, no container, no service mesh. Sole purpose is runner validation, not a production service.

## Business Domain
CI/CD Infrastructure / Platform Engineering. Not part of any payments domain.

## Role in Platform
Canary / smoke-test for GitHub Actions self-hosted runner pools. Validates that the runner environment (JDK, Maven, network access to artifact registries) is functional before production pipelines depend on it.

## Dependencies
| Dependency | Direction | Notes |
|---|---|---|
| `Onbe/om-ci-setup` | Consumes | Reusable CodeQL workflow (centralised) |
| Nexus `d-na-stk01.nam.wirecard.sys:8081` | Outbound | Legacy Wirecard artifact proxy |
| GitHub Packages `onbe/onbe_maven_releases` | Outbound | Onbe Maven registry |
| Self-hosted runner pool (Windows X64) | Depends on | CI execution environment |
| Self-hosted runner pool (Linux ubuntu-docker) | Depends on | CodeQL execution environment |

## Integration Patterns
None — no runtime integrations.

## Strategic Status
**Non-strategic / support tooling.** Should be retained only as long as the self-hosted runner pool requires a smoke-test project. No migration effort required unless runner infrastructure changes.

## Migration Blockers
- Plaintext credentials in `settings.xml` must be migrated to GitHub Actions secrets before any modernisation.
- The legacy Wirecard Nexus mirror hostname must be updated or removed.
