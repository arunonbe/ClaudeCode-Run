# ai-guidelines — DevOps & Operations View

## Build & Packaging

This repository contains no buildable artifact. There is no `pom.xml`, `build.gradle`, `Makefile`, `Dockerfile`, `package.json`, or any other build descriptor.

The `app-guidelines.md` template file contains Maven Wrapper build commands as a pattern for consuming projects to use:

```bash
./mvnw clean install -s .mvn/wrapper/settings.xml
./mvnw clean install -DskipTests -s .mvn/wrapper/settings.xml
./mvnw test -s .mvn/wrapper/settings.xml
./mvnw verify -s .mvn/wrapper/settings.xml
```

These commands are documentation/guidance for the projects that adopt these guidelines, not commands applicable to this repository itself.

## Deployment

Not applicable. This repository has no deployable artifact, no container image, no Helm chart, no Terraform, and no Kubernetes manifests. It is deployed solely by being copied (or referenced) into other project repositories.

## Configuration Management

No runtime configuration exists in this repository. The guideline documents prescribe the following configuration management practices for consuming projects:

- Use environment variables rather than Spring profiles to differentiate environment-specific configuration.
- Use `@ConfigurationProperties` classes with validation annotations for type-safe, fail-fast configuration binding.
- Prefer configuration properties classes over `@Value` annotations.
- Bind secrets via environment variables or secure configuration management (not hardcoded).
- Use `spring.jpa.open-in-view=false` explicitly.
- Secure all Spring Actuator endpoints except `/health`, `/info`, and `/metrics`.

The `java-spring-testing-standards.md` references `spring.cloud.azure.appconfiguration.enabled=false`, indicating consuming projects may use Azure App Configuration for external config management — but no further detail is provided here.

## Observability

No observability tooling is present in this repository. The guidelines prescribe the following observability standards for consuming projects:

- Use appropriate log levels: TRACE, DEBUG, INFO (default), WARN (bad requests/bad data), ERROR (alerts requiring support), FATAL (application must stop).
- Use parameterized logging.
- Include relevant context in log messages.
- Never log sensitive information.
- Expose Spring Actuator endpoints `/health`, `/info`, and `/metrics` without authentication.
- All other Actuator endpoints must be secured.

No specific APM tool, distributed tracing framework, or metrics platform is referenced.

## Infrastructure Dependencies

This repository has no runtime infrastructure dependencies. The testing standards reference two infrastructure patterns for consuming projects:

- H2 in-memory database for unit tests (profile: `test`).
- SQL Server via Testcontainers for integration tests (profile: `integration-test`), indicating that consuming projects target SQL Server as their production RDBMS.
- Implicit Azure dependency: the Testcontainers initializer class reference `TestcontainersInitializer` and the `spring.cloud.azure.appconfiguration.enabled=false` flag suggest consuming projects use Azure App Configuration.

## Operational Risks

- **No CI/CD pipeline in this repository:** There is no `.github/workflows/`, `Jenkinsfile`, `azure-pipelines.yml`, or equivalent. Updates to guidelines are not validated automatically.
- **No automated distribution mechanism:** Teams consume guidelines by manual copy. There is no package registry, Git submodule, or dependency mechanism to push updates to consuming projects.
- **Template left incomplete:** `app-guidelines.md` contains placeholder text that will produce misleading AI agent context if not replaced before use.
- **No health check or validation step:** No tooling exists to confirm that teams have correctly wired their agent entrypoint files to the `.ai/` guideline files.

## CI/CD

No CI/CD pipeline is configured in this repository. The `.github/` directory contains only `copilot-instructions.md` (an AI agent instruction file); there are no GitHub Actions workflow files. No pipeline definition of any kind was found.
