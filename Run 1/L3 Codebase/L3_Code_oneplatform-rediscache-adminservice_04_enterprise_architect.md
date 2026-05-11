# Enterprise Architect — oneplatform-rediscache-adminservice

## Platform Generation
**Gen-3** — Spring Boot 3.2.4 on Java 21 with Azure-native integrations (Key Vault, Blob Storage, Front Door, CDN Manager). Uses virtual threads (Project Loom). No legacy XML Spring context or XML-RPC.

## Business Domain
**Recipient Experience Platform / Configuration Management**
Supports the MyPaymentVault (mypaymentvault.com) cardholder portal by providing a managed, pre-warmed Redis cache of affiliate skins, program settings, and content pointers.

## Architectural Role
- **Supporting service** to `oneplatform-rest_API`: the REST API reads from Redis; this admin service writes to Redis.
- **Cache warming orchestrator**: bridges SQL Server (cbaseapp, Ecountcore) and Azure Blob Storage into a unified Redis cache.
- **CDN cache management**: provides operational control over Azure Front Door edge cache via a single internal API.
- No direct end-user traffic; purely internal/operational.

## System Dependencies
| System | Direction | Protocol |
|--------|-----------|----------|
| `oneplatform-rest_API` | Consumer of Redis written by this service | Shared Redis namespace |
| `cbaseapp` SQL Server | Upstream data source | JDBC/TLS 1.2 |
| `Ecountcore` SQL Server | Upstream data source | JDBC/TLS 1.2 |
| Azure Blob Storage (`data` container) | Upstream data source | Azure SDK (HTTPS) |
| Azure Key Vault | Credential provider | Azure SDK/Managed Identity |
| Azure Front Door / CDN | Management target | Azure Resource Manager SDK |

## Integration Patterns
- **Cache-aside (write path)**: Admin service explicitly writes structured data to Redis; reading services use Redis directly without going back to SQL.
- **Index-tag-as-metadata**: Azure Blob Storage index tags (not blob content) are used as a lightweight content routing table cached in Redis hashes.
- **Managed Identity**: Azure identity federation used in lieu of stored credentials for all Azure resource access.
- **Async virtual-thread parallelism**: Bulk cache warm-up uses Java 21 virtual threads for concurrent processing without thread pool exhaustion.

## Strategic Status
- **Active / in production use** (QA and production profiles are complete and reference production hostnames).
- Represents a clean Gen-3 pattern: Spring Boot 3, Java 21, Azure native, Key Vault secrets.
- No deprecated dependencies observed in the primary runtime path.
- The `.javaold` files indicate an in-progress refactoring (async config was rewritten to use virtual threads).

## Migration Blockers (for hypothetical further migration)
- Hard dependency on specific Redis key naming conventions shared with `oneplatform-rest_API` — any change to key taxonomy requires coordinated release.
- Azure subscription ID and tenant ID hardcoded in `application.properties` — these are infrastructure identifiers that belong in Key Vault or environment config, not source.
- Database hostnames using internal DNS (`q-lis-db01.nam.wirecard.sys`) — require DNS resolution within the VNet; cannot run outside Onbe's Azure or on-premises network without VPN.
- No Dockerfile: containerization strategy not yet defined for this service.
