# 03 DevOps & Operations — ecount-host-log4j_LIB

## Build System

The project uses **Apache Maven** with the Maven Wrapper (`mvnw` / `mvnw.cmd`) checked into the repository. The wrapper properties file at `.mvn/wrapper/maven-wrapper.properties` pins a specific Maven version, ensuring reproducible builds regardless of the developer's local Maven installation.

Parent POM: `com.ecount:module-parent:4` (`pom.xml` lines 6–9). The parent is an internal artefact that centralises plugin management for all Onbe legacy modules.

Build command:
```
./mvnw clean package
```
Output: `target/ecount-host-log4j-1.0.1-SNAPSHOT.jar`

## Versioning

Current version: `1.0.1-SNAPSHOT` (`pom.xml` line 15).

**Observation**: The library has never been released. SNAPSHOT artefacts are mutable — any consumer resolving this version may receive a different binary on each build. In a PCI DSS environment, the use of SNAPSHOT versions in production is a supply-chain governance gap because artefact integrity cannot be guaranteed. Recommendation: tag a release (`1.0.1`) and enforce immutability in Nexus/Artifactory.

## CI/CD Pipeline

The GitHub Actions workflow at `.github/workflows/codeql.yml` runs **GitHub CodeQL** static analysis on a weekly schedule (Saturday 00:52 UTC) and on manual dispatch (`workflow_dispatch`). The workflow delegates to a shared reusable workflow:

```yaml
uses: Onbe/om-ci-setup/.github/workflows/codeql-auto.yml@main
```

Runner: `self-hosted`, `X64`, `Linux`, `ubuntu-docker`.

There is **no build, test, or publish step** in any workflow in this repository. Artefact publication must be handled externally (e.g., from a developer workstation or a separate pipeline in the consuming project).

## Dependabot

`.github/dependabot.yml` is present (file exists in the repo), indicating Dependabot is configured to raise PRs for dependency updates. Given that the only runtime dependency is Log4j 1.2.15 — a severely vulnerable version — this should already be triggering alerts (see the security section in `05_solution_architect.md`).

## Deployment Model

The library is deployed as a JAR artefact to Onbe's internal Maven repository (Nexus / Artifactory). Consuming services declare it as a Maven dependency. There is no standalone deployment unit (no WAR, no Docker image, no service).

## Operational Monitoring

Because this is a library (no runtime process), there is no health endpoint, metrics endpoint, or log stream to monitor directly. Operational monitoring is performed indirectly via the consuming service's log output (e.g., if the hostname-resolution fails at startup, `EcountPatternParser` logs an error via `LogLog.error("Can not detect DNS/IP name of the running machine.")` at line 19 of `EcountPatternParser.java`).

## Upgrade Path

To adopt a newer Log4j version:
1. Update `pom.xml` dependency from `log4j:1.2.15` to `log4j2` (`org.apache.logging.log4j`).
2. Rewrite `EcountPatternLayout` and `EcountPatternParser` to extend Log4j 2 extension points (`AbstractStringLayout`, `PluginFactory`).
3. Increment the library version and publish a new release.
4. Update all consuming services to reference the new version.

This is a medium-effort migration but is **high-priority** given the CVE exposure detailed in `05_solution_architect.md`.
