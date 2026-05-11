# Enterprise Architect View — service-parent_PARENT

## Platform Generation

**Gen-1 / Gen-2 boundary artifact**. service-parent_PARENT straddles the eCount/Citi (Gen-1) and Wirecard/Northlane (Gen-2) eras:

- The `com.parents` groupId and `prepaid-parent` ancestry are eCount/Citi lineage
- The SCM URL (`gitlab.com/northlane/...`) indicates the POM was managed under the Wirecard/Northlane GitLab organization during Gen-2
- The version `9.0.1-SNAPSHOT` suggests active evolution; prior versions (e.g., `service-parent:7` referenced by `screen-configs_LIB`) represent the frozen Gen-1 branch

The parent POM hierarchy for the Onbe platform is:
```
prepaid-parent (com.parents)
  └── service-parent (com.parents) [this repo]
        └── Gen-1 and Gen-2 service JARs and WARs
```

For Gen-3 services, the hierarchy is separate:
```
onbe-spring-boot-parent_PARENT
  └── Gen-3 microservices (Spring Boot 3, Java 21, AKS)
```

## Integration Patterns

As a parent POM, service-parent_PARENT does not participate in any runtime integration pattern. Its architectural role is:

- **Convention standardization**: Enforces consistent Maven build conventions across all child service projects
- **Dependency version management**: Through `<dependencyManagement>` inherited from `prepaid-parent`, controls shared library versions
- **Repository registration**: Registers internal Nexus (and historically Codehaus) as plugin and artifact sources
- **Documentation anchor**: The POM description explicitly states it is "mainly for documentation purposes" — it codifies the platform's service classification (`ecount.project.type=services`)

The `ecount.project.type=services` property is a platform metadata tag likely used in build scripts or reporting tools to classify artifacts as service-layer components (vs. web applications, libraries, etc.).

## External Dependencies

The parent POM has minimal direct dependencies:

| Dependency | Version | Status |
|---|---|---|
| wagon-webdav | 1.0-beta-2 | EOL (pre-2010) |
| prepaid-parent | 4.0.1 | Internal |

Inherited by child projects through the POM hierarchy:
- All Gen-1 service dependencies (Spring 2.x, commons-*, legacy JDBC drivers) are governed by the parent hierarchy

## Position in the Broader Platform

service-parent_PARENT is a **foundational build governance artifact**. Its position in the ecosystem:

```
All Gen-1/Gen-2 service libraries and WARs
  → service-parent_PARENT (build governance)
    → prepaid-parent (artifact inheritance)
      → Onbe internal Maven repository (Nexus/GitHub Packages)
```

Directly affected child projects (sample — many more exist):
- `screen-configs_LIB` (inherits `service-parent:7`)
- `services-common_LIB` (inherits `prepaid-parent:6.0.12` directly — has moved past service-parent)
- `xaffiliate-service_LIB` (inherits `prepaid-parent:6.0.12` directly)
- Multiple `order_SVC` modules, `request_LIB`, `job_LIB`, etc.

Note: Some Gen-2 services have moved to inherit directly from `prepaid-parent`, bypassing `service-parent`. This suggests `service-parent` is being gradually phased out in favor of direct `prepaid-parent` inheritance or the Gen-3 `onbe-spring-boot-parent`.

## Migration Blockers

1. **Codehaus repository reference**: Cannot be updated by child projects individually; must be fixed in the parent POM itself to unblock builds across all consumers.
2. **HTTP Nexus URL**: Modern Maven enforces HTTPS; all child project builds may fail on Maven 3.8.1+ unless the parent POM URL is updated to HTTPS or the block is overridden.
3. **SNAPSHOT version in widespread use**: If child projects have pinned `service-parent:9.0.1-SNAPSHOT`, releasing a stable version requires coordinated version bumps across all consumers.
4. **`wagon-webdav` dependency**: If the internal Nexus instance no longer uses WebDAV for artifact deployment, this extension causes unnecessary classpath overhead and potential build instability.

## Strategic Status

**Maintenance mode, targeting retirement**.

- **Short term**: Fix Codehaus repository reference (remove or replace with Maven Central); update Nexus URL to HTTPS; cut a stable release version (9.0.1) to replace the SNAPSHOT.
- **Medium term**: Migrate all Gen-1/Gen-2 service projects to inherit directly from `prepaid-parent` (eliminating service-parent as an intermediary) or from `onbe-spring-boot-parent` for Gen-3 migration candidates.
- **Long term**: Retire service-parent_PARENT once all consumers have migrated to the Gen-3 parent POM hierarchy. The `ecount.project.type=services` metadata should be migrated to a modern build metadata standard (e.g., GitHub repository topics).
