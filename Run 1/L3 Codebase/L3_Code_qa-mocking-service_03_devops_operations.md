# DevOps / Operations View — qa-mocking-service

## Build System

There is no build system in this repository. It contains no source code to compile. The only build artifact is the WireMock Docker image pulled from Docker Hub (`wiremock/wiremock:latest`). The repository itself is purely a configuration-as-code artifact: JSON mapping files and a single `docker-compose.yml`.

## CI/CD Pipeline

No GitHub Actions workflows are present in this repository. There is no automated pipeline for linting, contract validation, or image publishing. The `.git` metadata confirms the repository is on the `main` branch but no CI configuration directory (`.github/workflows/`) was found. This means:
- Mapping files are never automatically validated for JSON syntax before merge.
- No container scanning is applied to the WireMock base image.
- No automated tests confirm that stub responses match current Fiserv API contracts.

## Deployment Model

Deployment is entirely local via Docker Compose. Developers run `docker-compose up` to start the service. The service listens on:
- Host port `8082` → container port `8080` (WireMock HTTP)

The mapping directory is volume-mounted from the host, meaning stub updates take effect on WireMock hot-reload without container restart (WireMock supports this natively). There is no Kubernetes manifest, Helm chart, Azure Container App configuration, or other cloud-deployment artifact.

## Runtime Details

- **WireMock image**: `wiremock/wiremock:latest` (version uncontrolled)
- **JVM**: embedded within the WireMock container (Liberica or OpenJDK depending on WireMock image tag)
- **WireMock flags**: `--verbose`, `--global-response-templating`
- **No Spring Boot, no application framework, no Java source**

## Secrets Management

No secrets are used or managed in this service. All stub responses are static JSON with no authentication, API keys, or credentials. The service does not authenticate incoming requests.

## Observability

Observability is limited to WireMock's verbose stdout logging. The `--verbose` flag causes WireMock to print full request and response details to container stdout. There is no structured logging, no metrics export (Prometheus, Azure Monitor), no distributed tracing, and no alerting integration. For a test-only tool this is acceptable, but verbose logging must be reviewed if real data values are ever introduced.

## EOL Runtimes and CVE Concerns

The critical risk is the use of `wiremock/wiremock:latest` without a pinned version tag. This creates two opposing risks:
1. An uncontrolled upgrade to a new WireMock major version could silently break stub behavior.
2. Running on an older cached image (if `latest` is not regularly pulled) could mean running a version with known CVEs in its embedded JVM or WireMock dependencies.

Remediation: pin to a specific WireMock version tag (e.g., `wiremock/wiremock:3.x.y`) and integrate Trivy or Grype container scanning in a GitHub Actions workflow triggered on pull requests that modify the docker-compose.yml or mapping files.

## Operational Risks

- No health check is defined in docker-compose.yml; the service cannot signal readiness to dependent test tooling.
- No resource limits (CPU, memory) are defined, creating a risk of resource contention if run alongside other dev services.
- The service is entirely undocumented beyond a brief README; onboarding new QA engineers requires tribal knowledge of Fiserv API semantics.
