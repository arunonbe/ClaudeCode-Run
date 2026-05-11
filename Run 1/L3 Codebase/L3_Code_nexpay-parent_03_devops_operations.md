# DevOps / Operations View — nexpay-parent

## Build System Role

The nexpay-parent is the Maven build governance layer for the NexPay Gen-3 platform. It is a POM-only artifact (no source code, no deployable JAR) that is published to GitHub Packages and consumed as the `<parent>` in every NexPay service's POM.

## Publishing and Release Process

### Distribution Management

```xml
<distributionManagement>
    <repository>
        <id>github-releases</id>
        <url>https://maven.pkg.github.com/onbe/onbe_maven_releases</url>
    </repository>
    <snapshotRepository>
        <id>github-snapshots</id>
        <url>https://maven.pkg.github.com/onbe/onbe_maven_releases</url>
    </snapshotRepository>
</distributionManagement>
```

Both releases and snapshots are published to GitHub Packages. This is a suitable choice for a private enterprise Maven registry. Access requires a GitHub personal access token or Actions token with `read:packages` scope.

### SNAPSHOT Risk

The current version `0.2.8-SNAPSHOT` means every `mvn install` or CI build that resolves this parent will pull whatever the latest snapshot is from the registry at build time. This creates **non-reproducible builds** — two CI runs at different times may get different dependency resolutions. For a PCI DSS Level 1 platform, non-reproducible builds are a compliance risk because the exact set of libraries in a production artifact cannot be guaranteed.

**Recommendation**: Release the parent POM to a stable version (e.g., `0.2.8`) before certifying NexPay services for production. Use `mvn versions:set -DnewVersion=0.2.8` and publish, then update child services to reference `0.2.8`.

## Version Enforcement

### maven-enforcer-plugin

```xml
<requireMavenVersion>
    <version>[4.0.0-rc-5,)</version>
</requireMavenVersion>
<requireJavaVersion>
    <version>[25,)</version>
</requireJavaVersion>
```

This enforces minimum build toolchain versions. CI/CD pipelines must install Maven 4.0.0-rc-5+ and JDK 25+. The Maven 4.x requirement is notable — Maven 4 introduced the new POM Model 4.1 (used here, `xmlns="http://maven.apache.org/POM/4.1.0"`) with improved multi-module support.

### Versions Plugin Configuration

```xml
<ignoredVersions>.*\.Dev.*,.*\.alpha.*,.*\.Alpha.*,.*\.Beta.*,.*\.RC.*,-M.*,.*-alpha.*,.*-beta.*,.*-rc.*,.*-RC.*,.*-jre.*,.*-preview.*</ignoredVersions>
```

The versions plugin is configured to ignore pre-release versions when suggesting upgrades. This prevents `versions:use-latest-releases` from pulling in alpha or release candidate dependencies, which is appropriate for a production payments platform.

## Testing Configuration

### Surefire (Unit Tests)

```xml
<includes> **/*Test.java, **/*Tests.java </includes>
<excludes> **/*IT.java, **/*ITCase.java, **/*IntegrationTest*.java </excludes>
<useModulePath>false</useModulePath>
```

Unit tests run with `mvn test`. The `useModulePath: false` setting is required for Java 25 module-path compatibility with Mockito and other test libraries that have not fully migrated to the module system.

### Failsafe (Integration Tests)

```xml
<includes> **/*IT.java, **/*ITCase.java, **/*IntegrationTest*.java </includes>
```

Integration tests run in the `integration-test` and `verify` phases. This allows `mvn test` in CI to skip potentially slow Testcontainers-based tests, with `mvn verify` running the full test suite.

## Code Coverage

### JaCoCo Configuration

Three JaCoCo executions are configured:
1. `prepare-agent` — instruments bytecode at test compilation time
2. `report` — generates per-module HTML/XML reports after unit tests
3. `report-aggregate` — generates a combined report across all submodules in the `test` phase

The aggregate report is used in CI to measure overall platform coverage. No coverage thresholds are configured in the parent POM — individual services may configure their own thresholds.

## Dependency Vulnerability Management

### Dependabot

Each NexPay service repository should have Dependabot configured (visible in service repos). The parent POM should be included in Dependabot scans to receive automated PRs for Spring Boot, Spring Cloud Azure, and other dependency updates.

### Transitive Dependency Risk

All NexPay services inherit transitive dependencies through the parent's `spring-boot-starter-parent` chain. A vulnerability in a Spring Boot managed dependency (e.g., Log4j, Spring Framework) requires:
1. Spring Boot to release an updated `spring-boot-starter-parent`.
2. `nexpay-parent` to update its Spring Boot version.
3. All child services to update their parent POM reference and redeploy.

This three-step propagation chain means a zero-day response could take hours to days depending on Spring Boot's release cadence.

## Build Plugin Inventory

| Plugin | Version | Purpose |
|---|---|---|
| `maven-compiler-plugin` | Spring Boot managed | Java 25, annotation processing |
| `maven-surefire-plugin` | Spring Boot managed | Unit test runner |
| `maven-failsafe-plugin` | Spring Boot managed | Integration test runner |
| `maven-enforcer-plugin` | Spring Boot managed | Toolchain version enforcement |
| `jacoco-maven-plugin` | Spring Boot managed | Code coverage |
| `versions-maven-plugin` | Spring Boot managed | Dependency version management |
| `openapi-generator-maven-plugin` | 7.21.0 | OpenAPI code generation |
| `merge-yaml-plugin` | 1.4 | YAML spec merging |

## Operational Considerations for Platform Engineers

### Upgrading the Parent POM

1. Update version in `nexpay-parent/pom.xml`.
2. Test locally against one consumer service (`mvn install` in parent, then `mvn verify` in consumer).
3. Publish SNAPSHOT to GitHub Packages.
4. Update all consumer services' parent references.
5. Run full CI pipeline on all services.
6. Publish as a stable release once all services pass.

### Responding to a CVE

When a CVE is discovered in a managed dependency:
1. Identify the fix version.
2. Update the dependency version in `nexpay-parent/pom.xml`.
3. If the fix requires a Spring Boot version bump, update `spring-boot-starter-parent` version.
4. Follow the upgrade procedure above.
5. Document the CVE remediation in the release notes.

All of this must happen within the PCI DSS patching timeline (critical: 1 month, high: 3 months for Req 6.3.3).
