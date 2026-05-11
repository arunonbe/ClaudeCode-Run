# DevOps / Operations View — xsearch_LIB

## Build System
- **Language / Framework:** Java 21, Maven
- **Parent POM:** `com.parents:prepaid-parent:6.0.12`
- **Artifact:** `com.ecount.service.xsearch:xsearch:2.0.1` (JAR)
- **Compiler target/source:** Java 21
- **Build command:** `mvn clean install -Dmaven.test.skip`
- **Plugins:** `maven-jar-plugin`, `maven-enforcer-plugin`
- **Test scope dependencies:** `spring-dbctx-mock` (2.0.1), `mssql-jdbc`, `jtds`
- **No JaCoCo configured**

## Deployment
- **Deployment model:** Published as a JAR; consumed as a compile-time dependency
- **Not directly deployed** — library used by xsearch-new_SVC and other search-dependent services
- **Runtime environment:** Embedded in a web application (WAR); Tomcat 10.x
- **DataSources at runtime:** Injected as Spring beans from JNDI or application context configuration

## Configuration Management
- Spring XML application context (`search.xml`) wires together DAOs, managers, and data sources
- Data source names (`EcountCoreDataSource`, `CbaseappDataSource`, `WebCertOmahaDataSource`, `JobSvcDataSource`) are resolved from the application context — configuration lives in the consuming service
- No in-repo secrets

## Observability
- Logging via Apache Commons Logging (`LogFactory.getLog(...)`) — bridges to the platform logging infrastructure
- Most debug log calls in `SearchServiceImpl` are commented out — significantly reduced search observability
- No metrics, no health endpoint, no distributed tracing
- No search audit logging

## Infrastructure Dependencies
| Dependency | Notes |
|---|---|
| xplatform (`com.ecount:xplatform:6.0.1`) | Business logic and domain objects |
| spring-context | Spring IoC |
| XStream | XML serialisation |
| SQL Server (x4) | EcountCoreDataSource, CbaseappDataSource, WebCertOmahaDataSource, JobSvcDataSource |

## Operational Risks
- **Four separate database connections:** Operationally complex; each database requires independent connection pool management, failover configuration, and credential rotation
- **Debug logging commented out:** Reduces observability; incidents involving incorrect search results are difficult to diagnose
- **No search audit log:** Impossible to reconstruct what data was accessed, by whom, or when — operational and compliance risk
- **`spring-dbctx-mock` in test scope:** The `com.citi.prepaid.spring-dbctx:spring-dbctx-mock` test dependency suggests tests use a mock data context — integration test fidelity against real databases may be limited
- **`maven.test.skip` default:** Tests are routinely skipped; regression for data-access logic is not enforced

## CI/CD
- No GitHub Actions workflows in this repository
- Expected integration with `om-ci-setup` Maven workflow
- Version `2.0.1` is a release (not SNAPSHOT) — version stability is better than xplatform_LIB
- No evidence of automated SAST or dependency scanning in this repo
