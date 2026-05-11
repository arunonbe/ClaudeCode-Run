# DevOps / Operations Report — wirecard_issuing-boot-actuator-utils_LIB

## Build System

**Maven 3.x** via Maven Wrapper. Parent POM: `com.parents:prepaid-parent:6.0.12`. Produces a JAR artifact (`issuing-boot-actuator-utils-2.0.0.jar`). Compiler target: Java 21.

## CI/CD Pipeline

**GitHub Actions** with three workflow files:

1. **`github-package-publish.yml`**: Publishes the JAR to GitHub Packages (`https://maven.pkg.github.com/onbe/onbe_maven_releases`). Uses `PAT_TOKEN` secret. This is the standard Onbe Gen-3 artifact publication pattern.

2. **`codeql.yml`**: GitHub CodeQL static analysis for Java — provides SAST coverage for security vulnerability detection.

3. **`dependabot.yml`**: Dependabot configuration for automated dependency update PRs.

No GitLab CI configuration is present, confirming this repository has been migrated to GitHub Actions.

## Deployment Model

Library JAR consumed as a Maven dependency by Wirecard issuing microservices. Published to GitHub Packages. Not independently deployable.

## Runtime

- **Java 21** (LTS — supported until September 2029).
- **Spring Boot Actuator** (version inherited from `prepaid-parent:6.0.12` BOM — the exact Spring Boot version needs to be confirmed from the parent POM).
- **Spring Web MVC** and **Spring Core** — also version-governed by the parent BOM.
- **Jackson Databind** — for JSON serialization.

The runtime environment of the library is determined by the consuming service, not by this library itself.

## Secrets Management

No secrets in this repository. The `PAT_TOKEN` GitHub secret is the only secret referenced, and it is correctly injected via GitHub Actions encrypted secrets.

## Observability

The library itself produces no logs, metrics, or traces. Its output is the modified health endpoint JSON that consuming services' monitoring systems parse. The `cached_ts` field in the serializer output is the only time-based observability data produced.

## EOL Runtimes / CVEs

- **Java 21**: Current LTS — no EOL concern.
- **Spring Boot Actuator**: Version is governed by `prepaid-parent:6.0.12`. If this parent pins an older Spring Boot version (e.g., 2.5.x which reached EOL in May 2023), the actuator library itself would inherit CVEs. The parent POM should be audited.
- **Jackson Databind**: Must be at a patched version. Jackson-databind has had multiple CVEs including deserialization vulnerabilities. Verify the version pinned by `prepaid-parent`.
- **JUnit (test scope)**: Test scope only; no runtime impact.

## Operational Notes

- Library version is `2.0.0` (release, not snapshot) — appropriate for a shared library.
- The `maven-wrapper.properties` file pins the Maven version used by the wrapper; this should be a recent Maven 3.8.x+ to ensure TLS 1.2+ enforcement for remote repository connections.
- Only two Java source files exist: `CustomHealthAggregator.java` and `CustomHealthSerializer.java`. The library is small and targeted.
