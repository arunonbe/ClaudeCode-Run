# DevOps & Operations Report: spring-dbctx_LIB

## Build System

- **Build tool**: Apache Maven (wrapper in `.mvn/wrapper/`)
- **Parent POM**: `com.parents:prepaid-parent:6.0.12` (same shared corporate parent as scheduler_WAPP)
- **Java version**: 21 (compiler source/target declared in root `pom.xml`)
- **Module structure**: Three sub-modules
  - `spring-dbctx-root`: XML bean definitions for JNDI DataSources (production)
  - `spring-dbctx-container`: Container-variant beans (includes JndiTemplate)
  - `spring-dbctx-mock`: Test DataSource beans using `ExpectedLookupTemplate` for unit testing without JNDI

- **Packaging**: JAR library; no WAR or Docker artefact — this is a shared library published to the internal Maven repository
- **Artifact coordinates**: `com.citi.prepaid.spring-dbctx:spring-dbctx:2.0.1`

## CI/CD Pipeline

Only two GitHub Actions workflows are present:

1. **`codeql.yml`**: GitHub CodeQL static analysis scan (security scanning)
2. **`github-package-publish.yml`**: Publishes the library JAR to GitHub Packages (the internal Maven package registry)
3. **`dependabot.yml`**: Automated dependency version updates

There is **no deployment workflow** — correct for a library. However, there is also no visible test execution step in the CI pipeline beyond the CodeQL scan. The Maven test phase (`mvn test`) would be invoked implicitly by a `mvn package` or `mvn install`, but this is not explicitly configured.

No Jenkins pipeline is present (unlike `scheduler_WAPP`), suggesting this library was migrated to GitHub Actions without a legacy Jenkins parallel.

## Deployment Model

As a shared library, `spring-dbctx` is not deployed independently — it is published to the internal Maven registry and consumed as a compile/runtime dependency by dozens of Gen-1 and Gen-2 services. The version `2.0.1` is a release (not a snapshot), indicating it follows Maven release conventions for library versioning.

The Maven distribution management URLs in related library `strongbox-remote-client_LIB` reveal the internal Nexus repository at `http://d-na-stk01.nam.wirecard.sys:8080/nexus/` — this is likely the repository from which `spring-dbctx` artifacts are published and consumed by Gen-1/Gen-2 services. The `spring-dbctx_LIB` repository's `github-package-publish.yml` publishes to GitHub Packages instead, suggesting a migration of the artifact registry from the legacy Wirecard Nexus to GitHub Packages is in progress or complete.

## Secrets Management

This library contains no secrets and does not manage secrets at runtime. Secrets (database credentials) are managed at the application server JNDI layer in each consuming service's container configuration (Tomcat `server.xml`, JBoss `standalone.xml`). The library deliberately externalises all credential concerns to the runtime environment.

The test variant (`spring-dbctx-mock`) contains an `ExpectedLookupTemplate` that provides mock JNDI responses for unit testing without requiring real database connections; this is a well-structured approach to testing isolation.

## Observability

None — this is a library with no runtime observability of its own. Connection pool metrics (active connections, wait time, pool exhaustion) are exposed through the JNDI DataSource implementation (HikariCP, DBCP, etc.) configured in each consuming application server, not through this library.

## EOL Runtime Concerns

- **Java 21 target**: The library declares Java 21 as compiler source/target, which is the current LTS version — no EOL concern for the runtime
- **Spring Framework XML configuration**: The entire library is Spring XML-based. Spring 6 deprecated the last remnants of XML-driven DataSource configuration in favour of annotation or Java-config based approaches. Services still using this library cannot migrate to Spring 6 without either rewriting to annotation config or maintaining this XML-based library
- **`TransactionAwareDataSourceProxy`**: Available in Spring 6, but the pattern of XML-bean-based DataSource configuration is increasingly unsupported by tooling and documentation
- **JNDI dependency**: Java EE JNDI is not available in Spring Boot embedded server deployments without additional setup; services using this library cannot easily migrate to the Gen-3 pattern of Azure-managed connection strings without replacing this library

## Operational Risk

Because `spring-dbctx` is a shared library included by many services, a regression introduced in a library release could cause widespread database connectivity failures across the platform. There is no visible integration testing that would catch a broken DataSource bean definition before the library is published. The GitHub Actions workflow should include a test step that validates each bean definition can be loaded correctly.
