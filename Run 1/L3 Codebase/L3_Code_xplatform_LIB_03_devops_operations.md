# DevOps / Operations View — xplatform_LIB

## Build System
- **Language / Framework:** Java 21, Maven
- **Parent POM:** `com.parents:prepaid-parent:6.0.13`
- **Artifact:** `com.ecount:xplatform:6.5.9-SNAPSHOT` (JAR)
- **Compiler target/source:** Java 21
- **Build command:** `mvn clean install -Dmaven.test.skip`
- **Plugins:** `maven-jar-plugin`, `jacoco-maven-plugin` (0.8.12), `maven-enforcer-plugin` (bans transitive dependencies with an approved exclusion list)
- **Source encoding:** Not explicitly set (inherits from parent POM)
- **Test framework:** JUnit 4 (test scope), EasyMock (test scope)

## Deployment
- **Deployment model:** Published as a JAR to a Maven repository; consumed as a compile-time dependency by downstream services
- **Not directly deployed** — this is a library, not a runnable service
- **Required at runtime by:** xsso_SVC (version 6.1.8), xsearch_LIB (version 6.0.1), and expected to be consumed by many other platform services
- **Runtime containers:** Tomcat 10.x (as stated in README); Jakarta EE 10 servlet API

## Configuration Management
- Externalised configuration loaded from `${CBASE_HOME_URL}/config/` at runtime (path convention from `xplatformlibrary`)
- JNDI DataSources (`jdbc/JobSvcDataSource`, etc.) — managed by the container (Tomcat)
- Azure AD configuration (`msal4j`) — credentials/tenant config expected to be externalised
- No in-repo secrets detected

## Observability
- Logging via SLF4J / Lombok `@Slf4j` annotations in newer classes; older classes may use custom eCount logging from `xplatformlibrary`
- JaCoCo configured for test coverage reporting (`report` phase)
- No distributed tracing, no metrics export, no health endpoint (library, not service)

## Infrastructure Dependencies
| Dependency | Version | Notes |
|---|---|---|
| xplatformlibrary | 4.2.0 | Foundation library (cache, crypto, config, logging) |
| cbtsclient (Wirecard CBTS) | 2.1.5 | Cross-border transfer RPC client |
| XStream | Managed by parent | XML serialisation |
| Hibernate Core | Managed by parent | ORM |
| commons-lang | Managed by parent | String/object utilities |
| msal4j (Microsoft Azure) | Managed by parent | Azure AD authentication |
| spring-jdbc | Managed by parent | JDBC template |
| jakarta.xml.bind-api | Managed by parent | JAXB |
| javalite-common | Managed by parent | Lightweight utilities |
| org.json | Managed by parent | JSON parsing |

## Operational Risks
- **SNAPSHOT version (`6.5.9-SNAPSHOT`)** in active development — consuming services that pin to SNAPSHOT may pick up breaking changes on each build
- **cbtsclient 2.1.5 (Wirecard heritage)** — support and security patch availability are uncertain post-acquisition; this is a critical dependency for cross-border functionality
- **SwarmCache (JGroups multicast)** — cache coherence relies on multicast networking; misconfigured network segments could cause stale data or split-brain scenarios
- **No dedicated health endpoint** — downstream services cannot query this library's readiness independently
- **Enforcer plugin** bans transitive dependencies with a long exclusion list — any addition of a new direct dependency requires explicit approval, which is a positive control but creates onboarding friction

## CI/CD
- No GitHub Actions workflow files detected in this repository
- Build is Maven-based; expected to be integrated into the central `om-ci-setup` workflow used by other repos in the organisation
- JaCoCo coverage reports generated at test phase — but `maven.test.skip` is the documented build command, suggesting tests are routinely skipped
