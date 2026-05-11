# DevOps & Operations View — correlation-web_LIB

## 1. Build System

| Item | Value |
|---|---|
| Build tool | Apache Maven (via Maven Wrapper) |
| Maven version | 3.9.5 (pinned in `.mvn/wrapper/maven-wrapper.properties:17`) |
| Java version | 21 (source and target in `pom.xml:21–22`) |
| Packaging | `jar` (`pom.xml:16`) |
| Artifact ID | `com.ecount.opensource:correlation-web:2.0.1` |
| Parent POM | `com.parents:prepaid-parent:6.0.12` |
| Build command | `mvn clean install -Dmaven.test.skip` (per README and CI) |
| Maven Wrapper JAR | `.mvn/wrapper/maven-wrapper.jar` (binary committed to repo) |

### Build Flags of Note
- `-Dmaven.test.skip` is used in both the CI publish workflow (`github-package-publish.yml:41`) and the README (`README.md:15`). **Tests are unconditionally skipped** — there are no test sources, but the flag also suppresses compilation of any future tests.

---

## 2. Dependency Resolution

Maven settings are in `.mvn/wrapper/settings.xml`. Two repositories are configured:

| Repository ID | URL | Purpose |
|---|---|---|
| `central` | `https://repo1.maven.org/maven2` | Standard Maven Central |
| `github-releases` | `https://maven.pkg.github.com/onbe/onbe_maven_releases` | Onbe internal GitHub Packages registry |

Authentication to the internal GitHub Packages registry uses `${env.GITHUB_TOKEN}` injected at build time (`settings.xml:7`). This token is supplied via GitHub Actions `secrets: inherit`.

**Dependabot** is configured (`.github/dependabot.yml`) to scan the Maven ecosystem weekly from the root directory.

---

## 3. CI/CD Pipelines

### Pipeline 1: `github-package-publish.yml` — Primary Library Publish

| Property | Value |
|---|---|
| Trigger | Push to `main`, PRs targeting `main`, manual `workflow_dispatch` |
| Reusable workflow | `Onbe/om-ci-setup/.github/workflows/java-package-publish.yml@main` |
| Secrets | `secrets: inherit` |
| Maven args | `-s ./.mvn/wrapper/settings.xml -Dmaven.test.skip` |
| Inputs | `version-tag`, `auto-increment`, `dry-run`, `update-dependencies` (all optional) |
| Output | Published JAR to `github-releases` (GitHub Packages) |

This is the **correct and intended** pipeline for this library.

### Pipeline 2: `deployment_temp.yml` — Misaligned/Stale Deploy Workflow

| Property | Value |
|---|---|
| Trigger | Push/PR to `main` and `feature/java-21-upgrade` |
| Reusable workflow | `Onbe/om-ci-setup/.github/workflows/java-workflow.yml@main` |
| APP_NAME | `AccountManagementAPI` — **WRONG: belongs to a different service** |
| PACT_PACTICIPANT | `account-management-api` — **WRONG** |
| TARGET_ROOT | `./accountmanagementapi-war` — **WRONG** |
| PUBLISH_TO_APIM | `true`, `EXTERNAL_APIM: true` — **WRONG for a library** |
| API_SUFFIX | `account-management-api` — **WRONG** |

This file (`deployment_temp.yml`) was copied from `AccountManagementAPI` and **never updated**. It will attempt to deploy an unrelated application's WAR on every push to `main`. This is an operational risk.

### Pipeline 3: `codeql.yml` — Security Scanning

| Property | Value |
|---|---|
| Trigger | Manual `workflow_dispatch` + weekly schedule (`cron: '53 17 * * 5'` — Fridays at 17:53 UTC) |
| Reusable workflow | `Onbe/om-ci-setup/.github/workflows/codeql-auto.yml@main` |
| Runner | `ubuntu-latest` |

CodeQL runs weekly. No language is explicitly specified; the central workflow likely auto-detects Java.

---

## 4. Configuration

The library itself has no runtime configuration files (no `application.properties`, no `application.yml`, no environment variables consumed). All configuration is build-time only:

- Header name constant comes from `correlation-core` via `LogContextConstants.CORRELATION_ID_HEADER`.
- No feature flags, no environment-specific behaviour.

---

## 5. Observability

| Signal | Detail |
|---|---|
| Logging | Lombok `@Slf4j` on `CorrelationWebContext` (`CorrelationWebContext.java:8`). Two TRACE-level log statements at lines 17 and 20. No INFO/WARN/ERROR emitted by this library. |
| Metrics | None. |
| Tracing | This library *enables* tracing via correlation IDs but does not itself emit trace spans. |
| Alerts | None defined in this repo. |

Log output is only visible when the consuming application's logging framework is configured at `TRACE` level for the `com.ecount.opensource.correlation` package. This is appropriate for a library — it avoids log pollution in production.

---

## 6. Infrastructure

This is a **library (JAR)**, not a deployable service. There is no:
- Container image / Dockerfile
- Kubernetes manifest
- Helm chart
- Infrastructure-as-Code (Terraform, CloudFormation)
- Health endpoint
- Port binding

The runtime footprint is zero bytes beyond the JVM of the consuming application. Tomcat 10.x+ is listed as a prerequisite in the README because the consuming applications use Jakarta Servlet API (`jakarta.servlet:jakarta.servlet-api` — `provided` scope in `pom.xml:33–36`), but this library does not manage Tomcat itself.

---

## 7. Operational Risks

| Risk | Severity | Recommendation |
|---|---|---|
| `deployment_temp.yml` actively references `AccountManagementAPI` | High | Delete or correct this file immediately; it will fire on every push to `main` and attempt a mismatched deployment. |
| No tests | Medium | Add unit tests for `CorrelationHeaderFilter` and `CorrelationWebContext` to catch regressions. |
| `mvnw.cmd` committed (308+205 lines of shell scripts) | Low | Standard practice for Maven Wrapper; acceptable. |
| Maven Wrapper JAR committed as binary | Low | Common approach; review periodically for supply chain risk. |
| Dependabot targets only Maven ecosystem | Low | No GitHub Actions ecosystem scan configured; `om-ci-setup` workflow versions pinned to `@main` (floating). |
| CodeQL schedule references `ubuntu-latest` (floating runner) | Low | Runner version could change; pin to a specific version if stability is required. |
