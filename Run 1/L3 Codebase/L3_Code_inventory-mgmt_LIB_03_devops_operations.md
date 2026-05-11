# DevOps / Operations View — inventory-mgmt_LIB

## Build
- **Build system**: Maven, single-module JAR.
- **Maven wrapper**: `mvnw` / `mvnw.cmd` present.
- **Parent POM**: `com.parents:prepaid-parent:6.0.12`.
- **Java version**: Java 21 (`maven.compiler.source/target: 21`).
- **Output**: `inventory-mgmt-2.0.2-SNAPSHOT.jar`.
- **Enforcer plugin**: `banTransitiveDependencies` enforced (with explicit exclusions) — dependency hygiene control.
- **Maven settings**: `.mvn/wrapper/settings.xml` references internal Nexus.

## Deployment
- **Deployment model**: JAR library published to internal Nexus via GitHub Package publish workflow (`.github/workflows/github-package-publish.yml`).
- Not deployed independently; consumed by inventory-mgmt-batch-client and ClientZone web applications.

## Configuration Management
- No application configuration in this library — all configuration (data source, file paths, feature flags) is injected by the consuming application via Spring setter injection.
- `isCardExpiryEnable` and `isAutoReorderEnable` flags are injected via Spring XML in consuming apps.
- `filePath` for XML request file generation is injected by consuming Spring contexts.

## Observability
- Logging via SLF4J with Lombok `@Slf4j` annotation.
- DEBUG-level logging of ecountIds, PUIDs, and program IDs in InventoryManagementManagerImpl.
- No metrics or health check endpoints (library, not service).
- File operation timings logged at INFO level (upload start/end times in seconds).

## Infrastructure Dependencies
| Dependency | Type | Notes |
|-----------|------|-------|
| JobSvc SQL Server | Database | Via Director-configured DBCP |
| ecountCore SQL Server | Database | Via Director-configured DBCP |
| cbaseapp SQL Server | Database | Via Director-configured DBCP |
| Director service registry | Service discovery | Resolves service endpoints and DB connections |
| Repository Service | XML-RPC service | File upload for reorder request files |
| Filesystem (filePath) | Local/NAS | XML request file staging area |
| xSecurity / xplatform | Internal frameworks | Spring XML-configured beans |

## Operational Risks
1. Dependency on Struts (`struts:struts`) included in the dependency tree — Struts has well-known critical CVE history; its presence must be justified.
2. `filePath` is a local or network filesystem path for XML file staging — if the path is unavailable, reorder operations fail silently or with RuntimeException.
3. Repository Service call is synchronous; a slow or unavailable Repository Service will block the batch thread for the duration of the XML-RPC timeout.
4. Large numbers of stored procedure inner classes reduce maintainability but do not add runtime risk.
5. The `check.log` file in the repository (`change.log`) should be reviewed for any operational history.

## CI/CD
- **GitHub Actions**: `.github/workflows/github-package-publish.yml` — publishes JAR to GitHub Packages.
- **GitHub Actions**: `.github/workflows/codeql.yml` — CodeQL security analysis.
- **Dependabot**: `.github/dependabot.yml`.
- No Jenkins pipeline in this repo.
- Default branch is `main`.
