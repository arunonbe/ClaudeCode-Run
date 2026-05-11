# custom-files_LIB — DevOps / Operations View

## Build System
- **Maven**; parent POM: `com.parents:prepaid-parent:6.0.12`.
- groupId: `com.ecount.custom`, artifactId: `custom-files-common`, version: `2.0.0`.
- Packaging: `jar`; finalName: `CustomFilesCommon`.
- Java 21 (`maven.compiler.source/target = 21`).
- Additional Maven plugins: `maven-jar-plugin` (with manifest classpath), `maven-assembly-plugin` (zip descriptor at `src/assemble/zipfile.xml` — file not present in repo), `maven-source-plugin` (sources JAR).

## CI/CD
- GitHub Actions: `.github/workflows/github-package-publish.yml` — publishes to GitHub Packages.
- `.github/workflows/codeql.yml` — CodeQL SAST scanning.
- Dependabot: `.github/dependabot.yml`.
- No deployment workflow — this is a library; consumers declare it as a Maven dependency.

## Artifact Publication
- Published to GitHub Packages (Maven registry) via `github-package-publish.yml`.
- Consumers reference it as `com.ecount.custom:custom-files-common:2.0.0`.

## Configuration
- No runtime configuration; pure library with no Spring context, no property files, no external dependencies at runtime.
- `pom.xml` has no `<dependencies>` section beyond what is inherited from `prepaid-parent:6.0.12` (parent POM content not in this repo).

## Observability
- No logging framework configured in this library itself.
- `BufferedFileWriter.java` presumably uses standard Java I/O — no structured logging.
- Library consumers are responsible for all observability.

## Infrastructure
- No containerisation.
- No infrastructure-as-code.
- Deployed as JAR to Maven repository only.

## Risks
- Parent POM `prepaid-parent:6.0.12` is a snapshot-like internal dependency; version must be resolvable from the configured Maven registry.
- `maven-assembly-plugin` references `src/assemble/zipfile.xml` which is **not present** in the repository — assembly goal will fail if invoked.
- Java 21 `field.setAccessible(true)` in `EcountRequestFile.getField()` requires `--add-opens` JVM flags or module `opens` declarations from consuming modules; not configured in this library's build.
- No unit tests present in the repository — no automated validation of the fixed-width format logic.
- Version `2.0.0` is a release version (no SNAPSHOT suffix) but no git tag or changelog is visible.
