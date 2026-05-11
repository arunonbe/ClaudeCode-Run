# nexpay-claim-code-svc — Enterprise Architect View

## Platform Generation

**Gen-3** — NexPay cloud-native microservice on Azure.

Evidence:
- Spring Boot (boot module with `NexpayConfigApplication`)
- Azure Container Apps deployment
- Azure App Configuration + Azure Key Vault for secrets
- Azure Managed Identity for authentication
- OpenTelemetry (OTLP) observability
- Flyway database migrations
- Spring Data JPA (repository pattern)
- Testcontainers for integration tests
- ECS structured logging
- `com.onbe.nexpay` namespace (fully migrated from Citi/eCount naming)
- Parent POM: `nexpay-parent` (Gen-3 NexPay shared parent)

## Business Domain

**Claim Code Management / Claimable Payments** — Part of the NexPay disbursement platform:
- Manages the claim code lifecycle for claimable payments (issued → claimed/expired/blocked)
- Provides the data access layer for the recipient's payment selection experience
- Supports all NexPay payment modalities: virtual card, physical card, push-to-card, PayPal, ACH, check

## Role in the Platform

```
[NexPay Recipient Web BFF / Client Admin Web BFF]
        |
        v
[nexpay-claim-code-svc]  ← claim code lookup, validation, recipient registration
        |
        v
[nexpay_claimable SQL Server database]
        |
        (data synced / co-managed with)
        v
[EcountCore database: claimable_payment, core_member, core_registration_basic]
```

This service is the **Gen-3 read/validation gateway** for claimable payment data. It does not own the authoritative write path (payments are presumably created by the legacy eCount core or another NexPay service) but provides the clean API surface for Gen-3 consumers.

## Dependencies

### Upstream (services nexpay-claim-code-svc depends on)
| Dependency | Type | Notes |
|---|---|---|
| `nexpay-parent:0.2.7-SNAPSHOT` | Maven POM | NexPay shared parent; SNAPSHOT — non-reproducible |
| Azure SQL Server (`nexpay_claimable`) | Database | Managed Azure SQL; connection via Key Vault |
| Azure App Configuration | Config store | Runtime configuration injection |
| Azure Key Vault | Secret store | Database connection strings |
| Azure Container Registry | Container images | Built and deployed by nexpay-iac |

### Downstream (services that consume nexpay-claim-code-svc)
Based on context and API naming:
- `nexpay-recipientweb-bff` — recipient-facing web UI backend
- `nexpay-clientadminweb-bff` — client admin UI backend  
- `nexpay-order-orchestrator` — orchestration of payment orders
- `nexpay-ivr-bff` (possibly, via claim code lookup for IVR flows)

## Integration Patterns

1. **REST API (HTTP/JSON)**: Spring Boot REST controllers exposed on port 8080; APIM-registered (internal only)
2. **Spring Data JPA**: Repository pattern over Azure SQL Server
3. **Flyway migrations**: Schema-as-code versioning
4. **Azure Managed Identity + App Configuration**: Secretless credential model
5. **OpenTelemetry OTLP**: Distributed tracing and metrics export
6. **Hibernate Envers**: Entity change auditing with actor identity from OTel baggage

## Strategic Status

| Dimension | Assessment |
|---|---|
| Lifecycle | **Active / Production** — Gen-3 live service |
| Technical debt | Low — clean Gen-3 patterns throughout |
| Java version | **Risk** — Java 25 (preview/early-access); should be Java 21 LTS |
| Parent SNAPSHOT | **Risk** — `nexpay-parent:0.2.7-SNAPSHOT` non-reproducible |
| Container scan | **Risk** — Disabled |
| Strategic fit | High — core component of NexPay disbursement platform |

## Migration Considerations (Forward-Looking)

This service is already Gen-3. Forward-looking considerations:
1. **Upgrade to Java 21 LTS**: Replace Java 25 with 21 for stability and LTS support
2. **Stabilise nexpay-parent**: Move from SNAPSHOT to a released version
3. **Enable container scanning**: Re-enable `CONTAINER_SCAN` once the scan configuration is stabilised
4. **Enable Flyway in QA**: Grant DDL permissions to QA DB user or run migrations via a separate elevated-privilege pipeline step
5. **Write path ownership**: Clarify whether this service will ever own write operations on `claimable_payment` or remain read-only; if write path is added, strong concurrency controls are needed (optimistic locking)
6. **Claim code logging**: Mask claim codes in log output to prevent token leakage in log aggregation systems
