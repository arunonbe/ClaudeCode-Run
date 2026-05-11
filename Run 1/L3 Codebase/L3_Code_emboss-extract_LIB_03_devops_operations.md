# 03 DevOps & Operations — emboss-extract_LIB

## Build System

- Build tool: **Apache Maven** with Maven Wrapper (`mvnw` / `mvnw.cmd`)
- Java compiler source/target: **1.5** (`pom.xml` lines 57–60) — Java 5 compatibility, an extremely old target
- Parent POM: **None** — this POM has no parent; it is a standalone POM with direct dependency declarations
- Packaging: `jar`
- Final artefact name: `embossExtract` (`pom.xml` line 64)
- Version: `1.0.0-SNAPSHOT`

Build command:
```
./mvnw clean package
```

The build uses `maven-jar-plugin` with a custom manifest file at `src/main/resources/META-INF/MANIFEST.MF`.

## Dependencies

All dependencies are declared with explicit versions directly in the POM (no BOM / dependency management):

| Dependency | Version | Notes |
|---|---|---|
| `junit:junit` | 3.8.1 | Extremely old test framework (2004 era) |
| `xerces:xercesImpl` | 2.8.1 | XML parser; old version |
| `org.springframework:spring` | 2.0 | Spring Framework 2.0 (2006 era) — no longer maintained |
| `org.springframework:spring-mock` | 2.0 | Spring test utilities for Spring 2.0 |
| `net.sourceforge.jtds:jtds` | 1.2 | jTDS JDBC driver |

Additionally, the `lib/` folder ships the following pre-built JARs checked into source control (a significant supply-chain risk):

| JAR | Notes |
|---|---|
| `lib/commons-logging.jar` | Apache Commons Logging |
| `lib/embossExtract.jar` | Pre-built version of the library itself (circular reference concern) |
| `lib/jtds-1.2.jar` | jTDS JDBC driver |
| `lib/log4j-1.2.8.jar` | **Log4j 1.2.8 — CVE-2019-17571 and more (Critical)** |
| `lib/spring-context.jar` | Spring 2.0 context |
| `lib/spring-core.jar` | Spring 2.0 core |
| `lib/spring.jar` | Spring 2.0 combined |
| `lib/xercesImpl-2.8.1.jar` | Xerces XML parser |

**Supply-chain risk**: Committing binary JARs to source control (`lib/`) means their provenance and integrity cannot be verified via the Maven dependency resolution chain. These JARs may contain vulnerabilities that are not tracked by any dependency scanning tool.

## CI/CD Pipeline

The `.github/workflows/codeql.yml` file runs **GitHub CodeQL** analysis:
- Trigger: `workflow_dispatch` and weekly schedule
- Uses: `Onbe/om-ci-setup/.github/workflows/codeql-auto.yml@main`
- Runner: self-hosted, X64, Linux, ubuntu-docker

**There is no automated build, test, or publish pipeline**. The library must be built and distributed manually.

## Configuration Management

Environment-specific configurations are managed via property files in `src/conf/{dev,stage,prod}/embossContext.properties`. These files are **not** injected by an external configuration service — they are bundled into the deployable artefact at build time. This approach:

1. Requires a separate build per environment (or a runtime override mechanism)
2. Embeds credentials in the built artefact (see security findings in `05_solution_architect.md`)

The `EmbossFilePath` property specifies where output files are written:
- Dev: `D://c-base//runtime//ndmroot/` (main resources)
- Stage/Prod: `D:/c-base/runtime/ndmroot/embossTest/` (prod config still points to a test path — likely a misconfiguration)

## Operational Execution

The library is invoked as a standalone Java command-line process:

```bash
java -cp embossExtract.jar com.ecount.process.emboss.extract.Extractor {vendorId}
```

The `Extractor.main(String[] args)` method reads `vendorId` from `args[0]`, creates an `ApplicationContext` from `classpath:com/ecount/process/emboss/appContext-emboss.xml`, and runs the extraction. Exit codes propagate from `EmbossQueueExtractException.getCode()`.

This suggests the library is invoked from a scheduler (cron, Control-M, or similar) as a batch job.

## Monitoring and Alerting

Logging is configured via `src/main/resources/log4j.xml` using Log4j 1.x with two appenders:
- `STDOUT` — DEBUG and INFO levels
- `STDERR` — WARN through FATAL

There is no structured logging, no metrics endpoint, and no alerting integration. Operational monitoring depends entirely on the scheduler capturing the exit code and inspecting stdout/stderr.

## File Transfer to Card Bureau

The library writes the XML file to the configured `EmbossFilePath` directory. The file must then be transmitted to the card bureau by an external mechanism. The comments in the code reference "NDM" (IBM Connect:Direct / Network Data Mover), which is a managed file transfer protocol used in the financial industry for secure file exchange. The NDM root path (`ndmroot`) in the property files confirms this. Verification that NDM encryption (TLS or PGP) is applied to the file before transmission is required for PCI DSS Req 4 compliance.
