# DevOps / Operations View — jobservice_common_LIB

## Build System

- **Build tool**: Maven 3.x with wrapper (`mvnw`, `mvnw.cmd`)
- **Maven settings**: `.mvn/wrapper/settings.xml`
- **Java target**: Java 21 (inherited from parent POM or explicitly set — pom.xml not fully detailed for this repo but parent `prepaid-parent` governs)
- **Packaging**: JAR library
- **Artifact coordinates**: `com.ecount.service.jobservice:job-common:4.0.4` (as referenced from `jobservice_SVC/pom.xml` line 58)

## CI/CD Pipelines

**File**: `.github/workflows/github-package-publish.yml`
- Publishes the JAR to GitHub Packages on merge to main
- Triggered by push/tag events

**File**: `.github/workflows/codeql.yml`
- GitHub CodeQL SAST scanning on push/PR
- Java source analysis only

**File**: `.github/dependabot.yml`
- Automated dependency version PRs

There is **no deployment pipeline** — this is a library, not a deployable service. Consumers of this library update their dependency version to adopt new releases.

## Versioning and Release Management

Because this library is shared across many consumers, version management is critical:

- **Current version**: 4.0.4 (referenced as release; `README.md` from `jobservice_SVC` confirms this was separated from the main service)
- **Major version history**: The jump from `job-common:2.0.13` (in `job-order-synchronization_LIB/pom.xml` line 88) to `job-common:4.0.4` (in `jobservice_SVC/pom.xml`) indicates multiple breaking changes and suggests that **not all consumers have been updated to the same version**.

This version divergence is an operations risk: `job-order-synchronization_LIB` is consuming `job-common:2.0.13` while `jobservice_SVC` is on `job-common:4.0.4`. If the domain model has changed between these versions, the two components may have incompatible representations of the same domain objects.

## Dependency Update Propagation

When a new version of `job-common` is published, the following consumers must be updated and tested:

| Consumer | Current Version Used | Update Effort |
|---|---|---|
| `jobservice_SVC` | 4.0.4 | Already on current |
| `job-order-synchronization_LIB` | 2.0.13 | **Major version gap — HIGH risk** |
| `autofile_SVC` | (requires investigation) | Unknown |
| `workflow-service` | (requires investigation) | Unknown |

The `deployment.yml` pattern in `job-scheduler_SVC` includes `UPDATE_DEPENDENCIES: true` and `UPDATE_PARENT_VERSION: true` flags, suggesting automated dependency bump PRs are part of the CI pipeline. Whether `job-common` updates propagate automatically depends on whether the Dependabot or similar tool is configured for internal Maven packages.

## Monitoring Implications

As a library, `job-common` has no runtime monitoring surface. However, it has significant **operational impact through its consumers**:

1. **Status mapping changes**: Any change to `JobServiceConstants.FILE_STATUS_MAP` immediately affects all status reports delivered to clients. No feature flag or gradual rollout is possible for such changes.

2. **Exception hierarchy changes**: Changes to `JobAgentServiceException` or `JobManagerServiceException` may change how errors are caught and logged in consumers, potentially suppressing or generating new alert conditions.

3. **Interface changes**: Adding or removing methods from `IJobManager`, `IJobAgent`, etc. requires all WAR consumers to be updated and redeployed simultaneously.

## Build Artifact Dependencies

This library depends on (from `jobservice_SVC/pom.xml` dependency management):
- No explicit runtime dependencies visible in the common LIB's own pom — it is intended to be a minimal, dependency-light library
- The `workflow-common` and `workflow-xmlrpc` dependencies are intentionally NOT in this library (that was the reason for the split)

## Development Workflow

Recommended workflow for making changes to `job-common`:

1. Create a branch in `jobservice_common_LIB`
2. Update version to next SNAPSHOT
3. Publish SNAPSHOT to GitHub Packages
4. Update dependent repos (`jobservice_SVC`, etc.) to use the SNAPSHOT
5. Test all consumers
6. Release the new version
7. Update all consumers to the release version
8. Deploy all consumers simultaneously (or in dependency order)

This workflow is currently undocumented and relies on developer discipline — a gap that should be addressed with a formal multi-repo release process.

## Change Risk Assessment

**Breaking changes to this library** carry the highest operational risk of any library in the job service ecosystem:
- Every consumer must be simultaneously updated and tested
- A partial rollout (some consumers on new version, some on old) is likely to break integrations
- No runtime compatibility layer exists (no schema evolution, no backward-compatible serialization)
- PCI DSS Requirement 6.3.2 (maintain an inventory of all custom and bespoke software) applies to this library as a cross-cutting dependency
