# Solution Architect Report: Spring-Config-Server_INFRA_CONT

## API Surface

Standard Spring Cloud Config Server endpoints (all inferred from framework behaviour, not from present source):

| Endpoint | Method | Purpose | Auth Required |
|---|---|---|---|
| `/{application}/{profile}` | GET | Retrieve config for app+profile | Should require Basic Auth |
| `/{application}/{profile}/{label}` | GET | Retrieve config for specific branch/tag | Should require Basic Auth |
| `/encrypt` | POST | Encrypt a value | Should require Basic Auth |
| `/decrypt` | POST | Decrypt a value | Should require Admin Auth |
| `/actuator/health` | GET | Health check | Should be public or restricted |
| `/actuator/env` | GET | View full property sources | Must be restricted/disabled |
| `/actuator/refresh` | POST | Refresh config | Must be restricted |

Without source code or a Dockerfile, the actual authentication configuration, which Actuator endpoints are exposed, and the TLS configuration cannot be verified.

## Security Posture

**Unassessable from available source; high risk by default.**

Spring Cloud Config Server ships with no authentication enabled by default. Without evidence of Spring Security configuration in this repository, the following assumptions apply and represent critical risks:

1. **Unauthenticated configuration access**: Any process that can reach the Config Server's port can read any application's configuration for any profile. In an environment where database passwords, API keys, and encryption keys are served as configuration, this means network-level access equals secret disclosure
2. **`/actuator/env` exposure**: If Actuator is enabled with its default configuration in older Spring Boot versions, `/actuator/env` exposes all property sources including those marked sensitive; this provides a complete credential dump
3. **`/decrypt` endpoint**: If encryption is enabled, the `/decrypt` endpoint decrypts arbitrary ciphertext submitted to it; without authentication, this is a decryption oracle available to any network caller

## Critical Vulnerabilities (Inferred from Framework Defaults)

Without source code, vulnerabilities are inferred from known Spring Cloud Config Server defaults and CVEs:

1. **CVE-2020-5410 (path traversal)**: Spring Cloud Config Server before 2.2.3 / 2.1.9 allowed path traversal via the `label` parameter when using the native filesystem backend, enabling arbitrary file read from the server filesystem. If the image version is not patched, this is critical
2. **Default no-auth configuration**: Spring Cloud Config has no authentication by default; PCI DSS Requirement 7 requires access restriction
3. **Missing TLS**: If served over HTTP (default port 8888 without TLS configuration), all configuration data including sensitive values is transmitted in plaintext on the internal network

## Technical Debt

- **Empty repository**: The most significant technical debt is that this repository contains no deployable content. The actual Docker image, its configuration, and its security controls are managed outside of source control, violating infrastructure-as-code principles and making audit, reproducibility, and change control impossible
- **No CI/CD**: Without a pipeline, changes to the Config Server image or configuration require manual operations with no automated testing, approval gate, or deployment record
- **Spring Boot 2.x EOL**: If the deployed image runs Spring Boot 2.x (the Gen-2 vintage), it reached end-of-life in November 2023 and no longer receives security patches
- **Undocumented encryption posture**: It is unknown whether `{cipher}` encryption is used for secrets in the backing config repository

## Immediate Recommendations

1. Add a Dockerfile and `application.yml` to this repository with Spring Security Basic Auth or OAuth2 protection of all Config Server endpoints
2. Verify the backing Git config repository uses `{cipher}` encrypted values for all secrets; rotate any plaintext secrets
3. Confirm TLS is terminated at or before the Config Server
4. Disable or access-restrict `/actuator/env` and `/decrypt` endpoints in production
5. Pin the Docker image to a specific, patched Spring Cloud Config version and document the CVE review date
6. Implement high-availability with at least two Config Server replicas; configure `spring.cloud.config.fail-fast=false` and retry with backoff in consumers to tolerate brief unavailability
