# request-file-bulk-card — DevOps & Operations View

## Build & Packaging

The project is built with **Maven**. The single module is `requestfile-bulk-card-impl` (groupId `com.ecount.process`, artifactId `requestfile-bulk-card-gen-impl`).

The Maven build produces two artifacts via the `maven-assembly-plugin`:
- A thin JAR with a declared `Main-Class` manifest entry pointing to `RequestfileBulkCardGenClient`.
- A fat ZIP archive (`zip-with-dependencies`) that bundles all runtime-scope JARs alongside the main JAR.

The Java source/target compatibility is set to **Java 1.5** in `maven-compiler-plugin`.

**Version:** `2013.2.1` is the declared POM version. The `change.log` records the working version as `2013.2.1-SNAPSHOT`, indicating this was never promoted to a clean release artifact. The last known production version noted in `change.log` is `1.0.3`.

There are no Docker images, Kubernetes manifests, or containerisation artefacts anywhere in the repository. No parent POM is declared.

## Deployment

The application is a **standalone executable JAR** (Java command-line process), not a web application. It has no servlet container, no WAR packaging, and no embedded server.

Deployment is by direct file-system placement on a Windows host. The `change.log` and all hard-coded paths reference `D:/c-base/...`, confirming deployment to a physical or virtual Windows server running the legacy `c-base` platform.

Execution is driven by passing five positional command-line arguments:
1. Input file path
2. Output file path
3. Program ID
4. Create date
5. Member ID

There are no Dockerfiles, no Kubernetes manifests, no Helm charts, and no cloud-platform deployment descriptors (ECS task definitions, Azure Container Apps configurations, etc.) in the repository.

## Configuration Management

Configuration is managed through **external properties files on the host file system**, not through environment variables or a central configuration service. Two files are required at runtime and their paths are hard-coded in the Spring `ApplicationContext`:

| Property file | Hard-coded path |
|---|---|
| Application config | `D:/c-base/config/requestfile-bulk-card-gen/requestfile-bulk-card-gen.properties` |
| Job-service data source | `D:/c-base/config/jobsvc-ds.properties` |

The Log4j properties path is also hard-coded as a Java constant in the main class:
```
private static final String LOG_PROPERTIES = "D:/c-base/config/requestfile-bulk-card-gen/log4j.properties";
```

The Spring context wires a `DriverManagerDataSource` bean (`JobSvcDataSource`) whose driver, URL, username, and password are resolved from `jobsvc-ds.properties` via `PropertyPlaceholderConfigurer`. Database credentials are **not committed to the repository** — they remain in the off-repository properties file on the host. However, there is no evidence of secrets management tooling (Vault, Azure Key Vault, AWS Secrets Manager, or similar); the credentials are stored as plain text in a file on disk.

The `request_file_id` re-run token is read at runtime via `System.getenv("request_file_id")` — this is the only use of an environment variable in the code.

No Azure App Config, Spring Cloud Config, or Windows Registry usage is present.

## Observability

**Logging:** The application uses **Apache Commons Logging** as the facade, with **Log4j** as the underlying provider. Log output level is controlled by the external `log4j.properties` file. Log statements use `log.info`, `log.debug`, and `log.error` calls throughout the main processing loop. The test-scope `log4j.properties` routes all output to stdout with a `PatternLayout` that includes timestamp, level, class name, line number, and message.

**Metrics:** None. No metrics framework (Micrometer, Dropwizard Metrics, JMX MBeans) is present.

**Tracing:** None. No distributed tracing instrumentation (OpenTelemetry, Zipkin, Jaeger) is present.

**Health check:** None. The process exits with a non-zero code on failure (`System.exit(-1)`, `-2`, `-3`) and logs an error, but there is no health-check endpoint, no liveness probe, and no structured success/failure signal beyond the JVM exit code.

Stack traces are written via `e.printStackTrace()` in the `processFile` method in addition to the logger, meaning raw stack output can appear on stderr uncontrolled.

## Infrastructure Dependencies

| Dependency | Detail |
|---|---|
| **SQL Server (Job Service DB)** | Connected via `DriverManagerDataSource` using Microsoft SQL Server JDBC drivers (`sqljdbc` 1.2, `mssqlserver` / `msbase` / `msutil` 2.2.0040). Connection string and credentials resolved from `jobsvc-ds.properties`. |
| **c-base platform** | Requires the proprietary ecount/c-base platform libraries (`xPlatform` 2.5.24, `cbase` domain objects, `requestfile-impl` 1.0.2). All resolved from an internal Maven repository not visible in this repo. |
| **Inventory management service** | The `com.citi.prepaid.service.inventory:inventory-mgmt:2013.2.1` library and its Spring context (`applicationContext-inventoryManagement.xml`) are loaded at startup from the classpath. |
| **Local file system** | Input CSV and output request files are read/written directly on the local file system. Paths are supplied at runtime as command-line arguments. |
| **Host file system (Windows)** | Requires `D:/c-base/config/...` directory tree with properties files and Log4j configuration. |

No IBM MQ, Azure Service Bus, Redis, FiServ FDR, or any messaging middleware dependency is present in this repository.

## Operational Risks

| Risk | Severity | Detail |
|---|---|---|
| **SNAPSHOT in production** | High | `change.log` records the current version as `2013.2.1-SNAPSHOT`. SNAPSHOT builds are non-reproducible; the same version label may resolve different bytecode at different times from the internal Maven repository. |
| **Severely EOL dependencies** | High | Spring Framework 2.0.4 (2007), JUnit 3.8.1 (2002), Commons IO 1.3.2, Commons Logging 1.1, XStream 1.1, AspectJ 1.5.3, JAXB 2.0EA3, and Microsoft SQL Server JDBC 1.2 are all well beyond end-of-life with known CVEs. Java 1.5 source/target compatibility is also EOL. |
| **Hard-coded Windows host paths** | High | `LOG_PROPERTIES` is a compile-time constant `"D:/c-base/config/..."`. The Spring XML also hard-codes `file:///d:/c-base/...` paths. Any host path change requires a code or XML change and a rebuild. |
| **No retry logic** | Medium | There is no retry mechanism around file processing, database writes, or the builder calls. A transient failure causes immediate process exit. |
| **No DLQ or error file handling** | Medium | Failed records are not isolated; an exception during line processing causes the entire run to abort with a `RuntimeException` wrapping. There is no dead-letter or partial-success mechanism. |
| **Plain-text credentials on disk** | Medium | Database credentials in `jobsvc-ds.properties` are expected as plain text on the host. No evidence of encryption-at-rest or secrets management tooling. |
| **Uncontrolled stack traces to stderr** | Low | `e.printStackTrace()` in `processFile` emits raw stack traces to stderr, which may surface in job scheduler logs without structured correlation. |
| **No structured exit-code contract** | Low | Exit codes `-1`, `-2`, `-3` are used but not documented in a runbook or scheduler configuration visible in this repository. |
| **Test code references live program IDs** | Low | `RequestfileBulkCardGenClientTest.testMain()` references what appear to be real program IDs (`04018324`) in test code. |
| **Comment stale copy-paste** | Informational | The Javadoc comment on `RequestfileBulkCardGenClient` still references "SubaruRewardsImpl" and the Subaru Rewards log path, indicating a copy-paste origin from a different process. |

## CI/CD

There are **no CI/CD pipeline files** in this repository. Specifically:
- No GitHub Actions workflows (`.github/workflows/`)
- No Jenkins `Jenkinsfile`
- No Azure Pipelines `azure-pipelines.yml`
- No CircleCI, TeamCity, or Bamboo configuration

The SCM entry in `pom.xml` points to a Subversion URL (`scm:svn:http://ecsvn.office.ecount.com/...`), suggesting the original version control was SVN and the repository was later migrated to Git. The Git history shows only a single commit ("Changes to remove console outputs"), confirming minimal Git history and no established Git-native pipeline.

There are **no security scanning integrations**: no SAST tooling (SonarQube, Checkmarx, Semgrep), no dependency vulnerability scanning (OWASP Dependency-Check, Snyk, Dependabot), and no container image scanning (Trivy, Anchore) — consistent with the absence of container artefacts.

Build is expected to be triggered manually via `mvn package` on a developer workstation or a build server with access to the internal `com.ecount` Maven repository.
