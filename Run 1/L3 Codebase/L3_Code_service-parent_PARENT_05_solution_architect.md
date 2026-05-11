# Solution Architect Report — service-parent_PARENT

## Architectural Role

`service-parent_PARENT` functions as the second level of Onbe's Maven POM hierarchy for service-tier modules. It defines the build contract that all Java services within the `ecount.project.type=services` category must conform to.

## POM Hierarchy Architecture

```
com.parents:prepaid-parent:4.0.1          [Top-level platform governance]
    └── com.parents:service-parent:9.0.1  [Service-tier governance]
            ├── services-common_LIB       [Shared service library]
            ├── [service-A]               [Individual microservice]
            ├── [service-B]               [Individual microservice]
            └── [N more service modules]
```

This two-level hierarchy is a sound architectural pattern for a payments platform of Onbe's scale. The top-level `prepaid-parent` manages platform-wide concerns (Java version, Spring Boot BOM, security plugin versions), while `service-parent` layers service-specific concerns on top.

## Inheritance Chain Analysis

The inheritance chain currently spans three generations. This is within acceptable range; chains exceeding four or five levels become difficult to reason about. Key observation: `service-parent` itself is at version `9.0.1`, indicating approximately nine major iterations. This suggests significant historical evolution, consistent with a platform that was built over more than a decade (the Codehaus Hibernate references suggest early 2000s origins).

## Legacy Technology Footprint

The POM retains significant technical debt from prior organisational iterations:

| Artefact | Original Context | Current Status |
|---|---|---|
| `d-na-stk01.nam.wirecard.sys` | Wirecard Nexus server | Likely defunct post-Wirecard insolvency (2020) |
| `snapshots.repository.codehaus.org` | Codehaus community platform | Dead since April 2015 |
| `wagon-webdav:1.0-beta-2` | WebDAV-based artifact deployment | Obsolete, replaced by HTTP wagon |
| Hibernate3 plugin (commented out) | ORM schema generation | Decommissioned but not removed |

The persistence of these artefacts represents accumulated technical debt that adds noise to build output, slows dependency resolution, and creates confusion for new developers.

## Architectural Concerns

### 1. Artifact Distribution Topology
The distribution management URLs point to a server (`d-na-stk01.nam.wirecard.sys`) that pre-dates the Onbe brand. If this server is still functional, it represents infrastructure running on legacy naming conventions and potentially legacy hardware/OS versions that may not receive security patches. If it is defunct, artifact deployment from this module is broken.

**Architecture recommendation:** Define a clear artifact repository strategy. If Onbe uses JFrog Artifactory or Sonatype Nexus on current infrastructure, update all POMs in the hierarchy to point there.

### 2. GitHub vs GitLab Duality
The repository contains both `.github/workflows/` (GitHub Actions) and `.gitlab-ci.yml` (GitLab CI). This indicates the project is or was mirrored between GitHub and GitLab. Maintaining dual CI configurations is a maintenance burden and can lead to divergence. A single source of truth for CI should be designated.

### 3. Java Version Governance Gap
This POM does not specify `maven.compiler.source` or `maven.compiler.target`. In a multi-service platform, it is architectural best practice to declare the minimum Java version in the parent POM so that:
- All services compile to the same bytecode level
- An enforcer rule can prevent accidental downgrade
- Java version upgrade coordination is centralised

The `services-common_LIB` child module declares Java 21. This should be standardised at this parent level.

### 4. Release Management Architecture
Version `9.0.1-SNAPSHOT` with `maven-release-plugin` configuration in the SCM section indicates a release-plugin-based workflow. This is a mature Maven pattern. However, using SNAPSHOT versions for parent POMs in active service environments creates non-deterministic builds.

**Recommendation:** Adopt a release branching strategy:
- `main` — always contains a released (non-SNAPSHOT) version
- `develop` — SNAPSHOT development
- Services always reference the released parent version

## Strategic Recommendations

### Short-Term (1–2 Sprints)
1. Remove all dead repository URLs (Codehaus, Wirecard Nexus)
2. Release `9.0.1` to enable downstream services to reference stable version
3. Consolidate CI to either GitHub Actions or GitLab CI — not both

### Medium-Term (1–2 Quarters)
1. Migrate from WebDAV wagon to HTTPS deployment to current Nexus/Artifactory
2. Centralise Java version declaration at this parent level
3. Add Maven Enforcer with dependency-convergence and Java version rules
4. Add OWASP Dependency-Check with fail-on-severity threshold

### Long-Term (Roadmap)
1. Evaluate migration to a Bill of Materials (BOM) pattern for more flexible dependency management
2. Consider Gradle as an alternative build tool for improved performance and incremental builds
3. Generate SBOM (Software Bill of Materials) as part of the build pipeline to support PCI DSS Requirement 6.3.2
