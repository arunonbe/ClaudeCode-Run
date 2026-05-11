# DevOps / Operations View — request-context_LIB

## Build System

Maven with Maven Wrapper (`mvnw`). Parent BOM: `com.parents:prepaid-parent:6.0.13`. The library itself is a simple JAR with minimal dependencies — essentially only the parent BOM, Lombok (via parent), and SLF4J (via parent). There is no Spring Boot dependency; this is a plain Java library.

Build configuration:
- `groupId: com.citi.prepaid.module`
- `artifactId: request-context`
- `version: 2.1.0`
- `maven.compiler.source/target: 21` (Java 21, LTS — appropriate)

The only build plugin is `maven-jar-plugin`, which packages the compiled classes. No test plugin configuration is visible beyond what the parent BOM provides.

## CI/CD Pipeline

GitHub Actions workflows are present:

**`.github/workflows/github-package-publish.yml`**: Publishes the JAR to the GitHub Package Registry (Onbe's internal Maven repository) on push to `main` or on workflow dispatch. The pipeline uses `PAT_TOKEN_PACKAGE` for authentication to the package registry.

**`.github/workflows/codeql.yml`**: CodeQL static analysis for Java security scanning. Triggers on push to `main` and pull requests targeting `main`. This provides SAST coverage for the library.

**`.github/dependabot.yml`**: Dependabot configuration for automated dependency update PRs.

The CI/CD configuration is appropriately minimal for a shared library: publish on merge to main, scan with CodeQL, automate dependency updates. There is no container build (JAR-only artifact) and no deployment step.

## Deployment Model

Published as a JAR to the GitHub Package Registry. Consumed by downstream services as a Maven dependency. Version `2.1.0` is a fixed release version (not SNAPSHOT), which is appropriate for a shared library — consuming services pin to a specific version and upgrade deliberately.

The library is not deployed independently; it is embedded within the JVM processes of consuming services (Gen-1 eCount services, potentially Gen-2 Spring Boot services that bridge the two platforms).

## Runtime Details

- **Java target**: 21 (LTS, supported through September 2029)
- **Framework**: No framework dependency — pure Java library with SLF4J and Lombok
- **Lombok**: Used for `@Slf4j` annotation in `ThreadLocalRequestContextHolder` and `HistoryRequestContextHolder`. The Lombok version is inherited from `prepaid-parent:6.0.13`.
- **No Spring dependency**: The library is framework-agnostic at the API level; the ThreadLocal mechanism works in any Java environment.

## Secrets Management

No secrets are required or managed by this library. The GitHub Actions pipeline uses `PAT_TOKEN_PACKAGE` (GitHub PAT) for publishing to the package registry, stored as a GitHub Actions secret.

## Observability

The library contributes to observability through:
- **SLF4J debug logging**: `ThreadLocalRequestContextHolder` logs context bind/unbind operations at DEBUG level, including `agent`, `programId`, `globalRequestID`, and `sasiContext` values. This provides per-thread context traceability when DEBUG logging is enabled.
- **`globalRequestID` propagation**: The UUID-based request ID is the primary observability contribution — it enables correlation of log entries across multiple services in a single request chain.

The library does not export metrics, traces (OpenTelemetry), or health endpoints — it is a utility library, not a service.

## EOL and CVE Concerns

- **Java 21**: LTS, actively maintained — no EOL concern.
- **Lombok**: Version determined by `prepaid-parent:6.0.13`. Lombok is not security-sensitive (compile-time annotation processor only).
- **SLF4J**: Version determined by parent BOM. SLF4J 1.x has known API-stability issues with newer logging frameworks; if the parent BOM pins SLF4J 1.x and consuming services use Logback 1.3+, there may be compatibility issues.
- **`java.util.Stack`**: Deprecated in modern Java in favor of `ArrayDeque`. This is a code quality issue rather than a security vulnerability, but `Stack` is synchronized (slower) and has known behavioral quirks. Migrating to `ArrayDeque` is recommended during any refactoring.
- **No `InheritableThreadLocal`**: The `ThreadLocal` implementation does not support thread inheritance. This is a design gap for async/parallel processing environments rather than a CVE, but it creates silent context loss in thread-pooled environments, which constitutes a reliability risk.
