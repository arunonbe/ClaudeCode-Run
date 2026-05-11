# Enterprise Architect View — nexpay-cardprocessor-svc

## Platform Generation

**Generation 3 — Core NexPay Payment Infrastructure**

`nexpay-cardprocessor-svc` is a first-class Gen-3 NexPay service. All indicators confirm Gen-3 status:
- Parent: `nexpay-parent:0.2.8-SNAPSHOT`
- Java 25, Spring Boot (via nexpay-parent), Maven 4
- PostgreSQL with Azure AD passwordless auth, Flyway migrations
- Azure Container Apps deployment, Azure Key Vault secrets, Azure App Configuration
- OpenTelemetry / Dynatrace instrumentation
- Multi-adapter SPI architecture for pluggable processor integrations

## Business Domain

**Card Issuance and Management — NexPay Core Payment Rail**

This service is the **card issuance authority** in the NexPay Gen-3 platform. It sits at the centre of the payment delivery path: when a recipient is onboarded and a payment is approved, this service is the component that actually creates the prepaid card at a card processor. It is the primary interface between Onbe's Gen-3 platform and external card processors (Thredd, FIS, and potentially Fiserv).

Without this service, no prepaid card can be issued in the Gen-3 payment flow.

## Position in the Architecture

```
[nexpay-recipientorchestrator-svc]
[nexpay-order-orchestrator]
         │ POST /v1/cards
         ▼
[nexpay-cardprocessor-svc]   ← THIS SERVICE
  │
  ├──→ ScopeResolver → [ProcessorConfig] table → selects adapter
  │
  ├──→ ThreddAdapter
  │       ├── POST /v2/scheme-services/create-card (Thredd REST API)
  │       └── POST /v2/scheme-services/{id}/transactions (initial load)
  │
  └──→ FisAdapter
          ├── POST to FIS CO_IssueCard.asp (form-encoded)
          └── POST to FIS CO_AssignCard_LoadValue.asp (initial load)
          └── mTLS (PKCS#12 client certificate)
  │
  └── PostgreSQL DB (cardprocessor database)
       ├── card (entity + Envers audit)
       ├── card_balance
       ├── job (async issuance)
       ├── processor_config
       ├── scope_map
       ├── card_product
       └── processor_account
```

## Dependencies

### Inbound (Consumers)
| Service | Interface | Usage |
|---|---|---|
| `nexpay-recipientorchestrator-svc` | REST (generated client from `-client` submodule) | Card issuance for claim-code saga |
| `nexpay-order-orchestrator` | REST | Card issuance for system-initiated orders |
| Internal APIM | Internal APIM (`INTERNAL_APIM: true`) | Routing to card processor service |

### Outbound
| Service | Interface | Criticality |
|---|---|---|
| Thredd REST API | HTTPS + JWT Bearer | Critical — primary modern processor |
| FIS `CO_IssueCard.asp` / `CO_AssignCard_LoadValue.asp` | HTTPS + mTLS + form-encoded | Critical — primary legacy US processor |
| PostgreSQL `cardprocessor` DB | Azure AD passwordless JDBC | Critical — card state persistence |
| Azure Key Vault | Managed Identity | Critical — processor credentials |
| Azure App Configuration | Managed Identity | High — runtime configuration |
| Dynatrace OTLP endpoint | HTTPS | Medium — observability |

## Integration Patterns

- **Provider SPI pattern**: `nexpay-cardprocessor-adapter-spi` defines the processor interface. `ThreddAdapter` and `FisAdapter` implement it. New processors can be added without changing the core service.
- **Scope-based routing**: `ScopeMap` table routes programs/redemption products to processor configs, enabling multi-processor programs and time-bounded migrations.
- **Idempotency**: Every card creation request carries an `Idempotency-Key` header. The `Card.idempotencyKey` column provides deduplication for network retries.
- **Async job pattern**: `POST /v1/jobs` creates a `Job` entity and returns immediately; polling `GET /v1/jobs/{jobId}` retrieves the result when processing completes.
- **Circuit breaker**: Resilience4j circuit breaker on balance inquiry calls to processors (50% failure rate threshold, 30s wait).
- **Hibernate Envers audit**: Every card state change is captured in `card_aud` — immutable audit trail for PCI DSS Req 10.

## Strategic Status

**Active Development — Critical Gen-3 Service**

This service is central to NexPay Gen-3's value proposition: processor-agnostic card issuance. Its `0.0.3-SNAPSHOT` version signals it is still in active development and has not reached a stable release. However, it is included in the production deployment pipeline (QA and prod targets in `java-build-deploy-aca.yml`).

**Architecture maturity**: The multi-module structure, SPI adapter pattern, Flyway-managed schema, and Envers audit trail represent high architectural maturity for a Gen-3 service. The main gaps are:
1. SNAPSHOT versions in production
2. Container security (root user)
3. `processorMetadata` JSONB PAN risk (pending audit)

## Enterprise Risk Register

| Risk | Severity | Notes |
|---|---|---|
| FIS `cardNum` in `processorMetadata` JSONB | Critical | May constitute unmasked PAN storage — must be audited before QSA assessment |
| SNAPSHOT versions in production pipeline | High | `nexpay-cardprocessor:0.0.3-SNAPSHOT` and `nexpay-parent:0.2.8-SNAPSHOT` |
| No PAN storage deduplication audit | High | The `card_aud` table audit trail must be verified to contain only masked PANs |
| Container runs as root | High | PCI DSS Req 7 / defence-in-depth risk |
| No explicit idempotency enforcement at DB level | High | `idempotencyKey` in `Card` entity — uniqueness constraint must be verified in Flyway DDL |
| Swagger UI enabled in QA (try-it-out) | Medium | See also nexpay-recipientorchestrator-svc analysis — shared pattern across NexPay |

## Compliance Architecture

- **PCI DSS CDE**: This service is firmly within the CDE. It issues PANs via Thredd, stores masked PANs, handles recipient PII, and holds processor credentials. PCI DSS Req 1-12 applies in full.
- **PCI DSS Req 3.4**: Masked PAN storage (first 6 / last 4) is compliant. `processorMetadata` JSONB must be verified to not contain full PANs.
- **PCI DSS Req 6**: The Envers `card_aud` table provides the immutable change log. CodeQL and container scan (when re-enabled) provide vulnerability management.
- **Reg E**: Each successful card creation represents a delivered payment instrument. The `card` entity and its audit trail constitute the Reg E transaction record.
- **OFAC**: OFAC screening occurs upstream in the orchestrator services, not here. This service must not proceed with card issuance without upstream confirmation of screening clearance.
