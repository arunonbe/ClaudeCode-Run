# DevOps / Operations — onbe-log4j-utils

## Build System
- Maven with multi-profile build: `java8` (Java 8, version `1.0.3-java8`) and `java21` (Java 21, version `1.0.3-java21`).
- Version is CI-variable driven via `${revision}` property, resolved by profile activation.
- Build wrapper: `mvnw` / `mvnw.cmd`.
- Maven settings: `.mvn/wrapper/settings.xml`.

## CI/CD Pipeline
- GitHub Actions: `.github/workflows/github-package-publish.yml`.
- Triggers: push to `main` and PRs targeting `main`.
- Two parallel jobs: `build-java8` and `build-java21` (java21 depends on java8 completing first via `needs`).
- Both jobs use shared workflow `Onbe/om-ci-setup/.github/workflows/java-package-publish.yml@feature/spring-boot-build-image`.
- CodeQL quality scanning enabled on both jobs.
- Artifacts published to GitHub Packages.

## Artifact Publishing
- Group: `com.onbe.logging`, artifact: `onbe-log4j-utils`, versions `1.0.3-java8` and `1.0.3-java21`.
- Classifier feature is defined in pom.xml but currently commented out.

## Config Management
- No runtime configuration.
- Consumer opt-in via Log4j 2 XML: add `<SanitizingFilter/>` to appender `<filters>` block, or include the shipped `onbe-common-log4j2-spring.xml`.

## Observability
- None (library). Logging framework itself is the observability tool.

## Infrastructure Dependencies
- Build-time only: Java 8/21 JDK, Maven, GitHub Actions, access to `Onbe/om-ci-setup`.

## Operational Risks
1. **Shared workflow on feature branch** (`@feature/spring-boot-build-image`) — same concern as onbe-log4j1-utils.
2. **Sequential dual-build adds pipeline latency**: java21 waits on java8 unnecessarily for independent artifacts.
3. **No smoke test for Spring Boot integration**: the `onbe-common-log4j2-spring.xml` config is not covered by any automated test in this repo.
4. **`MutableLogEvent` cast risk in production**: if Log4j 2 delivers an immutable event object (async appender path), a `ClassCastException` will be thrown and potentially swallowed, silently breaking logging.
