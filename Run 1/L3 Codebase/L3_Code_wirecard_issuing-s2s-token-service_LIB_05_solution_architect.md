# 05 Solution Architect — wirecard_issuing-s2s-token-service_LIB

## Technical Architecture
Multi-module Gradle project. Primary modules:
- **`iss-authorization-server`**: Spring Boot OAuth2 Authorization Server; issues signed JWTs via client-credentials flow; exposes JWK Set endpoint
- **`iss-resource-server`**: Spring Boot resource server; validates JWTs from the auth server
- **`iss-authorization-server-it`**: Integration tests; boots auth + resource server locally for end-to-end test
- **`sample-classic-spring`** / **`sample-spring-boot`**: client sample applications demonstrating token acquisition

Key classes in `iss-authorization-server`:
- `IssAuthorizationServerConfiguration` — `@EnableAuthorizationServer`; configures token store (JWT), token enhancer chain (BrandsEnhancer + KeyIdAwareJwtAccessTokenConverter), request factory
- `IssWebServerSecurityConfiguration` — `@EnableWebSecurity`; HTTP security: stateless sessions, CSRF disabled, `/jwk-key-set` public, `/callcenter-api/**` requires `TECHNICAL_USER_ADMIN`, basic auth
- `IssClientDetailsService` — JDBC-backed `ClientDetailsService`; loads client registrations from Oracle DB
- `IssUserDetailsService` — JDBC-backed `UserDetailsService`; loads user accounts from Oracle DB
- `KeyIdAwareJwtAccessTokenConverter` / `KeyIdAwareSigner` — adds `kid` (Key ID) header to JWT for JWK-based verification
- `InMemorySigningKeyRepository` — manages active and inactive RSA/EC signing key records; supports key rotation
- `HashingKeyIdGenerator` — derives key IDs from key material (deterministic)
- `BCProviderApplicationContextInitializer` — registers BouncyCastle JCE provider at startup
- `BrandsEnhancer` — injects `brands` claim into JWT token

## API Surface
| Endpoint | Method | Access | Description |
|---|---|---|---|
| `/oauth/token` | POST | Authenticated (client credentials) | Issues JWT access tokens |
| `/jwk-key-set` | GET | Public (permitAll) | JWK Set for public key distribution |
| `/callcenter-api/**` | Any | `TECHNICAL_USER_ADMIN` authority | Protected call-centre admin APIs |
| `{managementEndpointPath}/**` | Any | Public (permitAll) | Spring Boot Actuator health/info |

Token format: JWT (RS256 or EC); signed with active key from `InMemorySigningKeyRepository`; enhanced with brand claims.

## Security Posture
- **JWT signing**: BouncyCastle RSA/EC; `KeyIdAwareSigner` and `KeyIdAwareJwtAccessTokenConverter` correctly propagate `kid` to JWT header — enables safe key rotation without invalidating existing tokens
- **Password encoding**: `PasswordEncoder` injected into both `AuthorizationServerSecurityConfigurer` and `DaoAuthenticationProvider` — must confirm BCrypt or Argon2 in the actual bean definition
- **HSTS**: configured (`includeSubDomains=true`, `maxAge=31536000`) — correct
- **CSRF disabled**: appropriate for a stateless token endpoint
- **`/jwk-key-set` public**: correct — resource servers need unauthenticated access to public keys
- **Client credentials in Oracle DB**: credentials must be stored as hashed values; plain-text storage would be a critical security defect
- **TLS for Oracle**: `DataSourceConfig` supports TLS with truststore config (Base64-encoded truststore content in properties); must be enabled in production
- **HSTS not applied to the management endpoint**: management endpoint is `permitAll()`; if exposed externally, it should require authentication
- **`spring-security-oauth2` legacy**: this library is unsupported by Spring; known CVEs may not receive patches

## Technical Debt
| Item | Severity |
|---|---|
| `spring-security-oauth2` (EOL, unsupported by Spring) | Critical |
| Oracle JDBC driver dependency (Gradle; license-sensitive) | High |
| `spring.main.allow-bean-definition-overriding: true` — indicates bean naming conflicts | High |
| `allow-bean-definition-overriding` masks potential misconfiguration | High |
| Oracle12cDialect — Oracle 12c dialect; must update if Oracle version changes | Medium |
| In-memory signing key repository: key material loaded from config/DB; no HSM integration | Medium |
| Jenkins-based CI (no GitHub Actions parity) | Medium |
| Ansible RPM deployment (no Helm/Kubernetes) | Medium |
| `sample-classic-spring` and `sample-spring-boot` modules in same repo as production code | Low |
| `build.gradle` / `versioning.gradle` / `gradle.properties` — Gradle wrapper 5.x era (inferred); should be updated | Low |

## Gen-3 Migration
Recommended migration path:
1. Replace with Spring Authorization Server 1.x (`org.springframework.security:spring-authorization-server`) deployed as a Spring Boot 3 application
2. Migrate client/user credentials from Oracle to Azure SQL or Entra ID external identities
3. Replace in-memory signing key repository with Azure Key Vault managed key (RSA key, no exportable private key material in application config)
4. Deploy to AKS with Helm; replace Ansible RPM pipeline with GitHub Actions
5. Update all resource servers to point to the new issuer URI
6. Conduct coordinated key rotation with all resource server operators during cutover

## Code-Level Risks
- `DataSourceConfig.dataSource()` writes the Base64-decoded truststore to a file path (`truststoreProperties.getLocation()`) using `REPLACE_EXISTING` at startup — if the app starts as a non-privileged user without write permission to that path, the startup fails; if running as root, it writes a file at an attacker-controlled path (if `location` is configurable externally)
- `IssClientDetailsService` JDBC row mapper (`FooRowMapper`) name suggests a placeholder class name — should be renamed for clarity; not a security issue but indicates incomplete code review
- `BrandsEnhancer` class name and package are generic; without source, it's unclear what claims are injected — brand claims in JWTs must not include sensitive data that resource servers might over-trust
- `InMemorySigningKeyRepository` — key material is held in JVM heap; a heap dump would expose private signing keys; HSM integration is the secure alternative
- `tokenKeyAccess("permitAll()")` on the Authorization Server configurer exposes the public signing key via `/oauth/token_key` endpoint without authentication; this is intentional for key distribution but should be reviewed to ensure only the public key (not private key) is returned
