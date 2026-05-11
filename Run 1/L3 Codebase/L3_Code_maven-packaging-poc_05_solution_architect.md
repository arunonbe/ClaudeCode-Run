# maven-packaging-poc — Solution Architect View

## Technical Architecture

- **Language**: No Java source code present — POM-packaging modules only
- **Java target**: JDK 21 (configured in `pkg-module-a/pom.xml` and GitHub Actions setup)
- **JDK distribution**: Liberica (BellSoft) — consistent with Gen-3 Dockerfiles in other repos
- **Maven multi-module**: Root POM (`com.onbe.dev:maven-packaging-poc`) + child (`pkg-module-a`), both POM-packaging
- **Version management approach**:
  1. `${revision}` CI-friendly property (Maven 3.5+ feature)
  2. `ci-friendly-flatten-maven-plugin` rewrites POMs at build time to substitute `${revision}` with the actual version
  3. `maven-git-versioning-extension` derives version from branch name (`{branch}-SNAPSHOT`) or tag (`v{version}`)
  4. Manual override via `-Drevision` on the command line

## API Surface

None — no Java code, no REST endpoints, no library API.

## Security Posture

### Authentication
- GitHub Packages authentication via PAT token (`secrets.PAT_TOEKN_PACKAGE`)
- Maven settings (`settings.xml` in `.mvn/wrapper/`) likely contains the server authentication stanza referencing the PAT — this file was not read; it should be verified to not contain hardcoded credentials

### Cryptography
Not applicable.

### Secrets
| Secret | Storage | Risk |
|---|---|---|
| `PAT_TOEKN_PACKAGE` | GitHub Actions Secret | Correct — not hardcoded. **Name has typo** — verify actual secret name in GitHub. |
| Maven settings.xml | `.mvn/wrapper/settings.xml` | Should be verified to use variable interpolation (`${env.GITHUB_TOKEN}`) not hardcoded credentials |

### CVE Assessment
No application dependencies — no CVE risk from this repository directly.

## Technical Debt

| Item | File | Severity |
|---|---|---|
| Secret name typo `PAT_TOEKN_PACKAGE` | `.github/workflows/publish-artifact.yml` line 29 | High — breaks deploy |
| Legacy Nexus URL in `distributionManagement` | `pom.xml` lines 32–40 | Medium — stale; points to decommissioned Wirecard server |
| `wagon-webdav-jackrabbit` build extension | `pom.xml` lines 44–49 | Low — unnecessary dependency |
| Enforcer plugin explicitly skipped | `pom.xml` line 55 | Medium — removes dependency hygiene guard |
| `publish-artifact.yml` has multiple commented-out steps | `.github/workflows/publish-artifact.yml` lines 63–65, 75–79 | Low — indicates incomplete implementation |
| `pkg-module-a` has no Java sources | `pkg-module-a/pom.xml` | Low — POC-level limitation |
| README is empty (single line: `# maven-packaging-poc`) | `README.md` | Low — no documentation |
| Parent POM commented out | `pom.xml` lines 4–8 | Low — indicates intent to inherit from `prepaid-parent` was abandoned |

## Version Strategy Analysis

The POC combines two overlapping versioning mechanisms:
1. `${revision}` property (manual/CI-injected)
2. `maven-git-versioning-extension` (automatic from git)

These can conflict: if both are active, the git extension overrides the POM version, potentially ignoring the `-Drevision` passed by the workflow. The `maven-git-versioning-extension` configuration in `.mvn/wrapper/maven-git-versioning-extension.xml` maps:
- Any branch → `{branch}-SNAPSHOT`
- Tag matching `v*` → `{version}` (strips the `v` prefix)
- No matching ref → `{commit}` (git SHA)

**Risk**: During a tagged release build, if the tag does not start with `v`, the version will fall back to the git commit SHA.

## Gen-3 Migration Requirements (if this pattern is adopted)

1. Fix `PAT_TOEKN_PACKAGE` typo in workflow and GitHub Secrets
2. Remove `distributionManagement` Nexus block; leave only GitHub Packages (via `-DaltDeploymentRepository`)
3. Remove `wagon-webdav-jackrabbit` extension
4. Re-enable `maven-enforcer-plugin`
5. Verify `.mvn/wrapper/settings.xml` uses `${env.GITHUB_TOKEN}` for authentication
6. Add a sample Java class to `pkg-module-a` to validate full build/test/publish cycle
7. Add documentation to README explaining the versioning strategy and how to use it
8. Decide: use `${revision}` + `ci-friendly-flatten` OR `maven-git-versioning-extension` — not both

## Code-Level Risks (File:Line References)

| Risk | File | Line |
|---|---|---|
| Secret name typo | `.github/workflows/publish-artifact.yml` | 29 |
| Stale Wirecard Nexus URL | `pom.xml` | 34, 39 |
| Enforcer skipped | `pom.xml` | 55 |
