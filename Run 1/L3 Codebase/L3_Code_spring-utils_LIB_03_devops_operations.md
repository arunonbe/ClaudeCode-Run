# spring-utils_LIB — DevOps / Operations View

## Build System
- **Build tool**: Apache Maven (multi-module POM)
- **Root POM**: `pom.xml` — `com.citi.prepaid.springutils:springutils:3.1.0`, packaging `pom`
- **Parent POM**: `com.parents:prepaid-parent:6.0.13`
- **Java version**: 21 (compiler source and target)
- **Modules**:
  - `springutils-generic` — core Spring AOP/remoting utilities
  - `springutils-jms` — JMS invoker infrastructure
  - `springutils-mock` — commented out / excluded from build

## Dependency Resolution
- Artifacts are resolved from two Maven repositories configured in `.mvn/wrapper/settings.xml`:
  - Maven Central: `https://repo1.maven.org/maven2`
  - Onbe GitHub Packages: `https://maven.pkg.github.com/onbe/onbe_maven_releases`
- Authentication to GitHub Packages uses `GITHUB_TOKEN` environment variable (no hardcoded credentials observed).

## CI/CD Pipeline
| Workflow | File | Trigger | Description |
|---|---|---|---|
| GitHub Packages Publish | `.github/workflows/github-package-publish.yml` | Push to `main`, PR to `main`, `workflow_dispatch` | Builds and publishes the library to GitHub Packages; delegates to `Onbe/om-ci-setup` reusable workflow `java-package-publish.yml@main`. Tests skipped (`-Dmaven.test.skip`). |
| CodeQL Analysis | `.github/workflows/codeql.yml` | Weekly schedule (Thursday 10:42), `workflow_dispatch` | Static analysis via CodeQL; delegates to `Onbe/om-ci-setup` reusable workflow `codeql-auto.yml@main`. |
| Dependabot | `.github/dependabot.yml` | Weekly | Automated Maven dependency version PR creation. |

## Deployment
This is a JAR library, not a deployed service. Consumers include it as a Maven dependency. Published to `https://maven.pkg.github.com/onbe/onbe_maven_releases`.

## Configuration Management
- `SwitchedPropertyPlaceholderConfigurer` provides environment-switching via a classpath properties file. Consumers configure the switch resource and property/case mappings in their Spring XML application context.
- No Kubernetes/Helm/Terraform/Docker artifacts present — not applicable for a library.

## Observability
The library contributes to observability of consuming services by:
- Writing MDC keys (`AuditMethodInterceptor`, `MDCWriter`) that appear in structured log output.
- Exposing the `/monitor` Spring MVC endpoint (consumers must register the controller) for operational health dashboards.
- Collecting `MethodVisitStatistics` for per-method call counts and timings.
No direct metrics export (Prometheus, Micrometer, etc.) is implemented.

## Infra Dependencies
| Dependency | Scope | Notes |
|---|---|---|
| JMS broker | Runtime (springutils-jms consumers) | Queue/topic names are configuration-driven; broker type is not constrained |
| JDBC DataSource | Runtime (monitor DB executors) | Caller-supplied at config time |
| Spring Web MVC container | Runtime (monitor endpoint) | Tomcat 10.x per README |
| GitHub Packages registry | CI/CD | Library distribution |

## Operational Risks
| Risk | Severity | Notes |
|---|---|---|
| Tests skipped in publish pipeline | High | `mvn clean install -Dmaven.test.skip` — published artifacts may regress silently |
| Reusable workflow pinned to `@main` | Medium | Breaking changes in `om-ci-setup` main branch can break this library's CI without notice |
| Dependabot PRs not automatically merged | Low | Without auto-merge policy, CVE-patched dependency versions accumulate as open PRs |
| `springutils-mock` commented out | Low | Unclear if mock utilities are maintained separately or abandoned |
