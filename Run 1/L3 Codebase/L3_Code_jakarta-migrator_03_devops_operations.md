# DevOps / Operations View — jakarta-migrator

## Build System

| Attribute | Value |
|---|---|
| Build tool | Maven (mvnw wrapper) |
| Java | 21 (source and target) |
| Packaging | POM (aggregator — no deployable artifact at root) |
| Maven parent | `prepaid-parent:6.0.10` |
| Active modules | `acegi-security` (one module; Axis/spring-remoting commented out) |
| Maven Compiler Plugin | 3.11.0 |
| Eclipse Transformer Plugin | `0.5.0` (active in `acegi-security/pom.xml`) |

The build is minimal: `./mvnw clean package` downloads `org.acegisecurity:acegi-security:1.0.3` from Maven repositories, runs the Eclipse Transformer plugin to rewrite `javax.*` → `jakarta.*` bytecode, and produces `jakarta-acegi-security-1.0.3.jar` in the `acegi-security/target/` directory.

### MAVEN_ARGS Flag
All workflows use `-D aether.connector.https.securityMode=insecure`, which disables TLS certificate validation for Maven repository connections. This is a security risk in the supply chain — artifact downloads from GitHub Packages or Maven Central are not certificate-validated. This flag was likely added to work around a corporate proxy or self-signed certificate. It should be replaced with proper truststore configuration.

## CI/CD Pipelines

### GitHub Actions Workflows

| Workflow | Trigger | Purpose |
|---|---|---|
| `github-deploy.yml` | push/PR to main/master, release created | Build, then `mvn deploy` to GitHub Packages |
| `nexus-deploy.yml` | push/PR to main/master/feature/java-21-upgrade | Build (`mvn clean verify`), then `mvn deploy -Pnexus` to Nexus |
| `publish-artifact.yml` | (separate file — variant of github-deploy) | Publishes to GitHub Packages via PAT_TOKEN_PACKAGE |
| `codeql.yml` | Weekly Friday schedule + workflow_dispatch | CodeQL security scanning via shared `codeql-auto.yml` |
| `dependabot.yml` | Dependabot schedule | Dependency update PRs |

### Dual Publish Architecture

The project publishes to **two artifact registries**:
1. **GitHub Packages** (`https://maven.pkg.github.com/Onbe/`) — via `GITHUB_TOKEN`/`PAT_TOKEN_PACKAGE`
2. **Nexus** (`-Pnexus` profile in `prepaid-parent`) — via the Nexus deploy workflow

Consumers must determine which registry holds the canonical version. Historically, Maven repos in Onbe's ecosystem appear to use GitHub Packages for Gen-3 and Nexus for legacy/prepaid services.

### Self-Hosted Runners

Both deploy workflows use self-hosted runners:
```yaml
runs-on: [ self-hosted, X64, Linux, ubuntu-docker ]
```
This means the build runs on Onbe's own infrastructure, not GitHub-hosted runners. These runners must have network access to the upstream Maven repositories and the target artifact registries.

### Tests Skipped in CI

`-D maven.test.skip` is applied in all non-verify steps. Since this project has no test code (no `src/test` directory), this is inconsequential today. However, there is no verification that the transformation produces a correct artifact — only that the build does not fail.

## Configuration Management

The project has no runtime configuration. All configuration is build-time:
- `pom.xml` version properties define the source artifact versions
- Maven `settings.xml` (`.mvn/wrapper/settings.xml`) provides repository credentials at build time
- The `CBASE_HOME_URL` environment variable is not used here (it belongs to runtime services)

## Operational Risk

| Risk | Severity | Detail |
|---|---|---|
| TLS insecure mode in Maven | Medium | `-D aether.connector.https.securityMode=insecure` disables SSL validation for artifact downloads — supply chain risk |
| Tests always skipped | Low | No integration test verifies the transformed JAR works in a consuming service |
| No transformation verification | Medium | The Eclipse Transformer can silently miss reflection-based javax.* references; no post-transform validation step exists |
| Single active module | Low | Only `acegi-security` is active; remaining modules commented out suggest incomplete project lifecycle management |
| Version drift risk | Medium | `acegi-security/pom.xml` still references parent version `1.0.1` while the root `pom.xml` is at `1.0.2` — version mismatch |

## Infra Dependencies

- **GitHub Actions** (self-hosted runners with `ubuntu-docker` label)
- **GitHub Packages** (artifact publish target)
- **Nexus** (artifact publish target via `prepaid-parent` Nexus profile)
- **Maven Central** / `org.acegisecurity` upstream Maven registry (for source JAR download)
- No runtime infrastructure dependencies (build-only tool)

## Observability

None — this is a build-time library. There is no running service, no metrics, no health endpoints, no logs at runtime. Observability is limited to GitHub Actions workflow run logs.
