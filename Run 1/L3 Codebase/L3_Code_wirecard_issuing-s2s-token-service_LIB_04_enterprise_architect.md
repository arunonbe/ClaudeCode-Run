# 04 Enterprise Architect — wirecard_issuing-s2s-token-service_LIB

## Platform Generation
Gen-2 / Transitional. Spring Boot (OAuth2 Authorization Server pattern) with Gradle build, Ansible-based deployment to bare-metal/VM RPM targets (`p-s2sauth-app01/02.wirecard.sys`), Jenkins CI, and Oracle database backend. Predates the current GitHub Actions / Azure / containerised Gen-3 deployment model. Retains an on-premises Wirecard network deployment footprint.

## Business Domain
Identity and Access Management / Payments Security. Issues OAuth2 JWT access tokens for server-to-server (S2S) API authentication across Wirecard Issuing services. Acts as the trust anchor for service-to-service calls within the Wirecard/Onbe issuing platform.

## Role
OAuth2 Authorization Server for the Wirecard Issuing ecosystem. Services authenticate by presenting client credentials; the token service issues a signed JWT that is accepted by resource servers (`iss-resource-server`). Also provides a JWK endpoint (`/jwk-key-set`) for public key distribution, enabling decentralised JWT verification.

## Dependencies
| Dependency | Direction | Criticality |
|---|---|---|
| Oracle Database | Outbound | Critical — client credentials and user store |
| BouncyCastle (`bcprov-jdk15on`) | Compile | Critical — RSA/EC key operations for JWT signing |
| Spring Security OAuth2 (`spring-security-oauth2`) | Compile | Critical — authorization server framework |
| `iss-resource-server` (sibling module) | Runtime consumer | High — validates tokens issued by this service |
| Ansible inventory (`dev`, `qa`, `test`, `prod`) | Deploy | High — controls which VMs receive the RPM |
| Jenkins (Jenkinsfile) | CI | High — build, test, RPM, Sonar, publish, deploy |
| Nexus (internal RPM repo) | Artifact | High — RPM storage |
| Sonar | CI | Medium — code quality gate |

## Integration Patterns
- **OAuth2 Client Credentials flow**: services exchange `client_id`/`client_secret` for a signed JWT
- **JWK Set endpoint** (`/jwk-key-set`): resource servers fetch public keys to verify tokens without calling the auth server on each request
- **Ansible pull deployment**: Gradle builds RPM; Jenkins triggers Ansible playbook on target VMs
- **In-memory signing key repository** with active/inactive key records; supports key rotation with `kid` (Key ID) header in JWT
- **BrandsEnhancer**: injects brand-specific claims into the token during the token enhancement chain

## Strategic Status
**Critical dependency — migration required.** This service is the authentication backbone for the Wirecard Issuing S2S API ecosystem. Its current deployment is:
- On Wirecard on-premises VMs (`p-s2sauth-app01/02.wirecard.sys`)
- CI via Jenkins (legacy)
- Database on Oracle (legacy)
- No containerisation

Migration to a Gen-3 Azure-hosted OAuth2 / OIDC provider (Azure Entra ID external identities or a containerised Spring Authorization Server) is required as part of the Wirecard infrastructure decommission roadmap. Until migrated, this service is a critical single point of failure on the Wirecard network.

## Migration Blockers
- `spring-security-oauth2` (Spring Security OAuth2 legacy) has been end-of-life'd by Spring; must migrate to `spring-authorization-server` 1.x
- Oracle database dependency must be replaced; client/user data must be migrated to a supported cloud database
- All resource servers consuming JWTs from this issuer must update their `issuer-uri` configuration after migration
- Key material (RSA/EC private keys used for JWT signing) must be securely migrated; rotation must be coordinated with all resource server operators
- Jenkins pipeline must be replaced with GitHub Actions during migration
- Ansible RPM deployment must be replaced with Helm/Kubernetes manifests
