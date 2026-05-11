# Enterprise Architect — wirecard_corporate-client-module_LIB

## Platform Generation
**Gen-2** (Wirecard/Northlane issuing platform). Same generation markers as `check-agent`:
- Spring Boot 1.5.13.RELEASE
- Gradle 4.8-jdk8
- GitLab CI
- RPM packaging + Ansible rolling-update
- `d-*.wirecard.sys` DNS hostnames
- Oracle Database
- `com.wirecard.issuing` group ID

## Business Domain
**Corporate Client Lifecycle Management** within the prepaid card issuing domain. Manages the B2B side of the Northlane/Wirecard prepaid card platform — the corporate entities that hold card programs, issue cards to their employees/beneficiaries, and manage virtual client accounts.

Sits at the intersection of:
- **Client Onboarding** (create/activate/terminate corporate clients)
- **Card Program Management** (brand-to-client mapping, card program configuration)
- **Card Issuance Operations** (create cards, load/unload funds, close accounts)
- **Virtual Client Management** (sub-entities under corporate clients)

## Role in the Architecture
- **System of record** for corporate client master data in the Wirecard/Northlane platform.
- **Orchestrator**: For card-related operations, the CCM acts as an orchestrator calling CMM (Card Management Module) for card creation and CCP (Call Center Platform/Horus) for fund management.
- **Security boundary**: Brand-aware OAuth2 authorisation enforces that users only access clients for their authorized brands.
- **Upstream for card issuance**: Other Wirecard services that need corporate client context will reference this service.

## Dependencies
| Dependency | Direction | Purpose |
|---|---|---|
| CCP (Horus) `q-horust-app02.wirecard.sys` | Outbound | Fund reservation, A2A transfer, virtual client management |
| CMM `d-cmm-app01` | Outbound | Card creation, card program retrieval |
| Brand Server `q-brands-app01.wirecard.sys` | Outbound | Brand/card program catalogue |
| ISS Auth Server `q-s2sauth-app02.wirecard.sys` | Outbound | JWT JWK set, technical user management |
| ActiveMQ EventHub | Inbound | `AccountStateEvent` consumption |
| Oracle DB | Outbound | Primary persistence |

## Integration Patterns
- **REST (synchronous)**: Outbound calls to CCP, CMM, Brand Server, ISS Auth Server via `RestTemplate`-based clients.
- **OAuth2 Resource Server**: Inbound JWT authentication; brand-aware authorisation via Spring Security `@PreAuthorize`.
- **Event-driven (asynchronous)**: Inbound `AccountStateEvent` from EventHub.
- **AOP (correlation ID)**: `CorrelationIdInterceptor` on `CmmClient` passes correlation IDs across service calls.
- **Swagger/OpenAPI**: Springfox Swagger UI for API documentation.

## Strategic Status
- **Active Gen-2 service with high migration urgency**: This service is the system of record for corporate clients — a critical capability for the Northlane card issuing business.
- **Spring Boot 1.5.13 (EOL)**: Immediate security risk; must be on the migration roadmap.
- **Complex external dependencies**: Migration is complicated by reliance on CCP, CMM, Brand Server, and ISS Auth Server — all Wirecard/Northlane internal services with their own migration timelines.
- **Data sensitivity**: `T_PIN` column and PII in contacts make this service a PCI/GDPR priority.

## Migration Blockers
1. **Spring Boot 1.5.13**: Multi-step upgrade required (see `check-agent` analysis).
2. **`spring-security-oauth2`**: Must migrate to Spring Security 6.x OAuth2 Resource Server; JWT claim structure and brand-aware authentication logic must be re-implemented.
3. **`BrandsAwareAuthentication`** custom type: `com.wirecard.issuing.oauth2.resourceserver.BrandsAwareAuthentication` is a Wirecard library class. This library must be re-examined and potentially rewritten for Gen-3.
4. **Springfox Swagger 2**: Must migrate to SpringDoc OpenAPI.
5. **CCP and CMM HTTP clients**: `RestTemplate` must be replaced with `WebClient` or `RestClient` for Spring Boot 3.x; HTTP endpoint URLs must be updated.
6. **Oracle DB**: CCM stores complex domain data (addresses, contacts, legal entities) in Oracle. Liquibase changelogs contain Oracle-specific synonyms and grants.
7. **RPM packaging → OCI**: Ansible roles (`rolling_update`, `liquibase_migration`) must be replaced with Kubernetes manifests / Helm charts.
8. **`T_PIN` data remediation**: Before migration, the `T_PIN` column must be assessed and either removed, encrypted, or replaced with a secure reference — this is a data migration blocker with regulatory implications.
9. **Ansible inventories**: `ansible/inventories/prod` (not read) may contain production hostnames that must be migrated to new infrastructure.
