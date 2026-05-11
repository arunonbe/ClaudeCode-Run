# xfire-utils_LIB — DevOps / Operations View

## Build
- **Build tool**: Maven (Maven Wrapper `mvnw`/`mvnw.cmd`)
- **Java version**: Not specified in root POM; inherited from `module-parent:com.ecount:1`; likely Java 8 or earlier based on framework vintage
- **Packaging**: POM (root); two submodules each producing JAR
  - `xfire-utils-spring` — Spring SOAP client factory
  - `xfire-utils-springjms` — JMS-over-SOAP transport
- **Parent POM**: `com.ecount:module-parent:1`
- **Version**: `1.0.0-SNAPSHOT` (perpetual SNAPSHOT; never released to a stable version in visible history)
- **Key dependencies**:
  - `org.codehaus.xfire:xfire-spring:1.2.4`
  - `org.codehaus.xfire:xfire-jms:1.2.4`
  - `org.codehaus.xfire:xfire-jaxws:1.2.4`
  - `org.springframework:spring:2.0.2`
  - `org.apache.activemq:activemq-core:4.1.0-incubator` (test scope)
  - `geronimo-spec-*` (provided scope — J2EE specs)
- **External Maven repositories**: `people.apache.org/repo/m2-incubating-repository` and `people.apache.org/repo/m2-snapshot-repository` — Apache's historical incubating repository (no longer maintained)

## Deployment
- **CI/CD**: GitHub Actions for CodeQL and Dependabot only (`codeql.yml`, `dependabot.yml`)
- **No deployment workflow** — library consumed as a Maven dependency by other services
- **SCM origin**: SVN (`ecsvn.office.ecount.com/svn/ecount/modules/xfire-utils/trunk`) — originally an SVN project, later migrated to Git
- **Git branch**: `master`
- **No Dockerfile** — library, not a service

## Configuration Management
- **No runtime configuration**: Library behavior configured by consumers via Spring XML bean properties
- **No external properties files**
- **Maven repositories**: References external Apache incubating repositories that may no longer be resolvable (`people.apache.org/repo/m2-incubating-repository` is discontinued)

## Observability
- **Logging**: Apache Commons Logging (`commons-logging`) via XFire; consumers control logging configuration
- **Debug logging** built into `XFireClientFactoryBean`:
  - Logs registered XFire services and transports at INFO level on initialization
  - Logs endpoint resolution (WSDL endpoint found/not found)
  - Logs call details in exception handling
- **No metrics, health checks, or distributed tracing**

## Infrastructure Dependencies
| Dependency | Type | Notes |
|-----------|------|-------|
| `org.codehaus.xfire` (1.2.4) | SOAP framework | EOL; no security updates since 2007 |
| `org.springframework:spring:2.0.2` | Spring IoC | Very old; EOL |
| Apache incubating Maven repo | External repository | `people.apache.org/repo/m2-incubating-repository` — defunct |
| JMS provider | Runtime (consumers) | TIBCO, WebLogic, or ActiveMQ depending on consumer config |

## Operational Risks
1. **SNAPSHOT version forever**: `1.0.0-SNAPSHOT` means builds are non-deterministic; consumers may receive a different artifact
2. **Defunct Maven repository**: `people.apache.org/repo/m2-incubating-repository` is no longer maintained; builds may fail if `activemq-core:4.1.0-incubator` is not cached locally
3. **XFire 1.2.4 EOL**: No security patches; any CVE discovered affects all consumers
4. **Spring 2.0.2 EOL**: Oldest Spring version in this set of repos; no security patches
5. **No CI deployment pipeline**: Library is built and deployed only when manually triggered or when consuming services build
6. **SVN origin artifacts**: Some transitive dependencies may only exist in old SVN-backed Maven repositories; reproducibility risk

## CI/CD Pipeline
```
No deployment pipeline defined.

GitHub Actions (supplemental only):
  → codeql.yml: CodeQL security analysis on push/PR to master
  → dependabot.yml: Automated dependency update PRs

Library is consumed as:
  → Maven JAR dependency by other services in the ecount/Onbe platform
```
