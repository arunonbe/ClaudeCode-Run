# prepaid-parent_PARENT — Solution Architect View

## 1. Solution Role

`prepaid-parent_PARENT` is the **Maven Bill of Materials (BOM) and build policy hub** for the Onbe prepaid platform. As a solution artifact, it solves a classic large-codebase problem: dependency version sprawl and inconsistent build tooling across dozens of independently-developed microservices.

The solution pattern implemented here is **Maven inheritance + dependency management**: child projects inherit the parent via the `<parent>` stanza and gain:
- All `<dependencyManagement>` entries (versions available without declaring them in child POMs)
- All `<pluginManagement>` entries (plugin versions and configurations pre-set)
- All universally-inherited `<dependencies>` (Lombok, Spring Boot starter-log4j2, Spring Boot test)
- All `<build><plugins>` active on every build (compiler, install, source, release, enforcer, resources, surefire, JaCoCo)

## 2. Inheritance Mechanism

Child projects inherit the parent by declaring:
```xml
<parent>
  <groupId>com.parents</groupId>
  <artifactId>prepaid-parent</artifactId>
  <version>6.0.13</version>
</parent>
```

Confirmed child: `profile_SVC` (`profile/pom.xml` line 6–10).

The Maven wrapper settings (`settings.xml`) in `.mvn/wrapper/` configures repository access, enabling child projects to resolve the parent from the internal package registry using `./mvnw` without requiring a locally-installed Maven or manual `settings.xml` setup.

## 3. Universal Dependencies (Inherited by All Children)

Three dependencies are directly declared (not managed — always included):

```xml
<dependency>
  <groupId>org.projectlombok</groupId>
  <artifactId>lombok</artifactId>
  <optional>true</optional>   <!-- compile-time only, excluded from JAR -->
</dependency>
<dependency>
  <groupId>org.springframework.boot</groupId>
  <artifactId>spring-boot-starter-log4j2</artifactId>
</dependency>
<dependency>
  <groupId>org.springframework.boot</groupId>
  <artifactId>spring-boot-starter-test</artifactId>
  <scope>test</scope>
  <!-- excludes spring-boot-starter-logging (avoids Logback conflict) -->
</dependency>
```

**Implication**: Every child service automatically uses Log4j2 for logging (not Logback). This is a deliberate choice: Log4j2 is the Apache standard logging framework; using it universally ensures consistent log format and centralized SIEM integration.

## 4. Spring Boot BOM Import Strategy

Two Spring BOMs are imported in `<dependencyManagement>`:

```xml
<dependency>
  <groupId>org.springframework.boot</groupId>
  <artifactId>spring-boot-dependencies</artifactId>
  <version>3.4.5</version>
  <type>pom</type>
  <scope>import</scope>
</dependency>
<dependency>
  <groupId>org.springframework.cloud</groupId>
  <artifactId>spring-cloud-dependencies</artifactId>
  <version>2023.0.2</version>
  <type>pom</type>
  <scope>import</scope>
</dependency>
```

This cascades hundreds of Spring library versions into the dependency management section. The commented-out `ecount-bom` entry (lines 153–159) suggests an internal Onbe BOM was considered but not yet published.

## 5. Build Lifecycle Solution

The active `<build><plugins>` section configures the following lifecycle:

| Phase | Plugin | Action |
|---|---|---|
| compile | maven-compiler-plugin | Compile to Java 21 bytecode |
| test | maven-surefire-plugin | Run unit tests |
| verify | jacoco-maven-plugin | Generate coverage report |
| package | maven-jar-plugin / maven-war-plugin | Package artifact |
| install | maven-install-plugin | Install to local `.m2` |
| deploy | maven-source-plugin | Attach source JAR |
| release | maven-release-plugin | Tag + version management |
| build (all) | maven-enforcer-plugin | Rule validation |
| build (all) | maven-resources-plugin | Filter resources with `@` delimiter |

## 6. Enforcer Plugin Solution Detail

The enforcer is the security-critical element of the build solution. It runs on every `mvn verify` or `mvn install` call:

```
banDuplicatePomDependencyVersions   → catches copy-paste errors
bannedDependencies (log4j:log4j)    → PCI DSS security control
banTransitiveDependencies           → controls transitive sprawl
  (exceptions: Spring, Jackson, Hibernate, JAXB, log4j2)
requireMavenVersion(3.6)            → consistent build tooling
requireJavaVersion(21)              → LTS Java compliance
requireReleaseDeps                  → no SNAPSHOT in release
  (exception: same groupId artifacts)
```

The transitive dependency ban with exceptions is a well-calibrated design: Spring and Jackson are ubiquitous and safe to allow transitively; the others are explicitly tracked.

## 7. Maven Site and Reporting

The `<reporting>` section configures two report generators (pom.xml lines 893–906):
- `maven-surefire-report-plugin`: HTML test results report
- `taglist-maven-plugin`: Report on TODO/FIXME tags in code

Site generation is **skipped by default** (`maven-site-plugin.skip=true`). These can be enabled for documentation builds by passing `-Dmaven-site-plugin.skip=false`.

## 8. Recommended Solution Enhancements

1. **Add JaCoCo minimum coverage check**: Add a `<check>` execution to the JaCoCo plugin with `<rules>` requiring e.g. 60% line coverage minimum. This enforces test quality across all child services.
2. **Publish an internal ecount BOM**: The commented-out `ecount-bom` (lines 153–159) suggests intent. An internal BOM consolidating all `com.ecount.*` / `com.onbe.*` library versions would further reduce version sprawl in child POMs.
3. **Upgrade `java-jwt` to 4.x**: The Auth0 JWT library 3.4.0 has known vulnerabilities; upgrade to 4.x in the managed versions.
4. **Deprecate `struts` 1.2.9**: This version should only appear in a `legacyDependencies` profile, clearly flagged as deprecated, to prevent inadvertent new usage.
5. **Add SBOM generation**: Configure the `cyclonedx-maven-plugin` to generate an SBOM (Software Bill of Materials) as part of the build — essential for PCI DSS 6.3.2 compliance (maintain an inventory of all software components).
