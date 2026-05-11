# DevOps / Operations — webapp-common_LIB

## Build System
- **Tool**: Apache Maven 3.x via Maven Wrapper (`mvnw` / `mvnw.cmd`)
- **Parent POM**: `com.citi.prepaid.web:webapp-parent:6` (external / Onbe-internal parent)
- **Group ID**: `com.citi.prepaid.web.common` — legacy Citi namespace, not yet migrated to `com.onbe`
- **Artefact ID**: `webapp-common`, version `1.0.1`
- **Packaging**: `jar`
- **Java version**: Not explicitly declared in this POM; inherited from `webapp-parent:6`. Based on `javax.servlet` usage, likely targets Java 8 or earlier.
- **Test dependency**: `junit:junit:3.8.1` (scope: test) — extremely outdated.

## CI/CD Pipeline
- **Platform**: GitHub Actions
- **CodeQL Scan**: `.github/workflows/codeql.yml` — scheduled weekly (Wednesday 19:40 UTC, cron `40 19 * * 3`) and `workflow_dispatch`.
- **CodeQL runner**: self-hosted `['self-hosted', 'X64', 'Linux', 'ubuntu-docker']` via `Onbe/om-ci-setup/.github/workflows/codeql-auto.yml@main`.
- **No build pipeline**: No `build.yml` or publish workflow detected. Only CodeQL SAST scanning is automated.
- **Dependabot**: `.github/dependabot.yml` present — configuration not read, but likely enables automated dependency PRs.

## Configuration Management
- No `application.properties`, no Spring profiles, no external config server.
- Filter behaviour is configured entirely through `web.xml` `<init-param>` declarations in the consuming application — no self-contained configuration in this library.

## Observability
- Uses Apache Commons Logging (`org.apache.commons.logging.Log`) for DEBUG-level redirect URL logging.
- No metrics, no tracing, no structured logging.

## Infrastructure Dependencies
- Maven Wrapper + internal Maven repository (`webapp-parent` POM must be resolvable)
- GitHub Actions self-hosted runner (for CodeQL)
- No runtime infrastructure dependencies (library, not a service)

## Operational Risks
1. **No build/publish pipeline**: There is no automated workflow to build, test, or publish a new version of this library. Changes require a manual `mvn install` / `mvn deploy` by a developer.
2. **`junit 3.8.1`** is so old it predates JUnit 4; this prevents use of `@Test` annotations and modern testing patterns. The existing test `AppTest.java` appears to be a Maven archetype placeholder with no real tests.
3. **CodeQL is the only automated security gate**: Without a build pipeline, there is no automated check that the library compiles, passes tests, or produces a valid JAR before changes are merged.
4. **No version lifecycle management**: Version `1.0.1` with no release history visible in the repository. It is unclear which consuming applications depend on this exact version.
5. **`webapp-parent:6` availability**: If the internal parent POM becomes unavailable (Nexus outage, decommission), this library cannot be rebuilt.
