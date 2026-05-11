# security-audit-common_LIB — DevOps / Operations View

## Build System
- Maven with Maven Wrapper; Java 21 target (`maven.compiler.source=21`, `maven.compiler.target=21`).
- Parent POM: `com.parents:prepaid-parent:6.0.13`.
- Artefact: `com.citi.prepaid.audit:security-audit-common:6.1.8-SNAPSHOT`.
- Produces JAR via `maven-jar-plugin`.
- `maven-enforcer-plugin` enforces no transitive dependencies except Spring/Spring Boot.
- Dependencies: `spring-context`, `spring-jdbc`, `jakarta.servlet-api` (Tomcat 10+), `net.sourceforge.jtds:jtds` (SQL Server JDBC), `junit` (test), Lombok (`@Slf4j`).

## CI/CD Pipelines
| Workflow | Trigger | Runner | Purpose |
|---|---|---|---|
| `nexus-deploy.yml` | Push/PR to main/master/rp_master; workflow_dispatch | `self-hosted, X64, Linux, ubuntu-docker` | Build and publish to Nexus |
| `github-package-publish.yml` | Push to main, PR to main; workflow_dispatch | Delegates to `Onbe/om-ci-setup` reusable workflow | Publish to GitHub Packages |
| `codeql.yml` | Weekly Tue 12:30 UTC; workflow_dispatch | Delegates to `Onbe/om-ci-setup` reusable workflow | CodeQL SAST |

All CI workflows use `settings.xml` via `-s ./.mvn/wrapper/settings.xml` and pass `aether.connector.https.securityMode=insecure` (TLS disabled for artifact resolution). Tests are skipped in all pipeline invocations (`-D maven.test.skip`).

## Config Management
- Spring XML context file `securityAudit-context.xml` wires `SecurityAuditClientHelper`, `SecurityDataLoggerImpl`, and `SecurityDataDAOImpl` with `CbaseappDataSource` (JNDI reference — provided by consuming application container).
- No Spring Boot auto-configuration — pure Spring Framework library.
- PMD configuration committed (`.pmd`) with 180+ rules including security rules (`HardCodedCryptoKey`, `InsecureCryptoIv`, `ApexBadCrypto`).

## Observability
- Logging via Lombok `@Slf4j` in `SecurityDataLoggerImpl`.
- `log4j2-test.xml` in test resources for test-time logging.
- Metrics: none.
- Distributed tracing: none.
- Events written to database with timestamp; no SIEM/CEF forwarding implemented (stub only).

## Infrastructure Dependencies
| Dependency | Notes |
|---|---|
| SQL Server (`CbaseappDataSource`) | JNDI DataSource injected by application container; jTDS driver |
| Tomcat 10.x | Servlet container (jakarta.servlet-api provided scope) |
| Nexus `d-na-stk01.nam.wirecard.sys:8081` | Legacy Wirecard artifact proxy (may be decommissioned) |
| GitHub Packages `onbe/onbe_maven_releases` | Onbe Maven registry |
| `Onbe/om-ci-setup` | Centralised CI reusable workflows |

## Operational Risks
- Tests skipped in all pipelines — no regression protection on library changes.
- `aether.connector.https.securityMode=insecure` in CI pipelines disables TLS validation.
- The VBScript data extract (`citiCPSSecurityAuditDataExtract.vbs`) is embedded in the Java source tree (`src/main/java/com/citi/prepaid/audit/`) — an unusual location indicating it may not be deployed consistently. It reads SQL Server credentials from a local INI file and passes them as BCP command-line arguments.
- `enforcer.skip` flag passed in Nexus deploy — bypasses dependency enforcement on deployment builds.

## VBScript Export Operational Notes
- Reads config from `D:\C-Base\runtime\ndmroot\{USER}\program\importconfig.ini`.
- Executes BCP against two CSI IDs: 158929 (OnePlatform), 159547 (ClientZone).
- Output files written to `DATAFOLDER\upload\SecurityAuditData\{csi}\`.
- SQL credentials passed in BCP command: `-U {CBASE_USER} -P {CBASE_PASSWORD}` — visible in process list to other OS users.
