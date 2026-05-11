# DevOps / Operations Analysis: repository_LIB

## Build System
- **Maven** multi-module project (mvnw wrapper present)
- **Java**: Source/target **21** (maven.compiler.source/target = 21)
- **Parent POM**: `com.parents:prepaid-parent:6.0.12`
- **Artifact**: `com.citi.prepaid.service.repository:repository:3.0.1` (pom packaging — aggregator)
- **Modules**: repository-common, repository-impl, repository-xmlrpc, repository-client
- No Docker, no Kubernetes manifests in this library repo.

## Module Build Outputs
| Module | Artifact | Purpose |
|---|---|---|
| repository-common | repository-common-3.0.1.jar | Interfaces, TOs, comparators, utilities |
| repository-impl | repository-impl-3.0.1.jar | Hibernate DAOs, manager implementations |
| repository-xmlrpc | repository-xmlrpc-3.0.1.jar | XML-RPC proxy for the remote report service |
| repository-client | repository-client-3.0.1.jar | XML-RPC client for remote repository service |

## Deployment
This is a **library** — it is not deployed as a standalone service. It is included as a Maven dependency in consuming applications (e.g., client zone webapp, repository-service_SVC). Deployment is via Maven repository artifact publication.

No deployment pipeline configuration exists in this repo.

## Configuration Management
- Library behaviour is configured at runtime by the consuming application via Spring injection.
- `repositoryContext.xml` (in repository-impl resources) wires the Spring beans: `repositoryManager`, `reportManager`, DAO beans, and transaction manager.
- The Hibernate session factory (`sessionFactory`) is expected to be provided by the consuming application's Spring context (via `spring-dbctx-container`).
- No environment-specific configuration within the library itself.

## Observability
- Logging via **SLF4J + Lombok @Slf4j** (in repository-impl DAOs) — modern pattern compared to the webapp.
- No metrics or tracing instrumentation within the library.
- DAO-level debug logging for query results is present (`log.debug("get reports by name successful...")`).

## Infrastructure Dependencies
| Dependency | Type | Notes |
|---|---|---|
| SQL Server | Database | For report/report-category/program-report tables; connection managed by consuming app |
| Hibernate 5 | ORM | Session factory injected by container |
| `spring-dbctx-container:2.0.1` | Internal library | Manages Spring DB context/datasource |
| `springutils-generic:3.0.2` | Internal library | Utility layer |
| `xplatformlibrary:4.0.1` | Internal library | eCount platform utilities |
| `xplatform:6.0.1` | Internal library | eCount platform core |
| Repository Service (XML-RPC) | Remote service | Required for file operations via repository-client |

## Operational Risks
1. **Library versioning**: At version 3.0.1; multiple consumers depend on this — breaking changes require coordinated upgrades across all consuming services.
2. **Hibernate 5 + Java 21**: Hibernate 5 support for Java 21 may have compatibility issues; Hibernate 6 is the current generation.
3. **XML-RPC dependency** in repository-client: XML-RPC is an archaic protocol; the client relies on the `xmlrpc:3.1.4` library.
4. **No integration tests in CI**: Test classes exist (`ReportDAOTest`, etc.) but require a live SQL Server instance; no evidence of containerised test setup.
5. **Commented-out Hibernate configuration** in `repositoryContext.xml` (lines 58-103): Old Hibernate 3 config is commented out in-line, indicating configuration drift over time.

## CI/CD
No pipeline configuration present in this library repository. Publication to Maven repository is assumed to be done via `mvn deploy` in an external CI system (Jenkins/GitLab CI).
