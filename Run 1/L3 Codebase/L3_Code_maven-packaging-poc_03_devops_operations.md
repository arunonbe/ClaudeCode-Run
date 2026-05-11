# maven-packaging-poc — DevOps / Operations View

## Build System

- **Build tool**: Maven (Maven Wrapper `mvnw`)
- **Java version**: JDK 21 (`maven.compiler.source/target = 21` in `pkg-module-a/pom.xml`; GitHub Actions uses `java-version: '21'`)
- **Distribution**: Liberica JDK (`distribution: 'liberica'` in setup-java action)
- **Maven version**: Per `.mvn/wrapper/maven-wrapper.properties` (exact version not read, standard wrapper)
- **Multi-module structure**:
  - Root: `com.onbe.dev:maven-packaging-poc:${revision}` (version defaults to `1.0.0-SNAPSHOT`)
  - Child: `pkg-module-a` (empty POM-packaging module)
- **Key build plugins**:
  - `ci-friendly-flatten-maven-plugin` (v1.0.18, `com.outbrain.swinfra`) — resolves `${revision}` in POMs for CI compatibility
  - `build-helper-maven-plugin` (v3.5.0) — parses version components
  - `maven-enforcer-plugin` — explicitly **skipped** (`<skip>true</skip>`)
  - `wagon-webdav-jackrabbit` (v3.5.3) — WebDAV transport for Nexus (legacy; not used for GitHub Packages deploy)
- **Git versioning extension**: `maven-git-versioning-extension` (`qoomon`) — derives version from branch name (`{branch}-SNAPSHOT`) or tag (`v{version}`)

## Deployment

- **Target repository**: GitHub Packages (`maven.pkg.github.com/onbe/onbe_maven_releases`)
- **Deploy command**: `./mvnw deploy -s ./.mvn/wrapper/settings.xml -Dmaven.test.skip -Denforcer.skip -Pgithub -DcheckModificationExcludeList=mvnw -DaltDeploymentRepository=github-releases::https://maven.pkg.github.com/onbe/onbe_maven_releases --batch-mode -DuseGitHubPackages=true`
- **Version source**: `${revision}` supplied as `-Drevision=${{ github.event.inputs.VERSION_TAG }}`

## Config Management

- Version controlled entirely via Maven POM `${revision}` property and git-versioning extension
- GitHub Actions environment variable `GITHUB_TOKEN` set from `secrets.PAT_TOEKN_PACKAGE` (**typo in secret name**)
- No application runtime configuration (no Spring, no Azure App Config, no Key Vault)

## Observability

Not applicable — this is a build tooling POC with no runtime service.

## Infrastructure Dependencies

| Dependency | Type | Notes |
|---|---|---|
| GitHub Packages | Artefact registry | Target for Maven publish |
| GitHub Actions | CI/CD runner | `ubuntu-latest` |
| Legacy Nexus (`d-na-stk01.nam.wirecard.sys`) | Artefact registry | Referenced in `distributionManagement` but likely unused (GitHub Packages is actual target) |

## Operational Risks

1. **Secret name typo** (`PAT_TOEKN_PACKAGE`): The `GITHUB_TOKEN` environment variable will be empty if the secret is named `PAT_TOKEN_PACKAGE` in GitHub. Maven deploy will fail with authentication error.
2. **Enforcer plugin skipped**: `banTransitiveDependencies` and other enforcer rules are disabled — dependency hygiene is not enforced.
3. **Dual distribution management**: Root POM lists Wirecard Nexus as the release/snapshot repository while the workflow deploys to GitHub Packages via `-DaltDeploymentRepository`. This inconsistency can confuse developers running `mvn deploy` locally.
4. **No code to build**: `pkg-module-a` is a POM-packaging module with no sources. Publishing an empty POM to the artefact registry serves no functional purpose beyond testing the workflow itself.
5. **Commented-out release plugin workflow steps**: Several workflow steps (`Release`, `Create git tag` v2) are commented out, indicating the workflow is still being developed.

## CI/CD

| Workflow | File | Trigger | Action |
|---|---|---|---|
| `publish-artifact.yml` | `.github/workflows/publish-artifact.yml` | `workflow_dispatch` with inputs | Sets version, deploys to GitHub Packages, creates git tag |
| `codeql.yml` | `.github/workflows/codeql.yml` | Schedule + `workflow_dispatch` | Delegates to `Onbe/om-ci-setup` CodeQL workflow |

The `codeql.yml` runs CodeQL on a Java codebase that has no Java source files — it will produce no meaningful results but will run without error.
