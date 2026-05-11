# Business Analyst Report: Spring-Config-Server_INFRA_CONT

## Business Purpose

Spring-Config-Server_INFRA_CONT is a Docker container definition repository for the Spring Cloud Config Server used within the Onbe/Wirecard/Northlane platform. Spring Cloud Config Server provides centralised, versioned external configuration for all Gen-2 microservices. Rather than storing application properties in each service's deployment artefact, services fetch configuration at startup (and optionally at runtime) from this server, which serves property files backed by a Git repository or filesystem.

The repository itself contains almost no source code — it is documented as "docker image for spring-config-server" in its README — indicating that the actual configuration properties served by this server are stored in a separate configuration Git repository (typically a private `config-repo` or similar). The Docker image wraps the Spring Cloud Config Server application.

## Capabilities

- Centralised configuration distribution to all Gen-2 Spring Boot microservices
- Environment-specific configuration (dev, QA, staging, production) via Spring profiles
- Git-backed configuration for versioning and audit trail of configuration changes
- Potentially supports encrypted property values (Spring Cloud Config's `/encrypt` and `/decrypt` endpoints using symmetric or asymmetric keys)
- Health and status endpoints at Spring Boot Actuator paths

## Client and Cardholder Impact

Every Gen-2 microservice that uses Spring Cloud Config depends on this server at startup. If the Config Server is unavailable, services that require it will fail to start or will operate with stale cached configuration. This can cause:
- Inability to deploy or restart services during incident response
- Stale database connection strings or credentials being used after rotation
- Feature flags not propagating to services, potentially allowing or blocking cardholder transactions incorrectly

## Business Rules Enforced

- Application-specific, profile-specific, and default property hierarchies (Spring Cloud Config property precedence)
- Access to the Config Server determines which services can obtain what configuration; if access is not restricted, a compromised service could read configuration intended for other services

## Regulatory Obligations

- **PCI DSS Requirement 2 (Secure configuration)**: The Config Server is a critical control point for secure configuration distribution. Unencrypted secrets served over HTTP, or absence of access controls, constitute a PCI DSS failure
- **PCI DSS Requirement 3 (Protect stored cardholder data)**: If database credentials, API keys, or encryption keys are served as plaintext properties, they must be encrypted at rest in the backing Git repository using Spring Cloud Config's encryption feature
- **PCI DSS Requirement 7 (Restrict access by business need)**: Access to the Config Server must be restricted; only authorised services should be able to retrieve their configuration
- **GLBA**: Configuration controlling access to systems holding customer financial data must be managed securely

## Key Business Risks

1. **Secrets-in-plaintext risk**: If the backing configuration Git repository stores database passwords, API keys, or encryption keys as plaintext YAML/properties files, they are exposed to anyone with read access to that repository and to the Config Server's HTTP endpoints
2. **No source code present**: The near-empty repository (README only, no Dockerfile, no application.yml) means the actual configuration and security posture cannot be assessed from this repository alone; the risk profile depends entirely on the separate configuration Git repository and the Docker image source, neither of which is visible here
3. **Config Server access control gap**: Spring Cloud Config Server defaults to no authentication; without Spring Security configuration, any internal service or attacker with network access can read all application configurations
4. **Single point of failure**: Without replicated Config Server instances and fast-fail configuration, the entire Gen-2 service fleet could fail to start if the Config Server is down during a deployment or restart event
