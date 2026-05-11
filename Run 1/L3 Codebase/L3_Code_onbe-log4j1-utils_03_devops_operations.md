# DevOps / Operations — onbe-log4j1-utils

## Build System
- Maven, Java 8 target (`maven.compiler.source/target = 8`).
- Single Maven profile is implicit (no explicit profile declared); the pom.xml uses a fixed version `1.0.3-java8`.
- Build wrapper: `mvnw` / `mvnw.cmd` present.
- Maven settings file: `.mvn/wrapper/settings.xml` (contains repository configuration for GitHub Packages).

## CI/CD Pipeline
- GitHub Actions workflow: `.github/workflows/github-package-publish.yml`.
- Triggers: `workflow_dispatch` and PRs to `main`.
- Delegates to Onbe shared workflow: `Onbe/om-ci-setup/.github/workflows/java-package-publish.yml@feature/spring-boot-build-image`.
- Parameters: `UPDATE_DEPENDENCIES: false`, `CODEQL_QUALITY: true`, Maven args include `-P github -s ./.mvn/wrapper/settings.xml`.
- CodeQL security scanning is enabled on every build.
- No separate deployment stage; artifact is published to GitHub Packages.

## Artifact Publishing
- Group: `com.onbe.logging`, artifact: `onbe-log4j1-utils`, version: `1.0.3-java8`.
- Published to GitHub Packages registry (`https://npm.pkg.github.com` is npm; Maven equivalent registry URL is in the shared workflow).

## Config Management
- No runtime configuration. The library is purely compile-time.
- Consumer configuration is via `log4j.xml`: replace appender class names with `com.onbe.logging.SanitizingXXX`.

## Observability
- No operational metrics, health checks, or tracing hooks. It is a library, not a service.

## Infrastructure Dependencies
- None at runtime. Build-time: Maven, Java 8 JDK, GitHub Actions runner, access to `Onbe/om-ci-setup` shared workflows.

## Operational Risks
1. **Shared workflow pinned to a feature branch** (`@feature/spring-boot-build-image`) rather than a tagged release. This means pipeline behavior can change without a version bump in this repo.
2. **No integration test against a real appender I/O path** in CI; unit tests only cover the `LogUtils` logic.
3. **No release branch or tag strategy visible**: versioning is hardcoded in pom.xml rather than driven by CI variables.
