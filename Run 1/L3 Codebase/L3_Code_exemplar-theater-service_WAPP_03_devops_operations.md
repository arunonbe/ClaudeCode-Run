# DevOps / Operations View — exemplar-theater-service_WAPP

## Build System

**Build Tool**: Maven (with Maven Wrapper `mvnw` / `mvnw.cmd`)  
**Java Version**: 11  
**Spring Boot Parent**: 2.5.1  
**Maven Wrapper Version**: See `.mvn/wrapper/maven-wrapper.properties`  
**Maven Settings**: `.mvn/wrapper/settings.xml` (custom settings for Onbe artifact repository)

### Maven Modules (POM hierarchy)

The root `pom.xml` declares 8 modules:
1. `theater-service-service`
2. `theater-service-config`
3. `theater-service-data`
4. `theater-service-db-app`
5. `theater-service-db-scripts`
6. `theater-service-persistence`
7. `theater-service-qa`
8. `theater-service-rest-controller`

### Build Command
```bash
mvn clean install
```

### Key Build Plugins

| Plugin | Version | Purpose |
|--------|---------|---------|
| `maven-compiler-plugin` | 3.8.1 | Java 11 source/target compilation |
| `maven-surefire-plugin` | 2.22.2 | Unit test execution |
| `maven-checkstyle-plugin` | 3.1.2 | Code style enforcement (configured via `checkstyle.xml`) |
| `jacoco-maven-plugin` | 0.8.7 | Code coverage (90% threshold on INSTRUCTION, CLASS, LINE, BRANCH, METHOD) |
| `dependency-check-maven` | 6.2.2 | OWASP CVE dependency scanning |
| `pact-provider maven` | 4.2.6 | Contract test verification and publication to PactFlow |

### JaCoCo Coverage Thresholds (pom.xml lines 342–370)
All five counters must be at or above 90%:
- `INSTRUCTION`: 0.90
- `CLASS`: 0.90
- `LINE`: 0.90
- `BRANCH`: 0.90
- `METHOD`: 0.90

This is an unusually high bar and enforces comprehensive testing on all Gen-3 exemplar code.

### Checkstyle
`checkstyle.xml` at repo root. Applied in the `validate` phase, so style violations fail the build before compilation. `failsOnError: true` (pom.xml line 294).

## CI/CD Pipeline

### GitHub Actions — CodeQL (`.github/workflows/codeql.yml`)

```yaml
name: "CodeQL"
on:
  workflow_dispatch:
  schedule:
    - cron: 24 9 * * 6   # Weekly on Saturdays at 09:24 UTC
jobs:
  analyze:
    uses: Onbe/om-ci-setup/.github/workflows/codeql-auto.yml@main
    secrets: inherit
    with:
      java-runner: "['self-hosted', 'X64', 'Linux', 'ubuntu-docker']"
```

This reusable workflow runs CodeQL static analysis weekly and on manual trigger. It uses:
- Onbe's centralized CI workflow from `om-ci-setup` repository.
- A self-hosted GitHub Actions runner (X64, Linux, ubuntu-docker).

**Note**: There is no push/PR-triggered build pipeline visible in this repository. A complete CI/CD setup would include a build-and-test workflow triggered on pull requests.

### Dependabot (`.github/dependabot.yml`)

Configured for automated dependency updates. Exact configuration not read but standard for GitHub-hosted repos.

### PactFlow Integration (pom.xml lines 397–407)

The `pact-provider:maven` plugin publishes consumer-driven contract tests to `https://northlane.pactflow.io/`. This enables contract verification between the theater service and any consumer services. The `pactBrokerToken` is embedded in the pom.xml — this should be moved to a CI secret.

## Containerization

### Root-Level `docker-compose.yml`

Spins up the full exemplar stack with Dapr sidecars. Includes:
- The theater-service application container.
- Dapr sidecar container.
- Dependencies from `exemplar-database_WAPP`.

### `theater-service-rest-controller/Dockerfile`

Builds the runnable JAR into a Docker image. The `theater-service-rest-controller` module produces a `*-exec.jar` (Spring Boot fat JAR) that is the deployable artifact.

### Dapr Components (`theater-service-dapr-components/`)

| File | Purpose |
|------|---------|
| `config.yaml` | Dapr configuration (tracing etc.) |
| `pubsub-mqtt.yaml` | MQTT pub/sub component definition |
| `subscription.yaml` | Declarative topic subscription |

The pub/sub component `dii-integration` can be backed by MQTT (EMQ X public broker, for development) or Redis. The README notes that the public MQTT broker `broker.emqx.io` is used for testing only.

### Deploy Scripts

| File | Purpose |
|------|---------|
| `deploy/start-all.sh` / `start-all.ps1` | Start service + Dapr on Linux/Windows |
| `deploy/stop-all.sh` / `stop-all.ps1` | Stop service + Dapr |
| `deploy/dapr-config.yaml` | Dapr config for deployment environment |
| `deploy/theater-service.yaml` | Kubernetes manifest for AKS deployment |
| `deploy/zipkin.yaml` | Zipkin tracing deployment manifest |

## Operations

### Application Port
`server.port: 9000` (`application.yml` line 2)

### Health and Monitoring
Actuator endpoints exposed at `/monitoring/*` (all endpoints exposed). `health/show-details: ALWAYS`.

### Tracing
Zipkin integration via Dapr. Zipkin UI accessible at `http://localhost:9411/zipkin`.

### Running Without Docker (development mode)
```bash
dapr run --components-path ./theater-service-dapr-components \
  --app-id theater-service \
  --app-port 9000 \
  -- java -jar theater-service-rest-controller/target/theater-service-rest-controller-0.0.1-SNAPSHOT-exec.jar -p 9000
```

### Version Strategy
Current version: `0.0.1-SNAPSHOT`. No release versioning strategy is documented. For production use, a semantic versioning policy should be applied.
