# DevOps & Operations Report — onbe-spring-boot-parent_PARENT

## Build System

- **Build tool:** Apache Maven with Maven Wrapper (`mvnw` / `mvnw.cmd`), Maven ≥ 3.9.0 enforced
- **Artifact type:** POM-only (`<packaging>pom</packaging>`) — no compiled output
- **Java version:** 21 (enforced by `maven-enforcer-plugin`)
- **Kotlin version:** 2.1.10, language version 2.0
- **Spring Boot parent:** `spring-boot-starter-parent:3.4.3`
- **Current version:** `0.0.22-SNAPSHOT`

## CI/CD Pipeline

- **Platform:** GitHub Actions
- **Workflow:** `.github/workflows/github-package-publish.yml`
- **Trigger:** `workflow_dispatch` (manual) — the POM publish workflow requires manual initiation, appropriate for a foundational library where unintended releases would have broad impact
- **Reusable workflow:** Delegates to `Onbe/om-ci-setup/.github/workflows/java-package-publish.yml@main` (note: this references `@main`, unlike the `onbe-spring-boot` module which references a feature branch)
- **Dependabot:** Configured in `.github/dependabot.yml` for automated PR generation on dependency updates
- **Artifact publication:** GitHub Packages (Maven registry)

## Deployment Model

This is a pure BOM/parent POM with no deployable artifact. "Deployment" consists solely of publishing the POM artifact to GitHub Packages, where it is consumed as a Maven parent by all Onbe Gen-3 services. The publication is triggered manually to ensure deliberate release governance.

The README documents a Spring versions mapping table:

| This version | Spring Boot | Spring Framework |
|---|---|---|
| 0.0.22-SNAPSHOT | 3.4.3 | 6.2.3 |
| 0.0.21 | 3.4.2 | 6.2.2 |
| 0.0.20 | 3.4.1 | 6.2.1 |
| 0.0.19 | 3.4.0 | 6.2.0 |

Note: Version 0.0.18 is marked "DO NOT USE - Doesn't work. Upgrades to Spring Boot 3.4.0 incorrectly." This indicates a historical incident where a parent POM update caused downstream build breakage — underscoring the high risk of changes to this artifact.

## Runtime Environment

As a POM artifact, there is no runtime environment. The POM governs the runtime environments of consuming services:
- JVM: Java 21 (LTS)
- Azure Functions: Java 21 Linux runtime (via `spring-cloud-azure-function` profile)
- Container base images: Buildpacks-based (Spring Boot build-image plugin), with Datadog agent support toggleable via `BP_DATADOG_ENABLED` environment variable
- Image pull policy: `ALWAYS` — ensures fresh base images on every container build

## Secrets Management

No runtime secrets. Build-time secrets:
- GitHub Packages credentials injected via `settings.xml` in `.mvn/wrapper/settings.xml`, populated by GitHub Actions `secrets: inherit`
- GitHub token used for OpenAPI schema download from `raw.githubusercontent.com` (via `maven-antrun-plugin` when `openapi.schema.download.skip=false`)
- The QueryDSL JDBC URL template (line 721 of `pom.xml`) contains a placeholder password — this must not be replaced with a real credential in version-controlled files

## Observability

No runtime observability — this is a build artifact. Observability for consuming services is governed by the dependency choices in this POM:
- Micrometer (via Spring Boot BOM) for metrics
- OpenTelemetry 2.13.1-alpha instrumentation for distributed tracing
- Spring Boot Actuator for health/metrics endpoints
- Logstash-formatted structured logging (configured in `onbe-spring-boot` framework layer)

## Plugin Inventory and EOL / Risk Assessment

| Plugin | Version | Risk |
|---|---|---|
| spring-boot-maven-plugin | 3.4.3 | Current — low risk |
| cyclonedx-maven-plugin | 2.9.1 | Current — low risk |
| openapi-generator-maven-plugin | 7.11.0 | Current — low risk |
| maven-compiler-plugin | 3.13.0 | Current — low risk |
| maven-surefire-plugin | 3.5.2 | Current — low risk |
| maven-enforcer-plugin | 3.5.0 | Current — low risk |
| azure-functions-maven-plugin | 1.37.0 | Check for Azure Functions v4 compatibility |
| docker-maven-plugin (Fabric8) | 0.45.1 | Check latest release |
| swagger-codegen-maven-plugin | 3.0.58 | Managed but not primary; openapi-generator is primary |
| avro-maven-plugin | 1.12.0 | Current Avro stable |
| lmax-disruptor | 3.4.4 | Intentional hold (Log4j2 4.x not yet supported); track for upgrade |
| spring-boot-thin-layout | 1.0.31.RELEASE | Spring experimental — limited support lifecycle |

## EOL Risk Assessment

- Java 21 (LTS): Actively supported through 2029 — no risk
- Spring Boot 3.4.x: Current commercial support — no risk
- Spring Cloud Azure 5.20.0: Current — no risk
- `spring-boot-thin-layout:1.0.31.RELEASE`: The `org.springframework.boot.experimental` group ID indicates this is not a commercially supported Spring artifact. Dependency on this in the Azure Functions profile carries long-term supportability risk
- `opentelemetry-instrumentation:2.13.1-alpha`: Alpha status carries stability risk — not recommended for production critical path without internal validation testing
