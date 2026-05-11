# DevOps & Operations Report: Spring-Config-Server_INFRA_CONT

## Repository State

This repository contains only a README.md file ("docker image for spring-config-server") and Git metadata. There is no Dockerfile, no `application.yml`, no CI pipeline configuration, no `pom.xml` or `build.gradle`, and no source code of any kind. The INFRA_CONT suffix suggests this is intended as a container definition repository, but all substantive content is absent from the current commit.

## Inferred Deployment Model

Based on the repository name and purpose, the Spring Cloud Config Server is deployed as a Docker container, most likely on the same ECS or Kubernetes infrastructure used by other Gen-2 services. The shared `Onbe/om-ci-setup` GitHub Actions reusable workflow (used by other WAPP and SVC repos) would be the expected CI mechanism once a proper workflow is added.

## Secrets Management Concerns

Spring Cloud Config Server requires two categories of secrets in its own configuration:

1. **Git backend credentials**: If the backing configuration Git repository is private (as it should be for an organisation storing service credentials), the Config Server needs a Git username/token or SSH deploy key to clone/pull the repository. How this credential is provided to the running container is unknown from this repository.

2. **Encryption key**: If using Spring Cloud Config encryption (`encrypt.key` or `encrypt.keyStore`), the encryption key or keystore password must be injected at runtime. If stored in an environment variable passed to the container, the security of that mechanism depends on the container orchestration platform's secret management (AWS Secrets Manager, Parameter Store, or similar).

Without an `application.yml` or Dockerfile, it is impossible to determine whether:
- The Config Server requires client authentication (Spring Security basic auth or OAuth2)
- It runs over HTTPS with a valid certificate
- The encryption feature is enabled
- The git backend uses SSH or HTTPS with token
- The container runs as a non-root user

## Observability

Spring Cloud Config Server is a Spring Boot application and provides Actuator endpoints by default. These should include:
- `/actuator/health` — health status
- `/actuator/info` — build information
- `/actuator/env` — (if exposed) the full property source hierarchy; this endpoint is sensitive and should be disabled or access-restricted in production

No CI pipeline, no monitoring configuration, and no alerting rules are present in this repository.

## EOL and CVE Concerns

Spring Cloud Config versions aligned with Spring Boot 2.x (Gen-2) are no longer receiving mainstream support as Spring Boot 2.x reached end-of-life in November 2023. Known CVEs of note for Spring Cloud Config Server:
- **CVE-2020-5410**: Path traversal in Config Server for applications using `native` file system backend — allows reading arbitrary files from the server filesystem
- **CVE-2019-3799**: Path traversal allowing reading files outside the config repository directory
- If the deployed Docker image uses a Spring Cloud Config version vulnerable to these CVEs and the native filesystem backend is in use, arbitrary file disclosure is possible

Without knowing the exact image version, specific CVE status cannot be confirmed. Immediate action: identify the Docker image tag/digest in use, verify it against current Spring Cloud releases.

## Operational Gaps

The absence of any content in this repository is itself an operational risk:
- No repeatable build process: if the Docker image needs to be rebuilt, there is no Dockerfile to reproduce it
- No documented configuration for the Config Server's own settings
- No CI/CD gates for changes to the Config Server configuration
- No documented runbook or recovery procedure

This repo requires immediate remediation: either populate it with the actual Dockerfile and configuration, or document that the Config Server is managed through another mechanism.
