# DevOps / Operations View — xaffiliate-service_LIB

## Build System

- **Build tool**: Maven with Maven Wrapper (`mvnw`, `mvnw.cmd`)
- **Java version**: Java 21 (`maven.compiler.target=21`, `maven.compiler.source=21`)
- **Parent POM**: `com.parents:prepaid-parent:6.0.12` (direct inheritance; bypasses `service-parent`)
- **Version**: `4.0.1` (stable release, not SNAPSHOT — good practice for a shared library)
- **Packaging**: JAR library (`<packaging>jar</packaging>`)
- **Key dependencies**:
  - `org.springframework:spring-core/spring-orm/spring-context/spring-jdbc` — version managed by prepaid-parent (likely Spring 5.x or 6.x)
  - `org.hibernate.orm:hibernate-core` — version managed by prepaid-parent (Hibernate 6.x for Java 21 compatibility)
  - `commons-lang:commons-lang` — version managed by parent
  - `com.microsoft.sqlserver:mssql-jdbc` — test scope only (integration tests)
- **Enforcer**: `banTransitiveDependencies` with exclusions for Spring, Spring Boot, and Hibernate — enforces explicit dependency declaration
- **Build**: `maven-jar-plugin` for JAR packaging; no SBOM plugin observed in this POM (may be inherited from parent)

## CI/CD Pipeline

- **GitHub Actions**:
  - `.github/workflows/codeql.yml` — CodeQL static analysis (Java)
  - `.github/workflows/github-package-publish.yml` — publishes JAR to GitHub Packages Maven registry
- **GitLab CI**: `.gitlab-ci.yml` present — migration from GitLab to GitHub Actions is in progress; dual pipelines
- **Dependabot**: `.github/dependabot.yml` — automated dependency update PRs
- **No deployment workflow**: Library artifact published to GitHub Packages; no standalone deployment pipeline

## Deployment Model

- **Artifact type**: JAR library published to GitHub Packages Maven registry
- **Consumers**: OnePlatform web application (`oneplatform_WAPP`, `oneplatform-react_WAPP`), `csa_WAPP`, `bmcwizard_WAPP`, and other client zone applications that need affiliate configuration
- **Docker Compose**: `docker-compose.yml` and `entrypoint.sh` in repository root indicate a Docker-based local development environment with SQL Server for integration testing

## Runtime

- **Java 21** (compiled and targeted)
- **Hibernate ORM** (version from prepaid-parent; Hibernate 6.x for Java 21)
- **Spring** (Spring 6.x for Jakarta EE compatibility, or Spring 5.x — version from prepaid-parent)
- **SQL Server** (Microsoft JDBC driver for test scope; DataSource provided by consuming application at runtime)
- **No Spring Boot**: Library only; no embedded application server

## Secrets Management

- No secrets managed by this library; DataSource and session factory injection are externalized to consuming application context
- `docker-compose.yml` for local development may contain SQL Server credentials — must be verified to use synthetic/local credentials only, not real credentials
- MSSQL JDBC driver in test scope is used for integration testing against a local Docker SQL Server instance; real database credentials must not be committed

## Observability

- **Logging**: SLF4J (`@Slf4j` via Lombok in `AffiliateServiceImpl`) — log output routed via consuming application's logging configuration
- **Transaction management**: `@Transactional("affiliateTransactionManager")` on all service methods; transaction monitoring depends on the consuming application's transaction infrastructure
- **No standalone health endpoint**: Library has no Actuator integration; health is inferred from the consuming application
- **Debug logging**: Multiple `log.info()` statements in `AffiliateServiceImpl` log operational details (e.g., "Loading Locale Copy for Skin ID...", "STARTED:", "FINISHED:", timing information); these are appropriate for operational visibility but must be verified to not include sensitive data

## Known EOL Runtimes and CVEs

- **`4.0.1` stable version**: Positive indicator — stable release, not SNAPSHOT
- **Dual CI pipelines** (GitLab + GitHub Actions): Must synchronize or deactivate GitLab CI once GitHub Actions migration is complete to avoid conflicting artifact publications
- **`docker-compose.yml` with SQL Server**: The Docker Compose setup for integration testing is a good practice; however, SQL Server image version and security configuration must be reviewed to ensure test environment credentials are isolated from production
- **`AffiliateServiceImplOld.java`**: Dead code file increases the code analysis surface; should be removed to reduce false positives in CodeQL scans and maintainability burden
- **Exception handling**: Multiple `e.printStackTrace()` calls in `AffiliateServiceImpl` bypass the logging framework; in container environments (Docker), `System.err` may not be captured by the log aggregator, causing errors to be silently dropped. These must be replaced with `log.error("message", e)` calls.
- **Java 21 with Hibernate 6.x**: Confirm that Hibernate's use of `SessionFactory.getCurrentSession()` (the pattern used throughout) is compatible with the Hibernate 6.x context management approach; some session management APIs changed in Hibernate 6.
- **`change.log` file**: Present in repo root — may contain version history useful for understanding upgrade history; not a risk.
