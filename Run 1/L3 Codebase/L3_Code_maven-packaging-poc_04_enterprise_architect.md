# maven-packaging-poc — Enterprise Architect View

## Platform Generation

**Infrastructure / Tooling POC** — Not a production platform component. Does not fit the Gen-1/2/3 classification. It is a build-system experiment intended to inform Gen-3 library publishing practices.

## Business Domain

**Platform Engineering / Build Infrastructure** — This POC exists to validate Maven versioning and publishing patterns that would be adopted across all Gen-3 library repositories.

## Role in the Platform

`maven-packaging-poc` is a **reference experiment** for the Onbe platform engineering team. Its intended use is:
1. Demonstrate how `ci-friendly-flatten-maven-plugin` resolves `${revision}` placeholders in multi-module Maven projects
2. Validate `maven-git-versioning-extension` for automatic version derivation from Git branches/tags
3. Establish a GitHub Actions workflow pattern for publishing to GitHub Packages with proper PAT authentication and git tagging

If adopted, these patterns would standardise how all Onbe Java libraries are versioned and published — replacing legacy Nexus publishing and manual versioning in Gen-1/2 libraries.

## Dependencies

### Build-time only (no runtime dependencies)
| Plugin | Version | Purpose |
|---|---|---|
| `ci-friendly-flatten-maven-plugin` | 1.0.18 | POM flattening and CI-friendly versioning |
| `build-helper-maven-plugin` | 3.5.0 | Version component parsing |
| `maven-git-versioning-extension` | 9.4.0 (schema version) | Git branch/tag → Maven version |
| `wagon-webdav-jackrabbit` | 3.5.3 | WebDAV Maven transport (legacy, not needed for GitHub Packages) |

## Integration Patterns

This POC demonstrates one integration pattern:
- **Push to GitHub Packages**: Maven deploy to `maven.pkg.github.com` using a PAT token passed as the `GITHUB_TOKEN` environment variable

No service-to-service integration. No JMS. No REST.

## Strategic Status

| Dimension | Assessment |
|---|---|
| Lifecycle | **Experimental / Evaluate** — Determine if patterns should be promoted to standard library template |
| Maturity | Low — workflow has commented-out steps; secret name has a typo; no actual Java source |
| Business value | Medium (if adopted) — standardised versioning reduces build fragility across 100+ libraries |
| Risk | Low — no production impact; isolated POC |

## Migration Blockers

Not applicable (no production code). However, for this POC to become a reusable pattern:

1. **Fix secret name typo**: `PAT_TOEKN_PACKAGE` → `PAT_TOKEN_PACKAGE`
2. **Remove legacy Nexus `distributionManagement`**: Replace entirely with GitHub Packages
3. **Remove `wagon-webdav-jackrabbit`**: No longer needed
4. **Enable enforcer plugin**: Re-enable `banTransitiveDependencies` for dependency hygiene
5. **Add actual Java source** to `pkg-module-a` to validate end-to-end build/test/publish cycle
6. **Document adoption guidance**: README currently contains only the repo name

## Relationship to Other Repositories

If the patterns in this POC are successful, they should be applied to:
- `job_LIB` (replace Citi-era parent POM versioning)
- `jobserviceintegration_LIB` / `jobservice-integration_LIB` (currently SNAPSHOT, no publish workflow)
- All other `_LIB` repositories that use manual versioning
