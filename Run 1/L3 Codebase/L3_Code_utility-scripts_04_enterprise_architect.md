# Enterprise Architect — utility-scripts

## Platform Generation
**Cross-generation tooling** (not a deployable service). The scripts support Gen-1, Gen-2, and Gen-3 repositories. There is no single platform generation classification applicable.

## Business Domain
Platform Engineering / Developer Productivity. Supports all engineering domains (payments, card issuing, disbursements) indirectly by accelerating routine developer tasks.

## Role in the Architecture
- **Shared developer toolbox** — a commons repository that any Onbe engineer can contribute to or consume.
- Not a deployed service; no SLA, no uptime requirement.
- Provides horizontal value across all platform generations and business domains.

## Dependencies (outbound)
| External System | Script | Access Type |
|---|---|---|
| GitHub (`api.github.com`) | `clean_remote_repo.py` | REST API (branch/PR management) |
| Atlassian Confluence | `replace_page/replace_page.py` | REST API V2 (content management) |
| Microsoft SQL Server | `schema_doc_generator.py` | ODBC read (schema metadata) |
| Onbe Nexus / Maven Central | `update_deps.ps1` | Maven dependency resolution |

## Integration Patterns
- **Script-based CLI integration**: all tools are invoked manually from a developer's shell; no event-driven or API-driven invocation.
- **GitHub REST API** (token-authenticated, per-request, pull-then-delete): `clean_remote_repo.py`.
- **Confluence REST API** (Basic auth email+token, stateless): `replace_page/`.
- No message queues, no event hubs, no service mesh.

## Strategic Status
- **Active and maintained**: recent additions (`replace_page/`, `update_deps.ps1` PowerShell port) suggest ongoing investment.
- **No planned migration**: tooling repos do not follow the Gen-1/2/3 migration roadmap.
- The `schema_doc_generator.py` connecting to SQL Server databases is particularly relevant as those databases undergo Gen-3 migrations — the tool can support documentation of legacy schemas during migration.

## Migration Blockers
None — this is not a service subject to the Gen-3 migration programme. However, the following should be addressed before wider team adoption:
1. Secrets management: `schema_doc_generator.py` credential pattern must be externalised.
2. Python environment: root scripts lack dependency management; should adopt `uv` or `pip` requirements files for reproducibility.
