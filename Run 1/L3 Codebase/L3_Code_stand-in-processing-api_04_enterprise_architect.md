# Enterprise Architect Report: stand-in-processing-api

## Platform Generation

**Gen-3 (NexPay/Onbe, Azure)**. SASI is the most modern service in this batch: Java 21, Spring Boot 3.5.5, Azure-native infrastructure (AKS, Azure SQL, Key Vault, App Configuration, Service Bus), specification-first API design (OpenAPI + WSDL), JPA/Hibernate, Flyway migrations, Resilience4j, and an AI-assisted development workflow. It follows the Onbe Gen-3 architectural patterns throughout.

However, SASI occupies a unique position: it is a Gen-3 service whose primary function is to stand in for Gen-1/Gen-2 systems during outages. This means it maintains direct database connections to Gen-1/Gen-2 databases (`ecountcore`, `cbaseapp`, `jobsvc`, `ordersvc`) as read-only data sources, and its domain model mirrors the Gen-1 entity structure. SASI is therefore architecturally Gen-3 but functionally dependent on the Gen-1 data tier.

## Integration Patterns

- **Dual-protocol API**: REST (`/api/`, `/v1/`) via Spring MVC controllers generated from OpenAPI; SOAP (`/ws/`) via Apache CXF endpoints generated from WSDL; both share the same service and repository layer
- **MapStruct mapping**: Explicit SOAP↔REST object translation via generated MapStruct mappers — clean separation of protocol from business logic
- **Fiserv integration**: Outbound REST calls to Fiserv via mutual TLS (client certificate); protected by Resilience4j circuit breaker, retry, and timeout
- **Azure Service Bus**: Asynchronous `sasi-failover` queue for high-load scenarios during stand-in
- **Legacy database reads**: Direct JPA connections to Gen-1 databases (ecountcore, cbaseapp, etc.) for stand-in data; these bypass any API layer of the primary systems
- **EhCache**: Application-level caching of security validation results and frequently accessed configuration data

## External Dependencies

- **Fiserv Payment Platform**: Critical — sole external payment processor; circuit breaker deployed
- **Azure SQL Database**: Five separate database connections (primary SASI + four legacy); multi-AZ with geo-replication
- **Azure Key Vault**: Secret management; accessed via Managed Identity
- **Azure App Configuration**: Feature flags and configuration; `AZURE_APP_CONFIG_ENABLED` controls activation
- **Azure Service Bus**: Failover queue
- **Azure Kubernetes Service**: Container orchestration
- **Azure Application Gateway**: External load balancer with WAF

## Position in the Broader Platform

SASI is **the payment continuity backstop** — the last line of defence ensuring cardholders can transact when primary systems fail. This makes it uniquely critical:

- It must be operational when primary systems are not — meaning it cannot depend on any service from the primary system stack for its own availability
- It reads directly from legacy databases, creating a tight coupling to the Gen-1 data layer that will persist until Gen-1 databases are either migrated or fully decommissioned
- It exposes both SOAP (for backward compatibility with Gen-1 callers) and REST (for Gen-3 callers), bridging the protocol gap between generations

Within the ecosystem: Fiserv → authorisation request → (during outage) SASI → reads Gen-1 databases → responds to Fiserv → logs to primary SASI DB → reconciles with primary system when it recovers.

## Migration Blockers

1. **Gen-1 database dependency**: SASI reads from `ecountcore`, `cbaseapp`, `jobsvc`, and `ordersvc` directly; these databases can only be decommissioned after SASI's data model is fully migrated to Gen-3 databases — a multi-year effort
2. **SOAP backward compatibility**: Clients that use the SOAP interface (`CsApi_v1.wsdl`, `CsApi_v3.wsdl`) are likely Gen-1 or Gen-2 systems; these cannot be upgraded until those systems are themselves migrated
3. **`LegacyCryptoService`**: The ECount data access layer includes a `LegacyCryptoService` that likely handles eCount-era field encryption; SASI must understand and use this legacy encryption until the data is re-encrypted in a modern format
4. **Stand-in reconciliation**: The reconciliation process between SASI-processed stand-in transactions and primary system records is complex; any change to either SASI or the primary system must maintain reconciliation compatibility

## Strategic Status

**Strategic service — maintain and evolve**. Unlike most Gen-1/Gen-2 services which are candidates for decommissioning, SASI is a greenfield Gen-3 build that will grow in importance as the platform matures. Key strategic priorities:

1. Reduce its dependency on direct Gen-1 database reads by building event-driven data sync from primary systems to SASI's own Azure SQL database
2. Expand the SASI primary database to hold all data needed for stand-in operation, eliminating Gen-1 database read dependencies
3. Replace SOAP with REST-only as Gen-1/Gen-2 SOAP clients are migrated
4. Enforce the `disable-security-filter` property cannot be enabled in non-local environments
