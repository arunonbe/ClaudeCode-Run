# bank-lookup-client_LIB — DevOps & Operations View

## Build & Packaging

- **Build tool**: Apache Maven. Maven Wrapper present (`.mvn/wrapper/maven-wrapper.properties`) referencing Maven 3.9.1 with the wrapper jar bundled at `.mvn/wrapper/maven-wrapper.jar`.
- **Java target**: Compiled at source/target level **1.6** (Java 6) — `maven-compiler-plugin` configuration in `pom.xml`, lines 67–70. This is end-of-life and far below any supported JVM version.
- **Artifact coordinates**: `groupId=com.ecount.service.Core2.bank-lookup-client`, `artifactId=bank-lookup-client`, `version=1.2.0-SNAPSHOT`.
- **Parent POM**: `com.ecount.service:service-parent:5` — resolves from the internal ecount Maven repository. Not available in public Maven Central.
- **Packaging**: `maven-assembly-plugin` builds a fat JAR (`jar-with-dependencies`) with main class `com.ecount.process.BankLookupClient.client.AchOutboundProcessor`. The assembly goal is `attached` (deprecated in modern Maven versions), bound to the `package` phase.
- **Artifact classification**: Despite the name `_LIB`, the pom.xml names this `ACH Outbound Processor`, the assembly plugin sets a mainClass, and the SCM path (`Core2/bank-lookup-client`) all indicate this is packaged and invoked as a standalone fat JAR, not a library dependency.
- **Version status**: `1.2.0-SNAPSHOT` — this is not a release version, meaning this artifact is mutable and subject to overwrite in the snapshot repository.

## Deployment

- **Invocation model**: Command-line batch process. Launched with three arguments:
  ```
  java -jar bank-lookup-client-<version>-jar-with-dependencies.jar \
       <path-to-properties-file> \
       <path-to-input-ach-file> \
       <path-to-output-nacha-file>
  ```
- **No containerisation**: No Dockerfile or container specification present in the repository.
- **No service wrapper**: No init scripts, systemd units, or Windows service descriptors present.
- **Scheduling mechanism**: Not present in the repository. The CodeQL workflow runs on a `schedule` (weekly cron), but the ACH processor itself has no scheduler — it is invoked externally (presumably by a job scheduler such as Control-M, cron, or similar in the deployment environment).
- **Output location**: Output file is written to whatever path is passed as the third command-line argument. No default or standard path is enforced.
- **Exit codes**: `System.exit(1)` on failure, implicit `0` on success (`AchOutboundProcessor.java`, line 125).

## Configuration Management

- **External properties file**: All operational parameters are read from a file whose path is the first command-line argument. No default fallback path is available unless the zero-argument `Configuration.getInstance()` is used (which reads from `/AchOutboundProcessor.properties` bundled in the JAR).
- **No environment variable support**: All configuration is properties-file-driven. No `System.getenv()` calls are present.
- **No secrets management integration**: The StrongBox credentials (agent name, connection parameters) are stored in the properties file in plaintext. The agent string is transmitted as an HTTP header in cleartext.
- **No configuration reload**: Configuration is loaded once at startup. Changes require a restart.
- **Director configuration file**: A second properties file path is read from `Processor.director.client.configuration.file`; this file must contain `director.address` pointing to the Director service URI (`Configuration.java`, lines 362–391).
- **Key name swap bug**: Property keys `Processor.strongbox.host.connection.timeout` and `Processor.strongbox.pool.connection.timeout` have their constant string values swapped in `Configuration.java` (lines 65–66). Operators setting these values will get reversed behaviour compared to what the key names suggest.

## Observability

- **Logging framework**: Apache Commons Logging (JCL) facade over Log4j. Configuration in `src/main/resources/log4j.properties`.
- **Log destination**: Rolling file appender writing to `ach_processor.log` in the working directory. Maximum 10 MB per file, 5 backup files (50 MB total). No console appender is active in the default config (stdout appender is defined but root logger routes to `file` only).
- **Log level**: Root logger at `WARN`. Trace and debug statements exist throughout the codebase but are only activated if the log level is lowered. This means normal operations produce only warning and error entries.
- **No structured logging**: All log messages are plain text strings. No JSON or key-value structured format is used, making automated log parsing or SIEM ingestion more difficult.
- **No metrics**: No JMX, Micrometer, Prometheus, or other metrics instrumentation is present.
- **No distributed tracing**: No correlation ID or trace context beyond the `RPC-TxID` UUID (`StrongBoxClient.java`, line 463) attached to each individual StrongBox HTTP call.
- **Performance telemetry**: Elapsed wall-clock time is printed to stdout (`AchOutboundProcessor.java`, lines 203–205), but not to a log or monitoring system.
- **Health checks**: None.
- **Alerting**: Not configured in this repository. Relies entirely on external monitoring of log files or exit codes.

## Infrastructure Dependencies

| Dependency | Type | Resolved Via |
|---|---|---|
| Director service | Internal HTTP/XML-RPC service | URI in director properties file (`director.address`) |
| StrongBox repository service | Internal HTTP/XML-RPC service | URI resolved at runtime from Director (`IDirectorClient.getSerivceLocationURI`) |
| Internal Maven repository | Build-time artifact server | Parent POM `com.ecount.service:service-parent:5` and `director-client:1.0.11` |
| Local filesystem | Input/output ACH files | Command-line paths |
| JVM (Java 6 target) | Runtime | Host environment |

**Third-party library dependencies** (all declared in pom.xml):
- `director-client:1.0.11` — internal ecount library; not public
- `jdom:1.0` — old XML library
- `jexcelapi:jxl:2.4.2` — referenced but not used in any read source file
- `slf4j-api:1.1.0-RC1` and `slf4j-simple:1.1.0-RC1` — ancient pre-release SLF4J
- `flatpack:3.1.1` — FlatPack flat file parser

## Operational Risks

1. **Java 6 target**: Java 6 reached end-of-life in February 2013. Running on a modern JVM with a Java-6-compiled artifact is supported but the dependency chain (Commons HttpClient 3.x, SLF4J 1.1.0-RC1) is severely outdated and likely carries known CVEs.
2. **Apache Commons HttpClient 3.x** (referenced indirectly via `director-client` and used directly in `StrongBoxClient.java`): This library was superseded by HttpComponents HttpClient 4.x over a decade ago. It does not support TLS 1.2/1.3 natively.
3. **SNAPSHOT version in production**: `1.2.0-SNAPSHOT` is mutable. A deployment could inadvertently pick up a different build.
4. **No idempotency guarantee**: If the processor is interrupted mid-run, the partially written output file is not cleaned up or rolled back. Re-running would overwrite with a fresh (possibly partial) result depending on where failure occurred.
5. **ThreadPool shutdown on bounded queue exhaustion**: `RejectedExecutionException` causes `this.shutdown()` and an immediate failure, leaving the output file in a partial state with no cleanup signal.
6. **Busy-wait polling**: The main thread polls `Future.isDone()` in a `Thread.sleep()` loop (`BufferedProcessor.java`, lines 132–134; `DefaultProcessor.java`, lines 139–141). Under heavy load this is inefficient and imprecise.
7. **Single output FileChannel shared across threads via `synchronized`**: All worker threads compete for the same `synchronized (outputChannel)` lock (`ProcessorHelper.java`, line 126; `FlatPackProcessorHelper.java`, line 113). This is correct for thread safety but is a throughput bottleneck.
8. **Log file in working directory**: `ach_processor.log` is written relative to the JVM working directory, which may be unexpected if the JAR is invoked from different directories.

## CI/CD

- **GitHub Actions workflow**: `.github/workflows/codeql.yml` — runs **CodeQL** static analysis (Java) on a weekly schedule (Sunday at 04:35 UTC) and on manual dispatch. Delegates to a reusable workflow `Onbe/om-ci-setup/.github/workflows/codeql-auto.yml@main` using a self-hosted Linux x64 runner.
- **No build CI**: No workflow for `mvn package`, compilation verification, or unit testing.
- **No automated deployment**: No CD pipeline is present in the repository.
- **No integration or unit test automation**: The `src/test` directory contains only `AchOutboundProcessorDriver.java`, which is a manual invocation driver (duplicate of the main class), not a JUnit test.
- **Dependency management**: `dependabot.yml` configured for weekly Maven dependency version updates from the Maven ecosystem.
- **SCM**: Historically tracked in SVN (`ecsvn.office.ecount.com/svn/ecount/services/Core2/bank-lookup-client/trunk` per pom.xml `<scm>` section). The current repo is a Git repository (likely a migration).
