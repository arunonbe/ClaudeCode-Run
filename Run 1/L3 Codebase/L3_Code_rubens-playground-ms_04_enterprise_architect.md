# Enterprise Architect Analysis: rubens-playground-ms

## Platform Generation
**Gen-3 (prototype/playground)**

Strong Gen-3 indicators:
- Spring Boot (via `nexpay-parent`)
- OpenAPI-first design with code generation (`openapi-generator-maven-plugin`)
- Delegate pattern from OpenAPI generator
- Spring Data JPA (`OrderRepository extends JpaRepository`)
- Liquibase database migrations
- Containerised with multi-stage Dockerfile
- Non-root container user
- Spring Boot Actuator health checks
- Environment variable-based configuration (12-factor)
- Lombok (`@Data`, `@Builder`, `@Slf4j`)
- SendGrid SDK integration (modern SaaS email)
- FreeMarker templating for emails
- Azure Container Apps deployment target
- Package namespace `com.onbe.stablerails` (Onbe brand, not eCount/Citi)
- Parent POM `com.onbe.nexpay:nexpay-parent` (Nexpay Gen-3 platform)

## Business Domain
**Nexpay / StableRails — Order Management (Prototype)**

Prototype implementation of the order creation and reward notification flow for the Nexpay StableRails product. Demonstrates the Gen-3 microservice pattern for single-account order placement with smart link generation for recipient reward redemption.

## Architectural Role
**Developer Sandbox / Pattern Reference Implementation**

This service is explicitly a playground. Its architectural role is:
1. Validate the Gen-3 microservice pattern (OpenAPI-first, Spring Boot, JPA, Liquibase, Docker, Azure Container Apps)
2. Prototype the StableRails Orders API contract (`ordersapi.yml`)
3. Demonstrate the email notification flow via SendGrid + FreeMarker

It is NOT a production service and should NOT be used as a production component without:
- Authentication implementation (bearer auth defined in spec but not enforced)
- Security hardening (HTTPS enforcement, input sanitisation, secrets management)
- Performance and load testing
- PII handling controls (DOB encryption, log masking)

## Internal Dependencies
| Component | Role |
|---|---|
| `nexpay-parent:0.1.10-SNAPSHOT` | Spring Boot BOM + common Nexpay dependencies |
| PostgreSQL (DS_DB_ordersvc) | Primary data store |
| SendGrid | Email delivery |
| Azure Container Apps | Compute platform |
| `ordersapi.yml` | OpenAPI specification (co-located in repo) |

## Integration Patterns
- **OpenAPI-First**: API contract defined in YAML; code generated at build time; implementation via delegate pattern.
- **REST/JSON**: Standard HTTP REST API with JSON bodies.
- **Spring Data JPA**: Repository pattern for database access.
- **Liquibase**: Schema migration as code.
- **Email-as-notification**: Reward notification via transactional email (SendGrid).
- **Smart Link Pattern**: UUID-based URL for recipient reward redemption; stateless URL-based claim flow.

## Strategic Status
**Prototype — Valuable Pattern Reference for Gen-3**

This service demonstrates the correct Gen-3 architectural patterns that should be adopted when migrating Gen-1 services:
- OpenAPI contract-first
- Spring Boot with Actuator
- Docker/container-first
- Environment variable configuration
- Liquibase migration
- Proper non-root container security

However, as a playground it has gaps that prevent production promotion:
1. No authentication enforcement despite bearer auth in spec
2. Java 25 (pre-release JDK)
3. SNAPSHOT versioning
4. PII without encryption
5. Debug logging of full entity objects
6. Developer-named ("rubens") — indicates personal prototype, not team-owned production service

## Migration / Promotion Path to Production
1. Implement JWT bearer token validation (Spring Security + OAuth2 Resource Server).
2. Downgrade to current LTS JDK (Java 21).
3. Version the service properly (release versions, not SNAPSHOT).
4. Encrypt `date_of_birth` at application layer (or use column encryption).
5. Mask PII in DEBUG log output (custom `toString()` or LogMasker).
6. Replace SNAPSHOT parent with a release version of `nexpay-parent`.
7. Remove `dev-tools` from runtime dependencies (currently `runtime` scope, should be `optional`).
8. Add Azure Pipelines / GitHub Actions CI/CD pipeline.
9. Integrate with StrongBox or Azure Key Vault for SendGrid API key.
10. Add rate limiting and input size limits.
