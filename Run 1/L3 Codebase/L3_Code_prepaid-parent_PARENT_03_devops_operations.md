# prepaid-parent_PARENT — DevOps and Operations View

## 1. Build Artifact Identity

| Attribute | Value |
|---|---|
| GroupId | `com.parents` |
| ArtifactId | `prepaid-parent` |
| Version | `6.0.13` |
| Packaging | `pom` |
| Purpose | Maven parent POM — not a deployable artifact |

## 2. CI/CD Configuration

Three GitHub Actions workflow files are present:

### 2.1 `github-package-publish.yml`
Publishes the parent POM to GitHub Packages (GitHub Maven registry). This is the distribution mechanism — child projects reference this POM from the GitHub Package registry.

### 2.2 `codeql.yml`
CodeQL static analysis scanning on the parent POM itself. Since the parent POM contains no Java source code, CodeQL scans the POM XML for dependency-related security signals.

### 2.3 `dependabot.yml`
Automated dependency update PRs via GitHub Dependabot. Given the large number of `<properties>` version entries, Dependabot will raise PRs to update individual dependency versions. **This is a critical operational process** — each Dependabot PR must be reviewed to assess:
- Breaking API changes in major version bumps
- Platform-wide impact on all child services
- PCI DSS implications of version changes

## 3. Maven Plugin Management

The POM manages versions for all standard Maven plugins via `<pluginManagement>`:

| Plugin | Version | Purpose |
|---|---|---|
| `maven-compiler-plugin` | 3.13.0 | Java compilation (source/target 21) |
| `maven-install-plugin` | 3.1.1 | Local repository installation |
| `maven-source-plugin` | 3.3.0 | Source JAR generation |
| `maven-release-plugin` | 3.0.1 | Release management (tag, version bump) |
| `maven-jar-plugin` | 3.3.0 | JAR packaging |
| `maven-war-plugin` | 3.4.0 | WAR packaging |
| `maven-site-plugin` | 3.12.1 | Site documentation generation (skipped by default) |
| `maven-enforcer-plugin` | 3.4.1 | Build rule enforcement |
| `maven-resources-plugin` | 3.3.1 | Resource filtering |
| `maven-surefire-plugin` | 3.1.2 | Unit test execution |
| `spring-boot-maven-plugin` | 3.4.5 | Spring Boot fat JAR packaging |
| `jacoco-maven-plugin` | 0.8.12 | Code coverage (prepare-agent + report on verify) |

## 4. Enforcer Rules (Build-Time Governance)

The `maven-enforcer-plugin` is configured with multiple rules active on all child builds (pom.xml lines 822–866):

```xml
<banDuplicatePomDependencyVersions/>
<bannedDependencies>
  <excludes><exclude>log4j:log4j</exclude></excludes>
</bannedDependencies>
<banTransitiveDependencies>
  <excludes>
    <exclude>org.springframework*:*</exclude>
    <exclude>com.thoughtworks.xstream:xstream</exclude>
    <exclude>com.fasterxml.jackson.core:*</exclude>
    <exclude>org.hibernate.orm:hibernate-core</exclude>
    <exclude>jakarta.xml.bind:jakarta.xml.bind-api</exclude>
    <exclude>org.apache.logging.log4j:*</exclude>
  </excludes>
</banTransitiveDependencies>
<requireMavenVersion><version>3.6</version></requireMavenVersion>
<requireJavaVersion><version>21</version></requireJavaVersion>
<requireReleaseDeps>
  <message>No Snapshots Allowed!</message>
</requireReleaseDeps>
```

**Operational Impact**: Any child service build that attempts to add Log4j 1.x, use a SNAPSHOT dependency in a release build, use Java < 21, or use Maven < 3.6 will **fail the build immediately**. This is a positive security governance control.

## 5. JaCoCo Integration

JaCoCo is configured in the parent POM with two executions on all child projects:
1. `prepare-agent` (bound to test phase): Instruments bytecode for coverage collection
2. `post-unit-test` / `report` (bound to verify phase): Generates HTML/XML coverage reports

**Operational Note**: No minimum coverage thresholds are enforced. JaCoCo only reports; it does not fail builds. To enforce coverage gates (e.g., required for PCI DSS quality controls), add `<check>` goals with `<rules>` to the JaCoCo configuration.

## 6. Resource Filtering

The parent sets `<resource.delimiter>@</resource.delimiter>` (pom.xml line 25). Spring Boot's default delimiter is `@`, so `application.properties` and `application.yml` files can use `@property.name@` syntax for Maven resource filtering. This is the standard Spring Boot pattern.

## 7. Repository and Distribution

The Maven wrapper properties (`.mvn/wrapper/maven-wrapper.properties`) point to the Onbe internal Maven wrapper distribution. The `settings.xml` (`.mvn/wrapper/settings.xml`) configures the Maven repository mirror pointing to the internal Onbe Nexus/GitHub Package registry — child services inherit this settings context when using `./mvnw`.

## 8. Upgrade and Release Process

The `maven-release-plugin` (3.0.1) is configured for release management. The release process:
1. `mvn release:prepare` — bumps version from `6.0.13` → `6.0.14-SNAPSHOT`, tags git
2. `mvn release:perform` — builds and publishes to GitHub Packages

**Impact of parent upgrades**: All child services must explicitly opt into a new parent version by updating their `<parent>` version. The `UPDATE_PARENT_VERSION: true` flag visible in `profile_SVC`'s `deployment.yml` (line 37) suggests automated parent version updates are supported in the GitHub Actions pipeline for child services that opt in.
