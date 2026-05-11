# DevOps / Operations View — drawdown-data-manager_LIB

## Build System
- **Build tool:** Apache Maven (wrapper `mvnw` / `mvnw.cmd` present)
- **Maven parent:** `com.citi.prepaid.service:service-parent:6` (internal artifact; must be resolvable from Onbe/Citi Nexus/Artifactory)
- **Packaging:** Fat JAR via `maven-assembly-plugin` (jar-with-dependencies), output file name `drawdowndatamanager.jar`
- **Java target:** Not explicitly set; compiler plugin is commented out; defaults to Maven's JVM version at build time (likely Java 8 given the dependency vintage)
- **Main class:** `com.citi.service.drawdowndatamanager.DrawdownDataManager`

## CI/CD
- **GitHub Actions workflows present:**
  - `.github/workflows/codeql.yml` — CodeQL static analysis
  - `.github/dependabot.yml` — Dependabot dependency updates
- No build/test/deploy pipeline; only security scanning is automated.

## Configuration
| Config File | Location | Contents |
|-------------|----------|---------|
| `drawdown.properties` | `D:\c-base\config\` (hardcoded) | `input.file.path`, `strongbox.agent` |
| `director-client.properties` | `D:\c-base\config\` (hardcoded) | `director.address`, `gp.agent`, `gp.database` |

Configuration is file-based and path-hardcoded to a Windows drive (`D:\c-base`); not environment-variable-driven, not containerised.

## Runtime / Deployment
- Deployed and executed as a standalone JAR on a Windows host.
- No scheduler, no service wrapper, no container definition.
- Invocation: `java -jar drawdowndatamanager.jar` (PUT mode) or `java -jar drawdowndatamanager.jar <ref1> [ref2 ...]` (GET mode).

## Observability
- Logging: Log4j 1.2.15 (no appender configuration visible in this repo; assumed via parent POM or runtime config).
- No metrics, no tracing, no health endpoint.
- Errors surfaced via `e.printStackTrace()` only.

## Infrastructure Dependencies
- StrongBox service (XMLRPC endpoint) at `director.address`.
- GreatPlains SQL Server (connection via Director-managed DBCP datasource).
- File system path `D:\c-base\config\` on the execution host.

## Operational Risks
1. **Hardcoded Windows path** (`D:\c-base\config\`) breaks on any non-Windows or path-different host.
2. **No idempotency** — re-running the tool on the same CSV creates duplicate vault entries.
3. **No retry / circuit-breaker** — any transient StrongBox or DB failure aborts the entire run with no resume capability.
4. **No monitoring** — silent failures are possible if stderr is not captured.
5. **Log4j 1.2.15 CVEs** — multiple critical vulnerabilities (CVE-2019-17571 et al.); upgrade required.
6. **Dependabot enabled** but auto-merge is not confirmed; parent POM controls many versions.
