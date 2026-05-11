# DevOps / Operations View — RecipientApp

## Source Availability Limitation

The `RecipientApp` repository contains only the `.git` directory with no working tree files. No `Dockerfile`, `pom.xml`, `package.json`, CI workflow files, `application.yml`, or any build/deployment artifacts are available. The `.git/packed-refs` file indicates the repository has a `main` branch tracked from `origin`, suggesting it is a real repository rather than a placeholder, but the working tree content was not fetched in the shallow clone.

## Build System

Unknown. Based on the `App` suffix and naming conventions in the Onbe codebase, this could be:
- **Maven/Spring Boot** (consistent with other Java microservices)
- **Node.js/React** (if a web SPA)
- **React Native / Expo** (if a mobile application)
- **Flutter** (if a cross-platform mobile app)

Without `package.json`, `pom.xml`, or a `build.gradle`, the build system cannot be determined.

## CI/CD Pipeline

Unknown. No `.github/workflows/` directory is present in the working tree. If this is a production application following the Onbe Gen-3 CI standard, it would use the `om-ci-setup` shared workflow with Azure Container Registry publication and Azure API Management registration, consistent with `recipient-screening-api`.

## Deployment Model

Unknown. If this follows Gen-3 patterns:
- Containerized (Docker) deployment
- Azure Container Apps or AKS
- Per-environment configuration via Azure App Configuration
- Secrets via Azure Key Vault

## Runtime Details

Unknown. The technology stack cannot be determined without source files.

## Secrets Management

Unknown. Expected to follow the Azure Key Vault pattern established in other Gen-3 services.

## Observability

Unknown. Expected to include Spring Actuator (if Java) or equivalent health/metrics endpoints, with Azure Monitor integration.

## EOL and CVE Concerns

Cannot be assessed without source code or dependency manifest. If this is an actively maintained Gen-3 service, it should follow the same Java 21+/Spring Boot 3.x standards as `recipient-screening-api`. If it is a mobile application, it would have separate dependency vulnerability concerns related to mobile SDKs, device OS compatibility, and third-party libraries.

## Key Operational Risk

The primary operational risk for this repository at the enterprise level is the **absence of a checked-out working tree in the analysis corpus**. If this is a production service handling recipient data:

1. It may not be subject to the same security scanning, dependency review, and compliance assessment being applied to other repositories in this analysis.
2. Any CI/CD pipeline, Dockerfile, or configuration issues are invisible to this analysis.
3. The repository's `.git/shallow` file confirms this is a shallow clone — the full repository history and content may be required to complete the analysis.

**Recommendation**: Re-run the cloning/checkout process for `RecipientApp` with `--depth` sufficient to include the working tree, or perform a full clone. All 5 analysis files should be regenerated once source is available.
