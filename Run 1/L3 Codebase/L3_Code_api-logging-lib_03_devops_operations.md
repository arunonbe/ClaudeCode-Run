# api-logging-lib — DevOps & Operations View

## Build & Packaging

- **Build tool**: Apache Maven via the Maven Wrapper (`mvnw` / `mvnw.cmd`)
- **Maven version**: 3.9.5 (pinned in `.mvn/wrapper/maven-wrapper.properties`, line 17)
- **Java compile target**: 21 (`pom.xml`, lines 12-13, `maven.compiler.source` and `maven.compiler.target`)
- **Artifact type**: JAR (`<packaging>jar</packaging>`, `pom.xml` line 21)
- **Group ID**: `com.ecount.webservices`
- **Artifact ID**: `api-logging-lib`
- **Version**: `1.0.0` (static, not SNAPSHOT)
- **Build command** (per `README.md`):
  ```powershell
  .\mvnw.cmd -s .mvn\wrapper\settings.xml -f csapi-axis-soap-logging\pom.xml clean install
  ```
- **Test skip in CI**: The GitHub Actions publish workflow passes `-Dmaven.test.skip` (`github-package-publish.yml`, line 42), meaning tests are **not executed during the CI publish pipeline**.
- **Plugins used**:
  - `maven-compiler-plugin` 3.13.0
  - `maven-surefire-plugin` 3.1.2 (JUnit 5 runner)
  - `maven-jar-plugin` 3.3.0

## Deployment

- **Artifact registry**: GitHub Packages (`https://maven.pkg.github.com/onbe/onbe_maven_releases`) — configured in `.mvn/wrapper/settings.xml`, lines 26-29.
- **Authentication**: `GITHUB_TOKEN` environment variable injected at CI runtime (`.mvn/wrapper/settings.xml`, line 7). No credentials are hardcoded.
- **Deployment mechanism**: Publishing is performed by a reusable workflow `Onbe/om-ci-setup/.github/workflows/java-package-publish.yml@main` (referenced in `github-package-publish.yml`, line 38).
- **Consuming services**: Included as a Maven dependency in other Onbe services' `pom.xml` files. No Dockerfile or container image — the library ships as a JAR only.
- **Deployment to target services**: Handled entirely by the consuming service's own deployment pipeline. This library has no standalone deployment unit.

## Configuration Management

**Runtime configuration is entirely externalised** — no Spring, no CDI, no DI framework. Configuration is resolved at first call and reloaded every 60 seconds.

| Configuration Vector | Key / Variable | Purpose |
|----------------------|---------------|---------|
| JVM system property | `soap.logging.enabled` | Enable/disable logging |
| JVM system property | `soap.logging.sensitive.fields` or `soap.logging.sensitive-fields` | Override redacted field list |
| JVM system property | `soap.logging.config.file` | Path to external properties file |
| Environment variable | `SOAP_LOGGING_ENABLED` | Enable/disable logging |
| Environment variable | `SOAP_LOGGING_SENSITIVE_FIELDS` | Override redacted field list |
| Environment variable | `SOAP_LOGGING_CONFIG_FILE` | Path to external properties file |
| Classpath resource | `soap-logging-default.properties` | Bundled defaults (disabled + default fields) |

**Tomcat Windows service note** (from `README.md`, lines 85-109): JVM options must be added to the Windows service's **Java Options** registry entry; `catalina.bat` JVM options do not apply to the Windows service process.

**External file resolution**: Supports both plain filesystem paths (e.g., `D:\config\soap-logging.properties`) and `file:///` URIs. Backslash paths inside `file:` URIs are normalised to forward slashes (`normalizePath`, `SoapLoggingSettingsLoader` line 179). HTTP URLs are rejected (`normalizePath` returns `null` for non-file URIs).

**Configuration reload**: `SoapLoggingSettingsLoader.getCurrent()` uses a double-checked locking pattern with `volatile` fields (`cached`, `nextReloadAtMs`) to reload settings at most every 60 seconds without lock contention on the hot path.

## Observability

- **Logging framework**: SLF4J API (`org.slf4j:slf4j-api` 2.0.16). The library produces **no logs of its own** beyond SOAP traces; the consuming service must provide an SLF4J binding.
- **Logger name**: `com.ecount.axis.soap.logging.SoapLoggingHandler` and `com.ecount.axis.soap.logging.SoapLoggingSettingsLoader`
- **Log levels used**:
  - `INFO`: SOAP message traces (`SoapLoggingHandler`, line 59) and settings reload notifications (`SoapLoggingSettingsLoader`, line 91)
  - `WARN`: Handler failures and settings file load failures (`SoapLoggingHandler` lines 33, 46; `SoapLoggingSettingsLoader` lines 108, 114, 129)
- **Log format per SOAP trace** (SLF4J parameterised):
  ```
  SOAP {REQUEST|RESPONSE|FAULT} [service={serviceName}]
  {scrubbedXml}
  ```
- **Metrics/tracing**: None. No Micrometer, OpenTelemetry, or distributed tracing instrumentation in this library.
- **Health endpoints**: None. The library is passive.
- **Operational signal for misconfiguration**: If no SLF4J binding is present at runtime, SOAP log messages silently disappear. The `README.md` documents this explicitly (lines 35-40).

## Infrastructure Dependencies

| Dependency | Version | Scope | Purpose |
|------------|---------|-------|---------|
| `axis:jakarta-axis` | 1.4 | compile | Apache Axis SOAP engine — `BasicHandler`, `MessageContext`, `Message` |
| `axis:jakarta-axis-jaxrpc` | 1.4 | compile | JAX-RPC API for Axis |
| `axis:jakarta-axis-saaj` | 1.4 | compile | SAAJ API for Axis |
| `org.slf4j:slf4j-api` | 2.0.16 | compile | Logging facade |
| `commons-discovery:commons-discovery` | 0.2 | test | Service discovery for Axis in tests |
| `org.junit.jupiter:junit-jupiter` | 5.10.2 | test | Unit testing |

- **Apache Axis 1.4**: A **legacy SOAP stack** (Axis 1.x has been end-of-life for many years). This is the most significant infrastructure dependency constraint.
- **Java 21**: Modern LTS runtime — no version risk here.
- **No Spring Boot, no Jakarta EE, no cloud SDK dependencies**: The library is deliberately framework-agnostic.
- **No external network dependencies at runtime**: All configuration is local (classpath or filesystem).

## Operational Risks

1. **Tests skipped in CI publish pipeline**: `-Dmaven.test.skip` in `github-package-publish.yml` line 42 means regressions can be published without test gate enforcement.
2. **Static version `1.0.0`**: No snapshot or semantic versioning automation is evident in the `pom.xml`. Version bumps require manual `pom.xml` edits. The CI workflow supports `version-tag` override and `auto-increment` inputs, but relies on the `om-ci-setup` shared workflow implementation.
3. **Configuration reload latency**: Up to 60 seconds after changing an external properties file before the change takes effect. Disabling logging urgently (e.g., during a PCI incident) takes up to 60 seconds.
4. **No metrics on scrubbing failures**: If `[SOAP_PAYLOAD_REDACTED]` starts appearing in logs (indicating scrubbing exceptions), there is no alerting or counter — it is silent from an operational monitoring perspective.
5. **Axis 1.4 EOL**: Any CVEs in the Axis 1.x stack cannot be patched via upstream — requires platform migration.
6. **Windows service JVM options pitfall**: Documented in `README.md` — configuration changes applied to `catalina.bat` will not take effect when running as a Windows service, a common operational mistake.

## CI/CD

**Workflows** (`.github/workflows/`):

### `github-package-publish.yml`
- **Triggers**: `workflow_dispatch` (manual, with optional `version-tag`, `auto-increment`, `dry-run`, `update-dependencies` inputs), `push` to `main` (excluding `.mvn/**`, `.github/**`, `mvnw`, `mvnw.cmd` paths), `pull_request` to `main` (opened/synchronize/reopened).
- **Job**: Delegates entirely to `Onbe/om-ci-setup/.github/workflows/java-package-publish.yml@main`.
- **Build args**: `-s ./.mvn/wrapper/settings.xml -Dmaven.test.skip` — settings file is passed; tests are skipped.
- **Secrets**: `secrets: inherit` — all org/repo secrets passed through.

### `codeql.yml`
- **Triggers**: `workflow_dispatch` (manual) and weekly schedule (`cron: '53 17 * * 5'` — Fridays at 17:53 UTC).
- **Job**: Delegates to `Onbe/om-ci-setup/.github/workflows/codeql-auto.yml@main`.
- **Runner**: `ubuntu-latest`.
- **Purpose**: Static application security testing (SAST) via GitHub's CodeQL engine.

**Gap**: No separate test-only CI job exists; tests run only locally or via `mvnw.cmd clean install`. The publish pipeline skips tests entirely.
