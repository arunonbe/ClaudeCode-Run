# DevOps & Operations Report: strongbox-xmlrpc_SVC

## Build System

- **Build tool**: Apache Maven (wrapper in `.mvn/wrapper/`)
- **Parent POM**: `com.parents:prepaid-parent:6.0.12` (shared corporate parent, same as scheduler_WAPP)
- **Java version**: 21 (compiler source/target in root `pom.xml`)
- **Module structure**: Five sub-modules
  - `strong-box-common`: Interfaces and output DTOs (`ICryptoService`, `IStrongBox`, input/output objects)
  - `strong-box-client`: XML-RPC client implementations for remote invocation
  - `strong-box-impl`: Core implementation (`RepositoryService`, `CryptoService`, all DAOs)
  - `strong-box-xmlrpc`: XML-RPC service endpoint wiring (not in visible file list but in POM module list)
  - `strongbox-monitor`: Monitoring/health component
- **Key dependencies**: `xmlrpc:3.0.2`, `ecount-system:4.0.2`, `jakarta.servlet-api:6.0.0`, `director-client:2.0.1`

## CI/CD Pipeline

Four GitHub Actions workflows are defined:

1. **`deployment.yml`**: Uses shared `Onbe/om-ci-setup` reusable workflow, pushes on main branch; `APP_NAME: StrongBoxSVC`
2. **`redeploy.yaml`**: Manual redeploy
3. **`github-package-publish.yml`**: Publishes to GitHub Packages
4. **`codeql.yml`**: GitHub CodeQL security scanning

Additionally, a `.gitlab-ci.yml` is present — StrongBox predates the move to GitHub Actions and has a legacy GitLab CI pipeline, suggesting it was originally developed on the Wirecard/Northlane GitLab instance. This dual-pipeline situation means changes could theoretically be processed by either system.

## Deployment Model

- **Runtime**: Jakarta EE servlet container (WAR deployment); Jakarta Servlet 6.0 API dependency suggests Tomcat 10.x target
- **Containerisation**: `Dockerfile` is referenced in the GitHub Actions deployment workflow; a `Dockerfile` exists in the repo (`.trivyignore` and `.github/containerscan/allowedlist.yaml` confirm Trivy container scanning is in use)
- **Port**: HTTP on port 80 (default for Tomcat in Docker), consistent with other services in this batch
- **External binary dependency**: PGP operations require an external PGP binary to be installed in the Docker container; the Dockerfile must include PGP binary installation

The `service.default.properties` file in `strong-box-common` sets:
```
service.strongbox.url=http://ecappdev:8080/strong-box-xmlrpc/invoker/Strongbox
```
The `ecappdev` hostname and port 8080 suggest this is the QA/dev endpoint. The production endpoint configuration must be overridden at deployment time. The HTTP scheme (not HTTPS) is a critical finding for the production deployment.

## Secrets Management

StrongBox is the secrets management system for the rest of the platform, so its own secrets management is particularly important:

- The StrongBox service needs database credentials for the `strongbox` SQL Server database
- These credentials should be injected via JNDI (consistent with `spring-dbctx_LIB` patterns) or environment variables
- No `.env` file is present in this repository (unlike `scheduler_WAPP`); this is positive — credentials are not committed to source control
- How the StrongBox database credentials are managed at deployment time is not visible from the repository; this should be verified against the ECS/Kubernetes secret configuration

**Critical runtime risk**: The `encryptFolderPath` and `decryptFolderPath` properties in `CryptoService` determine where temporary PGP files are written. These paths must be:
1. Writable by the container process
2. Not accessible to other container processes
3. On ephemeral storage (not a persistent volume that might outlive the container)
4. Securely wiped on container restart

## Observability

- **Trivy container scanning**: `.trivyignore` and `allowedlist.yaml` confirm Trivy is used in CI for container vulnerability scanning
- **CodeQL**: Static analysis enabled
- **`strongbox-monitor` module**: A monitoring module exists; implementation not visible in available file listing
- **SLF4J + Lombok `@Slf4j`**: Standard logging in implementation classes; `LoggingUtils` class suggests custom logging utilities
- **Service URL health**: The default properties include a `connect.timeoutMillis=5000` and `read.timeoutMillis=30000` for client connections to the service, but no health check endpoint is visible in the server implementation

## EOL Runtimes and CVE Concerns

- **Java 21**: No EOL concern
- **Apache XML-RPC 3.0.2**: Apache XML-RPC 3.x was released circa 2008 and has had no maintenance releases since approximately 2010. It uses Apache HttpClient 3.x for transport, which has multiple known CVEs including connection pooling and SSL handling issues. XML-RPC 3.0.2 predates modern TLS versions and may not support TLS 1.2 or 1.3 without configuration overrides
- **External PGP binary**: The PGP binary version and CVE status depends on what is installed in the Docker image; if GnuPG is used, it should be a current maintained version
- **`ecount-system:4.0.2`**: Internal eCount system library; version status unknown, may contain outdated dependencies
- **Java serialisation**: The XML-RPC library performs Java object serialisation/deserialisation; class-level filtering (JEP 415, `ObjectInputFilter`) is not visible in the codebase
