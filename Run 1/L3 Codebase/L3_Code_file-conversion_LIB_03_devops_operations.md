# DevOps / Operations View — file-conversion_LIB

## Build System

**Build Tool**: Maven (with Maven Wrapper `mvnw` / `mvnw.cmd`)  
**Java Version**: Not explicitly declared in pom.xml (inherited from parent `module-parent:com.ecount:2`). Likely Java 5–8 era based on codebase patterns (raw types, `Vector`, `Hashtable` usage without generics).  
**Group ID**: `com.ecount.file.conversion`  
**Artifact ID**: `fileconversion`  
**Version**: `1.0.1-SNAPSHOT`  
**Packaging**: `jar`

### Parent POM
```xml
<parent>
    <artifactId>module-parent</artifactId>
    <groupId>com.ecount</groupId>
    <version>2</version>
</parent>
```
The parent POM (`module-parent_PARENT` repository) defines the shared build configuration for all `com.ecount` Gen-1 libraries. This includes the Onbe Maven repository settings (WebDAV-based artifact deployment via `wagon-webdav`).

### Maven Build Extension
```xml
<extension>
    <groupId>org.apache.maven.wagon</groupId>
    <artifactId>wagon-webdav</artifactId>
    <version>1.0-beta-2</version>
</extension>
```
Deploys artifacts via WebDAV to the Onbe Maven artifact repository. This is a Gen-1 artifact publishing pattern; modern Onbe services use GitLab Package Registry or Nexus.

### Build Command
```bash
./mvnw clean install
# or
mvn clean install
```

### Dependencies
The `pom.xml` only declares the parent — all dependencies come from the parent POM. There are no explicitly declared dependencies in this module. The code uses:
- `java.io.*` — standard library
- `java.util.*` — standard library (Vector, Hashtable, Enumeration — pre-generics)
- `java.util.zip.*` — standard library

No third-party dependencies. This is a pure Java standard library implementation.

## CI/CD Pipeline

### GitHub Actions — CodeQL (`.github/workflows/codeql.yml`)
Weekly CodeQL static analysis, consistent with other Onbe libraries. Runs on self-hosted runner.

### Dependabot (`.github/dependabot.yml`)
Automated dependency update PRs configured.

**No PR build pipeline, no automated tests, no quality gates configured.**

## Artifact Usage Pattern

This library is consumed as a Maven dependency by batch processing jobs. Consumers add:
```xml
<dependency>
    <groupId>com.ecount.file.conversion</groupId>
    <artifactId>fileconversion</artifactId>
    <version>1.0.1-SNAPSHOT</version>
</dependency>
```

Because it is at `SNAPSHOT` version, consuming projects will always pull the latest build from the Onbe Maven repository, which means a breaking change can silently affect consumers without a version bump.

## Runtime Characteristics

This is a **library** — it has no runtime process of its own. Its operational characteristics are determined entirely by the consuming application:
- No standalone deployment.
- No configuration files.
- No logging framework (uses `System.out.println` in debug mode within `FileValidator`).
- No health check endpoints.
- No metrics.

## Risk: SNAPSHOT Version in Production

The version `1.0.1-SNAPSHOT` is considered unstable in Maven semantics. In a production pipeline, SNAPSHOT dependencies should be avoided because:
1. The same version tag can resolve to different artifacts over time.
2. There is no guarantee of backward compatibility between builds.
3. Build reproducibility is not guaranteed.

**Recommendation**: Release as `1.0.1` (drop `-SNAPSHOT`) and apply semantic versioning for any future changes.

## Java Language Version Concerns

The code uses:
- `Vector` instead of `ArrayList` (pre-Java 1.2 legacy class)
- `Hashtable` instead of `HashMap` (pre-Java 1.2 legacy class)
- Raw types (no generics) throughout

This indicates the code was written before Java 1.5 generics (2004). It is compatible with any modern Java version for compilation and runtime, but represents significant technical debt in terms of type safety and performance.

## Deployment Dependencies

Any service using this library in a containerized (Docker/AKS) environment must ensure:
1. The Onbe Maven artifact repository is accessible during the build (either via internal registry mirror or cached dependency).
2. The library version used is pinned (not SNAPSHOT) in production builds.

## Recommended CI/CD Improvements

1. Add a PR-triggered build workflow.
2. Release as a stable version (remove `-SNAPSHOT`).
3. Add unit tests for all parser and writer methods (currently none).
4. Add OWASP dependency check (though currently no third-party deps, future additions should be scanned).
5. Enable Checkstyle to enforce consistent code style.
6. Modernize Java language features (generics, try-with-resources) in preparation for Java 17+ migration.
