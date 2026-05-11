# DevOps & Operations View — strict-null-checks_DEMO

## Build
- Build tool: Apache Maven (wrapper `mvnw` / `mvnw.cmd` present).
- Java target: 17 (`maven.compiler.source=17`, `maven.compiler.target=17`).
- Key compile-time plugin: `se.eris:notnull-instrumenter-maven-plugin:1.1.1` — instruments bytecode with `@NonNull` / `@Nullable` runtime assertions.
- Annotation processor: `org.projectlombok:lombok:1.18.32` (declared as annotation processor path).
- Packaging: plain JAR (no `<packaging>` override; defaults to `jar`).
- No tests are present; build produces only compiled classes.

## Deployment
Not deployable. This is a demonstration project only. No WAR, Docker image, or deployment descriptor exists.

## Configuration Management
- `.editorconfig` is present, enforcing consistent editor settings.
- `.vscode/settings.json` present (VSCode workspace configuration).
- Maven wrapper settings: `.mvn/wrapper/maven-wrapper.properties` and `.mvn/wrapper/settings.xml`.

## Observability
None. No logging framework, no metrics, no tracing.

## Infrastructure Dependencies
None at runtime. Build-time only: Maven, JDK 17.

## Operational Risks
- The `notnull-instrumenter-maven-plugin` notes Java 17 as its maximum supported version. Any JDK upgrade beyond 17 will silently break runtime null instrumentation with no build error.
- No CI/CD pipeline files (no `.github/workflows/`) are present in this repository.

## CI/CD
No GitHub Actions workflows found. No automated pipeline is configured for this repository.
