# maven-packaging-poc — Business Analyst View

## Business Purpose

`maven-packaging-poc` is a **proof-of-concept (POC) repository** exploring Maven build packaging and versioning techniques. It has no direct business function — it is a technical engineering experiment. Its purpose is to validate Maven CI-friendly versioning, the `ci-friendly-flatten-maven-plugin`, and the `maven-git-versioning-extension` for use in Onbe's Java library publishing pipeline.

This POC is relevant to the Onbe platform infrastructure team responsible for standardising how Java library versions are managed and published to GitHub Packages.

## Capabilities

- Demonstrates CI-friendly Maven versioning using the `${revision}` property pattern
- Experiments with the `ci-friendly-flatten-maven-plugin` (from `com.outbrain.swinfra`) for POM flattening
- Experiments with `maven-git-versioning-extension` (from `qoomon`) for Git-branch/tag-based version derivation
- Shows a multi-module Maven structure with a parent POM and child module (`pkg-module-a`)
- Demonstrates a GitHub Actions publish workflow that deploys to GitHub Packages (via `maven.pkg.github.com/onbe/onbe_maven_releases`)

## Entities

There are **no business entities** in this repository. It contains only POM files and build configuration — no Java source files.

## Business Rules

None applicable — this is a build tooling POC.

## Flows

1. Developer triggers `workflow_dispatch` on `publish-artifact.yml`
2. Workflow accepts version inputs: `VERSION_TAG`, `DEVELOPMENT_TAG`, `IS_RELEASE`, `RELEASE_TYPE` (Major/Minor/Patch)
3. Workflow runs `ci-friendly-flatten:version` to resolve the version
4. Runs `mvn deploy` with the resolved version to publish to `maven.pkg.github.com/onbe/onbe_maven_releases`
5. Creates a git tag via `ci-friendly-flatten:scmTag`

## Compliance Relevance

None. This is a build tooling POC with no production data, no PII, no payments logic.

## Risks

- **PAT token name typo**: The workflow uses `secrets.PAT_TOEKN_PACKAGE` — note the typo (`TOEKN` instead of `TOKEN`). If the secret is named correctly in GitHub (`PAT_TOKEN_PACKAGE`), this workflow will fail silently at deploy time.
- **Commented-out parent POM**: The `prepaid-parent` dependency is commented out, suggesting this POC was intended to eventually inherit from the standard Onbe parent but does not yet do so.
- **Distribution management pointing to legacy Nexus**: The root POM still references `d-na-stk01.nam.wirecard.sys:8080/nexus` (the old Wirecard/on-premise Nexus), while the GitHub Actions workflow deploys to GitHub Packages. These are inconsistent.
- **No source code**: As a POC, there is nothing to test or audit beyond build configuration.
