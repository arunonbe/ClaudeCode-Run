# CZ-OTP — DevOps / Operations View

## Repository Status
The `CZ-OTP` repository directory exists at `E:\OnbeEast363\repos\CZ-OTP` but is **completely empty** — no build files, Dockerfile, CI/CD workflows, or source code are present.

## Build System
Cannot be determined — no `pom.xml`, `build.gradle`, or equivalent found.

## CI/CD
Cannot be determined — no `.github/workflows/`, `Jenkinsfile`, or equivalent found.

## Configuration
Cannot be determined.

## Observability
Cannot be determined.

## Infrastructure
Cannot be determined.

## Operational Risks
- **No deployable artifact.** The service cannot be built or deployed in its current state.
- **No monitoring configuration.** Health check, logging, and alerting cannot be assessed.
- If this is a planned new service, the following should be established before development begins:
  - Maven / Gradle build with Spring Boot parent or equivalent.
  - GitHub Actions CI/CD workflow (following the `om-ci-setup` reusable workflow pattern used by other Onbe services).
  - Actuator health / liveness / readiness endpoints.
  - Log4j2 or Logback configuration with structured JSON logging.
  - OpenTelemetry instrumentation.
  - Dockerfile based on `bellsoft/liberica-openjre-alpine:21` (consistent with other Onbe services).
  - Dapr secret store integration for credential management.

## Action Required
Confirm whether CZ-OTP is a new unstarted service or whether the code resides on a non-default branch / different repository.
