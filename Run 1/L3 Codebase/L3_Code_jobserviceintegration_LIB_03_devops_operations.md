# jobserviceintegration_LIB — DevOps / Operations View

## Build System

- **Build tool**: Maven (Maven Wrapper `mvnw`)
- **Java target**: **1.6** (Java SE 6) — `maven-compiler-plugin` version 2.0.2 with `<source>1.6</source><target>1.6</target>`
- **Maven compiler plugin version**: 2.0.2 — extremely old
- **Multi-module structure**:
  - Root POM: `com.ecount.service:jobserviceintegration:1.0.1-SNAPSHOT`
  - Parent: `com.ecount.service:service-parent:3`
  - Modules: `Common`, `chrysler`, `jwt`, `LegacyForLife`, `nextel`, `qwest`, `subaru`, `toyota`
- **Packaging**: All modules produce JAR artefacts
- **Source JARs**: `maven-source-plugin` 2.0.3 is configured to attach source JARs on build

## Deployment

This is a **library** (JAR collection). Individual client integration JARs are consumed by the job service and batch processing hosts. There is **no deployment workflow** for this library — no GitHub Actions publish workflow is present (only CodeQL).

No Dockerfile, no container registry, no cloud deployment.

## Config Management

- Promotion configuration file path is a **compile-time constant** in `ChryslerFileContants` (exact path not visible in scanned code but referenced as `PROMO_CONFIG_FILE`). This is a filesystem path on the host running the batch processor.
- All runtime configuration is file-system-based (no environment variables, no Spring config, no secrets manager).
- JMS/database configuration: none — this library has no service dependencies.

## Observability

- Logging uses **Apache Commons Logging** (`commons-logging` 1.1.1) with `LogFactory.getLog()`.
- In `ChryslerFileConverter`, a `ThreadLocal<Log>` pattern is used to provide per-thread logger instances.
- Log output is entirely at `DEBUG` level and guarded by `if(log.get().isDebugEnabled())` — essentially no logs in production unless debug mode is enabled.
- **No structured logging, no distributed tracing, no metrics.**
- Conversion progress is printed to console via `System.out` (indirectly via `log.debug`).

## Infrastructure Dependencies

| Dependency | Type | Notes |
|---|---|---|
| Filesystem | OS | Input files, output files, promotion config, reply files |
| `commons-logging` 1.1.1 | Third-party | Logging facade |
| `com.ecount.service:service-parent:3` | Internal POM | Must be resolvable in build repo |

No database, no messaging, no network dependencies at runtime.

## Non-Java Artefacts

| Type | Location | Purpose |
|---|---|---|
| VBScript `.vbs` | `Common/scripts/`, `alg/`, `chrysler/` | Windows Script Host integration scripts for file import |
| Windows Script File `.wsf` | `alg/JobImportFile/`, `chrysler/` | Windows-based file processing orchestration |
| Perl scripts `.pl` | `Common/scripts/` | File transformation utilities |
| JavaScript `.js` | `Common/scripts/` | Batch file utility scripts (Windows Scripting Engine) |
| Binary JARs | `alg/common/`, `BulkCardGen/JobImportFile/BulkCardGen/` | Pre-compiled libraries committed to source control |

## Operational Risks

1. **Java 1.6 target**: Java SE 6 reached end-of-life in February 2013. Running this code on modern JVMs risks compatibility issues; no security patches available for base runtime.
2. **Binary JARs in source control**: `alg/common/ALGRequestFile.jar`, `CustomFilesCommon-1.0.0.jar`, and the extensive `BulkCardGen` JARs are unversioned compiled binaries. They cannot be audited for vulnerabilities, license compliance, or origin.
3. **Windows-only scripts**: `.vbs` and `.wsf` files only run on Windows; if the processing environment is Linux-based, these are non-functional.
4. **In-memory processing**: The `Hashtable`-based approach loads entire client files into JVM heap — for large files this will cause `OutOfMemoryError`.
5. **No error recovery**: If a conversion fails mid-stream, no partial output cleanup is performed (the `_batchFile.close()` in `finally` is the only protection).
6. **No CI publish pipeline**: No automated publishing to artifact repository means manual JAR distribution.

## CI/CD

| Workflow | Trigger | Action |
|---|---|---|
| `codeql.yml` | Wednesday 17:03 UTC (scheduled), `workflow_dispatch` | Delegates to `Onbe/om-ci-setup/.github/workflows/codeql-auto.yml@main`; Java SAST on self-hosted runner (`ubuntu-docker`) |
| Dependabot | Per `.github/dependabot.yml` | Automated dependency update PRs |

No build-and-publish workflow. No deployment pipeline. No Docker build.
