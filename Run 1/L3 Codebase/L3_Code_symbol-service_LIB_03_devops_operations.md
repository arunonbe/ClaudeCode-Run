# DevOps & Operations View — symbol-service_LIB

## Build
- Build tool: Apache Maven (wrapper present; `.mvn/wrapper/maven-wrapper.jar` in VCS — supply chain risk).
- Parent POM: `com.parents:prepaid-parent:6.0.12` (external).
- Java target: 21 (`maven.compiler.source=21`, `maven.compiler.target=21`).
- Modules: `symbol-common` (JAR), `symbol-svc` (JAR).
- Published to GitHub Packages.
- Tests require live SQL Server (hardcoded `eciflexsqldev:1433`); CI pipeline skips tests (`-Dmaven.test.skip`).

## Deployment
- Published as Maven library JARs (`symbol-common` and `symbol-svc`) to GitHub Packages.
- No Docker image or WAR deployment.
- Consuming services include `symbol-common` (interface + value objects) and optionally `symbol-svc` (implementation + DAO) as Maven dependencies.
- DataSource (`JobSvcDataSourceSymbol`) must be provided by the consuming application's Spring context.

## Configuration Management
- `symbol-svc` Spring XML (`applicationContext-symbol.xml`) defines `SymbolService`, `symbolLibrary`, `symbolServiceDAO`, and procedure beans.
- All procedure beans take `JobSvcDataSourceSymbol` as a constructor argument — the DataSource bean must be defined externally.
- Test datasource config (`applicationContext-symbol-datasource.xml`) references hardcoded paths (`d:/c-base/config/director-client.properties`, `d:/c-base/config/service/symbolservice/symbol.properties`) and hardcoded SQL Server credentials.
- `.mvn/.github/` directory contains a nested copy of GitHub workflow files — appears to be a template or duplicate; could cause confusion.

## Observability
- Logging via SLF4J with `ThreadLocal<Logger>` pattern (same as strongbox-lib).
- Each stored procedure class logs constructor DataSource, operation start, success, and exception messages at INFO/ERROR level.
- No metrics, no health endpoint, no distributed tracing.

## Infrastructure Dependencies
| Dependency | Details |
|------------|---------|
| SQL Server (`jobsvc_test` / production) | Symbol table; JTDS JDBC driver |
| `com.ecount.daoutil:dao-util:2.0.1` | JDBC utility base classes (`NoResultProcedure`, `OutputParameterReturningProcedure`) |
| `com.ecount.service.core.ecountcore:common:3.0.1` | ECount Core commons |
| SLF4J + Log4j2 (test) | Logging (`log4j2-test.xml` present in test resources) |

## Operational Risks
| Risk | Severity |
|------|----------|
| Tests require live SQL Server — CI always skips tests | High |
| Hardcoded `d:/c-base/config/` Windows path in test resources | Medium |
| `maven-wrapper.jar` in VCS | Medium |
| Duplicate `.mvn/.github/` workflow directory | Low |
| No connection pooling configuration visible in production Spring XML | Medium |

## CI/CD
- GitHub Actions workflow: `.github/workflows/github-package-publish.yml`
  - Triggers: push to `main`, PR to `main`, manual dispatch.
  - Delegates to `Onbe/om-ci-setup/.github/workflows/java-package-publish.yml@main`.
  - Tests skipped (`-Dmaven.test.skip`).
- CodeQL workflow: `.github/workflows/codeql.yml`
  - Schedule: weekly (Sunday).
  - Delegates to `Onbe/om-ci-setup/.github/workflows/codeql-auto.yml@main`.
- Additional workflow copies in `.mvn/.github/workflows/` — `deployment.yml` present (not read in detail); may be a template copy.
- Dependabot: `.github/dependabot.yml` and `.mvn/.github/dependabot.yml` — duplicate.
