# Enterprise Architecture — nexpay-recipient-profile-svc

## Platform Generation
**Gen-3 (NexPay)** — Core microservice in the NexPay Gen-3 platform.

## Business Domain
Recipient Identity Management. This service is the authoritative system of record for recipient personal profiles within the NexPay Gen-3 disbursements platform.

## Role in the Platform
| Attribute | Value |
|-----------|-------|
| Type | Domain microservice (data owner) |
| Deployed in production | Yes (Azure Container Apps) |
| Domain responsibility | Recipient profile CRUD + full audit history |
| API exposure | Internal APIM only (EXTERNAL_APIM: false) |

## Dependencies
### Upstream (callers of this service)
- `nexpay-recipientorchestrator-svc` — expected to call this service to store profiles after orchestration.
- `nexpay-recipientweb-bff` — may call indirectly via orchestrator.
- Internal tooling and admin services.

### Downstream (services this service calls)
- **Azure App Configuration** — startup configuration and feature flags.
- **Azure Key Vault** — secrets resolution via App Config.
- **Azure PostgreSQL** — primary data store.
- **Dynatrace OTLP endpoint** — telemetry in production.

## Integration Patterns
- **Synchronous REST API** — OpenAPI-generated interface (`RecipientProfilesApiDelegate`, `ProfileAddressesApiDelegate`, `ProfileAttributesApiDelegate`, `ExternalProfileMappingsApiDelegate`).
- **Optimistic locking** — `@Version` on all JPA entities for concurrent update safety.
- **Event sourcing-lite** — Hibernate Envers provides immutable revision history without a separate event bus.
- **Delegate pattern** — OpenAPI generator produces `*ApiDelegate` interfaces; implementation in `*-impl` module.

## Strategic Status
- **Active Gen-3 development** — version `0.0.1-SNAPSHOT`, not yet at a stable release.
- This service is the Gen-3 replacement for recipient identity management previously embedded in the eCount Core monolith.
- Strategic direction: decouple recipient identity from card-processing and order-management concerns into this dedicated bounded context.
- Parent POM `nexpay-parent:1.0.2` stabilising — indicates the platform is maturing.

## Migration Blockers
- No explicit migration from Gen-1/Gen-2 observed in this repo; a data migration from eCount Core `recipient` tables to PostgreSQL will be required at go-live.
- `ExternalProfileMapping.source_system` field is the bridge: it allows a NexPay profile to reference legacy system IDs, enabling phased migration.
- `CONTAINER_SCAN: false` must be re-enabled before production promotion.
- Swagger UI in qa/prod should be evaluated for disablement or gateway protection.
