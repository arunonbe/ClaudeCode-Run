# DevOps / Operations View — qa-test-automation

## Build System

Maven (Maven Wrapper 3.x) with GMavenPlus for Groovy compilation. The `pom.xml` defines:
- Groovy 4.0.20 (Apache Groovy)
- Spock Framework 2.3-groovy-4.0
- Spring Test 6.1.5
- Maven Surefire 3.2.5 (test runner)
- GMavenPlus 3.0.2 (Groovy compiler)

The project is `packaging: jar` but deploy is explicitly skipped (`maven-deploy-plugin` with `<skip>true</skip>`), confirming it is a test-only artifact not published to an artifact registry.

## CI/CD Pipeline

GitHub Actions pipeline defined in `.github/workflows/deploy_docker.yml`:
- **Triggers**: Push to any branch (excluding CI/wrapper files), pull requests to `main`, manual dispatch
- **Steps**:
  1. Checkout source repository
  2. Checkout `Onbe/om-ci-setup` (shared CI setup repository) as a sub-path
  3. Docker login to Azure Container Registry (credentials in GitHub Secrets: `REGISTRY_PASSWORD`, `REGISTRY_USERNAME`, `REGISTRY_LOGIN_SERVER`)
  4. Build and push Docker image via the composite action `om-ci-setup/composite-actions/build/docker-build` with `PROJECT_TYPE: JAVA` and `CONTAINER_SCAN: 'true'`

Container scanning is enabled (`CONTAINER_SCAN: 'true'`), which is a positive security control. The shared CI action handles the actual Trivy/scan tooling.

## Deployment Model

The test suite is packaged as a Docker image and pushed to the Azure Container Registry. At runtime, the container executes Maven tests against a specified QA environment:

```
CMD ["/bin/sh", "-c", "chmod +x mvnw && ./mvnw clean test \
  -Dtest=simulator.xmlrpc.${APPLICATION_NAME} \
  -s .mvn/wrapper/settings.xml \
  -Dapplication_url=${APPLICATION_URL} \
  -Denvironment=${ENVIRONMENT}"]
```

Runtime parameters are injected via environment variables:
- `APPLICATION_NAME` — the Spock spec class to run (e.g., `CryptoSvcSpec`)
- `APPLICATION_URL` — the base URL of the service under test
- `ENVIRONMENT` — environment label (currently only `qa` is configured)

## Runtime Details

- **Base image**: `bellsoft/liberica-openjdk-alpine:21` — Liberica JDK 21 on Alpine Linux
- **Java version**: 21 (LTS, supported through September 2029)
- **No Spring Boot runtime**: This is a pure test JAR; Spring context is loaded only within test execution scope
- **Maven settings**: `.mvn/wrapper/settings.xml` — points to Onbe's internal artifact repository (credentials managed via GitHub Secrets via `PAT_TOKEN_PACKAGE`)

Liberica JDK 21 on Alpine is a well-supported, actively maintained runtime. Java 21 is LTS; no EOL concern at this time. The `pom.xml` does not explicitly set Java version (no `maven.compiler.source/target` properties), which means it inherits from the eCount `prepaid-parent` BOM. This is a transparency gap.

## Secrets Management

Secrets referenced in the pipeline:
- `PAT_TOKEN_PACKAGE` — GitHub Personal Access Token for reading packages from Onbe's internal GitHub Package Registry (Maven dependencies)
- `PAT_TOKEN` — GitHub PAT for checking out the `om-ci-setup` repository
- `REGISTRY_PASSWORD`, `REGISTRY_USERNAME`, `REGISTRY_LOGIN_SERVER` — Azure Container Registry credentials

All secrets are stored in GitHub Actions secrets and injected as environment variables at pipeline runtime. No secrets are committed to the repository. The `Environments.groovy` file contains test system identifiers (not credentials), which is appropriate.

## Observability

No runtime observability is configured. The test suite produces:
- Maven Surefire XML and text reports (JUnit-compatible)
- JUnit5 XML 3.0 stateless reports (configured in Surefire)
- Console stdout from Spock and Spring

There is no Prometheus endpoint, no log aggregation, no distributed tracing. For a test execution container this is appropriate.

## EOL and CVE Concerns

- **SNAPSHOT dependencies**: All eCount platform dependencies use `-SNAPSHOT` versions, meaning builds are non-deterministic and may pull in incompatible changes. This is a significant stability risk for a CI pipeline.
- **Commons-lang (implied via eCount dependencies)**: eCount libraries pull in older commons-lang versions which may have known CVEs. Container scan coverage helps but dependency-level scanning (OWASP Dependency Check) is not visibly configured.
- **Spring Test 6.1.5**: Current and supported at time of analysis; no immediate CVE concern.
- **Byte Buddy 1.14.12**: Current at time of analysis.
