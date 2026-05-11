# Business Analyst View — wirecard_issuing-s2s-token-service_LIB

## Business Purpose

wirecard_issuing-s2s-token-service_LIB is the Gen-2 (Wirecard/Northlane) server-to-server (S2S) OAuth 2.0 authorization server for the Wirecard Issuing platform. It issues, validates, and manages JWT access tokens for server-to-server API calls between Wirecard Issuing microservices. This is an infrastructure security service, not a direct business transaction processor — it enables the secure service mesh that underlies Gen-2 card issuing operations.

The artifact name and package (`com.wirecard.authserver`) confirm this is a Wirecard AG origin codebase, developed during the Wirecard/Northlane era of Onbe's platform evolution. It deployed as a Spring Boot application on Linux (RPM package for systemd services) with Java 8.

## Capabilities Provided

- **OAuth 2.0 authorization server**: Issues signed JWT access tokens via Spring Security OAuth 2.0 (`spring-security-oauth2-autoconfigure`)
- **Client credentials flow**: S2S token issuance for machine-to-machine authentication (no human/cardholder authentication)
- **Multi-brand support**: `BrandsEnhancer` suggests token claims include brand context (multi-brand issuing environment)
- **Client details management**: `IssClientDetailsService` — custom OAuth 2.0 client registry backed by an Oracle database
- **User details service**: `IssUserDetailsService` — technical user authentication (service accounts, not cardholder users)
- **RSA/EC key management**: `KeysConfiguration`, `ActiveSigningKeyRecord`, `InactiveSigningKeyRecord`, `InMemorySigningKeyRepository` — RSA/EC key rotation support for JWT signing; `HashingKeyIdGenerator` for key ID derivation
- **JWT signing**: `KeyIdAwareJwtAccessTokenConverter` — signs JWTs with a configurable key; `KeyIdAwareSigner`/`KeyIdAwareSignerDecorator` support key-aware signing for multi-key environments
- **BouncyCastle cryptography**: `BCProviderApplicationContextInitializer` registers BouncyCastle as a JCE provider for cryptographic operations
- **Actuator monitoring**: Spring Boot Actuator + `issuing-boot-actuator-utils` for health endpoints
- **Integration testing**: `iss-authorization-server-it` module with Groovy/Spock tests (`TechnicalUserIntegrationTest`, `TokenIntegrationTest`)

## Client/Cardholder Impact

This service has no direct cardholder impact — it serves only machine-to-machine authentication. However, a failure of this service would block all Gen-2 Wirecard Issuing service-to-service calls, cascading to card processing, transaction authorization, and customer data access failures. This is a critical platform dependency.

## Business Rules Found in Code

- Tokens are scoped to specific brands (multi-brand issuing environment) — a service cannot use a token from brand A to access brand B resources
- Key rotation is supported: inactive signing keys are retained (for token validation) while new active keys issue new tokens — this supports zero-downtime key rotation
- Client authentication is backed by Oracle database — client credentials (service accounts) are managed centrally, not statically configured
- Token integrity is protected via JWT signature — any tampered token is rejected
- The `IssWebServerAccessDeniedHandler` and `IssWebServerAuthenticationEntryPoint` provide custom error responses for unauthorized access, preventing information disclosure in error messages

## Regulatory Obligations

- **PCI DSS Requirement 8**: Service accounts (OAuth 2.0 clients) must have unique credentials, time-limited tokens, and revocation capability. The `IssClientDetailsService` must enforce these requirements.
- **PCI DSS Requirement 8.6.2**: Application/service accounts must not be shared and must use strong authentication. The S2S token service enforces this for Gen-2 services.
- **GLBA**: As infrastructure security for card issuing operations, this service is in scope for GLBA safeguard requirements.
- **PCI DSS Requirement 12.3.2**: Cryptographic key management procedures must govern the signing keys managed by this service (key generation, storage, rotation, retirement, destruction).

## Key Business Risks Found in Code

- **Spring Boot 2.1.5 / Spring Security OAuth 2.0**: Spring Security OAuth 2.0 project reached end-of-life; replaced by Spring Authorization Server. No security patches will be released for this dependency. **Critical for a security-critical service.**
- **Java 8 requirement**: The RPM deployment requires JDK 8 (`requires('wd-jdk8', '1.8.0_141', GREATER | EQUAL)`). Java 8 is EOL for commercial use (Oracle) and requires an LTS subscription for continued security patches.
- **Wirecard AG copyright**: License and vendor fields in the RPM spec still reference `(C) 2018, Wirecard AG` — post-acquisition ownership and IP must be clarified.
- **Oracle database backend**: `validationQuery: select 1 from dual` confirms Oracle-specific syntax; migration away from Oracle would require schema migration and DAO layer changes.
- **Horus crypto library**: `com.wirecard.horus:horus-crypto:8.35.0.RC3_20170904163352_8786975238bd` — a Wirecard proprietary cryptography library with a release candidate version from 2017. Post-insolvency/acquisition, this library may no longer receive security updates.
