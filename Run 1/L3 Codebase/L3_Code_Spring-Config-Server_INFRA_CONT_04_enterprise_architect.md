# Enterprise Architect Report: Spring-Config-Server_INFRA_CONT

## Platform Generation

**Gen-2 (Wirecard/Northlane) infrastructure component**. Spring Cloud Config Server is the canonical externalised configuration pattern for Gen-2 Spring Boot microservices. Its presence signals that the Wirecard/Northlane platform adopted the 12-factor app configuration pattern, separating configuration from deployable artefacts. The absence of source in this repository suggests the Config Server has been operational for some time and may predate structured repository practices.

## Integration Patterns

- **Config client integration**: Gen-2 services declare `spring-cloud-starter-config` as a dependency and set `spring.cloud.config.uri` in their `bootstrap.yml` to point to this server. On startup, before the application context loads, the client connects to the Config Server and fetches the property set
- **Git backend**: Standard Spring Cloud Config uses a Git repository as the backing store; the Config Server clones/pulls the repo and serves files from it, providing versioning and audit history
- **Encryption/decryption**: The `/encrypt` and `/decrypt` endpoints can be used by administrators to encrypt values before committing them to the config repo, and the server decrypts on serve (or clients decrypt if `spring.cloud.config.server.encrypt.enabled=false`)
- **Refresh**: Services can refresh their configuration without restart using Spring Cloud Bus (AMQP/Kafka) or `/actuator/refresh` endpoint

## External Dependencies

- A separate private Git repository containing the actual configuration files — this is the critical dependency and the primary risk surface
- Git hosting service (GitHub, GitLab, or an internal Gitea/Bitbucket instance)
- Docker registry for the Config Server image
- Potentially: Spring Cloud Bus message broker (RabbitMQ or Kafka) for configuration refresh propagation

## Position in the Broader Platform

Spring-Config-Server is the single source of truth for runtime configuration across all Gen-2 services. Its position in the dependency graph makes it a **Tier-0 infrastructure component**: if it is unavailable and consuming services have `spring.cloud.config.fail-fast=true`, the entire Gen-2 fleet cannot start. Even with `fail-fast=false`, services will use their locally-packaged fallback configuration, which may be stale or incomplete.

Within the three-generation architecture:
- **Gen-1 services** (eCount/Citi Java, XML config): do not use Spring Cloud Config; they use JNDI, filesystem-based property files, and the `CBASE_HOME_URL` convention
- **Gen-2 services**: use Spring Cloud Config Server for all externalised configuration
- **Gen-3 services**: use Azure App Configuration and Azure Key Vault directly, bypassing the Spring Cloud Config Server

The Config Server is therefore a mid-life infrastructure component — no longer needed for Gen-3 and not applicable to Gen-1.

## Migration Blockers

1. **Tight coupling of Gen-2 services**: Every Gen-2 service that uses `spring.cloud.config` is a consumer; migrating away requires touching all Gen-2 service bootstraps simultaneously or running Config Server alongside the Azure-native alternative
2. **Secret migration**: Encrypted values in the backing Git config repository must be re-encrypted and migrated to Azure Key Vault as part of any Gen-3 migration; the migration window requires both old and new secret stores to be live simultaneously
3. **Unknown configuration surface**: Without access to the backing Git config repository, the full scope of what is stored and served is unknown; this makes safe migration planning difficult

## Strategic Status

**Retain for Gen-2 duration, then decommission**. As Gen-2 services migrate to Gen-3 (Azure App Configuration + Key Vault), the Spring Cloud Config Server's consumer population shrinks. The eventual decommissioning path is:

1. Audit all consumers of Config Server
2. For each consumer migrating to Gen-3: move its configuration to Azure App Configuration, move its secrets to Azure Key Vault
3. Remove `spring-cloud-starter-config` dependency from the service
4. When the last consumer is migrated, decommission the Config Server and archive the config Git repository

In the interim, this repository must be populated with a proper Dockerfile and CI pipeline to ensure the Config Server can be reliably rebuilt and redeployed.
